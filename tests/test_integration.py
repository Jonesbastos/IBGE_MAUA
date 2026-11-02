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
    read_gold_demografia_sexo,
    read_gold_hierarquia,
    read_gold_pib_historico,
    read_gold_populacao_historica,
    read_gold_resumo_socioeconomico,
    read_silver,
    read_silver_censitario,
    read_silver_pib,
    read_silver_populacao,
)
from desafio_ibge.main import main, run_pipeline


@pytest.fixture
def test_pipeline_db(tmp_path: Path) -> Path:
    """Cria um caminho temporário para o banco SQLite do teste de pipeline."""
    return tmp_path / "integration_pipeline.db"


@pytest.fixture
def mock_socioeconomico_payload() -> dict[str, dict[str, Any]]:
    """Gera payload mock completo e válido para os 5 indicadores socioeconômicos."""
    return {
        "censo_pop_area_densidade": {
            "municipio_id": MAUA_IBGE_CODE,
            "indicador": "censo_pop_area_densidade",
            "periodo_referencia": "2022",
            "fonte_oficial": "IBGE - Censo 2022",
            "endpoint_url": "https://api.ibge.gov.br/4714",
            "payload": [
                {
                    "id": "93",
                    "variavel": "População residente",
                    "unidade": "Pessoas",
                    "resultados": [
                        {
                            "series": [
                                {
                                    "localidade": {"id": str(MAUA_IBGE_CODE)},
                                    "serie": {"2022": "418261"},
                                }
                            ]
                        }
                    ],
                },
                {
                    "id": "6318",
                    "variavel": "Área territorial",
                    "unidade": "km²",
                    "resultados": [
                        {
                            "series": [
                                {
                                    "localidade": {"id": str(MAUA_IBGE_CODE)},
                                    "serie": {"2022": "61.937"},
                                }
                            ]
                        }
                    ],
                },
                {
                    "id": "614",
                    "variavel": "Densidade demográfica",
                    "unidade": "hab/km²",
                    "resultados": [
                        {
                            "series": [
                                {
                                    "localidade": {"id": str(MAUA_IBGE_CODE)},
                                    "serie": {"2022": "6753.01"},
                                }
                            ]
                        }
                    ],
                },
            ],
            "http_status": 200,
        },
        "populacao_estimada_historica": {
            "municipio_id": MAUA_IBGE_CODE,
            "indicador": "populacao_estimada_historica",
            "periodo_referencia": "2001-2026",
            "fonte_oficial": "IBGE - Estimativas",
            "endpoint_url": "https://api.ibge.gov.br/6579",
            "payload": [
                {
                    "id": "9324",
                    "variavel": "População residente estimada",
                    "unidade": "Pessoas",
                    "resultados": [
                        {
                            "series": [
                                {
                                    "localidade": {"id": str(MAUA_IBGE_CODE)},
                                    "serie": {
                                        "2020": "415000",
                                        "2021": "418000",
                                    },
                                }
                            ]
                        }
                    ],
                }
            ],
            "http_status": 200,
        },
        "pib_municipal_historico": {
            "municipio_id": MAUA_IBGE_CODE,
            "indicador": "pib_municipal_historico",
            "periodo_referencia": "2002-2023",
            "fonte_oficial": "IBGE - PIB",
            "endpoint_url": "https://api.ibge.gov.br/pib",
            "payload": [
                {
                    "id": 46997,
                    "indicador": "Produto Interno Bruto a preços correntes",
                    "res": [
                        {
                            "localidade": "352940",
                            "res": {
                                "2020": "1000000",
                                "2021": "1200000",
                            },
                        }
                    ],
                },
                {
                    "id": 47001,
                    "indicador": "Produto Interno Bruto per capita",
                    "res": [
                        {
                            "localidade": "352940",
                            "res": {
                                "2020": "25000",
                                "2021": "30000",
                            },
                        }
                    ],
                },
            ],
            "http_status": 200,
        },
        "censo_alfabetizacao": {
            "municipio_id": MAUA_IBGE_CODE,
            "indicador": "censo_alfabetizacao",
            "periodo_referencia": "2022",
            "fonte_oficial": "IBGE - Censo 2022",
            "endpoint_url": "https://api.ibge.gov.br/9543",
            "payload": [
                {
                    "id": "2513",
                    "variavel": "Taxa de alfabetização",
                    "unidade": "%",
                    "resultados": [
                        {
                            "series": [
                                {
                                    "localidade": {"id": str(MAUA_IBGE_CODE)},
                                    "serie": {"2022": "96.74"},
                                }
                            ]
                        }
                    ],
                }
            ],
            "http_status": 200,
        },
        "censo_sexo": {
            "municipio_id": MAUA_IBGE_CODE,
            "indicador": "censo_sexo",
            "periodo_referencia": "2022",
            "fonte_oficial": "IBGE - Censo 2022",
            "endpoint_url": "https://api.ibge.gov.br/9514",
            "payload": [
                {
                    "id": "93",
                    "variavel": "População residente",
                    "unidade": "Pessoas",
                    "resultados": [
                        {
                            "classificacoes": [{"categoria": {"4": "Homens"}}],
                            "series": [
                                {
                                    "localidade": {"id": str(MAUA_IBGE_CODE)},
                                    "serie": {"2022": "201348"},
                                }
                            ],
                        },
                        {
                            "classificacoes": [{"categoria": {"5": "Mulheres"}}],
                            "series": [
                                {
                                    "localidade": {"id": str(MAUA_IBGE_CODE)},
                                    "serie": {"2022": "216913"},
                                }
                            ],
                        },
                    ],
                }
            ],
            "http_status": 200,
        },
    }


@pytest.fixture
def mock_client(
    maua_raw_payload: dict[str, Any],
    mock_socioeconomico_payload: dict[str, dict[str, Any]],
) -> MagicMock:
    """Retorna um mock de IBGEClient com suporte aos dois fluxos."""
    client = MagicMock(spec=IBGEClient)
    client.fetch_municipio_by_id.return_value = maua_raw_payload
    client.fetch_all_socioeconomico_maua.return_value = mock_socioeconomico_payload
    return client


# ---------------------------------------------------------------------------
# Testes do Fluxo Principal (Caminho Feliz & Idempotência)
# ---------------------------------------------------------------------------


def test_run_pipeline_end_to_end_success(
    test_pipeline_db: Path,
    mock_client: MagicMock,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa a execução sequencial completa dos dois fluxos com saída 0."""
    exit_code = run_pipeline(db_path=test_pipeline_db, client=mock_client)
    assert exit_code == 0

    # 1. Verifica chamadas de extração dos dois fluxos
    mock_client.fetch_municipio_by_id.assert_called_once_with(MAUA_IBGE_CODE)
    mock_client.fetch_all_socioeconomico_maua.assert_called_once()

    # 2. Valida Camada Bronze (Territorial e Socioeconômica)
    bronze_data = read_bronze(MAUA_IBGE_CODE, db_path=test_pipeline_db)
    assert bronze_data is not None
    assert bronze_data["id"] == MAUA_IBGE_CODE

    conn = get_db_connection(test_pipeline_db)
    try:
        cur_bs = conn.execute(
            "SELECT COUNT(*) AS total FROM bronze_ibge_socioeconomico;"
        )
        assert cur_bs.fetchone()["total"] == 5
    finally:
        conn.close()

    # 3. Valida Camada Silver (Todas as 4 tabelas)
    df_silver_mun = read_silver(MAUA_IBGE_CODE, db_path=test_pipeline_db)
    assert len(df_silver_mun) == 1

    df_silver_pop = read_silver_populacao(MAUA_IBGE_CODE, db_path=test_pipeline_db)
    assert len(df_silver_pop) >= 3  # Censo 2022 + 2 Estimativas

    df_silver_pib = read_silver_pib(MAUA_IBGE_CODE, db_path=test_pipeline_db)
    assert len(df_silver_pib) >= 2

    df_silver_cen = read_silver_censitario(MAUA_IBGE_CODE, db_path=test_pipeline_db)
    assert len(df_silver_cen) >= 4  # Área, Densidade, Alfabetização, Sexo

    # 4. Valida Camada Gold (Todas as 6 Views disponíveis e consistentes)
    assert not read_gold_hierarquia(MAUA_IBGE_CODE, db_path=test_pipeline_db).empty
    assert not read_gold_populacao_historica(
        MAUA_IBGE_CODE, db_path=test_pipeline_db
    ).empty
    assert not read_gold_pib_historico(MAUA_IBGE_CODE, db_path=test_pipeline_db).empty
    assert not read_gold_demografia_sexo(MAUA_IBGE_CODE, db_path=test_pipeline_db).empty
    assert not read_gold_resumo_socioeconomico(
        MAUA_IBGE_CODE, db_path=test_pipeline_db
    ).empty


def test_run_pipeline_idempotency_multiple_runs(
    test_pipeline_db: Path,
    mock_client: MagicMock,
) -> None:
    """Garante que rodar o pipeline duas vezes mantém idempotência e integridade."""
    # Primeira execução
    code_1 = run_pipeline(db_path=test_pipeline_db, client=mock_client)
    assert code_1 == 0

    # Segunda execução sobre o mesmo banco
    code_2 = run_pipeline(db_path=test_pipeline_db, client=mock_client)
    assert code_2 == 0

    # Valida contagens estáveis no SQLite
    conn = get_db_connection(test_pipeline_db)
    try:
        cur_br = conn.execute("SELECT COUNT(*) AS total FROM bronze_ibge_raw;")
        assert cur_br.fetchone()["total"] == 1

        cur_bs = conn.execute(
            "SELECT COUNT(*) AS total FROM bronze_ibge_socioeconomico;"
        )
        assert cur_bs.fetchone()["total"] == 5

        cur_sm = conn.execute("SELECT COUNT(*) AS total FROM silver_municipio;")
        assert cur_sm.fetchone()["total"] == 1

        cur_sp = conn.execute("SELECT COUNT(*) AS total FROM silver_ibge_populacao;")
        assert cur_sp.fetchone()["total"] == 3
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Testes de Tratamento de Falhas e Interrupção (Fail-Fast)
# ---------------------------------------------------------------------------


def test_run_pipeline_fails_on_territorial_extraction_error(
    test_pipeline_db: Path,
) -> None:
    """Verifica que erro na extração territorial interrompe o fluxo com código 1."""
    failing_client = MagicMock(spec=IBGEClient)
    failing_client.fetch_municipio_by_id.side_effect = IBGEExtractionError(
        "Timeout na extração de Localidades"
    )

    exit_code = run_pipeline(db_path=test_pipeline_db, client=failing_client)
    assert exit_code == 1

    # Nenhuma tabela posterior deve ter registros
    conn = get_db_connection(test_pipeline_db)
    try:
        cur_b = conn.execute("SELECT COUNT(*) AS total FROM bronze_ibge_raw;")
        assert cur_b.fetchone()["total"] == 0
    finally:
        conn.close()


def test_run_pipeline_fails_on_socioeconomico_extraction_error(
    test_pipeline_db: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Verifica interrupção caso a extração socioeconômica falhe."""
    client = MagicMock(spec=IBGEClient)
    client.fetch_municipio_by_id.return_value = maua_raw_payload
    client.fetch_all_socioeconomico_maua.side_effect = IBGEExtractionError(
        "SIDRA fora do ar"
    )

    exit_code = run_pipeline(db_path=test_pipeline_db, client=client)
    assert exit_code == 1

    # Camada Bronze territorial foi salva, mas a socioeconômica não
    conn = get_db_connection(test_pipeline_db)
    try:
        cur_b = conn.execute("SELECT COUNT(*) AS total FROM bronze_ibge_raw;")
        assert cur_b.fetchone()["total"] == 1

        cur_bs = conn.execute(
            "SELECT COUNT(*) AS total FROM bronze_ibge_socioeconomico;"
        )
        assert cur_bs.fetchone()["total"] == 0
    finally:
        conn.close()


def test_run_pipeline_fails_on_validation_error(test_pipeline_db: Path) -> None:
    """Verifica que dados com schema territorial corrompido abortam o pipeline."""
    invalid_client = MagicMock(spec=IBGEClient)
    invalid_client.fetch_municipio_by_id.return_value = {
        "id": 9999999,
        "nome": "Invalido",
    }

    exit_code = run_pipeline(db_path=test_pipeline_db, client=invalid_client)
    assert exit_code == 1


def test_run_pipeline_fails_on_bronze_storage_error(
    test_pipeline_db: Path,
    mock_client: MagicMock,
) -> None:
    """Verifica interrupção quando a persistência na Bronze territorial falha."""
    with patch(
        "desafio_ibge.main.save_bronze",
        side_effect=IBGEStorageError("Erro de gravação"),
    ):
        exit_code = run_pipeline(db_path=test_pipeline_db, client=mock_client)
        assert exit_code == 1


def test_run_pipeline_fails_on_silver_storage_error(
    test_pipeline_db: Path,
    mock_client: MagicMock,
) -> None:
    """Verifica interrupção quando a persistência na Silver territorial falha."""
    with patch(
        "desafio_ibge.main.save_silver",
        side_effect=IBGEStorageError("Erro Silver"),
    ):
        exit_code = run_pipeline(db_path=test_pipeline_db, client=mock_client)
        assert exit_code == 1


def test_run_pipeline_fails_on_socio_bronze_storage_error(
    test_pipeline_db: Path,
    mock_client: MagicMock,
) -> None:
    """Verifica interrupção quando a persistência na Bronze socioeconômica falha."""
    with patch(
        "desafio_ibge.main.save_all_socioeconomico_bronze",
        side_effect=IBGEStorageError("Erro Bronze Socio"),
    ):
        exit_code = run_pipeline(db_path=test_pipeline_db, client=mock_client)
        assert exit_code == 1


def test_run_pipeline_fails_on_socio_silver_storage_error(
    test_pipeline_db: Path,
    mock_client: MagicMock,
) -> None:
    """Verifica interrupção quando a persistência na Silver socioeconômica falha."""
    with patch(
        "desafio_ibge.main.save_all_socioeconomico_silver",
        side_effect=IBGEStorageError("Erro Silver Socio"),
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
