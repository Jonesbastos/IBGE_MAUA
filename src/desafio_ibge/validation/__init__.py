"""Submódulo de validação de schemas e contratos de dados."""

from desafio_ibge.validation.schema import (
    IBGEValidationError,
    MesorregiaoSchema,
    MicrorregiaoSchema,
    MunicipioSchema,
    RegiaoImediataSchema,
    RegiaoIntermediariaSchema,
    RegiaoSchema,
    UFSchema,
    validate_maua_payload,
    validate_municipio_payload,
)

__all__ = [
    "IBGEValidationError",
    "MesorregiaoSchema",
    "MicrorregiaoSchema",
    "MunicipioSchema",
    "RegiaoImediataSchema",
    "RegiaoIntermediariaSchema",
    "RegiaoSchema",
    "UFSchema",
    "validate_maua_payload",
    "validate_municipio_payload",
]
