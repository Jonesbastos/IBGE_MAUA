"""Submódulo de validação de schemas e contratos de dados."""

from desafio_ibge.validation.schema import (
    CensitarioSilverSchema,
    IBGEValidationError,
    MesorregiaoSchema,
    MicrorregiaoSchema,
    MunicipioSchema,
    PIBSilverSchema,
    PopulacaoSilverSchema,
    RegiaoImediataSchema,
    RegiaoIntermediariaSchema,
    RegiaoSchema,
    UFSchema,
    validate_censitario_record,
    validate_maua_payload,
    validate_municipio_payload,
    validate_pib_record,
    validate_populacao_record,
)

__all__ = [
    "CensitarioSilverSchema",
    "IBGEValidationError",
    "MesorregiaoSchema",
    "MicrorregiaoSchema",
    "MunicipioSchema",
    "PIBSilverSchema",
    "PopulacaoSilverSchema",
    "RegiaoImediataSchema",
    "RegiaoIntermediariaSchema",
    "RegiaoSchema",
    "UFSchema",
    "validate_censitario_record",
    "validate_maua_payload",
    "validate_municipio_payload",
    "validate_pib_record",
    "validate_populacao_record",
]
