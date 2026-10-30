"""Contratos de dados e validação de esquemas via Pydantic v2.

Define os modelos tipados e as regras de qualidade dos dados (Data Quality)
para os nós cadastrais e territoriais retornados pela API de Localidades do IBGE.
"""

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from desafio_ibge.config.settings import MAUA_IBGE_CODE

logger = logging.getLogger(__name__)


class IBGEValidationError(Exception):
    """Exceção levantada quando um payload do IBGE viola o contrato de dados."""


class RegiaoSchema(BaseModel):
    """Esquema de Macrorregião geográfica (ex: Sudeste, Sul, etc.)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(..., description="Identificador da Macrorregião")
    sigla: str = Field(..., min_length=2, max_length=2, description="Sigla da Região")
    nome: str = Field(..., min_length=1, description="Nome da Macrorregião")


class UFSchema(BaseModel):
    """Esquema de Unidade da Federação (Estado)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(..., description="Código numérico da UF (ex: 35 para SP)")
    sigla: str = Field(..., min_length=2, max_length=2, description="Sigla da UF")
    nome: str = Field(..., min_length=1, description="Nome do Estado")
    regiao: RegiaoSchema = Field(..., description="Macrorregião à qual pertence a UF")


class MesorregiaoSchema(BaseModel):
    """Esquema de Mesorregião geográfica (Divisão Tradicional de 1989)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(..., description="Código da mesorregião")
    nome: str = Field(..., min_length=1, description="Nome da mesorregião")
    uf: UFSchema = Field(..., alias="UF", description="Unidade da Federação")


class MicrorregiaoSchema(BaseModel):
    """Esquema de Microrregião geográfica (Divisão Tradicional de 1989)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(..., description="Código da microrregião")
    nome: str = Field(..., min_length=1, description="Nome da microrregião")
    mesorregiao: MesorregiaoSchema = Field(
        ..., description="Mesorregião à qual pertence"
    )


class RegiaoIntermediariaSchema(BaseModel):
    """Esquema de Região Geográfica Intermediária (Divisão de 2017)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(..., description="Código da Região Intermediária")
    nome: str = Field(..., min_length=1, description="Nome da Região Intermediária")
    uf: UFSchema = Field(..., alias="UF", description="Unidade da Federação")


class RegiaoImediataSchema(BaseModel):
    """Esquema de Região Geográfica Imediata (Divisão de 2017)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(..., description="Código da Região Imediata")
    nome: str = Field(..., min_length=1, description="Nome da Região Imediata")
    regiao_intermediaria: RegiaoIntermediariaSchema = Field(
        ...,
        alias="regiao-intermediaria",
        description="Região Intermediária vinculada",
    )


class MunicipioSchema(BaseModel):
    """Esquema principal representando um Município brasileiro na base do IBGE."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(..., description="Código de 7 dígitos do município no IBGE")
    nome: str = Field(..., min_length=1, description="Nome oficial do município")
    microrregiao: MicrorregiaoSchema = Field(
        ..., description="Hierarquia de Microrregião (1989)"
    )
    regiao_imediata: RegiaoImediataSchema = Field(
        ...,
        alias="regiao-imediata",
        description="Hierarquia de Região Imediata (2017)",
    )

    @field_validator("id")
    @classmethod
    def validate_ibge_code_format(cls, value: int) -> int:
        """Garante que o código IBGE possui exatamente 7 dígitos válidos."""
        str_val = str(value)
        if len(str_val) != 7 or not str_val.isdigit():
            msg = (
                f"Código IBGE municipal deve conter exatamente 7 dígitos numéricos. "
                f"Valor recebido: {value}"
            )
            logger.error(msg)
            raise ValueError(msg)
        return value


def validate_municipio_payload(
    data: dict[str, Any],
    expected_id: int | None = None,
) -> MunicipioSchema:
    """Valida um payload JSON de município contra o contrato de dados Pydantic.

    Args:
        data: Dicionário bruto retornado pela API do IBGE.
        expected_id: Código opcional para validação estrita (ex: MAUA_IBGE_CODE).

    Returns:
        Instância validada de MunicipioSchema.

    Raises:
        IBGEValidationError: Se o payload for inválido, incompleto ou divergir do ID.
    """
    if not isinstance(data, dict):
        msg = (
            f"Payload para validação deve ser um dicionário. "
            f"Recebido: {type(data).__name__}"
        )
        logger.error(msg)
        raise IBGEValidationError(msg)

    try:
        model = MunicipioSchema.model_validate(data)
    except ValidationError as exc:
        msg = f"Falha de validação no contrato de dados do IBGE: {exc}"
        logger.error(msg)
        raise IBGEValidationError(msg) from exc

    if expected_id is not None and model.id != expected_id:
        msg = (
            f"Código municipal divergente do esperado. "
            f"Esperado: {expected_id}, recebido: {model.id}"
        )
        logger.error(msg)
        raise IBGEValidationError(msg)

    logger.info(
        "Payload validado com sucesso: %s (ID %s)",
        model.nome,
        model.id,
    )
    return model


def validate_maua_payload(data: dict[str, Any]) -> MunicipioSchema:
    """Valida especificamente o payload de Mauá contra o contrato e o código 3529401.

    Args:
        data: Dicionário contendo os dados de Mauá retornados pela API.

    Returns:
        MunicipioSchema com os dados validados.
    """
    return validate_municipio_payload(data, expected_id=MAUA_IBGE_CODE)
