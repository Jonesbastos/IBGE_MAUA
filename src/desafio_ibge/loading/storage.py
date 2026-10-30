"""Módulo de persistência e gerenciamento do banco de dados relacional SQLite.

Implementa as camadas Bronze (armazenamento do payload bruto com metadados e hash)
e Silver (persistência relacional normalizada com restrições e tipagem) da
Medallion Architecture do projeto desafio_IBGE.
"""

import hashlib
import json
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from desafio_ibge.config.settings import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

# Colunas obrigatórias para a camada Silver (conforme schema normalizado)
SILVER_COLUMNS: tuple[str, ...] = (
    "id",
    "nome",
    "microrregiao_id",
    "microrregiao_nome",
    "microrregiao_mesorregiao_id",
    "microrregiao_mesorregiao_nome",
    "microrregiao_mesorregiao_uf_id",
    "microrregiao_mesorregiao_uf_sigla",
    "microrregiao_mesorregiao_uf_nome",
    "microrregiao_mesorregiao_uf_regiao_id",
    "microrregiao_mesorregiao_uf_regiao_sigla",
    "microrregiao_mesorregiao_uf_regiao_nome",
    "regiao_imediata_id",
    "regiao_imediata_nome",
    "regiao_imediata_regiao_intermediaria_id",
    "regiao_imediata_regiao_intermediaria_nome",
    "regiao_imediata_regiao_intermediaria_uf_id",
    "regiao_imediata_regiao_intermediaria_uf_sigla",
    "regiao_imediata_regiao_intermediaria_uf_nome",
    "regiao_imediata_regiao_intermediaria_uf_regiao_id",
    "regiao_imediata_regiao_intermediaria_uf_regiao_sigla",
    "regiao_imediata_regiao_intermediaria_uf_regiao_nome",
)

# DDL da Camada Bronze (armazenamento do JSON bruto e metadados de ingestão)
DDL_BRONZE_RAW = """
CREATE TABLE IF NOT EXISTS bronze_ibge_raw (
    ibge_id INTEGER PRIMARY KEY,
    endpoint_url TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    checksum_sha256 TEXT NOT NULL
);
"""

# DDL da Camada Silver (dados relacionais higienizados em snake_case com restrições)
DDL_SILVER_MUNICIPIO = """
CREATE TABLE IF NOT EXISTS silver_municipio (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    microrregiao_id INTEGER NOT NULL,
    microrregiao_nome TEXT NOT NULL,
    microrregiao_mesorregiao_id INTEGER NOT NULL,
    microrregiao_mesorregiao_nome TEXT NOT NULL,
    microrregiao_mesorregiao_uf_id INTEGER NOT NULL,
    microrregiao_mesorregiao_uf_sigla TEXT NOT NULL,
    microrregiao_mesorregiao_uf_nome TEXT NOT NULL,
    microrregiao_mesorregiao_uf_regiao_id INTEGER NOT NULL,
    microrregiao_mesorregiao_uf_regiao_sigla TEXT NOT NULL,
    microrregiao_mesorregiao_uf_regiao_nome TEXT NOT NULL,
    regiao_imediata_id INTEGER NOT NULL,
    regiao_imediata_nome TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_id INTEGER NOT NULL,
    regiao_imediata_regiao_intermediaria_nome TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_id INTEGER NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_sigla TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_nome TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_regiao_id INTEGER NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_regiao_sigla TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_regiao_nome TEXT NOT NULL,
    transformed_at TEXT NOT NULL
);
"""

# DDL da Camada Gold: View Analítica de Hierarquia Geográfica
DDL_DROP_GOLD_HIERARQUIA = "DROP VIEW IF EXISTS gold_vw_municipio_hierarquia;"
DDL_GOLD_HIERARQUIA = """
CREATE VIEW IF NOT EXISTS gold_vw_municipio_hierarquia AS
SELECT
    id AS municipio_id,
    nome AS municipio_nome,
    microrregiao_mesorregiao_uf_id AS uf_id,
    microrregiao_mesorregiao_uf_sigla AS uf_sigla,
    microrregiao_mesorregiao_uf_nome AS uf_nome,
    microrregiao_mesorregiao_uf_regiao_id AS regiao_id,
    microrregiao_mesorregiao_uf_regiao_sigla AS regiao_sigla,
    microrregiao_mesorregiao_uf_regiao_nome AS regiao_nome,
    regiao_imediata_id AS regiao_imediata_id,
    regiao_imediata_nome AS regiao_imediata_nome,
    regiao_imediata_regiao_intermediaria_id AS regiao_intermediaria_id,
    regiao_imediata_regiao_intermediaria_nome AS regiao_intermediaria_nome,
    microrregiao_id AS microrregiao_id,
    microrregiao_nome AS microrregiao_nome,
    microrregiao_mesorregiao_id AS mesorregiao_id,
    microrregiao_mesorregiao_nome AS mesorregiao_nome,
    transformed_at
FROM silver_municipio;
"""

# DDL da Camada Gold: View de Auditoria e Qualidade de Dados (Data Quality)
DDL_DROP_GOLD_AUDITORIA = "DROP VIEW IF EXISTS gold_vw_qualidade_auditoria;"
DDL_GOLD_AUDITORIA = """
CREATE VIEW IF NOT EXISTS gold_vw_qualidade_auditoria AS
SELECT
    b.ibge_id AS bronze_ibge_id,
    s.id AS silver_id,
    COALESCE(b.ibge_id, s.id) AS municipio_id,
    COALESCE(s.nome, 'NÃO DISPONÍVEL NA SILVER') AS municipio_nome,
    b.endpoint_url,
    b.http_status,
    b.checksum_sha256,
    b.ingestion_timestamp,
    s.transformed_at,
    CASE WHEN b.ibge_id IS NOT NULL THEN 1 ELSE 0 END AS flag_presente_bronze,
    CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END AS flag_presente_silver,
    CASE
        WHEN b.ibge_id IS NOT NULL AND s.id IS NOT NULL THEN 'CONFORME'
        WHEN b.ibge_id IS NOT NULL AND s.id IS NULL THEN 'AUSENTE_NA_SILVER'
        WHEN b.ibge_id IS NULL AND s.id IS NOT NULL THEN 'AUSENTE_NA_BRONZE'
        ELSE 'INDEFINIDO'
    END AS status_integracao,
    CASE
        WHEN (b.ibge_id BETWEEN 1000000 AND 9999999)
             OR (s.id BETWEEN 1000000 AND 9999999)
        THEN 1
        ELSE 0
    END AS flag_codigo_ibge_valido,
    CASE
        WHEN b.checksum_sha256 IS NOT NULL AND length(b.checksum_sha256) = 64
        THEN 1
        ELSE 0
    END AS flag_checksum_valido,
    CASE
        WHEN b.http_status = 200 THEN 1
        ELSE 0
    END AS flag_http_ok,
    CASE
        WHEN s.id IS NOT NULL AND (
            s.nome IS NULL OR trim(s.nome) = '' OR
            s.microrregiao_id IS NULL OR
            s.microrregiao_mesorregiao_uf_sigla IS NULL OR
            s.regiao_imediata_id IS NULL
        ) THEN 1
        ELSE 0
    END AS flag_campos_obrigatorios_nulos,
    CASE
        WHEN s.id IS NOT NULL AND (
            s.microrregiao_mesorregiao_uf_sigla =
                s.regiao_imediata_regiao_intermediaria_uf_sigla
            AND s.microrregiao_mesorregiao_uf_regiao_sigla =
                s.regiao_imediata_regiao_intermediaria_uf_regiao_sigla
        ) THEN 1
        WHEN s.id IS NOT NULL THEN 0
        ELSE NULL
    END AS flag_consistencia_geografica,
    CASE
        WHEN b.ingestion_timestamp IS NOT NULL AND s.transformed_at IS NOT NULL
        THEN ROUND(
            (julianday(s.transformed_at) - julianday(b.ingestion_timestamp)) * 86400.0,
            2
        )
        ELSE NULL
    END AS latencia_processamento_segundos
FROM bronze_ibge_raw b
LEFT JOIN silver_municipio s ON b.ibge_id = s.id

UNION ALL

SELECT
    NULL AS bronze_ibge_id,
    s.id AS silver_id,
    s.id AS municipio_id,
    s.nome AS municipio_nome,
    NULL AS endpoint_url,
    NULL AS http_status,
    NULL AS checksum_sha256,
    NULL AS ingestion_timestamp,
    s.transformed_at,
    0 AS flag_presente_bronze,
    1 AS flag_presente_silver,
    'AUSENTE_NA_BRONZE' AS status_integracao,
    CASE
        WHEN s.id BETWEEN 1000000 AND 9999999 THEN 1
        ELSE 0
    END AS flag_codigo_ibge_valido,
    0 AS flag_checksum_valido,
    0 AS flag_http_ok,
    CASE
        WHEN (
            s.nome IS NULL OR trim(s.nome) = '' OR
            s.microrregiao_id IS NULL OR
            s.microrregiao_mesorregiao_uf_sigla IS NULL OR
            s.regiao_imediata_id IS NULL
        ) THEN 1
        ELSE 0
    END AS flag_campos_obrigatorios_nulos,
    CASE
        WHEN (
            s.microrregiao_mesorregiao_uf_sigla =
                s.regiao_imediata_regiao_intermediaria_uf_sigla
            AND s.microrregiao_mesorregiao_uf_regiao_sigla =
                s.regiao_imediata_regiao_intermediaria_uf_regiao_sigla
        ) THEN 1
        ELSE 0
    END AS flag_consistencia_geografica,
    NULL AS latencia_processamento_segundos
FROM silver_municipio s
WHERE s.id NOT IN (SELECT ibge_id FROM bronze_ibge_raw);
"""


class IBGEStorageError(Exception):
    """Exceção base para erros operacionais na camada de armazenamento."""


class IBGEStorageTransactionError(IBGEStorageError):
    """Lançada quando uma transação no SQLite falha e sofre rollback."""


def resolve_db_path(db_path: Path | str | None = None) -> Path | str:
    """Resolve e prepara o caminho de destino do banco de dados SQLite.

    Args:
        db_path: Caminho para o arquivo SQLite ou None para o padrão.

    Returns:
        Caminho resolvido (Path ou ":memory:").
    """
    if db_path is None:
        target = DEFAULT_DB_PATH
    elif isinstance(db_path, str) and db_path == ":memory:":
        return ":memory:"
    else:
        target = Path(db_path)

    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def get_db_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Cria e configura uma conexão com o banco de dados SQLite.

    Habilita chaves estrangeiras, modo WAL (para arquivos em disco) e busy timeout.

    Args:
        db_path: Caminho para o banco ou ":memory:".

    Returns:
        Instância configurada de sqlite3.Connection com Row factory.
    """
    target = resolve_db_path(db_path)
    conn = sqlite3.connect(str(target), timeout=10.0)
    conn.row_factory = sqlite3.Row

    if target != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


@contextmanager
def db_transaction(
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> Generator[sqlite3.Connection]:
    """Gerencia transações no SQLite com commit automático ou rollback em falha.

    Args:
        db_path: Caminho para o banco (ignorado se conn for fornecido).
        conn: Conexão existente opcional para compartilhamento de sessão.

    Yields:
        Conexão com transação aberta.

    Raises:
        IBGEStorageTransactionError: Em caso de falha de execução de comandos SQL.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection(db_path)
        should_close = True

    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("Falha na transação do SQLite. Rollback executado: %s", exc)
        raise IBGEStorageTransactionError(f"Erro transacional no banco: {exc}") from exc
    finally:
        if should_close:
            conn.close()


def init_db(
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Inicializa as tabelas Bronze/Silver e as Views analíticas Gold no SQLite.

    Garante recriação idempotente das Views para refletir alterações de schema.

    Args:
        db_path: Caminho do banco SQLite.
        conn: Conexão opcional existente.
    """
    with db_transaction(db_path=db_path, conn=conn) as active_conn:
        active_conn.execute(DDL_BRONZE_RAW)
        active_conn.execute(DDL_SILVER_MUNICIPIO)
        # Sincronização idempotente das Views da camada Gold
        active_conn.execute(DDL_DROP_GOLD_HIERARQUIA)
        active_conn.execute(DDL_GOLD_HIERARQUIA)
        active_conn.execute(DDL_DROP_GOLD_AUDITORIA)
        active_conn.execute(DDL_GOLD_AUDITORIA)
        logger.info("Tabelas Bronze/Silver e Views Gold inicializadas e sincronizadas.")


# ---------------------------------------------------------------------------
# Operações da Camada Bronze (Raw Ingestion)
# ---------------------------------------------------------------------------


def save_bronze(
    raw_payload: dict[str, Any],
    endpoint_url: str,
    http_status: int = 200,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> str:
    """Persiste o payload bruto da API na camada Bronze de forma idempotente.

    Armazena o JSON original sem desaninhamento, acompanhado de carimbo UTC,
    URL de origem e hash SHA-256 para controle de integridade.

    Args:
        raw_payload: Dicionário retornado pela API do IBGE contendo a chave 'id'.
        endpoint_url: URL consultada para obter o dado.
        http_status: Código de status HTTP da requisição.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        String hexadecimal do checksum SHA-256 gerado.

    Raises:
        IBGEStorageError: Se o payload for inválido ou não contiver a chave 'id'.
    """
    if not isinstance(raw_payload, dict) or "id" not in raw_payload:
        msg = "Payload Bronze inválido. Deve ser um dict contendo a chave 'id'."
        logger.error(msg)
        raise IBGEStorageError(msg)

    ibge_id = int(raw_payload["id"])
    json_str = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True)
    checksum = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
    timestamp = datetime.now(UTC).isoformat()

    query = """
    INSERT INTO bronze_ibge_raw (
        ibge_id, endpoint_url, payload_json,
        ingestion_timestamp, http_status, checksum_sha256
    ) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(ibge_id) DO UPDATE SET
        endpoint_url = excluded.endpoint_url,
        payload_json = excluded.payload_json,
        ingestion_timestamp = excluded.ingestion_timestamp,
        http_status = excluded.http_status,
        checksum_sha256 = excluded.checksum_sha256;
    """

    init_db(db_path=db_path, conn=conn)

    with db_transaction(db_path=db_path, conn=conn) as active_conn:
        active_conn.execute(
            query,
            (ibge_id, endpoint_url, json_str, timestamp, http_status, checksum),
        )
        logger.info(
            "Camada Bronze atualizada para município %d. Hash: %s",
            ibge_id,
            checksum[:8],
        )

    return checksum


def read_bronze(
    ibge_id: int,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Recupera o payload JSON original armazenado na Bronze para reprocessamento.

    Args:
        ibge_id: Código IBGE do município.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        Dicionário desaninhado original ou None se não encontrado.
    """
    query = "SELECT payload_json FROM bronze_ibge_raw WHERE ibge_id = ?;"
    close_after = False

    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        cursor = conn.execute(query, (ibge_id,))
        row = cursor.fetchone()
        if row:
            data: dict[str, Any] = json.loads(row["payload_json"])
            return data
        return None
    finally:
        if close_after:
            conn.close()


def read_bronze_record(
    ibge_id: int,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Recupera o registro completo da camada Bronze com todos os metadados.

    Args:
        ibge_id: Código IBGE do município.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        Dicionário contendo todos os atributos de auditoria da linha ou None.
    """
    query = "SELECT * FROM bronze_ibge_raw WHERE ibge_id = ?;"
    close_after = False

    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        cursor = conn.execute(query, (ibge_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if close_after:
            conn.close()


# ---------------------------------------------------------------------------
# Operações da Camada Silver (Conformed & Cleansed)
# ---------------------------------------------------------------------------


def save_silver(
    df: pd.DataFrame,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Persiste dados higienizados e normalizados na Silver com idempotência (UPSERT).

    Args:
        df: DataFrame Pandas contendo as 22 colunas mapeadas no schema.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        Número de registros persistidos/atualizados na camada Silver.

    Raises:
        IBGEStorageError: Se o DataFrame for vazio ou faltar colunas obrigatórias.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        msg = "DataFrame inválido ou vazio para persistência na camada Silver."
        logger.error(msg)
        raise IBGEStorageError(msg)

    # Validação de presença das colunas obrigatórias
    missing_cols = [col for col in SILVER_COLUMNS if col not in df.columns]
    if missing_cols:
        msg = f"Colunas obrigatórias ausentes no DataFrame Silver: {missing_cols}"
        logger.error(msg)
        raise IBGEStorageError(msg)

    init_db(db_path=db_path, conn=conn)

    timestamp = datetime.now(UTC).isoformat()
    cols_sql = ", ".join(SILVER_COLUMNS) + ", transformed_at"
    placeholders = ", ".join(["?"] * (len(SILVER_COLUMNS) + 1))

    update_clauses = [
        f"{col} = excluded.{col}" for col in SILVER_COLUMNS if col != "id"
    ]
    update_clauses.append("transformed_at = excluded.transformed_at")
    update_sql = ", ".join(update_clauses)

    upsert_query = f"""
    INSERT INTO silver_municipio ({cols_sql})
    VALUES ({placeholders})
    ON CONFLICT(id) DO UPDATE SET
        {update_sql};
    """

    records_count = 0
    with db_transaction(db_path=db_path, conn=conn) as active_conn:
        for _, row in df.iterrows():
            values = [row[col] for col in SILVER_COLUMNS]
            values.append(timestamp)
            active_conn.execute(upsert_query, values)
            records_count += 1

        logger.info("Camada Silver atualizada com %d registro(s).", records_count)

    return records_count


def read_silver(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta dados estruturados da camada Silver retornando um DataFrame Pandas.

    Args:
        municipio_id: ID específico para consulta pontual, ou None para todos.
        db_path: Caminho do banco SQLite.
        conn: Conexão opcional.

    Returns:
        DataFrame Pandas contendo os registros encontrados.
    """
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = "SELECT * FROM silver_municipio WHERE id = ?;"
            cursor = conn.execute(query, (municipio_id,))
        else:
            query = "SELECT * FROM silver_municipio ORDER BY id;"
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()

        data = [dict(row) for row in rows]
        df = pd.DataFrame(data)
        return df
    finally:
        if close_after:
            conn.close()


# ---------------------------------------------------------------------------
# Operações da Camada Gold (Analytical Views & Data Quality Metrics)
# ---------------------------------------------------------------------------


def read_gold_hierarquia(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta dados analíticos da View Gold de hierarquia geográfica.

    Retorna os nós territoriais estruturados em snake_case para apresentação
    analítica, preservando as árvores de 1989 e 2017 do IBGE.

    Args:
        municipio_id: Código IBGE opcional para filtro pontual.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        DataFrame Pandas contendo a árvore geográfica padronizada.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = "SELECT * FROM gold_vw_municipio_hierarquia WHERE municipio_id = ?;"
            cursor = conn.execute(query, (municipio_id,))
        else:
            query = "SELECT * FROM gold_vw_municipio_hierarquia ORDER BY municipio_id;"
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()

        data = [dict(row) for row in rows]
        return pd.DataFrame(data)
    finally:
        if close_after:
            conn.close()


def read_gold_auditoria(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta indicadores de Data Quality e integridade da View Gold de auditoria.

    Cruza Bronze e Silver identificando conformidade, falhas de schema, registros
    órfãos e latência de processamento em segundos.

    Args:
        municipio_id: Código IBGE opcional para filtro pontual.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        DataFrame Pandas contendo o relatório de auditoria e métricas de qualidade.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = "SELECT * FROM gold_vw_qualidade_auditoria WHERE municipio_id = ?;"
            cursor = conn.execute(query, (municipio_id,))
        else:
            query = "SELECT * FROM gold_vw_qualidade_auditoria ORDER BY municipio_id;"
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()

        data = [dict(row) for row in rows]
        return pd.DataFrame(data)
    finally:
        if close_after:
            conn.close()


def get_kpis_geograficos(
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Calcula KPIs e agregações geográficas a partir da camada Gold.

    Função reutilizável pelo Dashboard analítico para sumarização de distribuição
    territorial baseada estritamente nos dados oficiais persistidos.

    Args:
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        Dicionário com total de municípios e distribuições por UF, Região e Áreas.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        total_cursor = conn.execute(
            "SELECT COUNT(*) AS total FROM gold_vw_municipio_hierarquia;"
        )
        total_municipios = total_cursor.fetchone()["total"]

        def _get_counts(column: str) -> dict[str, int]:
            query = f"""
            SELECT {column} AS label, COUNT(*) AS count
            FROM gold_vw_municipio_hierarquia
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            ORDER BY count DESC, label ASC;
            """
            cursor = conn.execute(query)
            return {row["label"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_municipios": total_municipios,
            "municipios_por_uf": _get_counts("uf_sigla"),
            "municipios_por_regiao": _get_counts("regiao_nome"),
            "municipios_por_regiao_intermediaria": _get_counts(
                "regiao_intermediaria_nome"
            ),
            "municipios_por_regiao_imediata": _get_counts("regiao_imediata_nome"),
        }
    finally:
        if close_after:
            conn.close()


def get_kpis_qualidade(
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Calcula indicadores analíticos de Data Quality e governança da camada Gold.

    Calcula taxas de conformidade, total de registros conformes e pendentes,
    ocorrência de valores nulos e carimbos de última ingestão/transformação.

    Args:
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        Dicionário com métricas agregadas de qualidade prontas para visualização.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        query = """
        SELECT
            COUNT(*) AS total_registros_auditados,
            COALESCE(SUM(flag_presente_bronze), 0) AS total_presente_bronze,
            COALESCE(SUM(flag_presente_silver), 0) AS total_presente_silver,
            COALESCE(
                SUM(CASE WHEN status_integracao = 'CONFORME' THEN 1 ELSE 0 END),
                0
            ) AS total_conforme,
            COALESCE(
                SUM(
                    CASE WHEN status_integracao = 'AUSENTE_NA_SILVER'
                    THEN 1 ELSE 0 END
                ),
                0
            ) AS total_ausente_silver,
            COALESCE(
                SUM(
                    CASE WHEN status_integracao = 'AUSENTE_NA_BRONZE'
                    THEN 1 ELSE 0 END
                ),
                0
            ) AS total_ausente_bronze,
            COALESCE(SUM(flag_campos_obrigatorios_nulos), 0) AS total_campos_nulos,
            COALESCE(
                SUM(CASE WHEN flag_codigo_ibge_valido = 1 THEN 1 ELSE 0 END),
                0
            ) AS total_codigos_validos,
            COALESCE(
                SUM(CASE WHEN flag_checksum_valido = 1 THEN 1 ELSE 0 END),
                0
            ) AS total_checksums_validos,
            COALESCE(
                SUM(CASE WHEN flag_http_ok = 1 THEN 1 ELSE 0 END),
                0
            ) AS total_http_ok,
            COALESCE(
                SUM(CASE WHEN flag_consistencia_geografica = 1 THEN 1 ELSE 0 END),
                0
            ) AS total_consistencia_geografica,
            MAX(ingestion_timestamp) AS ultima_ingestao_utc,
            MAX(transformed_at) AS ultima_transformacao_utc,
            AVG(latencia_processamento_segundos) AS latencia_media_segundos
        FROM gold_vw_qualidade_auditoria;
        """
        cursor = conn.execute(query)
        row = cursor.fetchone()

        total_auditados = row["total_registros_auditados"] or 0
        total_conforme = row["total_conforme"] or 0
        taxa_conformidade = (
            round((total_conforme / total_auditados) * 100.0, 2)
            if total_auditados > 0
            else 0.0
        )

        latencia = row["latencia_media_segundos"]
        latencia_arredondada = round(latencia, 2) if latencia is not None else None

        return {
            "total_registros_auditados": total_auditados,
            "total_presente_bronze": row["total_presente_bronze"],
            "total_presente_silver": row["total_presente_silver"],
            "total_conforme": total_conforme,
            "total_ausente_silver": row["total_ausente_silver"],
            "total_ausente_bronze": row["total_ausente_bronze"],
            "total_falhas_qualidade": (
                row["total_campos_nulos"]
                + row["total_ausente_silver"]
                + row["total_ausente_bronze"]
            ),
            "taxa_conformidade_pct": taxa_conformidade,
            "total_campos_nulos": row["total_campos_nulos"],
            "total_codigos_validos": row["total_codigos_validos"],
            "total_checksums_validos": row["total_checksums_validos"],
            "total_http_ok": row["total_http_ok"],
            "total_consistencia_geografica": row["total_consistencia_geografica"],
            "latencia_media_segundos": latencia_arredondada,
            "ultima_ingestao_utc": row["ultima_ingestao_utc"],
            "ultima_transformacao_utc": row["ultima_transformacao_utc"],
        }
    finally:
        if close_after:
            conn.close()
