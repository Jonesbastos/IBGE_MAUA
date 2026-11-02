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
    canonical_json_sha256,
    db_transaction,
    get_db_connection,
    get_kpis_geograficos,
    get_kpis_qualidade,
    init_db,
    list_bronze_socioeconomico,
    read_bronze,
    read_bronze_record,
    read_bronze_socioeconomico,
    read_gold_auditoria,
    read_gold_hierarquia,
    read_silver,
    save_all_socioeconomico_bronze,
    save_bronze,
    save_bronze_socioeconomico,
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
        assert cursor.fetchone()["total"] == 6
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


# ---------------------------------------------------------------------------
# Testes da Camada Bronze Socioeconômica (FASE 10 — Subetapa 10.2)
# ---------------------------------------------------------------------------


def test_canonical_json_sha256_deterministic() -> None:
    """Verifica se dicts com chaves desordenadas geram o mesmo hash determinístico."""
    payload1 = {"z": 100, "a": "texto", "m": [1, 2, 3]}
    payload2 = {"a": "texto", "m": [1, 2, 3], "z": 100}

    json1, hash1 = canonical_json_sha256(payload1)
    json2, hash2 = canonical_json_sha256(payload2)

    assert json1 == json2
    assert hash1 == hash2
    assert len(hash1) == 64


def test_save_and_read_bronze_socioeconomico_success(test_db_path: Path) -> None:
    """Testa persistência e leitura de dados brutos na bronze_ibge_socioeconomico."""
    mock_payload = [{"id": "93", "variavel": "População", "serie": {"2022": "418261"}}]
    url = "https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022/variaveis/93"

    checksum = save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="censo_pop_area_densidade",
        periodo_referencia="2022",
        fonte_oficial="Censo Demográfico 2022",
        endpoint_url=url,
        raw_payload=mock_payload,
        http_status=200,
        db_path=test_db_path,
    )
    assert len(checksum) == 64

    record = read_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="censo_pop_area_densidade",
        periodo_referencia="2022",
        db_path=test_db_path,
    )
    assert record is not None
    assert record["municipio_id"] == MAUA_IBGE_CODE
    assert record["indicador"] == "censo_pop_area_densidade"
    assert record["periodo_referencia"] == "2022"
    assert record["fonte_oficial"] == "Censo Demográfico 2022"
    assert record["endpoint_url"] == url
    assert record["checksum_sha256"] == checksum
    assert record["http_status"] == 200
    assert record["payload"] == mock_payload


def test_read_bronze_socioeconomico_not_found(test_db_path: Path) -> None:
    """Verifica retorno None quando registro socioeconômico não existe."""
    record = read_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="inexistente",
        periodo_referencia="2022",
        db_path=test_db_path,
    )
    assert record is None


def test_bronze_socioeconomico_upsert_idempotent(test_db_path: Path) -> None:
    """Testa se executar a ingestão duas vezes não duplica linhas (idempotência)."""
    mock_payload = [{"id": "93", "valor": "418261"}]
    url = "https://servicodados.ibge.gov.br/api/v3/teste"

    ck1 = save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="pop_teste",
        periodo_referencia="2022",
        fonte_oficial="Teste IBGE",
        endpoint_url=url,
        raw_payload=mock_payload,
        db_path=test_db_path,
    )

    ck2 = save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="pop_teste",
        periodo_referencia="2022",
        fonte_oficial="Teste IBGE",
        endpoint_url=url,
        raw_payload=mock_payload,
        db_path=test_db_path,
    )

    assert ck1 == ck2

    conn = get_db_connection(test_db_path)
    count = conn.execute("SELECT COUNT(*) FROM bronze_ibge_socioeconomico;").fetchone()[
        0
    ]
    conn.close()
    assert count == 1


def test_bronze_socioeconomico_update_record(test_db_path: Path) -> None:
    """Testa atualização de registro quando o payload oficial sofre modificação."""
    url = "https://servicodados.ibge.gov.br/api/v3/teste"

    ck1 = save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="pib_teste",
        periodo_referencia="2023",
        fonte_oficial="PIB IBGE",
        endpoint_url=url,
        raw_payload={"versao": 1, "pib": 1000},
        db_path=test_db_path,
    )

    ck2 = save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="pib_teste",
        periodo_referencia="2023",
        fonte_oficial="PIB IBGE Atualizado",
        endpoint_url=url,
        raw_payload={"versao": 2, "pib": 1200},
        db_path=test_db_path,
    )

    assert ck1 != ck2

    record = read_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="pib_teste",
        periodo_referencia="2023",
        db_path=test_db_path,
    )
    assert record is not None
    assert record["checksum_sha256"] == ck2
    assert record["fonte_oficial"] == "PIB IBGE Atualizado"
    assert record["payload"]["versao"] == 2


def test_bronze_socioeconomico_invalid_inputs(test_db_path: Path) -> None:
    """Testa validação de integridade nos parâmetros da Bronze socioeconômica."""
    with pytest.raises(IBGEStorageError, match="Campos identificadores"):
        save_bronze_socioeconomico(
            municipio_id=MAUA_IBGE_CODE,
            indicador="",
            periodo_referencia="2022",
            fonte_oficial="IBGE",
            endpoint_url="http://test",
            raw_payload={"x": 1},
            db_path=test_db_path,
        )

    with pytest.raises(IBGEStorageError, match="Payload inválido"):
        save_bronze_socioeconomico(
            municipio_id=MAUA_IBGE_CODE,
            indicador="teste",
            periodo_referencia="2022",
            fonte_oficial="IBGE",
            endpoint_url="http://test",
            raw_payload="string_invalida_nao_json",  # type: ignore[arg-type]
            db_path=test_db_path,
        )


def test_list_bronze_socioeconomico(test_db_path: Path) -> None:
    """Testa listagem e filtro de indicadores na camada Bronze."""
    save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="ind_1",
        periodo_referencia="2022",
        fonte_oficial="IBGE",
        endpoint_url="http://test1",
        raw_payload=[1],
        db_path=test_db_path,
    )
    save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="ind_2",
        periodo_referencia="2023",
        fonte_oficial="IBGE",
        endpoint_url="http://test2",
        raw_payload=[2],
        db_path=test_db_path,
    )
    save_bronze_socioeconomico(
        municipio_id=9999999,
        indicador="ind_outro",
        periodo_referencia="2022",
        fonte_oficial="IBGE",
        endpoint_url="http://test3",
        raw_payload=[3],
        db_path=test_db_path,
    )

    all_items = list_bronze_socioeconomico(db_path=test_db_path)
    assert len(all_items) == 3

    maua_items = list_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE, db_path=test_db_path
    )
    assert len(maua_items) == 2


def test_save_all_socioeconomico_bronze(test_db_path: Path) -> None:
    """Testa função utilitária para salvamento em lote de indicadores."""
    batch = {
        "ind_a": {
            "municipio_id": MAUA_IBGE_CODE,
            "periodo_referencia": "2022",
            "fonte_oficial": "Fonte A",
            "endpoint_url": "http://a",
            "payload": {"a": 1},
        },
        "ind_b": {
            "municipio_id": MAUA_IBGE_CODE,
            "periodo_referencia": "2023",
            "fonte_oficial": "Fonte B",
            "endpoint_url": "http://b",
            "payload": [1, 2],
        },
    }
    checksums = save_all_socioeconomico_bronze(batch, db_path=test_db_path)
    assert len(checksums) == 2
    assert "ind_a" in checksums
    assert "ind_b" in checksums


def test_bronze_socioeconomico_preserves_existing_bronze_raw(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Garante que a nova tabela não interfere nas tabelas territoriais existentes."""
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{MAUA_IBGE_CODE}"
    save_bronze(maua_raw_payload, endpoint_url=url, db_path=test_db_path)

    save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="censo_pop",
        periodo_referencia="2022",
        fonte_oficial="Censo 2022",
        endpoint_url="http://socio",
        raw_payload=[{"pop": 418261}],
        db_path=test_db_path,
    )

    raw_rec = read_bronze(MAUA_IBGE_CODE, db_path=test_db_path)
    assert raw_rec is not None
    assert raw_rec["id"] == MAUA_IBGE_CODE


# ---------------------------------------------------------------------------
# Testes da Camada Silver Socioeconômica (População, PIB e Censitário)
# ---------------------------------------------------------------------------


def test_save_and_read_silver_populacao(test_db_path: Path) -> None:
    """Testa persistência, leitura e UPSERT idempotente em silver_ibge_populacao."""
    from desafio_ibge.loading.storage import (
        read_silver_populacao,
        save_silver_populacao,
    )

    df_pop = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "populacao": 418261,
                "tipo_populacao": "Censo Demográfico",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_pop_area_densidade",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2021,
                "populacao": 479000,
                "tipo_populacao": "Estimativa Populacional",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE - Estimativas",
                "bronze_indicador": "populacao_estimada_historica",
            },
        ]
    )

    # 1. Primeira persistência
    count = save_silver_populacao(df_pop, db_path=test_db_path)
    assert count == 2

    # 2. Leitura
    read_df = read_silver_populacao(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(read_df) == 2
    assert "transformed_at" in read_df.columns

    # 3. UPSERT idempotente (atualiza população estimada com retificação)
    df_pop_updated = df_pop.copy()
    df_pop_updated.loc[df_pop_updated["ano_referencia"] == 2021, "populacao"] = 479500
    save_silver_populacao(df_pop_updated, db_path=test_db_path)

    read_df_updated = read_silver_populacao(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(read_df_updated) == 2  # Não duplicou registros
    val_2021 = read_df_updated.loc[
        read_df_updated["ano_referencia"] == 2021, "populacao"
    ].iloc[0]
    assert val_2021 == 479500


def test_save_and_read_silver_pib(test_db_path: Path) -> None:
    """Testa persistência e integridade relacional em silver_ibge_pib."""
    from desafio_ibge.loading.storage import read_silver_pib, save_silver_pib

    df_pib = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2023,
                "indicador_id": 46997,
                "indicador_nome": "PIB corrente",
                "valor": 25000732.02,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE - PIB",
                "bronze_indicador": "pib_municipal_historico",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2023,
                "indicador_id": 47001,
                "indicador_nome": "PIB per capita",
                "valor": 59773.11,
                "unidade": "Reais",
                "tipo_valor": "Per Capita",
                "fonte_oficial": "IBGE - PIB",
                "bronze_indicador": "pib_municipal_historico",
            },
        ]
    )

    count = save_silver_pib(df_pib, db_path=test_db_path)
    assert count == 2

    read_df = read_silver_pib(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(read_df) == 2
    assert set(read_df["indicador_id"]) == {46997, 47001}


def test_save_and_read_silver_censitario(test_db_path: Path) -> None:
    """Testa persistência e recuperação em silver_ibge_censitario."""
    from desafio_ibge.loading.storage import (
        read_silver_censitario,
        save_silver_censitario,
    )

    df_cen = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "variavel_id": 6318,
                "variavel_nome": "Área territorial",
                "categoria_classificacao": "Total",
                "valor": 61.937,
                "unidade": "km²",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_pop_area_densidade",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "variavel_id": 2513,
                "variavel_nome": "Taxa de alfabetização",
                "categoria_classificacao": "Total",
                "valor": 96.74,
                "unidade": "%",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_alfabetizacao",
            },
        ]
    )

    count = save_silver_censitario(df_cen, db_path=test_db_path)
    assert count == 2

    read_df = read_silver_censitario(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(read_df) == 2
    assert "Taxa de alfabetização" in read_df["variavel_nome"].values


def test_save_silver_invalid_inputs(test_db_path: Path) -> None:
    """Garante que DataFrames vazios ou sem colunas obrigatórias levantam erro."""
    from desafio_ibge.loading.storage import (
        save_silver_censitario,
        save_silver_pib,
        save_silver_populacao,
    )

    empty_df = pd.DataFrame()
    with pytest.raises(IBGEStorageError):
        save_silver_populacao(empty_df, db_path=test_db_path)

    with pytest.raises(IBGEStorageError):
        save_silver_pib(empty_df, db_path=test_db_path)

    with pytest.raises(IBGEStorageError):
        save_silver_censitario(empty_df, db_path=test_db_path)

    missing_cols_df = pd.DataFrame([{"municipio_id": 3529401}])
    with pytest.raises(IBGEStorageError):
        save_silver_populacao(missing_cols_df, db_path=test_db_path)


def test_save_all_socioeconomico_silver(test_db_path: Path) -> None:
    """Testa persistência em lote da Silver Socioeconômica via dicionário."""
    from desafio_ibge.loading.storage import (
        read_silver_censitario,
        read_silver_pib,
        read_silver_populacao,
        save_all_socioeconomico_silver,
    )

    dfs = {
        "populacao": pd.DataFrame(
            [
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2022,
                    "populacao": 418261,
                    "tipo_populacao": "Censo Demográfico",
                    "unidade": "Pessoas",
                    "fonte_oficial": "IBGE",
                    "bronze_indicador": "censo",
                }
            ]
        ),
        "pib": pd.DataFrame(
            [
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2023,
                    "indicador_id": 46997,
                    "indicador_nome": "PIB",
                    "valor": 25000732.0,
                    "unidade": "Mil Reais",
                    "tipo_valor": "Corrente",
                    "fonte_oficial": "IBGE",
                    "bronze_indicador": "pib",
                }
            ]
        ),
        "censitario": pd.DataFrame(
            [
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2022,
                    "variavel_id": 6318,
                    "variavel_nome": "Área",
                    "categoria_classificacao": "Total",
                    "valor": 61.937,
                    "unidade": "km²",
                    "fonte_oficial": "IBGE",
                    "bronze_indicador": "censo",
                }
            ]
        ),
    }

    counts = save_all_socioeconomico_silver(dfs, db_path=test_db_path)
    assert counts == {"populacao": 1, "pib": 1, "censitario": 1}

    assert len(read_silver_populacao(MAUA_IBGE_CODE, db_path=test_db_path)) == 1
    assert len(read_silver_pib(MAUA_IBGE_CODE, db_path=test_db_path)) == 1
    assert len(read_silver_censitario(MAUA_IBGE_CODE, db_path=test_db_path)) == 1


def test_read_silver_without_filter(test_db_path: Path) -> None:
    """Testa recuperação dos DataFrames Silver sem especificar municipio_id."""
    from desafio_ibge.loading.storage import (
        read_silver_censitario,
        read_silver_pib,
        read_silver_populacao,
        save_silver_censitario,
        save_silver_pib,
        save_silver_populacao,
    )

    df_pop = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "populacao": 418261,
                "tipo_populacao": "Censo Demográfico",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "censo",
            }
        ]
    )
    save_silver_populacao(df_pop, db_path=test_db_path)
    all_pop = read_silver_populacao(municipio_id=None, db_path=test_db_path)
    assert len(all_pop) == 1

    df_pib = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2023,
                "indicador_id": 46997,
                "indicador_nome": "PIB",
                "valor": 25000732.0,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            }
        ]
    )
    save_silver_pib(df_pib, db_path=test_db_path)
    all_pib = read_silver_pib(municipio_id=None, db_path=test_db_path)
    assert len(all_pib) == 1

    df_cen = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "variavel_id": 6318,
                "variavel_nome": "Área",
                "categoria_classificacao": "Total",
                "valor": 61.937,
                "unidade": "km²",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "censo",
            }
        ]
    )
    save_silver_censitario(df_cen, db_path=test_db_path)
    all_cen = read_silver_censitario(municipio_id=None, db_path=test_db_path)
    assert len(all_cen) == 1


# ---------------------------------------------------------------------------
# Testes da Camada Gold Socioeconômica (Views Analíticas e Métricas SQL)
# ---------------------------------------------------------------------------


def test_gold_socioeconomico_views_creation(test_db_path: Path) -> None:
    """Valida se todas as novas views analíticas são criadas em init_db."""
    from desafio_ibge.loading.storage import get_db_connection, init_db

    init_db(db_path=test_db_path)
    conn = get_db_connection(db_path=test_db_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'view' ORDER BY name;"
        )
        views = [row["name"] for row in cursor.fetchall()]
        assert "gold_populacao_historica" in views
        assert "gold_pib_historico" in views
        assert "gold_demografia_sexo" in views
        assert "gold_resumo_socioeconomico" in views
        assert "gold_vw_municipio_hierarquia" in views
        assert "gold_vw_qualidade_auditoria" in views
    finally:
        conn.close()


def test_gold_populacao_historica_lag_and_variations(test_db_path: Path) -> None:
    """Testa cálculo de LAG, variação absoluta, percentual e anos consecutivos."""
    from desafio_ibge.loading.storage import (
        read_gold_populacao_historica,
        save_silver_populacao,
    )

    df_pop = pd.DataFrame(
        [
            # Estimativas com anos consecutivos e salto de ano
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2020,
                "populacao": 400000,
                "tipo_populacao": "Estimativa Populacional",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pop_est",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2021,
                "populacao": 410000,
                "tipo_populacao": "Estimativa Populacional",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pop_est",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2023,  # Pulo de 2 anos (não consecutivo)
                "populacao": 420000,
                "tipo_populacao": "Estimativa Populacional",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pop_est",
            },
            # Censo Demográfico em metodologia separada
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "populacao": 418261,
                "tipo_populacao": "Censo Demográfico",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "censo_pop",
            },
        ]
    )
    save_silver_populacao(df_pop, db_path=test_db_path)

    gold_pop = read_gold_populacao_historica(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(gold_pop) == 4

    # 1. Censo não herda LAG das estimativas
    censo_row = gold_pop[gold_pop["tipo_populacao"] == "Censo Demográfico"].iloc[0]
    assert pd.isna(censo_row["variacao_absoluta_anterior"])
    assert pd.isna(censo_row["variacao_percentual_anterior"])

    # 2. Estimativas 2020: primeira observação, LAG é nulo
    est_2020 = gold_pop[
        (gold_pop["tipo_populacao"] == "Estimativa Populacional")
        & (gold_pop["ano_referencia"] == 2020)
    ].iloc[0]
    assert pd.isna(est_2020["variacao_absoluta_anterior"])

    # 3. Estimativas 2021: variação absoluta = 10000, percentual = 2.5%, consecutivo = 1
    est_2021 = gold_pop[
        (gold_pop["tipo_populacao"] == "Estimativa Populacional")
        & (gold_pop["ano_referencia"] == 2021)
    ].iloc[0]
    assert est_2021["variacao_absoluta_anterior"] == 10000
    assert est_2021["variacao_percentual_anterior"] == 2.50
    assert est_2021["flag_anos_consecutivos"] == 1

    # 4. Estimativas 2023: não consecutivo (2023 - 2021 != 1)
    est_2023 = gold_pop[
        (gold_pop["tipo_populacao"] == "Estimativa Populacional")
        & (gold_pop["ano_referencia"] == 2023)
    ].iloc[0]
    assert est_2023["flag_anos_consecutivos"] == 0


def test_gold_pib_historico_nominal_and_sectoral_shares(test_db_path: Path) -> None:
    """Testa pivotagem, cálculo de variação nominal e participações setoriais do PIB."""
    from desafio_ibge.loading.storage import (
        read_gold_pib_historico,
        save_silver_pib,
    )

    df_pib = pd.DataFrame(
        [
            # 2020
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2020,
                "indicador_id": 46997,
                "indicador_nome": "PIB corrente",
                "valor": 1000000.0,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2020,
                "indicador_id": 47001,
                "indicador_nome": "PIB per capita",
                "valor": 25000.0,
                "unidade": "Reais",
                "tipo_valor": "Per Capita",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
            # 2021
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2021,
                "indicador_id": 46997,
                "indicador_nome": "PIB corrente",
                "valor": 1200000.0,  # Variação nominal +20%
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2021,
                "indicador_id": 47001,
                "indicador_nome": "PIB per capita",
                "valor": 30000.0,  # Variação per capita +20%
                "unidade": "Reais",
                "tipo_valor": "Per Capita",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2021,
                "indicador_id": 47007,
                "indicador_nome": "VAB Indústria",
                "valor": 400000.0,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2021,
                "indicador_id": 47008,
                "indicador_nome": "VAB Serviços",
                "valor": 600000.0,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2021,
                "indicador_id": 47004,
                "indicador_nome": "VAB Total",
                "valor": 1000000.0,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
        ]
    )
    save_silver_pib(df_pib, db_path=test_db_path)

    gold_pib = read_gold_pib_historico(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(gold_pib) == 2

    row_2021 = gold_pib[gold_pib["ano_referencia"] == 2021].iloc[0]
    assert row_2021["variacao_nominal_pib_pct"] == 20.0
    assert row_2021["variacao_nominal_per_capita_pct"] == 20.0
    assert row_2021["participacao_industria_vab_pct"] == 40.0
    assert row_2021["participacao_servicos_vab_pct"] == 60.0


def test_gold_demografia_sexo_razao_and_zero_division(test_db_path: Path) -> None:
    """Testa cálculo de razão de sexo demográfica e prevenção de divisão por zero."""
    from desafio_ibge.loading.storage import (
        read_gold_demografia_sexo,
        save_silver_censitario,
    )

    # 1. Cenário normal de Censo 2022
    df_cen = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "variavel_id": 93,
                "variavel_nome": "População residente por sexo",
                "categoria_classificacao": "Homens",
                "valor": 200000.0,
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_sexo",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "variavel_id": 93,
                "variavel_nome": "População residente por sexo",
                "categoria_classificacao": "Mulheres",
                "valor": 200000.0,
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_sexo",
            },
        ]
    )
    save_silver_censitario(df_cen, db_path=test_db_path)

    gold_sexo = read_gold_demografia_sexo(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(gold_sexo) == 1
    row = gold_sexo.iloc[0]
    assert row["populacao_masculina"] == 200000
    assert row["populacao_feminina"] == 200000
    assert row["populacao_total"] == 400000
    assert row["participacao_masculina_pct"] == 50.0
    assert row["participacao_feminina_pct"] == 50.0
    assert row["razao_sexo"] == 100.0


def test_gold_resumo_socioeconomico_and_kpis(test_db_path: Path) -> None:
    """Testa consolidação multitemática da view de resumo e KPIs de alto nível."""
    from desafio_ibge.loading.storage import (
        get_kpis_socioeconomicos,
        read_gold_resumo_socioeconomico,
        save_all_socioeconomico_silver,
    )

    dfs = {
        "populacao": pd.DataFrame(
            [
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2022,
                    "populacao": 418261,
                    "tipo_populacao": "Censo Demográfico",
                    "unidade": "Pessoas",
                    "fonte_oficial": "IBGE - Censo 2022",
                    "bronze_indicador": "censo_pop",
                },
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2026,
                    "populacao": 429064,
                    "tipo_populacao": "Estimativa Populacional",
                    "unidade": "Pessoas",
                    "fonte_oficial": "IBGE - Estimativas",
                    "bronze_indicador": "pop_est",
                },
            ]
        ),
        "pib": pd.DataFrame(
            [
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2023,
                    "indicador_id": 46997,
                    "indicador_nome": "PIB corrente",
                    "valor": 25000732.02,
                    "unidade": "Mil Reais",
                    "tipo_valor": "Corrente",
                    "fonte_oficial": "IBGE - PIB",
                    "bronze_indicador": "pib",
                },
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2023,
                    "indicador_id": 47001,
                    "indicador_nome": "PIB per capita",
                    "valor": 59773.04,
                    "unidade": "Reais",
                    "tipo_valor": "Per Capita",
                    "fonte_oficial": "IBGE - PIB",
                    "bronze_indicador": "pib",
                },
            ]
        ),
        "censitario": pd.DataFrame(
            [
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2022,
                    "variavel_id": 6318,
                    "variavel_nome": "Área territorial",
                    "categoria_classificacao": "Total",
                    "valor": 61.937,
                    "unidade": "km²",
                    "fonte_oficial": "IBGE - Censo 2022",
                    "bronze_indicador": "censo",
                },
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2022,
                    "variavel_id": 614,
                    "variavel_nome": "Densidade demográfica",
                    "categoria_classificacao": "Total",
                    "valor": 6753.01,
                    "unidade": "hab/km²",
                    "fonte_oficial": "IBGE - Censo 2022",
                    "bronze_indicador": "censo",
                },
                {
                    "municipio_id": MAUA_IBGE_CODE,
                    "ano_referencia": 2022,
                    "variavel_id": 2513,
                    "variavel_nome": "Taxa de alfabetização",
                    "categoria_classificacao": "Total",
                    "valor": 96.74,
                    "unidade": "%",
                    "fonte_oficial": "IBGE - Censo 2022",
                    "bronze_indicador": "censo",
                },
            ]
        ),
    }

    save_all_socioeconomico_silver(dfs, db_path=test_db_path)

    df_resumo = read_gold_resumo_socioeconomico(MAUA_IBGE_CODE, db_path=test_db_path)
    assert len(df_resumo) >= 6
    temas = set(df_resumo["tema"])
    assert "Demografia" in temas
    assert "Economia" in temas
    assert "Território" in temas
    assert "Educação" in temas

    kpis = get_kpis_socioeconomicos(MAUA_IBGE_CODE, db_path=test_db_path)
    assert kpis["populacao_censo_2022"] == 418261
    assert kpis["populacao_estimada_recente"] == 429064
    assert kpis["ano_estimativa_recente"] == 2026
    assert kpis["pib_corrente_mil_reais"] == 25000732.02
    assert kpis["pib_per_capita_reais"] == 59773.04
    assert kpis["area_territorial_km2"] == 61.937
    assert kpis["taxa_alfabetizacao_pct"] == 96.74


def test_gold_read_without_filters(test_db_path: Path) -> None:
    """Testa execução das leituras da Gold sem filtro de municipio_id."""
    from desafio_ibge.loading.storage import (
        read_gold_demografia_sexo,
        read_gold_pib_historico,
        read_gold_populacao_historica,
        read_gold_resumo_socioeconomico,
    )

    assert read_gold_populacao_historica(None, db_path=test_db_path).empty
    assert read_gold_pib_historico(None, db_path=test_db_path).empty
    assert read_gold_demografia_sexo(None, db_path=test_db_path).empty
    assert read_gold_resumo_socioeconomico(None, db_path=test_db_path).empty


# ---------------------------------------------------------------------------
# Testes de Volumetria e Governança da Arquitetura Medallion
# ---------------------------------------------------------------------------


def test_get_volumetria_medallion_empty_db(test_db_path: Path) -> None:
    """Verifica que get_volumetria_medallion retorna 0 em banco vazio."""
    from desafio_ibge.loading.storage import (
        CATALOGO_OBJETOS_MEDALLION,
        get_volumetria_medallion,
        init_db,
    )

    init_db(db_path=test_db_path)
    df_vol = get_volumetria_medallion(db_path=test_db_path)

    assert not df_vol.empty
    assert len(df_vol) == len(CATALOGO_OBJETOS_MEDALLION)
    assert set(df_vol["total_registros"]) == {0}
    assert "camada" in df_vol.columns
    assert "dominio" in df_vol.columns
    assert "descricao_granularidade" in df_vol.columns


def test_get_volumetria_medallion_populated(
    test_db_path: Path,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Valida volumetria real e discriminação territorial vs socioeconômica."""
    from desafio_ibge.loading.storage import (
        get_volumetria_medallion,
        init_db,
        save_bronze,
        save_bronze_socioeconomico,
        save_silver,
        save_silver_populacao,
    )

    init_db(db_path=test_db_path)

    # 1. Territorial
    save_bronze(
        maua_raw_payload,
        endpoint_url="https://api/territorial",
        db_path=test_db_path,
    )
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=test_db_path)

    # 2. Socioeconômico Bronze
    save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="censo_pop_area_densidade",
        periodo_referencia="2022",
        raw_payload=[{"ano": 2022, "pop": 418261}],
        endpoint_url="https://api/censo",
        fonte_oficial="IBGE - Censo 2022",
        db_path=test_db_path,
    )

    # 3. Socioeconômico Silver
    df_pop = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "populacao": 418261,
                "tipo_populacao": "Censo Demográfico",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "censo",
            }
        ]
    )
    save_silver_populacao(df_pop, db_path=test_db_path)

    df_vol = get_volumetria_medallion(db_path=test_db_path)

    # Checagens dinâmicas
    bronze_raw = df_vol[df_vol["objeto"] == "bronze_ibge_raw"].iloc[0]
    assert bronze_raw["total_registros"] == 1
    assert bronze_raw["dominio"] == "Territorial"

    bronze_socio = df_vol[df_vol["objeto"] == "bronze_ibge_socioeconomico"].iloc[0]
    assert bronze_socio["total_registros"] == 1
    assert bronze_socio["dominio"] == "Socioeconômico"

    silver_mun = df_vol[df_vol["objeto"] == "silver_municipio"].iloc[0]
    assert silver_mun["total_registros"] == 1
    assert silver_mun["dominio"] == "Territorial"

    silver_pop = df_vol[df_vol["objeto"] == "silver_ibge_populacao"].iloc[0]
    assert silver_pop["total_registros"] == 1
    assert silver_pop["dominio"] == "Socioeconômico"

    gold_pop = df_vol[df_vol["objeto"] == "gold_populacao_historica"].iloc[0]
    assert gold_pop["total_registros"] == 1
    assert gold_pop["dominio"] == "Socioeconômico"


def test_get_metadados_governanca(test_db_path: Path) -> None:
    """Verifica agregação dinâmica de períodos históricos e contagens de indicadores."""
    from desafio_ibge.loading.storage import (
        get_metadados_governanca,
        init_db,
        save_silver_pib,
        save_silver_populacao,
    )

    init_db(db_path=test_db_path)

    # Vazio
    meta_empty = get_metadados_governanca(db_path=test_db_path)
    assert meta_empty["populacao_min_ano"] is None
    assert meta_empty["pib_total_anos"] == 0

    # Popula dados de teste
    df_pop = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2010,
                "populacao": 400000,
                "tipo_populacao": "Censo",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "censo",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2020,
                "populacao": 450000,
                "tipo_populacao": "Estimativa",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "estimativa",
            },
        ]
    )
    save_silver_populacao(df_pop, db_path=test_db_path)

    df_pib = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2015,
                "indicador_id": 46997,
                "indicador_nome": "PIB corrente",
                "valor": 1000000.0,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2018,
                "indicador_id": 47001,
                "indicador_nome": "PIB per capita",
                "valor": 30000.0,
                "unidade": "Reais",
                "tipo_valor": "Per Capita",
                "fonte_oficial": "IBGE",
                "bronze_indicador": "pib",
            },
        ]
    )
    save_silver_pib(df_pib, db_path=test_db_path)

    meta = get_metadados_governanca(db_path=test_db_path)
    assert meta["populacao_min_ano"] == 2010
    assert meta["populacao_max_ano"] == 2020
    assert meta["populacao_total_anos"] == 2

    assert meta["pib_min_ano"] == 2015
    assert meta["pib_max_ano"] == 2018
    assert meta["pib_total_anos"] == 2
    assert meta["pib_total_indicadores"] == 2
    assert meta["total_silver"] == 4


# ---------------------------------------------------------------------------
# Testes de Snapshot e Portabilidade para Nuvem (Deploy Streamlit Cloud)
# ---------------------------------------------------------------------------


def test_export_and_restore_database_snapshot_roundtrip(
    fully_populated_db_path: Path,
    tmp_path: Path,
) -> None:
    """Verifica exportação e restauração de snapshot SQL com integridade total."""
    from desafio_ibge.loading.storage import (
        export_database_snapshot,
        restore_database_snapshot,
    )

    sql_target = tmp_path / "test_snapshot.sql"
    exported_path = export_database_snapshot(
        source_db=fully_populated_db_path,
        target_sql=sql_target,
    )
    assert exported_path.exists()
    assert exported_path.stat().st_size > 0

    restored_db = tmp_path / "test_restored.db"
    total_obj = restore_database_snapshot(
        source_sql=exported_path,
        target_db=restored_db,
    )
    assert total_obj >= 12  # 6 tabelas + 6 views

    df_h = read_gold_hierarquia(db_path=restored_db)
    assert not df_h.empty
    assert df_h["municipio_nome"].iloc[0] == "Mauá"


def test_export_database_snapshot_missing_source(tmp_path: Path) -> None:
    """Testa erro amigável ao exportar snapshot de banco inexistente."""
    from desafio_ibge.loading.storage import export_database_snapshot

    with pytest.raises(FileNotFoundError, match="não encontrado"):
        export_database_snapshot(
            source_db=tmp_path / "nonexistent.db",
            target_sql=tmp_path / "out.sql",
        )


def test_restore_database_snapshot_missing_sql(tmp_path: Path) -> None:
    """Testa erro amigável ao restaurar de script SQL inexistente."""
    from desafio_ibge.loading.storage import restore_database_snapshot

    with pytest.raises(FileNotFoundError, match="não encontrado"):
        restore_database_snapshot(
            source_sql=tmp_path / "nonexistent.sql",
            target_db=tmp_path / "out.db",
        )


def test_ensure_database_ready_with_existing_database(
    fully_populated_db_path: Path,
    tmp_path: Path,
) -> None:
    """Verifica que ensure_database_ready não altera banco já populado."""
    from desafio_ibge.loading.storage import ensure_database_ready

    ready = ensure_database_ready(db_path=fully_populated_db_path)
    assert ready is True


def test_ensure_database_ready_memory_returns_false() -> None:
    """Verifica que ensure_database_ready não atua sobre banco :memory:."""
    from desafio_ibge.loading.storage import ensure_database_ready

    assert ensure_database_ready(db_path=":memory:") is False


def test_ensure_database_ready_auto_restore_with_env(
    fully_populated_db_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica restauração automática acionada por IBGE_AUTO_RESTORE=1."""
    from desafio_ibge.loading.storage import (
        ensure_database_ready,
        export_database_snapshot,
    )

    sql_target = tmp_path / "snapshot.sql"
    export_database_snapshot(
        source_db=fully_populated_db_path,
        target_sql=sql_target,
    )

    new_db = tmp_path / "auto_restored.db"
    assert not new_db.exists()

    monkeypatch.setenv("IBGE_AUTO_RESTORE", "1")
    ready = ensure_database_ready(db_path=new_db, snapshot_path=sql_target)
    assert ready is True
    assert new_db.exists()

    df_h = read_gold_hierarquia(db_path=new_db)
    assert not df_h.empty
