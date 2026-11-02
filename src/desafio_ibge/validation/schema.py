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


# ---------------------------------------------------------------------------
# Contratos Pydantic v2 para as Tabelas Silver Socioeconômicas
# ---------------------------------------------------------------------------


class PopulacaoSilverSchema(BaseModel):
    """Contrato de dados para registros de população da camada Silver.

    Cobre tanto contagens censitárias (Censo 2022) quanto estimativas anuais.
    """

    model_config = ConfigDict(extra="ignore")

    municipio_id: int = Field(..., description="Código IBGE de 7 dígitos")
    ano_referencia: int = Field(
        ..., ge=1900, le=2100, description="Ano de referência da contagem"
    )
    populacao: int = Field(
        ..., gt=0, description="População residente apurada ou estimada"
    )
    tipo_populacao: str = Field(
        ...,
        min_length=1,
        description="Metodologia: 'Censo Demográfico' ou 'Estimativa Populacional'",
    )
    unidade: str = Field(default="Pessoas", min_length=1)
    fonte_oficial: str = Field(..., min_length=1, description="Fonte oficial do IBGE")
    bronze_indicador: str = Field(
        ..., min_length=1, description="Identificador do indicador na Bronze"
    )

    @field_validator("municipio_id")
    @classmethod
    def validate_municipio_id(cls, value: int) -> int:
        """Garante código IBGE de 7 dígitos numéricos."""
        str_val = str(value)
        if len(str_val) != 7 or not str_val.isdigit():
            msg = f"Código municipal deve ter exatamente 7 dígitos: {value}"
            logger.error(msg)
            raise ValueError(msg)
        return value


class PIBSilverSchema(BaseModel):
    """Contrato de dados para séries de PIB e VAB setorial da camada Silver."""

    model_config = ConfigDict(extra="ignore")

    municipio_id: int = Field(..., description="Código IBGE de 7 dígitos")
    ano_referencia: int = Field(
        ..., ge=1900, le=2100, description="Ano de referência econômico"
    )
    indicador_id: int = Field(
        ..., gt=0, description="Identificador numérico do indicador no IBGE"
    )
    indicador_nome: str = Field(
        ..., min_length=1, description="Descrição padronizada do indicador"
    )
    valor: float = Field(..., description="Valor numérico do indicador econômico")
    unidade: str = Field(..., min_length=1, description="Unidade monetária de medida")
    tipo_valor: str = Field(
        ..., min_length=1, description="Tipo do valor: 'Corrente' ou 'Per Capita'"
    )
    fonte_oficial: str = Field(
        default="IBGE - Produto Interno Bruto dos Municípios",
        min_length=1,
    )
    bronze_indicador: str = Field(
        default="pib_municipal_historico",
        min_length=1,
    )

    @field_validator("municipio_id")
    @classmethod
    def validate_municipio_id(cls, value: int) -> int:
        """Garante código IBGE de 7 dígitos numéricos."""
        str_val = str(value)
        if len(str_val) != 7 or not str_val.isdigit():
            msg = f"Código municipal deve ter exatamente 7 dígitos: {value}"
            logger.error(msg)
            raise ValueError(msg)
        return value

    @field_validator("valor")
    @classmethod
    def validate_valor_finito(cls, value: float) -> float:
        """Assegura que o valor é um número real finito (não NaN nem Infinito)."""
        import math

        if math.isnan(value) or math.isinf(value):
            msg = f"Valor econômico não pode ser NaN ou Infinito: {value}"
            logger.error(msg)
            raise ValueError(msg)
        return value


class CensitarioSilverSchema(BaseModel):
    """Contrato de dados para atributos censitários detalhados da camada Silver."""

    model_config = ConfigDict(extra="ignore")

    municipio_id: int = Field(..., description="Código IBGE de 7 dígitos")
    ano_referencia: int = Field(
        ..., ge=1900, le=2100, description="Ano de referência censitário"
    )
    variavel_id: int = Field(
        ..., gt=0, description="Identificador da variável no SIDRA"
    )
    variavel_nome: str = Field(
        ..., min_length=1, description="Nome oficial da variável apurada"
    )
    categoria_classificacao: str = Field(
        default="Total",
        min_length=1,
        description="Categoria demográfica (ex: 'Total', 'Homens', 'Mulheres')",
    )
    valor: float = Field(..., description="Valor medido apurado")
    unidade: str = Field(..., min_length=1, description="Unidade de medida")
    fonte_oficial: str = Field(
        default="IBGE - Censo Demográfico 2022",
        min_length=1,
    )
    bronze_indicador: str = Field(..., min_length=1)

    @field_validator("municipio_id")
    @classmethod
    def validate_municipio_id(cls, value: int) -> int:
        """Garante código IBGE de 7 dígitos numéricos."""
        str_val = str(value)
        if len(str_val) != 7 or not str_val.isdigit():
            msg = f"Código municipal deve ter exatamente 7 dígitos: {value}"
            logger.error(msg)
            raise ValueError(msg)
        return value

    @field_validator("valor")
    @classmethod
    def validate_valor_finito(cls, value: float) -> float:
        """Assegura que o valor é um número real finito."""
        import math

        if math.isnan(value) or math.isinf(value):
            msg = f"Valor censitário não pode ser NaN ou Infinito: {value}"
            logger.error(msg)
            raise ValueError(msg)
        return value


def validate_populacao_record(data: dict[str, Any]) -> PopulacaoSilverSchema:
    """Valida um registro tabular de população antes da inserção na Silver.

    Args:
        data: Dicionário contendo os campos do schema de população.

    Returns:
        Instância validada de PopulacaoSilverSchema.

    Raises:
        IBGEValidationError: Se violar os contratos de schema ou tipagem.
    """
    try:
        return PopulacaoSilverSchema.model_validate(data)
    except ValidationError as exc:
        msg = f"Falha de validação no contrato de População Silver: {exc}"
        logger.error(msg)
        raise IBGEValidationError(msg) from exc


def validate_pib_record(data: dict[str, Any]) -> PIBSilverSchema:
    """Valida um registro tabular econômico de PIB antes da inserção na Silver.

    Args:
        data: Dicionário contendo os campos do schema de PIB.

    Returns:
        Instância validada de PIBSilverSchema.

    Raises:
        IBGEValidationError: Se violar os contratos de schema ou tipagem.
    """
    try:
        return PIBSilverSchema.model_validate(data)
    except ValidationError as exc:
        msg = f"Falha de validação no contrato de PIB Silver: {exc}"
        logger.error(msg)
        raise IBGEValidationError(msg) from exc


def validate_censitario_record(data: dict[str, Any]) -> CensitarioSilverSchema:
    """Valida um registro tabular de atributos censitários antes da inserção na Silver.

    Args:
        data: Dicionário contendo os campos do schema censitário.

    Returns:
        Instância validada de CensitarioSilverSchema.

    Raises:
        IBGEValidationError: Se violar os contratos de schema ou tipagem.
    """
    try:
        return CensitarioSilverSchema.model_validate(data)
    except ValidationError as exc:
        msg = f"Falha de validação no contrato Censitário Silver: {exc}"
        logger.error(msg)
        raise IBGEValidationError(msg) from exc
