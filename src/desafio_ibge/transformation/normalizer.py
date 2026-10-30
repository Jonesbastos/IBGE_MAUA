"""Módulo de normalização, desaninhamento e transformação de dados com Pandas.

Transforma cargas JSON estruturadas da API de Localidades do IBGE em
DataFrames relacionais tabulares de 1 linha por município, padronizando colunas
em snake_case e aplicando coerção estrita de tipos.
"""

import copy
import logging
from typing import Any

import pandas as pd

from desafio_ibge.validation.schema import MunicipioSchema, validate_municipio_payload

logger = logging.getLogger(__name__)

# Mapeamento oficial de colunas e tipos analíticos estritos
DTYPES_MAPPING: dict[str, str] = {
    "id": "int64",
    "nome": "string",
    "microrregiao_id": "int64",
    "microrregiao_nome": "string",
    "microrregiao_mesorregiao_id": "int64",
    "microrregiao_mesorregiao_nome": "string",
    "microrregiao_mesorregiao_uf_id": "int64",
    "microrregiao_mesorregiao_uf_sigla": "string",
    "microrregiao_mesorregiao_uf_nome": "string",
    "microrregiao_mesorregiao_uf_regiao_id": "int64",
    "microrregiao_mesorregiao_uf_regiao_sigla": "string",
    "microrregiao_mesorregiao_uf_regiao_nome": "string",
    "regiao_imediata_id": "int64",
    "regiao_imediata_nome": "string",
    "regiao_imediata_regiao_intermediaria_id": "int64",
    "regiao_imediata_regiao_intermediaria_nome": "string",
    "regiao_imediata_regiao_intermediaria_uf_id": "int64",
    "regiao_imediata_regiao_intermediaria_uf_sigla": "string",
    "regiao_imediata_regiao_intermediaria_uf_nome": "string",
    "regiao_imediata_regiao_intermediaria_uf_regiao_id": "int64",
    "regiao_imediata_regiao_intermediaria_uf_regiao_sigla": "string",
    "regiao_imediata_regiao_intermediaria_uf_regiao_nome": "string",
}


def sanitize_column_names(columns: pd.Index) -> list[str]:
    """Saneia os nomes de colunas gerados pelo json_normalize.

    Converte hífens em sublinhados e força padrão snake_case em minúsculas.

    Args:
        columns: Índice de nomes de colunas originais do DataFrame.

    Returns:
        Lista de strings contendo os nomes de colunas saneados.
    """
    return [col.replace("-", "_").lower() for col in columns]


def apply_schema_types(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica tipagem forte e explícita nas colunas conhecidas do DataFrame.

    Args:
        df: DataFrame resultante do achatamento.

    Returns:
        Novo DataFrame com as colunas convertidas para os dtypes adequados.
    """
    converted_df = df.copy()
    for col, dtype_target in DTYPES_MAPPING.items():
        if col in converted_df.columns:
            converted_df[col] = converted_df[col].astype(dtype_target)
    return converted_df


def json_to_dataframe(
    raw_data: dict[str, Any] | list[dict[str, Any]] | MunicipioSchema,
    validate: bool = True,
) -> pd.DataFrame:
    """Transforma e achata o payload JSON do IBGE em um DataFrame normalizado.

    Garante que o dado de entrada não seja mutado, normaliza os 4 níveis
    hierárquicos de nós aninhados, elimina hífens dos nomes de atributos e
    força a tipagem estrita para compatibilidade com bancos relacionais e Parquet.

    Args:
        raw_data: Dicionário bruto, lista de dicionários ou instância MunicipioSchema.
        validate: Se True, valida os dados contra o schema Pydantic antes de normalizar.

    Returns:
        DataFrame Pandas tabular contendo os registros municipais achatados.

    Raises:
        IBGEValidationError: Caso validate=True e o schema seja violado.
    """
    # 1. Isolamento contra mutação do dado original de entrada
    if isinstance(raw_data, MunicipioSchema):
        # Utiliza o dump com aliases originais para normalização padrão
        payload: Any = raw_data.model_dump(by_alias=True)
    elif isinstance(raw_data, list):
        if validate:
            for item in raw_data:
                validate_municipio_payload(item)
        payload = copy.deepcopy(raw_data)
    else:
        if validate:
            validate_municipio_payload(raw_data)
        payload = copy.deepcopy(raw_data)

    logger.info("Iniciando normalização tabular com pandas.json_normalize")

    # 2. Desaninhamento hierárquico via json_normalize com separador '_'
    df = pd.json_normalize(payload, sep="_")

    # 3. Saneamento e padronização dos nomes de colunas (remoção de hífens)
    df.columns = sanitize_column_names(df.columns)

    # 4. Enforce explícito de tipos
    df = apply_schema_types(df)

    logger.info(
        "Normalização concluída: %d linha(s) e %d coluna(s) geradas.",
        len(df),
        len(df.columns),
    )
    return df
