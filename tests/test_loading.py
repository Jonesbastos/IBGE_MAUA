"""Testes unitários e de integração para a camada de armazenamento (Bronze e Silver)."""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from desafio_ibge.config.settings import MAUA_IBGE_CODE
from desafio_ibge.loading.storage import (
    IBGEStorageError,
    IBGEStorageTransactionError,
    db_transaction,
    get_db_connection,
    get_kpis_geograficos,
    get_kpis_qualidade,
    init_db,
    read_bronze,
    read_bronze_record,
    read_gold_auditoria,
    read_gold_hierarquia,
    read_silver,
    save_bronze,
    save_silver,
)
from desafio_ibge.transformation.normalizer import json_to_dataframe


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Retorna um caminho temporário isolado para banco SQLite de testes."""
    return tmp_path / "test_ibge.db"


# ---------------------------------------------------------------------------
# Testes da Camada Bronze
# ---------------------------------------------------------------------------


def test_save_and_read_bronze_success(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa armazenamento e recuperação íntegra do JSON bruto na camada Bronze."""
    url = (
        "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/"
        f"{MAUA_IBGE_CODE}"
    )
    checksum = save_bronze(
        raw_payload=maua_raw_payload,
        endpoint_url=url,
        http_status=200,
        db_path=test_db_path,
    )

    assert isinstance(checksum, str)
    assert len(checksum) == 64

    # Recupera o payload original e valida que preservou a estrutura aninhada
    retrieved = read_bronze(MAUA_IBGE_CODE, db_path=test_db_path)
    assert retrieved is not None
    assert retrieved == maua_raw_payload
    assert retrieved["id"] == MAUA_IBGE_CODE
    assert "microrregiao" in retrieved
    assert "regiao-imediata" in retrieved
    assert retrieved["microrregiao"]["mesorregiao"]["UF"]["sigla"] == "SP"


def test_bronze_metadata_audit_record(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Verifica o registro completo de metadados na tabela bronze_ibge_raw."""
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/3529401"
    save_bronze(
        raw_payload=maua_raw_payload,
        endpoint_url=url,
        http_status=200,
        db_path=test_db_path,
    )

    record = read_bronze_record(MAUA_IBGE_CODE, db_path=test_db_path)
    assert record is not None
    assert record["ibge_id"] == MAUA_IBGE_CODE
    assert record["endpoint_url"] == url
    assert record["http_status"] == 200
    assert "ingestion_timestamp" in record
    assert "checksum_sha256" in record
    # Valida formato ISO do timestamp
    datetime.fromisoformat(record["ingestion_timestamp"])


def test_bronze_idempotency_upsert(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Garante que múltiplas gravações do mesmo município não duplicam registros."""
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/3529401"

    # Salva pela primeira vez
    save_bronze(maua_raw_payload, endpoint_url=url, db_path=test_db_path)

    # Salva novamente (segunda execução com mesmo ID)
    save_bronze(maua_raw_payload, endpoint_url=url, db_path=test_db_path)

    conn = get_db_connection(test_db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) AS total FROM bronze_ibge_raw;")
        count = cursor.fetchone()["total"]
        assert count == 1
    finally:
        conn.close()


def test_save_bronze_invalid_payload(test_db_path: Path) -> None:
    """Testa erro ao tentar salvar payload que não possui a chave 'id'."""
    with pytest.raises(IBGEStorageError, match="chave 'id'"):
        save_bronze(
            {"nome": "Sem ID"},
            endpoint_url="http://test",
            db_path=test_db_path,
        )


def test_read_bronze_not_found(test_db_path: Path) -> None:
    """Testa leitura de município inexistente na camada Bronze."""
    init_db(db_path=test_db_path)
    result = read_bronze(9999999, db_path=test_db_path)
    assert result is None
    record = read_bronze_record(9999999, db_path=test_db_path)
    assert record is None


# ---------------------------------------------------------------------------
# Testes da Camada Silver
# ---------------------------------------------------------------------------


def test_save_and_read_silver_success(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa persistência e leitura relacional tabular de Mauá na camada Silver."""
    df_maua = json_to_dataframe(maua_raw_payload)

    rows = save_silver(df_maua, db_path=test_db_path)
    assert rows == 1

    # Lê da camada Silver e verifica conformidade das 22 colunas + transformed_at
    silver_df = read_silver(MAUA_IBGE_CODE, db_path=test_db_path)
    assert not silver_df.empty
    assert len(silver_df) == 1
    assert silver_df["id"].iloc[0] == MAUA_IBGE_CODE
    assert silver_df["nome"].iloc[0] == "Mauá"
    assert silver_df["microrregiao_nome"].iloc[0] == "São Paulo"
    assert silver_df["microrregiao_mesorregiao_uf_sigla"].iloc[0] == "SP"
    assert silver_df["regiao_imediata_id"].iloc[0] == 350001
    assert "transformed_at" in silver_df.columns


def test_silver_idempotency_upsert(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Garante que múltiplas chamadas a save_silver atualizam sem duplicar linhas."""
    df_maua = json_to_dataframe(maua_raw_payload)

    # Primeira gravação
    save_silver(df_maua, db_path=test_db_path)

    # Segunda gravação do mesmo DataFrame
    save_silver(df_maua, db_path=test_db_path)

    conn = get_db_connection(test_db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) AS total FROM silver_municipio;")
        count = cursor.fetchone()["total"]
        assert count == 1
    finally:
        conn.close()


def test_silver_upsert_updates_existing_record(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa se o UPSERT da camada Silver realmente atualiza campos modificados."""
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=test_db_path)

    # Modifica o nome para simular atualização cadastral
    df_modified = df_maua.copy()
    df_modified["nome"] = "Mauá Atualizada"
    save_silver(df_modified, db_path=test_db_path)

    silver_df = read_silver(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(silver_df) == 1
    assert silver_df["nome"].iloc[0] == "Mauá Atualizada"


def test_save_silver_missing_columns(test_db_path: Path) -> None:
    """Garante que DataFrames incompletos são rejeitados antes de tocar o banco."""
    incomplete_df = pd.DataFrame([{"id": 3529401, "nome": "Incompleto"}])

    with pytest.raises(IBGEStorageError, match="Colunas obrigatórias ausentes"):
        save_silver(incomplete_df, db_path=test_db_path)


def test_save_silver_empty_dataframe(test_db_path: Path) -> None:
    """Rejeita DataFrame vazio na camada Silver."""
    with pytest.raises(IBGEStorageError, match="DataFrame inválido ou vazio"):
        save_silver(pd.DataFrame(), db_path=test_db_path)


def test_read_silver_empty_table(test_db_path: Path) -> None:
    """Testa leitura da Silver quando a tabela está vazia."""
    init_db(db_path=test_db_path)
    res = read_silver(db_path=test_db_path)
    assert res.empty


# ---------------------------------------------------------------------------
# Testes de Conexão, Transação e Rollback
# ---------------------------------------------------------------------------


def test_db_transaction_rollback_on_error(test_db_path: Path) -> None:
    """Testa reversão transacional (rollback) em caso de exceção no bloco with."""
    init_db(db_path=test_db_path)

    # Tenta inserir e depois levanta erro intencional
    with pytest.raises(IBGEStorageTransactionError):
        with db_transaction(db_path=test_db_path) as conn:
            conn.execute(
                "INSERT INTO bronze_ibge_raw VALUES (?, ?, ?, ?, ?, ?);",
                (9999999, "url", "{}", "2026-01-01", 200, "hash"),
            )
            # Erro de sintaxe proposital para forçar exceção no bloco
            conn.execute("INVALID SQL STATEMENT PROVOKING ERROR;")

    # Verifica que o rollback desfez a inserção de 9999999
    conn = get_db_connection(test_db_path)
    try:
        query = "SELECT COUNT(*) AS total FROM bronze_ibge_raw WHERE ibge_id = 9999999;"
        cursor = conn.execute(query)
        assert cursor.fetchone()["total"] == 0
    finally:
        conn.close()


def test_in_memory_sqlite_database() -> None:
    """Testa operações em banco SQLite em memória (:memory:)."""
    conn = get_db_connection(":memory:")
    try:
        init_db(conn=conn)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        assert "bronze_ibge_raw" in tables
        assert "silver_municipio" in tables

        cursor_views = conn.execute("SELECT name FROM sqlite_master WHERE type='view';")
        views = [row["name"] for row in cursor_views.fetchall()]
        assert "gold_vw_municipio_hierarquia" in views
        assert "gold_vw_qualidade_auditoria" in views
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Testes da Camada Gold (Hierarquia Geográfica e Auditoria de Qualidade)
# ---------------------------------------------------------------------------


def test_gold_views_creation(test_db_path: Path) -> None:
    """Verifica que as Views Gold são criadas no catálogo do SQLite."""
    init_db(db_path=test_db_path)
    conn = get_db_connection(test_db_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;"
        )
        views = [row["name"] for row in cursor.fetchall()]
        assert "gold_vw_municipio_hierarquia" in views
        assert "gold_vw_qualidade_auditoria" in views
    finally:
        conn.close()


def test_gold_views_idempotent_reinitialization(test_db_path: Path) -> None:
    """Garante que init_db pode ser chamado repetidamente sem erros de views."""
    init_db(db_path=test_db_path)
    init_db(db_path=test_db_path)
    init_db(db_path=test_db_path)

    conn = get_db_connection(test_db_path)
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) AS total FROM sqlite_master WHERE type='view';"
        )
        assert cursor.fetchone()["total"] == 2
    finally:
        conn.close()


def test_read_gold_hierarquia_maua_success(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Verifica a extração e integridade dos nós da View de hierarquia para Mauá."""
    # Ingestão e transformação de Mauá
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=test_db_path)

    # Consulta sem ID (todos os municípios)
    df_all = read_gold_hierarquia(db_path=test_db_path)
    assert not df_all.empty
    assert len(df_all) == 1

    # Consulta pontual por ID
    df_maua_gold = read_gold_hierarquia(
        municipio_id=MAUA_IBGE_CODE,
        db_path=test_db_path,
    )
    assert not df_maua_gold.empty
    assert len(df_maua_gold) == 1

    row = df_maua_gold.iloc[0]
    assert row["municipio_id"] == MAUA_IBGE_CODE
    assert row["municipio_nome"] == "Mauá"
    assert row["uf_sigla"] == "SP"
    assert row["uf_nome"] == "São Paulo"
    assert row["regiao_sigla"] == "SE"
    assert row["regiao_nome"] == "Sudeste"
    assert row["regiao_imediata_id"] == 350001
    assert row["regiao_imediata_nome"] == "São Paulo"
    assert row["regiao_intermediaria_id"] == 3501
    assert row["regiao_intermediaria_nome"] == "São Paulo"
    assert row["microrregiao_id"] == 35061
    assert row["microrregiao_nome"] == "São Paulo"
    assert row["mesorregiao_id"] == 3515
    assert row["mesorregiao_nome"] == "Metropolitana de São Paulo"
    assert "transformed_at" in row


def test_read_gold_hierarquia_empty_table(test_db_path: Path) -> None:
    """Verifica que a View de hierarquia retorna DataFrame vazio sem erros."""
    init_db(db_path=test_db_path)
    df = read_gold_hierarquia(db_path=test_db_path)
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_read_gold_auditoria_maua_conforme(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Valida cálculo de auditoria e conformidade de Mauá nas camadas."""
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{MAUA_IBGE_CODE}"
    save_bronze(maua_raw_payload, endpoint_url=url, db_path=test_db_path)
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=test_db_path)

    df_auditoria = read_gold_auditoria(
        municipio_id=MAUA_IBGE_CODE,
        db_path=test_db_path,
    )
    assert not df_auditoria.empty
    assert len(df_auditoria) == 1

    audit = df_auditoria.iloc[0]
    assert audit["municipio_id"] == MAUA_IBGE_CODE
    assert audit["municipio_nome"] == "Mauá"
    assert audit["status_integracao"] == "CONFORME"
    assert audit["flag_presente_bronze"] == 1
    assert audit["flag_presente_silver"] == 1
    assert audit["flag_codigo_ibge_valido"] == 1
    assert audit["flag_checksum_valido"] == 1
    assert audit["flag_http_ok"] == 1
    assert audit["flag_campos_obrigatorios_nulos"] == 0
    assert audit["flag_consistencia_geografica"] == 1
    assert audit["latencia_processamento_segundos"] is not None
    assert audit["latencia_processamento_segundos"] >= 0.0


def test_read_gold_auditoria_bronze_without_silver(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Identifica registro órfão na Bronze (ausente na Silver)."""
    url = "https://example.com/santo_andre"
    santo_andre = dict(maua_raw_payload)
    santo_andre["id"] = 3547809
    santo_andre["nome"] = "Santo André"

    save_bronze(santo_andre, endpoint_url=url, db_path=test_db_path)

    df_auditoria = read_gold_auditoria(municipio_id=3547809, db_path=test_db_path)
    assert not df_auditoria.empty
    row = df_auditoria.iloc[0]

    assert row["municipio_id"] == 3547809
    assert row["status_integracao"] == "AUSENTE_NA_SILVER"
    assert row["flag_presente_bronze"] == 1
    assert row["flag_presente_silver"] == 0
    assert row["flag_consistencia_geografica"] is None
    assert row["latencia_processamento_segundos"] is None


def test_read_gold_auditoria_silver_without_bronze(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Identifica registro órfão na Silver (ausente na Bronze)."""
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=test_db_path)

    df_auditoria = read_gold_auditoria(
        municipio_id=MAUA_IBGE_CODE,
        db_path=test_db_path,
    )
    assert not df_auditoria.empty
    row = df_auditoria.iloc[0]

    assert row["municipio_id"] == MAUA_IBGE_CODE
    assert row["status_integracao"] == "AUSENTE_NA_BRONZE"
    assert row["flag_presente_bronze"] == 0
    assert row["flag_presente_silver"] == 1
    assert row["latencia_processamento_segundos"] is None


def test_read_gold_auditoria_with_null_fields(test_db_path: Path) -> None:
    """Verifica detecção de campos obrigatórios vazios ou nulos na Silver."""
    init_db(db_path=test_db_path)

    # Inserção direta na Silver com nome em branco para teste de auditoria
    with db_transaction(db_path=test_db_path) as conn:
        conn.execute(
            """
            INSERT INTO silver_municipio (
                id, nome, microrregiao_id, microrregiao_nome,
                microrregiao_mesorregiao_id, microrregiao_mesorregiao_nome,
                microrregiao_mesorregiao_uf_id, microrregiao_mesorregiao_uf_sigla,
                microrregiao_mesorregiao_uf_nome, microrregiao_mesorregiao_uf_regiao_id,
                microrregiao_mesorregiao_uf_regiao_sigla,
                microrregiao_mesorregiao_uf_regiao_nome,
                regiao_imediata_id, regiao_imediata_nome,
                regiao_imediata_regiao_intermediaria_id,
                regiao_imediata_regiao_intermediaria_nome,
                regiao_imediata_regiao_intermediaria_uf_id,
                regiao_imediata_regiao_intermediaria_uf_sigla,
                regiao_imediata_regiao_intermediaria_uf_nome,
                regiao_imediata_regiao_intermediaria_uf_regiao_id,
                regiao_imediata_regiao_intermediaria_uf_regiao_sigla,
                regiao_imediata_regiao_intermediaria_uf_regiao_nome,
                transformed_at
            ) VALUES (
                3599999, '', 35061, 'São Paulo',
                3515, 'Metropolitana', 35, 'SP', 'São Paulo', 3, 'SE', 'Sudeste',
                350001, 'São Paulo', 3501, 'São Paulo', 35, 'SP', 'São Paulo',
                3, 'SE', 'Sudeste', '2026-01-01T00:00:00+00:00'
            );
            """
        )

    df_auditoria = read_gold_auditoria(municipio_id=3599999, db_path=test_db_path)
    assert not df_auditoria.empty
    row = df_auditoria.iloc[0]
    assert row["flag_campos_obrigatorios_nulos"] == 1


def test_read_gold_auditoria_empty_table(test_db_path: Path) -> None:
    """Verifica que a View de auditoria retorna DataFrame vazio sem erros."""
    init_db(db_path=test_db_path)
    df = read_gold_auditoria(db_path=test_db_path)
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# Testes de Agregações Analíticas e KPIs Gold
# ---------------------------------------------------------------------------


def test_get_kpis_geograficos_maua(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Verifica agregação de KPIs geográficos com o dado de Mauá."""
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=test_db_path)

    kpis = get_kpis_geograficos(db_path=test_db_path)
    assert kpis["total_municipios"] == 1
    assert kpis["municipios_por_uf"] == {"SP": 1}
    assert kpis["municipios_por_regiao"] == {"Sudeste": 1}
    assert kpis["municipios_por_regiao_imediata"] == {"São Paulo": 1}
    assert kpis["municipios_por_regiao_intermediaria"] == {"São Paulo": 1}


def test_get_kpis_geograficos_empty(test_db_path: Path) -> None:
    """Verifica KPIs geográficos em banco vazio."""
    kpis = get_kpis_geograficos(db_path=test_db_path)
    assert kpis["total_municipios"] == 0
    assert kpis["municipios_por_uf"] == {}
    assert kpis["municipios_por_regiao"] == {}


def test_get_kpis_qualidade_maua(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Verifica KPIs de qualidade quando Mauá está sincronizado nas duas camadas."""
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{MAUA_IBGE_CODE}"
    save_bronze(maua_raw_payload, endpoint_url=url, db_path=test_db_path)
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=test_db_path)

    kpis = get_kpis_qualidade(db_path=test_db_path)
    assert kpis["total_registros_auditados"] == 1
    assert kpis["total_presente_bronze"] == 1
    assert kpis["total_presente_silver"] == 1
    assert kpis["total_conforme"] == 1
    assert kpis["total_ausente_silver"] == 0
    assert kpis["total_ausente_bronze"] == 0
    assert kpis["total_falhas_qualidade"] == 0
    assert kpis["taxa_conformidade_pct"] == 100.0
    assert kpis["total_campos_nulos"] == 0
    assert kpis["total_codigos_validos"] == 1
    assert kpis["total_checksums_validos"] == 1
    assert kpis["total_http_ok"] == 1
    assert kpis["total_consistencia_geografica"] == 1
    assert kpis["ultima_ingestao_utc"] is not None
    assert kpis["ultima_transformacao_utc"] is not None


def test_get_kpis_qualidade_empty(test_db_path: Path) -> None:
    """Verifica KPIs de qualidade em banco vazio."""
    kpis = get_kpis_qualidade(db_path=test_db_path)
    assert kpis["total_registros_auditados"] == 0
    assert kpis["taxa_conformidade_pct"] == 0.0
    assert kpis["total_falhas_qualidade"] == 0
    assert kpis["ultima_ingestao_utc"] is None
