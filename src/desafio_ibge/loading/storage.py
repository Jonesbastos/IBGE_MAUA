"""Módulo de persistência e gerenciamento do banco de dados relacional SQLite.

Implementa as camadas Bronze (armazenamento do payload bruto com metadados e hash)
e Silver (persistência relacional normalizada com restrições e tipagem) da
Medallion Architecture do projeto desafio_IBGE.
"""

import hashlib
import json
import logging
import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from desafio_ibge.config.settings import DEFAULT_DB_PATH, DEFAULT_SNAPSHOT_PATH

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

# DDL da Camada Bronze Socioeconômica (JSON bruto de indicadores e séries históricas)
DDL_BRONZE_SOCIOECONOMICO = """
CREATE TABLE IF NOT EXISTS bronze_ibge_socioeconomico (
    municipio_id INTEGER NOT NULL,
    indicador TEXT NOT NULL,
    periodo_referencia TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    endpoint_url TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
    PRIMARY KEY (municipio_id, indicador, periodo_referencia)
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

# DDL da Camada Silver: Contagens e Estimativas Populacionais Históricas
DDL_SILVER_IBGE_POPULACAO = """
CREATE TABLE IF NOT EXISTS silver_ibge_populacao (
    municipio_id INTEGER NOT NULL,
    ano_referencia INTEGER NOT NULL,
    populacao INTEGER NOT NULL,
    tipo_populacao TEXT NOT NULL,
    unidade TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    bronze_indicador TEXT NOT NULL,
    transformed_at TEXT NOT NULL,
    PRIMARY KEY (municipio_id, ano_referencia, tipo_populacao)
);
"""

# DDL da Camada Silver: PIB Municipal e VAB Setorial
DDL_SILVER_IBGE_PIB = """
CREATE TABLE IF NOT EXISTS silver_ibge_pib (
    municipio_id INTEGER NOT NULL,
    ano_referencia INTEGER NOT NULL,
    indicador_id INTEGER NOT NULL,
    indicador_nome TEXT NOT NULL,
    valor REAL NOT NULL,
    unidade TEXT NOT NULL,
    tipo_valor TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    bronze_indicador TEXT NOT NULL,
    transformed_at TEXT NOT NULL,
    PRIMARY KEY (municipio_id, ano_referencia, indicador_id)
);
"""

# DDL da Camada Silver: Dados Censitários Detalhados
DDL_SILVER_IBGE_CENSITARIO = """
CREATE TABLE IF NOT EXISTS silver_ibge_censitario (
    municipio_id INTEGER NOT NULL,
    ano_referencia INTEGER NOT NULL,
    variavel_id INTEGER NOT NULL,
    variavel_nome TEXT NOT NULL,
    categoria_classificacao TEXT NOT NULL,
    valor REAL NOT NULL,
    unidade TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    bronze_indicador TEXT NOT NULL,
    transformed_at TEXT NOT NULL,
    PRIMARY KEY (municipio_id, ano_referencia, variavel_id, categoria_classificacao)
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

# DDL da Camada Gold: População Histórica e Variações Metodológicas
DDL_DROP_GOLD_POPULACAO_HISTORICA = "DROP VIEW IF EXISTS gold_populacao_historica;"
DDL_GOLD_POPULACAO_HISTORICA = """
CREATE VIEW IF NOT EXISTS gold_populacao_historica AS
WITH pop_base AS (
    SELECT
        p.municipio_id,
        m.nome AS municipio_nome,
        p.ano_referencia,
        p.populacao,
        p.tipo_populacao,
        p.unidade,
        p.fonte_oficial,
        LAG(p.ano_referencia) OVER (
            PARTITION BY p.municipio_id, p.tipo_populacao
            ORDER BY p.ano_referencia
        ) AS ano_anterior,
        LAG(p.populacao) OVER (
            PARTITION BY p.municipio_id, p.tipo_populacao
            ORDER BY p.ano_referencia
        ) AS pop_anterior
    FROM silver_ibge_populacao p
    LEFT JOIN silver_municipio m ON p.municipio_id = m.id
)
SELECT
    municipio_id,
    municipio_nome,
    ano_referencia,
    populacao,
    tipo_populacao,
    unidade,
    CASE
        WHEN pop_anterior IS NOT NULL THEN (populacao - pop_anterior)
        ELSE NULL
    END AS variacao_absoluta_anterior,
    CASE
        WHEN pop_anterior IS NOT NULL THEN
            ROUND(((populacao - pop_anterior) * 100.0) / NULLIF(pop_anterior, 0), 2)
        ELSE NULL
    END AS variacao_percentual_anterior,
    CASE
        WHEN ano_anterior IS NULL THEN NULL
        WHEN (ano_referencia - ano_anterior) = 1 THEN 1
        ELSE 0
    END AS flag_anos_consecutivos,
    fonte_oficial
FROM pop_base;
"""

# DDL da Camada Gold: PIB Municipal Histórico, Per Capita e VAB Setorial
DDL_DROP_GOLD_PIB_HISTORICO = "DROP VIEW IF EXISTS gold_pib_historico;"
DDL_GOLD_PIB_HISTORICO = """
CREATE VIEW IF NOT EXISTS gold_pib_historico AS
WITH pib_pivot AS (
    SELECT
        p.municipio_id,
        m.nome AS municipio_nome,
        p.ano_referencia,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 46997 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 46998 THEN p.valor END)
        ) AS pib_corrente_mil_reais,
        MAX(CASE WHEN p.indicador_id = 47001 THEN p.valor END) AS pib_per_capita_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47006 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47010 THEN p.valor END)
        ) AS vab_agropecuaria_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47007 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47012 THEN p.valor END)
        ) AS vab_industria_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47008 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47013 THEN p.valor END)
        ) AS vab_servicos_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47009 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47014 THEN p.valor END)
        ) AS vab_administracao_publica_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47004 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47015 THEN p.valor END)
        ) AS vab_total_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47022 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47023 THEN p.valor END)
        ) AS impostos_mil_reais,
        'IBGE - Produto Interno Bruto dos Municípios' AS fonte_oficial
    FROM silver_ibge_pib p
    LEFT JOIN silver_municipio m ON p.municipio_id = m.id
    GROUP BY p.municipio_id, m.nome, p.ano_referencia
),
pib_lag AS (
    SELECT
        *,
        LAG(pib_corrente_mil_reais) OVER (
            PARTITION BY municipio_id ORDER BY ano_referencia
        ) AS pib_anterior,
        LAG(pib_per_capita_reais) OVER (
            PARTITION BY municipio_id ORDER BY ano_referencia
        ) AS pib_per_capita_anterior,
        LAG(ano_referencia) OVER (
            PARTITION BY municipio_id ORDER BY ano_referencia
        ) AS ano_anterior
    FROM pib_pivot
)
SELECT
    municipio_id,
    municipio_nome,
    ano_referencia,
    pib_corrente_mil_reais,
    pib_per_capita_reais,
    vab_agropecuaria_mil_reais,
    vab_industria_mil_reais,
    vab_servicos_mil_reais,
    vab_administracao_publica_mil_reais,
    vab_total_mil_reais,
    impostos_mil_reais,
    'Mil Reais' AS unidade_pib,
    'Reais' AS unidade_per_capita,
    CASE
        WHEN pib_anterior IS NOT NULL
             AND (ano_referencia - ano_anterior) = 1 THEN
            ROUND(
                ((pib_corrente_mil_reais - pib_anterior) * 100.0)
                / NULLIF(pib_anterior, 0),
                2
            )
        ELSE NULL
    END AS variacao_nominal_pib_pct,
    CASE
        WHEN pib_per_capita_anterior IS NOT NULL
             AND (ano_referencia - ano_anterior) = 1 THEN
            ROUND(
                ((pib_per_capita_reais - pib_per_capita_anterior) * 100.0)
                / NULLIF(pib_per_capita_anterior, 0),
                2
            )
        ELSE NULL
    END AS variacao_nominal_per_capita_pct,
    ROUND(
        (vab_agropecuaria_mil_reais * 100.0) / NULLIF(vab_total_mil_reais, 0),
        2
    ) AS participacao_agropecuaria_vab_pct,
    ROUND(
        (vab_industria_mil_reais * 100.0) / NULLIF(vab_total_mil_reais, 0),
        2
    ) AS participacao_industria_vab_pct,
    ROUND(
        (vab_servicos_mil_reais * 100.0) / NULLIF(vab_total_mil_reais, 0),
        2
    ) AS participacao_servicos_vab_pct,
    ROUND(
        (vab_administracao_publica_mil_reais * 100.0)
        / NULLIF(vab_total_mil_reais, 0),
        2
    ) AS participacao_administracao_publica_vab_pct,
    fonte_oficial
FROM pib_lag;
"""

# DDL da Camada Gold: Demografia por Sexo e Razão de Sexo
DDL_DROP_GOLD_DEMOGRAFIA_SEXO = "DROP VIEW IF EXISTS gold_demografia_sexo;"
DDL_GOLD_DEMOGRAFIA_SEXO = """
CREATE VIEW IF NOT EXISTS gold_demografia_sexo AS
WITH sexo_agg AS (
    SELECT
        c.municipio_id,
        m.nome AS municipio_nome,
        c.ano_referencia,
        MAX(
            CASE WHEN c.categoria_classificacao = 'Homens'
                 THEN c.valor END
        ) AS populacao_masculina,
        MAX(
            CASE WHEN c.categoria_classificacao = 'Mulheres'
                 THEN c.valor END
        ) AS populacao_feminina,
        c.fonte_oficial
    FROM silver_ibge_censitario c
    LEFT JOIN silver_municipio m ON c.municipio_id = m.id
    WHERE c.variavel_nome LIKE '%sexo%'
       OR c.categoria_classificacao IN ('Homens', 'Mulheres')
    GROUP BY c.municipio_id, m.nome, c.ano_referencia, c.fonte_oficial
)
SELECT
    municipio_id,
    municipio_nome,
    ano_referencia,
    CAST(populacao_masculina AS INTEGER) AS populacao_masculina,
    CAST(populacao_feminina AS INTEGER) AS populacao_feminina,
    CAST((populacao_masculina + populacao_feminina) AS INTEGER)
        AS populacao_total,
    ROUND(
        (populacao_masculina * 100.0)
        / NULLIF(populacao_masculina + populacao_feminina, 0),
        2
    ) AS participacao_masculina_pct,
    ROUND(
        (populacao_feminina * 100.0)
        / NULLIF(populacao_masculina + populacao_feminina, 0),
        2
    ) AS participacao_feminina_pct,
    ROUND(
        (populacao_masculina * 100.0) / NULLIF(populacao_feminina, 0),
        2
    ) AS razao_sexo,
    fonte_oficial
FROM sexo_agg;
"""

# DDL da Camada Gold: Resumo Consolidado Socioeconômico
DDL_DROP_GOLD_RESUMO_SOCIOECONOMICO = "DROP VIEW IF EXISTS gold_resumo_socioeconomico;"
DDL_GOLD_RESUMO_SOCIOECONOMICO = """
CREATE VIEW IF NOT EXISTS gold_resumo_socioeconomico AS
SELECT
    p.municipio_id,
    m.nome AS municipio_nome,
    'Demografia' AS tema,
    'População residente total (Censo 2022)' AS indicador,
    p.populacao AS valor,
    p.unidade,
    p.ano_referencia,
    p.fonte_oficial,
    p.transformed_at
FROM silver_ibge_populacao p
LEFT JOIN silver_municipio m ON p.municipio_id = m.id
WHERE p.tipo_populacao = 'Censo Demográfico'

UNION ALL

SELECT
    p.municipio_id,
    m.nome AS municipio_nome,
    'Demografia' AS tema,
    'População residente estimada mais recente' AS indicador,
    p.populacao AS valor,
    p.unidade,
    p.ano_referencia,
    p.fonte_oficial,
    p.transformed_at
FROM silver_ibge_populacao p
LEFT JOIN silver_municipio m ON p.municipio_id = m.id
WHERE p.tipo_populacao = 'Estimativa Populacional'
  AND p.ano_referencia = (
      SELECT MAX(ano_referencia) FROM silver_ibge_populacao
      WHERE tipo_populacao = 'Estimativa Populacional'
  )

UNION ALL

SELECT
    c.municipio_id,
    m.nome AS municipio_nome,
    CASE
        WHEN c.variavel_nome LIKE '%sexo%' THEN 'Demografia'
        WHEN c.variavel_nome LIKE '%alfabetiz%' THEN 'Educação'
        ELSE 'Território'
    END AS tema,
    c.variavel_nome || CASE
        WHEN c.categoria_classificacao != 'Total'
        THEN ' (' || c.categoria_classificacao || ')'
        ELSE ''
    END AS indicador,
    c.valor,
    c.unidade,
    c.ano_referencia,
    c.fonte_oficial,
    c.transformed_at
FROM silver_ibge_censitario c
LEFT JOIN silver_municipio m ON c.municipio_id = m.id

UNION ALL

SELECT
    pib.municipio_id,
    pib.municipio_nome,
    'Economia' AS tema,
    'Produto Interno Bruto a preços correntes' AS indicador,
    pib.pib_corrente_mil_reais AS valor,
    pib.unidade_pib AS unidade,
    pib.ano_referencia,
    pib.fonte_oficial,
    pib.transformed_at
FROM (
    SELECT
        p.municipio_id,
        m.nome AS municipio_nome,
        p.ano_referencia,
        p.valor AS pib_corrente_mil_reais,
        p.unidade AS unidade_pib,
        p.fonte_oficial,
        p.transformed_at
    FROM silver_ibge_pib p
    LEFT JOIN silver_municipio m ON p.municipio_id = m.id
    WHERE p.indicador_id = 46997
      AND p.ano_referencia = (
          SELECT MAX(ano_referencia) FROM silver_ibge_pib WHERE indicador_id = 46997
      )
) pib

UNION ALL

SELECT
    pib.municipio_id,
    pib.municipio_nome,
    'Economia' AS tema,
    'Produto Interno Bruto per capita' AS indicador,
    pib.pib_per_capita_reais AS valor,
    pib.unidade_per_capita AS unidade,
    pib.ano_referencia,
    pib.fonte_oficial,
    pib.transformed_at
FROM (
    SELECT
        p.municipio_id,
        m.nome AS municipio_nome,
        p.ano_referencia,
        p.valor AS pib_per_capita_reais,
        p.unidade AS unidade_per_capita,
        p.fonte_oficial,
        p.transformed_at
    FROM silver_ibge_pib p
    LEFT JOIN silver_municipio m ON p.municipio_id = m.id
    WHERE p.indicador_id = 47001
      AND p.ano_referencia = (
          SELECT MAX(ano_referencia) FROM silver_ibge_pib WHERE indicador_id = 47001
      )
) pib;
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
        active_conn.execute(DDL_BRONZE_SOCIOECONOMICO)
        active_conn.execute(DDL_SILVER_MUNICIPIO)
        active_conn.execute(DDL_SILVER_IBGE_POPULACAO)
        active_conn.execute(DDL_SILVER_IBGE_PIB)
        active_conn.execute(DDL_SILVER_IBGE_CENSITARIO)
        # Sincronização idempotente das Views da camada Gold
        active_conn.execute(DDL_DROP_GOLD_HIERARQUIA)
        active_conn.execute(DDL_GOLD_HIERARQUIA)
        active_conn.execute(DDL_DROP_GOLD_AUDITORIA)
        active_conn.execute(DDL_GOLD_AUDITORIA)
        active_conn.execute(DDL_DROP_GOLD_POPULACAO_HISTORICA)
        active_conn.execute(DDL_GOLD_POPULACAO_HISTORICA)
        active_conn.execute(DDL_DROP_GOLD_PIB_HISTORICO)
        active_conn.execute(DDL_GOLD_PIB_HISTORICO)
        active_conn.execute(DDL_DROP_GOLD_DEMOGRAFIA_SEXO)
        active_conn.execute(DDL_GOLD_DEMOGRAFIA_SEXO)
        active_conn.execute(DDL_DROP_GOLD_RESUMO_SOCIOECONOMICO)
        active_conn.execute(DDL_GOLD_RESUMO_SOCIOECONOMICO)
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


def canonical_json_sha256(payload: Any) -> tuple[str, str]:
    """Serializa o payload em JSON canônico determinístico e calcula o SHA-256.

    Args:
        payload: Dict ou List retornado pela API.

    Returns:
        Tupla com (json_string_canonica, checksum_sha256_hex).
    """
    json_str = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    checksum = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
    return json_str, checksum


def save_bronze_socioeconomico(
    municipio_id: int,
    indicador: str,
    periodo_referencia: str,
    fonte_oficial: str,
    endpoint_url: str,
    raw_payload: Any,
    http_status: int = 200,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> str:
    """Persiste o payload bruto socioeconômico na Bronze com idempotência.

    Implementa UPSERT idempotente baseado na chave composta:
    (municipio_id, indicador, periodo_referencia).

    Args:
        municipio_id: Código IBGE do município (ex: 3529401).
        indicador: Nome identificador do indicador (ex: 'censo_pop_area_densidade').
        periodo_referencia: Período coberto (ex: '2022', '2001-2026', '2002-2023').
        fonte_oficial: Nome da fonte oficial do IBGE.
        endpoint_url: URL consultada para a extração.
        raw_payload: Dict ou List com os dados brutos da API.
        http_status: Código de status HTTP da resposta.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        String hexadecimal do checksum SHA-256 gerado deterministicamente.

    Raises:
        IBGEStorageError: Se os identificadores ou payload forem inválidos.
    """
    if not indicador or not periodo_referencia or not fonte_oficial:
        msg = (
            "Campos identificadores (indicador, periodo_referencia, fonte_oficial) "
            "são obrigatórios para a camada Bronze socioeconômica."
        )
        logger.error(msg)
        raise IBGEStorageError(msg)

    if not isinstance(raw_payload, (dict, list)):
        msg = (
            f"Payload inválido para o indicador {indicador}: "
            f"esperado dict ou list, recebido {type(raw_payload).__name__}."
        )
        logger.error(msg)
        raise IBGEStorageError(msg)

    json_str, checksum = canonical_json_sha256(raw_payload)
    timestamp = datetime.now(UTC).isoformat()

    query = """
    INSERT INTO bronze_ibge_socioeconomico (
        municipio_id, indicador, periodo_referencia,
        fonte_oficial, endpoint_url, payload_json,
        checksum_sha256, http_status, ingestion_timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(municipio_id, indicador, periodo_referencia) DO UPDATE SET
        fonte_oficial = excluded.fonte_oficial,
        endpoint_url = excluded.endpoint_url,
        payload_json = excluded.payload_json,
        checksum_sha256 = excluded.checksum_sha256,
        http_status = excluded.http_status,
        ingestion_timestamp = excluded.ingestion_timestamp;
    """

    init_db(db_path=db_path, conn=conn)

    with db_transaction(db_path=db_path, conn=conn) as active_conn:
        active_conn.execute(
            query,
            (
                int(municipio_id),
                indicador,
                periodo_referencia,
                fonte_oficial,
                endpoint_url,
                json_str,
                checksum,
                http_status,
                timestamp,
            ),
        )
        logger.info(
            "Bronze socioeconômico atualizada: %s (município: %s, ref: %s). Hash: %s",
            indicador,
            municipio_id,
            periodo_referencia,
            checksum[:8],
        )

    return checksum


def read_bronze_socioeconomico(
    municipio_id: int,
    indicador: str,
    periodo_referencia: str,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    """Recupera um indicador socioeconômico armazenado na camada Bronze.

    Args:
        municipio_id: Código IBGE do município.
        indicador: Nome do indicador gravado.
        periodo_referencia: Período de referência consultado.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        Dicionário com colunas da tabela e campo 'payload' decodificado, ou None.
    """
    init_db(db_path=db_path, conn=conn)
    query = """
    SELECT
        municipio_id, indicador, periodo_referencia,
        fonte_oficial, endpoint_url, payload_json,
        checksum_sha256, http_status, ingestion_timestamp
    FROM bronze_ibge_socioeconomico
    WHERE municipio_id = ? AND indicador = ? AND periodo_referencia = ?;
    """
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        cursor = conn.execute(query, (int(municipio_id), indicador, periodo_referencia))
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "municipio_id": row["municipio_id"],
            "indicador": row["indicador"],
            "periodo_referencia": row["periodo_referencia"],
            "fonte_oficial": row["fonte_oficial"],
            "endpoint_url": row["endpoint_url"],
            "payload": json.loads(row["payload_json"]),
            "payload_json": row["payload_json"],
            "checksum_sha256": row["checksum_sha256"],
            "http_status": row["http_status"],
            "ingestion_timestamp": row["ingestion_timestamp"],
        }
    finally:
        if close_after:
            conn.close()


def list_bronze_socioeconomico(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Lista o sumário dos indicadores socioeconômicos persistidos na Bronze.

    Args:
        municipio_id: Filtro opcional por código do município.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        Lista de dicionários com os metadados dos indicadores persistidos.
    """
    init_db(db_path=db_path, conn=conn)
    query = """
    SELECT
        municipio_id, indicador, periodo_referencia,
        fonte_oficial, endpoint_url, checksum_sha256,
        http_status, ingestion_timestamp
    FROM bronze_ibge_socioeconomico
    """
    params: list[Any] = []
    if municipio_id is not None:
        query += " WHERE municipio_id = ?"
        params.append(int(municipio_id))
    query += " ORDER BY indicador, periodo_referencia;"

    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        cursor = conn.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        if close_after:
            conn.close()


def save_all_socioeconomico_bronze(
    socioeconomico_dict: dict[str, dict[str, Any]],
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, str]:
    """Persiste um lote de indicadores socioeconômicos na camada Bronze.

    Args:
        socioeconomico_dict: Dicionário retornado por fetch_all_socioeconomico_maua.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        Dicionário mapeando chave do indicador ao seu hash SHA-256.
    """
    checksums: dict[str, str] = {}
    for key, data in socioeconomico_dict.items():
        ck = save_bronze_socioeconomico(
            municipio_id=data["municipio_id"],
            indicador=data.get("indicador", key),
            periodo_referencia=data["periodo_referencia"],
            fonte_oficial=data["fonte_oficial"],
            endpoint_url=data["endpoint_url"],
            raw_payload=data["payload"],
            http_status=data.get("http_status", 200),
            db_path=db_path,
            conn=conn,
        )
        checksums[key] = ck
    return checksums


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
# Operações da Camada Silver Socioeconômica
# ---------------------------------------------------------------------------


def save_silver_populacao(
    df: pd.DataFrame,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Persiste dados de população na silver_ibge_populacao com idempotência (UPSERT).

    Args:
        df: DataFrame Pandas contendo as colunas de população normalizadas.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        Número de registros persistidos/atualizados.

    Raises:
        IBGEStorageError: Se o DataFrame for vazio ou inválido.
    """
    cols = [
        "municipio_id",
        "ano_referencia",
        "populacao",
        "tipo_populacao",
        "unidade",
        "fonte_oficial",
        "bronze_indicador",
    ]
    if not isinstance(df, pd.DataFrame) or df.empty:
        msg = "DataFrame inválido ou vazio para silver_ibge_populacao."
        logger.error(msg)
        raise IBGEStorageError(msg)

    missing = [c for c in cols if c not in df.columns]
    if missing:
        msg = f"Colunas obrigatórias ausentes em silver_ibge_populacao: {missing}"
        logger.error(msg)
        raise IBGEStorageError(msg)

    init_db(db_path=db_path, conn=conn)
    timestamp = datetime.now(UTC).isoformat()

    query = """
    INSERT INTO silver_ibge_populacao (
        municipio_id, ano_referencia, populacao, tipo_populacao,
        unidade, fonte_oficial, bronze_indicador, transformed_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(municipio_id, ano_referencia, tipo_populacao) DO UPDATE SET
        populacao = excluded.populacao,
        unidade = excluded.unidade,
        fonte_oficial = excluded.fonte_oficial,
        bronze_indicador = excluded.bronze_indicador,
        transformed_at = excluded.transformed_at;
    """

    count = 0
    with db_transaction(db_path=db_path, conn=conn) as active_conn:
        for _, row in df.iterrows():
            active_conn.execute(
                query,
                (
                    int(row["municipio_id"]),
                    int(row["ano_referencia"]),
                    int(row["populacao"]),
                    str(row["tipo_populacao"]),
                    str(row["unidade"]),
                    str(row["fonte_oficial"]),
                    str(row["bronze_indicador"]),
                    timestamp,
                ),
            )
            count += 1
        logger.info("silver_ibge_populacao atualizada com %d registro(s).", count)
    return count


def read_silver_populacao(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta registros de contagem e estimativa populacional da Silver.

    Args:
        municipio_id: Código IBGE opcional para filtro.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        DataFrame Pandas ordenado por ano_referencia e tipo_populacao.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = (
                "SELECT * FROM silver_ibge_populacao WHERE municipio_id = ? "
                "ORDER BY ano_referencia ASC, tipo_populacao ASC;"
            )
            cursor = conn.execute(query, (int(municipio_id),))
        else:
            query = (
                "SELECT * FROM silver_ibge_populacao "
                "ORDER BY municipio_id ASC, ano_referencia ASC, tipo_populacao ASC;"
            )
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        if close_after:
            conn.close()


def save_silver_pib(
    df: pd.DataFrame,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Persiste dados econômicos na silver_ibge_pib com idempotência (UPSERT).

    Args:
        df: DataFrame Pandas contendo as variáveis do PIB normalizadas.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        Número de registros persistidos/atualizados.

    Raises:
        IBGEStorageError: Se o DataFrame for vazio ou inválido.
    """
    cols = [
        "municipio_id",
        "ano_referencia",
        "indicador_id",
        "indicador_nome",
        "valor",
        "unidade",
        "tipo_valor",
        "fonte_oficial",
        "bronze_indicador",
    ]
    if not isinstance(df, pd.DataFrame) or df.empty:
        msg = "DataFrame inválido ou vazio para silver_ibge_pib."
        logger.error(msg)
        raise IBGEStorageError(msg)

    missing = [c for c in cols if c not in df.columns]
    if missing:
        msg = f"Colunas obrigatórias ausentes em silver_ibge_pib: {missing}"
        logger.error(msg)
        raise IBGEStorageError(msg)

    init_db(db_path=db_path, conn=conn)
    timestamp = datetime.now(UTC).isoformat()

    query = """
    INSERT INTO silver_ibge_pib (
        municipio_id, ano_referencia, indicador_id, indicador_nome,
        valor, unidade, tipo_valor, fonte_oficial, bronze_indicador, transformed_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(municipio_id, ano_referencia, indicador_id) DO UPDATE SET
        indicador_nome = excluded.indicador_nome,
        valor = excluded.valor,
        unidade = excluded.unidade,
        tipo_valor = excluded.tipo_valor,
        fonte_oficial = excluded.fonte_oficial,
        bronze_indicador = excluded.bronze_indicador,
        transformed_at = excluded.transformed_at;
    """

    count = 0
    with db_transaction(db_path=db_path, conn=conn) as active_conn:
        for _, row in df.iterrows():
            active_conn.execute(
                query,
                (
                    int(row["municipio_id"]),
                    int(row["ano_referencia"]),
                    int(row["indicador_id"]),
                    str(row["indicador_nome"]),
                    float(row["valor"]),
                    str(row["unidade"]),
                    str(row["tipo_valor"]),
                    str(row["fonte_oficial"]),
                    str(row["bronze_indicador"]),
                    timestamp,
                ),
            )
            count += 1
        logger.info("silver_ibge_pib atualizada com %d registro(s).", count)
    return count


def read_silver_pib(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta séries temporais econômicas da tabela silver_ibge_pib.

    Args:
        municipio_id: Código IBGE opcional para filtro.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        DataFrame Pandas ordenado por ano_referencia e indicador_id.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = (
                "SELECT * FROM silver_ibge_pib WHERE municipio_id = ? "
                "ORDER BY ano_referencia ASC, indicador_id ASC;"
            )
            cursor = conn.execute(query, (int(municipio_id),))
        else:
            query = (
                "SELECT * FROM silver_ibge_pib "
                "ORDER BY municipio_id ASC, ano_referencia ASC, indicador_id ASC;"
            )
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        if close_after:
            conn.close()


def save_silver_censitario(
    df: pd.DataFrame,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Persiste dados censitários detalhados na silver_ibge_censitario via UPSERT.

    Args:
        df: DataFrame Pandas contendo os registros censitários normalizados.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        Número de registros persistidos/atualizados.

    Raises:
        IBGEStorageError: Se o DataFrame for vazio ou inválido.
    """
    cols = [
        "municipio_id",
        "ano_referencia",
        "variavel_id",
        "variavel_nome",
        "categoria_classificacao",
        "valor",
        "unidade",
        "fonte_oficial",
        "bronze_indicador",
    ]
    if not isinstance(df, pd.DataFrame) or df.empty:
        msg = "DataFrame inválido ou vazio para silver_ibge_censitario."
        logger.error(msg)
        raise IBGEStorageError(msg)

    missing = [c for c in cols if c not in df.columns]
    if missing:
        msg = f"Colunas obrigatórias ausentes em silver_ibge_censitario: {missing}"
        logger.error(msg)
        raise IBGEStorageError(msg)

    init_db(db_path=db_path, conn=conn)
    timestamp = datetime.now(UTC).isoformat()

    query = """
    INSERT INTO silver_ibge_censitario (
        municipio_id, ano_referencia, variavel_id, variavel_nome,
        categoria_classificacao, valor, unidade, fonte_oficial,
        bronze_indicador, transformed_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(municipio_id, ano_referencia, variavel_id, categoria_classificacao)
    DO UPDATE SET
        variavel_nome = excluded.variavel_nome,
        valor = excluded.valor,
        unidade = excluded.unidade,
        fonte_oficial = excluded.fonte_oficial,
        bronze_indicador = excluded.bronze_indicador,
        transformed_at = excluded.transformed_at;
    """

    count = 0
    with db_transaction(db_path=db_path, conn=conn) as active_conn:
        for _, row in df.iterrows():
            active_conn.execute(
                query,
                (
                    int(row["municipio_id"]),
                    int(row["ano_referencia"]),
                    int(row["variavel_id"]),
                    str(row["variavel_nome"]),
                    str(row["categoria_classificacao"]),
                    float(row["valor"]),
                    str(row["unidade"]),
                    str(row["fonte_oficial"]),
                    str(row["bronze_indicador"]),
                    timestamp,
                ),
            )
            count += 1
        logger.info("silver_ibge_censitario atualizada com %d registro(s).", count)
    return count


def read_silver_censitario(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta indicadores censitários estruturados da Silver.

    Args:
        municipio_id: Código IBGE opcional para filtro.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional.

    Returns:
        DataFrame Pandas ordenado por ano_referencia, variavel_id e categoria.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = (
                "SELECT * FROM silver_ibge_censitario WHERE municipio_id = ? "
                "ORDER BY ano_referencia ASC, variavel_id ASC, "
                "categoria_classificacao ASC;"
            )
            cursor = conn.execute(query, (int(municipio_id),))
        else:
            query = (
                "SELECT * FROM silver_ibge_censitario "
                "ORDER BY municipio_id ASC, ano_referencia ASC, "
                "variavel_id ASC, categoria_classificacao ASC;"
            )
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        if close_after:
            conn.close()


def save_all_socioeconomico_silver(
    dfs: dict[str, pd.DataFrame],
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, int]:
    """Persiste o conjunto completo de DataFrames da Silver Socioeconômica.

    Args:
        dfs: Dicionário contendo as chaves 'populacao', 'pib' e 'censitario'.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        Dicionário com a quantidade de registros gravados por tabela.
    """
    init_db(db_path=db_path, conn=conn)
    counts = {}

    if "populacao" in dfs and not dfs["populacao"].empty:
        counts["populacao"] = save_silver_populacao(
            dfs["populacao"], db_path=db_path, conn=conn
        )
    if "pib" in dfs and not dfs["pib"].empty:
        counts["pib"] = save_silver_pib(dfs["pib"], db_path=db_path, conn=conn)
    if "censitario" in dfs and not dfs["censitario"].empty:
        counts["censitario"] = save_silver_censitario(
            dfs["censitario"], db_path=db_path, conn=conn
        )

    logger.info("Persistência em lote da Silver Socioeconômica concluída: %s", counts)
    return counts


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


def read_gold_populacao_historica(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta a série histórica de população e variações da camada Gold.

    Apresenta dados de Censo e Estimativas com cálculo de variação absoluta
    e percentual entre observações compatíveis.

    Args:
        municipio_id: Código IBGE opcional para filtro pontual.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        DataFrame Pandas contendo a série temporal de população.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = (
                "SELECT * FROM gold_populacao_historica WHERE municipio_id = ? "
                "ORDER BY tipo_populacao, ano_referencia ASC;"
            )
            cursor = conn.execute(query, (int(municipio_id),))
        else:
            query = (
                "SELECT * FROM gold_populacao_historica "
                "ORDER BY municipio_id, tipo_populacao, ano_referencia ASC;"
            )
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        if close_after:
            conn.close()


def read_gold_pib_historico(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta séries econômicas de PIB, per capita e VABs setoriais da Gold.

    Apresenta PIB corrente, PIB per capita, VABs da Agropecuária, Indústria,
    Serviços e Administração Pública, além de variações percentuais nominais.

    Args:
        municipio_id: Código IBGE opcional para filtro pontual.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        DataFrame Pandas com séries econômicas consolidadas.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = (
                "SELECT * FROM gold_pib_historico WHERE municipio_id = ? "
                "ORDER BY ano_referencia ASC;"
            )
            cursor = conn.execute(query, (int(municipio_id),))
        else:
            query = (
                "SELECT * FROM gold_pib_historico "
                "ORDER BY municipio_id, ano_referencia ASC;"
            )
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        if close_after:
            conn.close()


def read_gold_demografia_sexo(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta a composição demográfica por sexo e razão de sexo da Gold.

    Apresenta contagens por homens e mulheres, participações percentuais e
    razão de sexo demográfica (homens para cada 100 mulheres).

    Args:
        municipio_id: Código IBGE opcional para filtro pontual.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        DataFrame Pandas com indicadores demográficos por sexo.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = (
                "SELECT * FROM gold_demografia_sexo WHERE municipio_id = ? "
                "ORDER BY ano_referencia ASC;"
            )
            cursor = conn.execute(query, (int(municipio_id),))
        else:
            query = (
                "SELECT * FROM gold_demografia_sexo "
                "ORDER BY municipio_id, ano_referencia ASC;"
            )
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        if close_after:
            conn.close()


def read_gold_resumo_socioeconomico(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Consulta o sumário de indicadores socioeconômicos consolidados da Gold.

    Apresenta visão consolidada para o dashboard interativo preservando
    estritamente o período de referência de cada indicador.

    Args:
        municipio_id: Código IBGE opcional para filtro pontual.
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        DataFrame Pandas no formato longo de indicadores consolidados.
    """
    init_db(db_path=db_path, conn=conn)
    close_after = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_after = True

    try:
        if municipio_id is not None:
            query = (
                "SELECT * FROM gold_resumo_socioeconomico WHERE municipio_id = ? "
                "ORDER BY tema, indicador;"
            )
            cursor = conn.execute(query, (int(municipio_id),))
        else:
            query = (
                "SELECT * FROM gold_resumo_socioeconomico "
                "ORDER BY municipio_id, tema, indicador;"
            )
            cursor = conn.execute(query)

        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        if close_after:
            conn.close()


def get_kpis_socioeconomicos(
    municipio_id: int | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Sumariza os principais KPIs socioeconômicos e demográficos de Mauá.

    Função consumida pelo Dashboard analítico para exibição dos cards de topo.

    Args:
        municipio_id: Código IBGE opcional (padrão: 3529401).
        db_path: Caminho para o banco SQLite.
        conn: Conexão opcional existente.

    Returns:
        Dicionário com os principais indicadores estruturados.
    """
    df_resumo = read_gold_resumo_socioeconomico(
        municipio_id=municipio_id, db_path=db_path, conn=conn
    )
    df_sexo = read_gold_demografia_sexo(
        municipio_id=municipio_id, db_path=db_path, conn=conn
    )

    kpis: dict[str, Any] = {
        "populacao_censo_2022": None,
        "populacao_estimada_recente": None,
        "ano_estimativa_recente": None,
        "pib_corrente_mil_reais": None,
        "ano_pib_corrente": None,
        "pib_per_capita_reais": None,
        "ano_pib_per_capita": None,
        "area_territorial_km2": None,
        "densidade_demografica": None,
        "taxa_alfabetizacao_pct": None,
        "razao_sexo": None,
        "participacao_masculina_pct": None,
        "participacao_feminina_pct": None,
    }

    if not df_resumo.empty:
        for _, row in df_resumo.iterrows():
            ind = str(row["indicador"])
            val = row["valor"]
            ano = row["ano_referencia"]
            if "Censo 2022" in ind and "total" in ind.lower():
                kpis["populacao_censo_2022"] = int(val)
            elif "estimada mais recente" in ind.lower():
                kpis["populacao_estimada_recente"] = int(val)
                kpis["ano_estimativa_recente"] = int(ano)
            elif "preços correntes" in ind.lower():
                kpis["pib_corrente_mil_reais"] = float(val)
                kpis["ano_pib_corrente"] = int(ano)
            elif "per capita" in ind.lower():
                kpis["pib_per_capita_reais"] = float(val)
                kpis["ano_pib_per_capita"] = int(ano)
            elif "área territorial" in ind.lower():
                kpis["area_territorial_km2"] = float(val)
            elif "densidade demográfica" in ind.lower():
                kpis["densidade_demografica"] = float(val)
            elif "taxa de alfabetização" in ind.lower():
                kpis["taxa_alfabetizacao_pct"] = float(val)

    if not df_sexo.empty:
        first_sexo = df_sexo.iloc[0]
        kpis["razao_sexo"] = float(first_sexo["razao_sexo"])
        kpis["participacao_masculina_pct"] = float(
            first_sexo["participacao_masculina_pct"]
        )
        kpis["participacao_feminina_pct"] = float(
            first_sexo["participacao_feminina_pct"]
        )

    return kpis


# =============================================================================
# Consultas Analíticas de Governança e Volumetria da Arquitetura Medallion
# =============================================================================

CATALOGO_OBJETOS_MEDALLION: list[dict[str, str]] = [
    {
        "camada": "Bronze",
        "objeto": "bronze_ibge_raw",
        "tipo_objeto": "Tabela Física",
        "dominio": "Territorial",
        "descricao_granularidade": "JSON bruto oficial da API de Localidades (Mauá)",
    },
    {
        "camada": "Bronze",
        "objeto": "bronze_ibge_socioeconomico",
        "tipo_objeto": "Tabela Física",
        "dominio": "Socioeconômico",
        "descricao_granularidade": (
            "JSONs brutos das 5 pesquisas socioeconômicas do IBGE"
        ),
    },
    {
        "camada": "Silver",
        "objeto": "silver_municipio",
        "tipo_objeto": "Tabela Física",
        "dominio": "Territorial",
        "descricao_granularidade": (
            "Hierarquia geográfica normalizada (1 linha/município)"
        ),
    },
    {
        "camada": "Silver",
        "objeto": "silver_ibge_populacao",
        "tipo_objeto": "Tabela Física",
        "dominio": "Socioeconômico",
        "descricao_granularidade": (
            "Série anual de população residente (Censo e Estimativas)"
        ),
    },
    {
        "camada": "Silver",
        "objeto": "silver_ibge_pib",
        "tipo_objeto": "Tabela Física",
        "dominio": "Socioeconômico",
        "descricao_granularidade": (
            "Série histórica longa de PIB, VAB setorial e impostos"
        ),
    },
    {
        "camada": "Silver",
        "objeto": "silver_ibge_censitario",
        "tipo_objeto": "Tabela Física",
        "dominio": "Socioeconômico",
        "descricao_granularidade": (
            "Variáveis censitárias (sexo, alfabetização, área, densidade)"
        ),
    },
    {
        "camada": "Gold",
        "objeto": "gold_vw_municipio_hierarquia",
        "tipo_objeto": "View Analítica",
        "dominio": "Territorial",
        "descricao_granularidade": (
            "Visão analítica das divisões regionais e geográficas"
        ),
    },
    {
        "camada": "Gold",
        "objeto": "gold_vw_qualidade_auditoria",
        "tipo_objeto": "View Analítica",
        "dominio": "Territorial",
        "descricao_granularidade": (
            "Painel de reconciliação e integridade Bronze-Silver territorial"
        ),
    },
    {
        "camada": "Gold",
        "objeto": "gold_populacao_historica",
        "tipo_objeto": "View Analítica",
        "dominio": "Socioeconômico",
        "descricao_granularidade": (
            "Série temporal com LAGs, variações e continuidade"
        ),
    },
    {
        "camada": "Gold",
        "objeto": "gold_pib_historico",
        "tipo_objeto": "View Analítica",
        "dominio": "Socioeconômico",
        "descricao_granularidade": (
            "Série temporal analítica de PIB corrente, per capita e VABs"
        ),
    },
    {
        "camada": "Gold",
        "objeto": "gold_demografia_sexo",
        "tipo_objeto": "View Analítica",
        "dominio": "Socioeconômico",
        "descricao_granularidade": (
            "Distribuição por sexo e razão demográfica de gênero"
        ),
    },
    {
        "camada": "Gold",
        "objeto": "gold_resumo_socioeconomico",
        "tipo_objeto": "View Analítica",
        "dominio": "Socioeconômico",
        "descricao_granularidade": (
            "Indicadores estratégicos consolidados em formato longo"
        ),
    },
]


def get_volumetria_medallion(
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Calcula a volumetria física real de cada tabela e view no SQLite.

    Discrimina os objetos por camada Medallion (Bronze, Silver, Gold) e
    domínio de negócio (Territorial vs Socioeconômico), sem hardcode de valores.

    Args:
        db_path: Caminho opcional para o banco de dados SQLite.
        conn: Conexão ativa opcional.

    Returns:
        DataFrame com colunas:
        ["camada", "objeto", "tipo_objeto", "dominio", "total_registros",
         "descricao_granularidade"]
    """
    should_close = False
    if conn is None:
        target = resolve_db_path(db_path)
        if target != ":memory:" and not Path(target).exists():
            return pd.DataFrame(
                columns=[
                    "camada",
                    "objeto",
                    "tipo_objeto",
                    "dominio",
                    "total_registros",
                    "descricao_granularidade",
                ]
            )
        conn = get_db_connection(db_path)
        should_close = True

    registros: list[dict[str, Any]] = []

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
        objetos_existentes = {row[0] for row in cursor.fetchall()}

        for item in CATALOGO_OBJETOS_MEDALLION:
            nome_obj = item["objeto"]
            total = 0
            if nome_obj in objetos_existentes:
                cursor.execute(f"SELECT COUNT(*) FROM {nome_obj}")  # noqa: S608
                total = int(cursor.fetchone()[0])

            registros.append(
                {
                    "camada": item["camada"],
                    "objeto": nome_obj,
                    "tipo_objeto": item["tipo_objeto"],
                    "dominio": item["dominio"],
                    "total_registros": total,
                    "descricao_granularidade": item["descricao_granularidade"],
                }
            )
    finally:
        if should_close and conn:
            conn.close()

    return pd.DataFrame(registros)


def get_metadados_governanca(
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Coleta metadados operacionais, cobertura temporal e catálogo de indicadores.

    Realiza consultas dinâmicas às tabelas Silver e Gold no SQLite para apurar
    períodos históricos e contagem de indicadores distintos.

    Args:
        db_path: Caminho opcional para o banco SQLite.
        conn: Conexão ativa opcional.

    Returns:
        Dicionário estruturado com métricas de governança.
    """
    metadados: dict[str, Any] = {
        "populacao_min_ano": None,
        "populacao_max_ano": None,
        "populacao_total_anos": 0,
        "pib_min_ano": None,
        "pib_max_ano": None,
        "pib_total_anos": 0,
        "pib_total_indicadores": 0,
        "censitario_total_variaveis": 0,
        "gold_total_indicadores": 0,
        "gold_temas": [],
        "total_bronze": 0,
        "total_silver": 0,
        "total_gold": 0,
        "total_territorial": 0,
        "total_socioeconomico": 0,
    }

    should_close = False
    if conn is None:
        target = resolve_db_path(db_path)
        if target != ":memory:" and not Path(target).exists():
            return metadados
        conn = get_db_connection(db_path)
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
        objetos = {row[0] for row in cursor.fetchall()}

        # 1. Metadados de População
        if "silver_ibge_populacao" in objetos:
            cursor.execute(
                "SELECT MIN(ano_referencia), MAX(ano_referencia), "
                "COUNT(DISTINCT ano_referencia) FROM silver_ibge_populacao"
            )
            row_pop = cursor.fetchone()
            if row_pop and row_pop[0] is not None:
                metadados["populacao_min_ano"] = int(row_pop[0])
                metadados["populacao_max_ano"] = int(row_pop[1])
                metadados["populacao_total_anos"] = int(row_pop[2])

        # 2. Metadados de PIB
        if "silver_ibge_pib" in objetos:
            cursor.execute(
                "SELECT MIN(ano_referencia), MAX(ano_referencia), "
                "COUNT(DISTINCT ano_referencia), COUNT(DISTINCT indicador_id) "
                "FROM silver_ibge_pib"
            )
            row_pib = cursor.fetchone()
            if row_pib and row_pib[0] is not None:
                metadados["pib_min_ano"] = int(row_pib[0])
                metadados["pib_max_ano"] = int(row_pib[1])
                metadados["pib_total_anos"] = int(row_pib[2])
                metadados["pib_total_indicadores"] = int(row_pib[3])

        # 3. Metadados Censitários
        if "silver_ibge_censitario" in objetos:
            cursor.execute(
                "SELECT COUNT(DISTINCT variavel_id) FROM silver_ibge_censitario"
            )
            row_cens = cursor.fetchone()
            if row_cens and row_cens[0] is not None:
                metadados["censitario_total_variaveis"] = int(row_cens[0])

        # 4. Metadados Gold Resumo
        if "gold_resumo_socioeconomico" in objetos:
            cursor.execute(
                "SELECT COUNT(DISTINCT indicador) FROM gold_resumo_socioeconomico"
            )
            row_res = cursor.fetchone()
            if row_res and row_res[0] is not None:
                metadados["gold_total_indicadores"] = int(row_res[0])

            cursor.execute(
                "SELECT DISTINCT tema FROM gold_resumo_socioeconomico ORDER BY tema"
            )
            metadados["gold_temas"] = [r[0] for r in cursor.fetchall() if r[0]]

        # 5. Totais agregados calculados a partir da volumetria real
        df_vol = get_volumetria_medallion(conn=conn)
        if not df_vol.empty:
            metadados["total_bronze"] = int(
                df_vol[df_vol["camada"] == "Bronze"]["total_registros"].sum()
            )
            metadados["total_silver"] = int(
                df_vol[df_vol["camada"] == "Silver"]["total_registros"].sum()
            )
            metadados["total_gold"] = int(
                df_vol[df_vol["camada"] == "Gold"]["total_registros"].sum()
            )
            metadados["total_territorial"] = int(
                df_vol[df_vol["dominio"] == "Territorial"]["total_registros"].sum()
            )
            metadados["total_socioeconomico"] = int(
                df_vol[df_vol["dominio"] == "Socioeconômico"]["total_registros"].sum()
            )
    finally:
        if should_close and conn:
            conn.close()

    return metadados


# =============================================================================
# Gestão de Snapshot SQL e Portabilidade para Nuvem (Streamlit Cloud Deploy)
# =============================================================================


def export_database_snapshot(
    source_db: Path | str = DEFAULT_DB_PATH,
    target_sql: Path | str = DEFAULT_SNAPSHOT_PATH,
) -> Path:
    """Exporta o banco de dados SQLite completo para um script SQL snapshot versionado.

    Utiliza sqlite3.Connection.iterdump() para gerar um arquivo SQL autocontido
    com os DDLs e INSERTs de todas as tabelas Bronze, Silver e Views Gold.

    Args:
        source_db: Caminho para o banco SQLite de origem.
        target_sql: Caminho de destino para gravação do arquivo .sql.

    Returns:
        Path para o arquivo .sql gerado.
    """
    src = Path(resolve_db_path(source_db))
    if not src.exists():
        raise FileNotFoundError(f"Banco SQLite de origem não encontrado: {src}")

    target = Path(target_sql)
    target.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(src))
    try:
        dump = "\n".join(conn.iterdump())
    finally:
        conn.close()

    target.write_text(dump, encoding="utf-8")
    logger.info(
        "Snapshot SQL exportado com sucesso para: %s (%d bytes)",
        target,
        len(dump.encode("utf-8")),
    )
    return target


def restore_database_snapshot(
    source_sql: Path | str = DEFAULT_SNAPSHOT_PATH,
    target_db: Path | str = DEFAULT_DB_PATH,
) -> int:
    """Restaura o banco SQLite a partir de um script SQL snapshot.

    Executa o script SQL em uma nova conexão SQLite, recriando as tabelas e views.

    Args:
        source_sql: Caminho para o script SQL snapshot.
        target_db: Caminho para o banco SQLite de destino.

    Returns:
        Total de objetos (tabelas e views) restaurados.
    """
    src = Path(source_sql)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo snapshot SQL não encontrado: {src}")

    target = resolve_db_path(target_db)
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)

    sql_script = src.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(sql_script)
        conn.commit()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type IN ('table', 'view')"
        )
        total_obj = int(cursor.fetchone()[0])
    finally:
        conn.close()

    logger.info(
        "Banco restaurado a partir do snapshot %s no destino %s (%d objetos).",
        src,
        target,
        total_obj,
    )
    return total_obj


def ensure_database_ready(
    db_path: Path | str | None = None,
    snapshot_path: Path | str | None = None,
) -> bool:
    """Garante que o banco SQLite esteja pronto e populado para leitura analítica.

    Caso o banco de destino não exista ou esteja vazio (situação comum em deploy
    no Streamlit Community Cloud onde data/*.db é ignorado pelo Git), restaura
    automaticamente os dados a partir do snapshot SQL versionado, sem efetuar
    chamadas de rede ou acionar o pipeline de ingestão.

    Caso o banco já exista com dados, nenhuma alteração é realizada (zero-write).

    Args:
        db_path: Caminho opcional do banco SQLite (padrão: DEFAULT_DB_PATH).
        snapshot_path: Caminho opcional do snapshot SQL (padrão: DEFAULT_SNAPSHOT_PATH).

    Returns:
        True se o banco estiver pronto para leitura analítica, False caso contrário.
    """
    target = resolve_db_path(db_path)
    snapshot = Path(snapshot_path or DEFAULT_SNAPSHOT_PATH)

    # 1. Se for banco em memória (:memory:), verificar se já possui tabelas
    if target == ":memory:":
        return False

    target_path = Path(target)

    # 2. Se o arquivo já existe e possui dados, manter intacto (zero write)
    if target_path.exists() and target_path.stat().st_size > 0:
        try:
            conn = sqlite3.connect(str(target_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE type='table' AND name='silver_municipio'"
            )
            has_silver = cursor.fetchone()[0] > 0
            if has_silver:
                cursor.execute("SELECT count(*) FROM silver_municipio")
                count_mun = cursor.fetchone()[0]
                if count_mun > 0:
                    conn.close()
                    return True
            conn.close()
        except Exception as exc:
            logger.warning(
                "Erro ao inspecionar banco existente %s: %s", target_path, exc
            )

    # 3. Se o banco não existe ou está vazio, verificar se deve restaurar do snapshot
    # Restaura se for o banco padrão ou se IBGE_AUTO_RESTORE=1 estiver ativo
    is_default_db = False
    try:
        is_default_db = target_path.resolve() == DEFAULT_DB_PATH.resolve()
    except Exception:
        is_default_db = str(target_path) == str(DEFAULT_DB_PATH)

    auto_restore_env = os.environ.get("IBGE_AUTO_RESTORE", "0") == "1"

    if (is_default_db or auto_restore_env) and snapshot.exists():
        logger.info(
            "Banco SQLite ausente em %s. Restaurando do snapshot versionado: %s",
            target_path,
            snapshot,
        )
        try:
            restore_database_snapshot(source_sql=snapshot, target_db=target_path)
            return True
        except Exception as exc:
            logger.error(
                "Falha ao restaurar banco a partir do snapshot versionado: %s", exc
            )
            return False

    return False
