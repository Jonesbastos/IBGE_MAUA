"""Submódulo de extração e ingestão de dados das APIs do IBGE."""

from desafio_ibge.extraction.ibge_client import (
    IBGEClient,
    IBGEExtractionError,
    get_municipio_maua,
)

__all__ = [
    "IBGEClient",
    "IBGEExtractionError",
    "get_municipio_maua",
]
