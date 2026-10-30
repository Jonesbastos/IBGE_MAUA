"""Testes unitários para os módulos de validação de schema e transformação."""

import copy
from typing import Any

import pytest

from desafio_ibge.config.settings import MAUA_IBGE_CODE
from desafio_ibge.transformation.normalizer import (
    json_to_dataframe,
    sanitize_column_names,
)
from desafio_ibge.validation.schema import (
    IBGEValidationError,
    MunicipioSchema,
    validate_maua_payload,
    validate_municipio_payload,
)


def test_validate_maua_payload_success(maua_raw_payload: dict[str, Any]) -> None:
    """Valida se o payload oficial de Mauá é aceito com sucesso pelo Pydantic."""
    schema = validate_maua_payload(maua_raw_payload)
    assert schema.id == MAUA_IBGE_CODE
    assert schema.nome == "Mauá"
    assert schema.microrregiao.id == 35061
    assert schema.microrregiao.mesorregiao.uf.sigla == "SP"
    assert schema.regiao_imediata.id == 350001
    assert schema.regiao_imediata.regiao_intermediaria.id == 3501


def test_validate_municipio_payload_non_dict() -> None:
    """Valida que entradas que não são dicionários levantam IBGEValidationError."""
    with pytest.raises(IBGEValidationError, match="deve ser um dicionário"):
        validate_municipio_payload(["não", "um", "dict"])  # type: ignore


@pytest.mark.parametrize(
    "invalid_id",
    [
        12345,  # 5 dígitos (inválido)
        123456,  # 6 dígitos (inválido)
        12345678,  # 8 dígitos (inválido)
        -3529401,  # negativo
    ],
)
def test_validate_ibge_code_invalid_digits(
    maua_raw_payload: dict[str, Any],
    invalid_id: int,
) -> None:
    """Valida rejeição de códigos IBGE fora do padrão estrito de 7 dígitos."""
    payload = copy.deepcopy(maua_raw_payload)
    payload["id"] = invalid_id
    with pytest.raises(IBGEValidationError, match="7 dígitos numéricos"):
        validate_municipio_payload(payload)


def test_validate_maua_divergent_expected_id(maua_raw_payload: dict[str, Any]) -> None:
    """Valida falha ao esperar Mauá (3529401) e receber outro código de 7 dígitos."""
    payload = copy.deepcopy(maua_raw_payload)
    payload["id"] = 3550308  # São Paulo capital (7 dígitos válidos)

    with pytest.raises(IBGEValidationError, match="Código municipal divergente"):
        validate_maua_payload(payload)


@pytest.mark.parametrize(
    "missing_key",
    ["id", "nome", "microrregiao", "regiao-imediata"],
)
def test_validate_missing_mandatory_fields(
    maua_raw_payload: dict[str, Any],
    missing_key: str,
) -> None:
    """Garante que a ausência de nós obrigatórios no primeiro nível levanta erro."""
    payload = copy.deepcopy(maua_raw_payload)
    del payload[missing_key]

    with pytest.raises(IBGEValidationError, match="Falha de validação"):
        validate_municipio_payload(payload)


@pytest.mark.parametrize(
    "invalid_key,invalid_value",
    [
        ("id", None),
        ("id", "texto_invalido"),
        ("nome", None),
        ("nome", ""),
    ],
)
def test_validate_invalid_field_types_or_nulls(
    maua_raw_payload: dict[str, Any],
    invalid_key: str,
    invalid_value: Any,
) -> None:
    """Valida rejeição de tipos incompatíveis ou campos nulos obrigatórios."""
    payload = copy.deepcopy(maua_raw_payload)
    payload[invalid_key] = invalid_value

    with pytest.raises(IBGEValidationError):
        validate_municipio_payload(payload)


def test_json_to_dataframe_flattening_success(
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa achatamento bem-sucedido de Mauá para DataFrame tabular de 1 linha."""
    df = json_to_dataframe(maua_raw_payload)

    # Verifica formato do DataFrame
    assert df.shape[0] == 1
    assert df.shape[1] == 22

    # Verifica integridade dos campos achatados de primeiro e segundo nível
    assert df["id"].iloc[0] == MAUA_IBGE_CODE
    assert df["nome"].iloc[0] == "Mauá"
    assert df["microrregiao_id"].iloc[0] == 35061
    assert df["microrregiao_nome"].iloc[0] == "São Paulo"
    assert df["microrregiao_mesorregiao_id"].iloc[0] == 3515
    assert df["microrregiao_mesorregiao_nome"].iloc[0] == "Metropolitana de São Paulo"
    assert df["microrregiao_mesorregiao_uf_sigla"].iloc[0] == "SP"
    assert df["microrregiao_mesorregiao_uf_regiao_nome"].iloc[0] == "Sudeste"

    # Verifica divisão 2017 (Região Imediata e Intermediária)
    assert df["regiao_imediata_id"].iloc[0] == 350001
    assert df["regiao_imediata_nome"].iloc[0] == "São Paulo"
    assert df["regiao_imediata_regiao_intermediaria_id"].iloc[0] == 3501
    assert df["regiao_imediata_regiao_intermediaria_uf_sigla"].iloc[0] == "SP"


def test_json_to_dataframe_converts_hyphens_to_snake_case(
    maua_raw_payload: dict[str, Any],
) -> None:
    """Garante que nenhuma coluna do DataFrame final contenha hífens."""
    df = json_to_dataframe(maua_raw_payload)

    for col in df.columns:
        assert "-" not in col, f"Coluna '{col}' contém hífen proibido!"
        assert col == col.lower(), f"Coluna '{col}' não está em minúsculas!"

    # Verifica existência das colunas saneadas
    assert "regiao_imediata_id" in df.columns
    assert "regiao_imediata_regiao_intermediaria_id" in df.columns


def test_json_to_dataframe_preserves_original_payload(
    maua_raw_payload: dict[str, Any],
) -> None:
    """Verifica que a função de transformação não modifica o dicionário original."""
    payload_clone = copy.deepcopy(maua_raw_payload)

    # Executa a transformação
    _ = json_to_dataframe(maua_raw_payload)

    # O objeto original deve permanecer rigorosamente idêntico ao clone
    assert maua_raw_payload == payload_clone


def test_json_to_dataframe_from_pydantic_instance(
    maua_raw_payload: dict[str, Any],
) -> None:
    """Verifica compatibilidade com instâncias já validadas de MunicipioSchema."""
    schema_instance = validate_maua_payload(maua_raw_payload)
    assert isinstance(schema_instance, MunicipioSchema)

    df = json_to_dataframe(schema_instance)
    assert df.shape[0] == 1
    assert df["id"].iloc[0] == MAUA_IBGE_CODE
    assert "regiao_imediata_id" in df.columns


def test_json_to_dataframe_list_input(
    sp_municipios_payload: list[dict[str, Any]],
) -> None:
    """Testa transformação em lote recebendo uma lista de municípios."""
    df = json_to_dataframe(sp_municipios_payload)

    assert df.shape[0] == 2
    assert set(df["id"]) == {3547809, 3529401}
    assert set(df["nome"]) == {"Santo André", "Mauá"}


def test_sanitize_column_names_utility() -> None:
    """Testa diretamente a função de saneamento de nomes de colunas."""
    import pandas as pd

    cols = pd.Index(["id", "regiao-imediata_ID", "MICRORREGIAO-NOME"])
    sanitized = sanitize_column_names(cols)
    assert sanitized == ["id", "regiao_imediata_id", "microrregiao_nome"]
