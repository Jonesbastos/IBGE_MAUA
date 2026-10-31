"""Testes de integração do orquestrador principal do pipeline (main.py)."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from desafio_ibge.config.settings import MAUA_IBGE_CODE
from desafio_ibge.extraction.ibge_client import (
    IBGEClient,
    IBGEExtractionError,
)
from desafio_ibge.loading.storage import (
    IBGEStorageError,
    get_db_connection,
    read_bronze,
    read_gold_hierarquia,
    read_silver,
)
from desafio_ibge.main import main, run_pipeline


@pytest.fixture
def test_pipeline_db(tmp_path: Path) -> Path:
    """Cria um caminho temporário para o banco SQLite do teste de pipeline."""
    return tmp_path / "integration_pipeline.db"


@pytest.fixture
def mock_client(maua_raw_payload: dict[str, Any]) -> MagicMock:
    """Retorna um mock de IBGEClient configurado para fornecer Mauá."""
    client = MagicMock(spec=IBGEClient)
    client.fetch_municipio_by_id.return_value = maua_raw_payload
    return client


# ---------------------------------------------------------------------------
# Testes do Fluxo Principal (Caminho Feliz & Idempotência)
# ---------------------------------------------------------------------------


def test_run_pipeline_end_to_end_success(
    test_pipeline_db: Path,
    mock_client: MagicMock,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa a execução sequencial completa do pipeline com código de saída 0."""
    exit_code = run_pipeline(db_path=test_pipeline_db, client=mock_client)
    assert exit_code == 0

    # 1. Verifica se a chamada de extração ocorreu com o código de Mauá
    mock_client.fetch_municipio_by_id.assert_called_once_with(MAUA_IBGE_CODE)

    # 2. Valida persistência na Camada Bronze
    bronze_data = read_bronze(MAUA_IBGE_CODE, db_path=test_pipeline_db)
    assert bronze_data is not None
    assert bronze_data["id"] == MAUA_IBGE_CODE
    assert bronze_data["nome"] == "Mauá"

    # 3. Valida persistência na Camada Silver
    df_silver = read_silver(MAUA_IBGE_CODE, db_path=test_pipeline_db)
    assert not df_silver.empty
    assert len(df_silver) == 1
    assert df_silver.iloc[0]["id"] == MAUA_IBGE_CODE
    assert df_silver.iloc[0]["nome"] == "Mauá"
    assert "transformed_at" in df_silver.columns

    # 4. Valida sincronização na Camada Gold
    df_gold = read_gold_hierarquia(
        MAUA_IBGE_CODE,
        db_path=test_pipeline_db,
    )
    assert not df_gold.empty
    assert len(df_gold) == 1
    assert df_gold.iloc[0]["municipio_id"] == MAUA_IBGE_CODE
    assert df_gold.iloc[0]["uf_sigla"] == "SP"
    assert df_gold.iloc[0]["regiao_nome"] == "Sudeste"


def test_run_pipeline_idempotency_multiple_runs(
    test_pipeline_db: Path,
    mock_client: MagicMock,
) -> None:
    """Garante que rodar o pipeline duas vezes mantém idempotência e unicidade."""
    # Primeira execução
    code_1 = run_pipeline(db_path=test_pipeline_db, client=mock_client)
    assert code_1 == 0

    # Segunda execução sobre o mesmo banco
    code_2 = run_pipeline(db_path=test_pipeline_db, client=mock_client)
    assert code_2 == 0

    # Valida contagens unitárias no SQLite
    conn = get_db_connection(test_pipeline_db)
    try:
        cur_b = conn.execute("SELECT COUNT(*) AS total FROM bronze_ibge_raw;")
        assert cur_b.fetchone()["total"] == 1

        cur_s = conn.execute("SELECT COUNT(*) AS total FROM silver_municipio;")
        assert cur_s.fetchone()["total"] == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Testes de Tratamento de Falhas e Interrupção (Fail-Fast)
# ---------------------------------------------------------------------------


def test_run_pipeline_fails_on_extraction_error(test_pipeline_db: Path) -> None:
    """Verifica que erro na extração interrompe o fluxo e retorna código 1."""
    failing_client = MagicMock(spec=IBGEClient)
    failing_client.fetch_municipio_by_id.side_effect = IBGEExtractionError(
        "Erro de timeout simulado"
    )

    exit_code = run_pipeline(db_path=test_pipeline_db, client=failing_client)
    assert exit_code == 1

    # Nenhuma camada posterior deve ter registros
    conn = get_db_connection(test_pipeline_db)
    try:
        cur_b = conn.execute("SELECT COUNT(*) AS total FROM bronze_ibge_raw;")
        assert cur_b.fetchone()["total"] == 0

        cur_s = conn.execute("SELECT COUNT(*) AS total FROM silver_municipio;")
        assert cur_s.fetchone()["total"] == 0
    finally:
        conn.close()


def test_run_pipeline_fails_on_validation_error(test_pipeline_db: Path) -> None:
    """Verifica que dados com schema inválido abortam antes da carga."""
    invalid_client = MagicMock(spec=IBGEClient)
    # Payload sem o ID de Mauá e com dados corrompidos
    invalid_client.fetch_municipio_by_id.return_value = {
        "id": 9999999,
        "nome": "Invalido",
    }

    exit_code = run_pipeline(db_path=test_pipeline_db, client=invalid_client)
    assert exit_code == 1

    # Confirma que camadas subsequentes não receberam dados corrompidos
    conn = get_db_connection(test_pipeline_db)
    try:
        cur_b = conn.execute("SELECT COUNT(*) AS total FROM bronze_ibge_raw;")
        assert cur_b.fetchone()["total"] == 0

        cur_s = conn.execute("SELECT COUNT(*) AS total FROM silver_municipio;")
        assert cur_s.fetchone()["total"] == 0
    finally:
        conn.close()


def test_run_pipeline_fails_on_bronze_storage_error(
    test_pipeline_db: Path,
    mock_client: MagicMock,
) -> None:
    """Verifica interrupção quando a persistência na Bronze falha."""
    with patch(
        "desafio_ibge.main.save_bronze",
        side_effect=IBGEStorageError("Falha de gravação simulada no disco"),
    ):
        exit_code = run_pipeline(db_path=test_pipeline_db, client=mock_client)
        assert exit_code == 1

    # Camada Silver não deve ter sido executada
    conn = get_db_connection(test_pipeline_db)
    try:
        cur_s = conn.execute("SELECT COUNT(*) AS total FROM silver_municipio;")
        assert cur_s.fetchone()["total"] == 0
    finally:
        conn.close()


def test_run_pipeline_fails_on_silver_storage_error(
    test_pipeline_db: Path,
    mock_client: MagicMock,
) -> None:
    """Verifica interrupção quando a persistência na Silver falha."""
    with patch(
        "desafio_ibge.main.save_silver",
        side_effect=IBGEStorageError("Falha de I/O na tabela Silver"),
    ):
        exit_code = run_pipeline(db_path=test_pipeline_db, client=mock_client)
        assert exit_code == 1


def test_run_pipeline_fails_on_db_init_exception(tmp_path: Path) -> None:
    """Verifica tratamento de falha na inicialização do schema do banco."""
    with patch(
        "desafio_ibge.main.init_db",
        side_effect=RuntimeError("Permissão negada no banco"),
    ):
        exit_code = run_pipeline(db_path=tmp_path / "bad.db")
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Testes do Ponto de Entrada CLI (main)
# ---------------------------------------------------------------------------


def test_main_cli_exit_code_success() -> None:
    """Testa que main() chama sys.exit(0) quando o pipeline é bem-sucedido."""
    with patch("desafio_ibge.main.run_pipeline", return_value=0):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_main_cli_exit_code_failure() -> None:
    """Testa que main() chama sys.exit(1) quando o pipeline falha."""
    with patch("desafio_ibge.main.run_pipeline", return_value=1):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
