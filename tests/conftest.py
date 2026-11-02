"""Fixtures compartilhadas para a suite de testes do desafio_ibge."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from desafio_ibge.config.settings import MAUA_IBGE_CODE
from desafio_ibge.loading.storage import (
    init_db,
    save_bronze,
    save_silver,
    save_silver_censitario,
    save_silver_pib,
    save_silver_populacao,
)
from desafio_ibge.transformation.normalizer import json_to_dataframe


@pytest.fixture
def maua_raw_payload() -> dict[str, Any]:
    """Retorna o payload JSON oficial de Mauá (SP) idêntico ao retornado pelo IBGE.

    Conforme especificado em docs/doc_api.md.
    """
    return {
        "id": 3529401,
        "nome": "Mauá",
        "microrregiao": {
            "id": 35061,
            "nome": "São Paulo",
            "mesorregiao": {
                "id": 3515,
                "nome": "Metropolitana de São Paulo",
                "UF": {
                    "id": 35,
                    "sigla": "SP",
                    "nome": "São Paulo",
                    "regiao": {
                        "id": 3,
                        "sigla": "SE",
                        "nome": "Sudeste",
                    },
                },
            },
        },
        "regiao-imediata": {
            "id": 350001,
            "nome": "São Paulo",
            "regiao-intermediaria": {
                "id": 3501,
                "nome": "São Paulo",
                "UF": {
                    "id": 35,
                    "sigla": "SP",
                    "nome": "São Paulo",
                    "regiao": {
                        "id": 3,
                        "sigla": "SE",
                        "nome": "Sudeste",
                    },
                },
            },
        },
    }


@pytest.fixture
def sp_municipios_payload(maua_raw_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Retorna lista simulada de municípios do Estado de SP contendo Mauá."""
    santo_andre = {
        "id": 3547809,
        "nome": "Santo André",
        "microrregiao": maua_raw_payload["microrregiao"],
        "regiao-imediata": maua_raw_payload["regiao-imediata"],
    }
    return [santo_andre, maua_raw_payload]


@pytest.fixture
def populated_db_path(tmp_path: Path, maua_raw_payload: dict[str, Any]) -> Path:
    """Cria um banco SQLite temporário populado com o registro de Mauá (SP)."""
    db_file = tmp_path / "test_populated.db"
    init_db(db_path=db_file)

    url = (
        "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/"
        f"{MAUA_IBGE_CODE}"
    )
    save_bronze(maua_raw_payload, endpoint_url=url, db_path=db_file)
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=db_file)
    return db_file


@pytest.fixture
def fully_populated_db_path(
    tmp_path: Path,
    maua_raw_payload: dict[str, Any],
) -> Path:
    """Cria banco SQLite com camadas Territorial e Socioeconômica completas."""
    db_file = tmp_path / "test_fully_populated.db"
    init_db(db_path=db_file)

    # 1. Territorial
    url = (
        "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/"
        f"{MAUA_IBGE_CODE}"
    )
    save_bronze(maua_raw_payload, endpoint_url=url, db_path=db_file)
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=db_file)

    # 2. População
    df_pop = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2021,
                "populacao": 479000,
                "tipo_populacao": "Estimativa de População",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE - Estimativas",
                "bronze_indicador": "populacao_estimada_historica",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "populacao": 418261,
                "tipo_populacao": "Censo Demográfico",
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_pop_area_densidade",
            },
        ]
    )
    save_silver_populacao(df_pop, db_path=db_file)

    # 3. PIB (formato longo do schema silver_ibge_pib)
    df_pib = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "indicador_id": 46997,
                "indicador_nome": "PIB corrente",
                "valor": 24000000.0,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE - PIB Municipal",
                "bronze_indicador": "pib_municipal_historico",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "indicador_id": 47001,
                "indicador_nome": "PIB per capita",
                "valor": 55000.0,
                "unidade": "Reais",
                "tipo_valor": "Per Capita",
                "fonte_oficial": "IBGE - PIB Municipal",
                "bronze_indicador": "pib_municipal_historico",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2023,
                "indicador_id": 46997,
                "indicador_nome": "PIB corrente",
                "valor": 25000732.02,
                "unidade": "Mil Reais",
                "tipo_valor": "Corrente",
                "fonte_oficial": "IBGE - PIB Municipal",
                "bronze_indicador": "pib_municipal_historico",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2023,
                "indicador_id": 47001,
                "indicador_nome": "PIB per capita",
                "valor": 59773.04,
                "unidade": "Reais",
                "tipo_valor": "Per Capita",
                "fonte_oficial": "IBGE - PIB Municipal",
                "bronze_indicador": "pib_municipal_historico",
            },
        ]
    )
    save_silver_pib(df_pib, db_path=db_file)

    # 4. Censitário (formato longo do schema silver_ibge_censitario)
    df_cens = pd.DataFrame(
        [
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "variavel_id": 9991,
                "variavel_nome": "População residente por sexo",
                "categoria_classificacao": "Homens",
                "valor": 201348.0,
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_demografia_sexo",
            },
            {
                "municipio_id": MAUA_IBGE_CODE,
                "ano_referencia": 2022,
                "variavel_id": 9992,
                "variavel_nome": "População residente por sexo",
                "categoria_classificacao": "Mulheres",
                "valor": 216913.0,
                "unidade": "Pessoas",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_demografia_sexo",
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
                "variavel_id": 6319,
                "variavel_nome": "Densidade demográfica",
                "categoria_classificacao": "Total",
                "valor": 6753.01,
                "unidade": "hab/km²",
                "fonte_oficial": "IBGE - Censo 2022",
                "bronze_indicador": "censo_pop_area_densidade",
            },
        ]
    )
    save_silver_censitario(df_cens, db_path=db_file)
    return db_file


@pytest.fixture
def empty_db_path(tmp_path: Path) -> Path:
    """Cria um banco SQLite temporário inicializado, porém sem dados."""
    db_file = tmp_path / "test_empty.db"
    init_db(db_path=db_file)
    return db_file
