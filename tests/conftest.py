"""Fixtures compartilhadas para a suite de testes do desafio_ibge."""

from typing import Any

import pytest


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
