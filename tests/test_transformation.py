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


# ---------------------------------------------------------------------------
# Testes dos Contratos Pydantic v2 e Transformações Silver Socioeconômicas
# ---------------------------------------------------------------------------


def test_populacao_silver_schema_valid() -> None:
    """Testa validação bem-sucedida de contrato de População Silver."""
    from desafio_ibge.validation.schema import validate_populacao_record

    valid_data = {
        "municipio_id": 3529401,
        "ano_referencia": 2022,
        "populacao": 418261,
        "tipo_populacao": "Censo Demográfico",
        "unidade": "Pessoas",
        "fonte_oficial": "IBGE - Censo Demográfico 2022",
        "bronze_indicador": "censo_pop_area_densidade",
    }
    model = validate_populacao_record(valid_data)
    assert model.municipio_id == 3529401
    assert model.populacao == 418261
    assert model.tipo_populacao == "Censo Demográfico"


@pytest.mark.parametrize("invalid_id", [12345, 123456, 12345678, "texto"])
def test_populacao_silver_schema_invalid_ibge_id(invalid_id: Any) -> None:
    """Rejeita códigos de município que não tenham 7 dígitos numéricos."""
    from desafio_ibge.validation.schema import (
        IBGEValidationError,
        validate_populacao_record,
    )

    data = {
        "municipio_id": invalid_id,
        "ano_referencia": 2022,
        "populacao": 418261,
        "tipo_populacao": "Censo Demográfico",
        "unidade": "Pessoas",
        "fonte_oficial": "IBGE",
        "bronze_indicador": "censo",
    }
    with pytest.raises(IBGEValidationError):
        validate_populacao_record(data)


@pytest.mark.parametrize("invalid_pop", [0, -100])
def test_populacao_silver_schema_invalid_populacao(invalid_pop: int) -> None:
    """Rejeita contagens populacionais menores ou iguais a zero."""
    from desafio_ibge.validation.schema import (
        IBGEValidationError,
        validate_populacao_record,
    )

    data = {
        "municipio_id": 3529401,
        "ano_referencia": 2022,
        "populacao": invalid_pop,
        "tipo_populacao": "Censo Demográfico",
        "unidade": "Pessoas",
        "fonte_oficial": "IBGE",
        "bronze_indicador": "censo",
    }
    with pytest.raises(IBGEValidationError):
        validate_populacao_record(data)


def test_pib_silver_schema_valid() -> None:
    """Testa validação do contrato de PIB Silver com valores finitos."""
    from desafio_ibge.validation.schema import validate_pib_record

    valid_data = {
        "municipio_id": 3529401,
        "ano_referencia": 2023,
        "indicador_id": 46997,
        "indicador_nome": "Produto Interno Bruto a preços correntes",
        "valor": 25000732.02,
        "unidade": "Mil Reais",
        "tipo_valor": "Corrente",
        "fonte_oficial": "IBGE - Produto Interno Bruto dos Municípios",
        "bronze_indicador": "pib_municipal_historico",
    }
    model = validate_pib_record(valid_data)
    assert model.indicador_id == 46997
    assert model.valor == 25000732.02


@pytest.mark.parametrize("invalid_val", [float("nan"), float("inf"), float("-inf")])
def test_pib_silver_schema_rejects_nan_inf(invalid_val: float) -> None:
    """Garante que NaN e Infinito são expressamente rejeitados na validação."""
    from desafio_ibge.validation.schema import (
        IBGEValidationError,
        validate_pib_record,
    )

    data = {
        "municipio_id": 3529401,
        "ano_referencia": 2023,
        "indicador_id": 46997,
        "indicador_nome": "PIB",
        "valor": invalid_val,
        "unidade": "Mil Reais",
        "tipo_valor": "Corrente",
        "fonte_oficial": "IBGE",
        "bronze_indicador": "pib",
    }
    with pytest.raises(IBGEValidationError):
        validate_pib_record(data)


def test_censitario_silver_schema_valid() -> None:
    """Testa contrato de dados censitários detalhados."""
    from desafio_ibge.validation.schema import validate_censitario_record

    valid_data = {
        "municipio_id": 3529401,
        "ano_referencia": 2022,
        "variavel_id": 6318,
        "variavel_nome": "Área territorial",
        "categoria_classificacao": "Total",
        "valor": 61.937,
        "unidade": "km²",
        "fonte_oficial": "IBGE - Censo Demográfico 2022",
        "bronze_indicador": "censo_pop_area_densidade",
    }
    model = validate_censitario_record(valid_data)
    assert model.variavel_id == 6318
    assert model.valor == 61.937


def test_transform_bronze_populacao() -> None:
    """Testa normalização tabular de Censo e Estimativas filtrando valores inválidos."""
    from desafio_ibge.transformation.normalizer import transform_bronze_populacao

    mock_records = [
        {
            "indicador": "censo_pop_area_densidade",
            "payload": [
                {
                    "id": "93",
                    "variavel": "População residente",
                    "unidade": "Pessoas",
                    "resultados": [
                        {
                            "series": [
                                {
                                    "localidade": {"id": "3529401"},
                                    "serie": {"2022": "418261"},
                                }
                            ]
                        }
                    ],
                }
            ],
        },
        {
            "indicador": "populacao_estimada_historica",
            "payload": [
                {
                    "id": "9324",
                    "variavel": "População residente estimada",
                    "unidade": "Pessoas",
                    "resultados": [
                        {
                            "series": [
                                {
                                    "localidade": {"id": "3529401"},
                                    "serie": {
                                        "2020": "415000",
                                        "2021": "-",
                                        "2026": "...",
                                    },
                                }
                            ]
                        }
                    ],
                }
            ],
        },
    ]

    df = transform_bronze_populacao(mock_records, validate=True)
    assert len(df) == 2  # 2022 (censo) e 2020 (estimativa); "-", "..." ignorados
    assert set(df["ano_referencia"]) == {2020, 2022}
    assert (
        df.loc[df["ano_referencia"] == 2022, "tipo_populacao"].iloc[0]
        == "Censo Demográfico"
    )
    assert (
        df.loc[df["ano_referencia"] == 2020, "tipo_populacao"].iloc[0]
        == "Estimativa Populacional"
    )


def test_transform_bronze_pib_pesquisa38() -> None:
    """Testa normalização do PIB desaninhando múltiplos anos e omitindo nulos."""
    from desafio_ibge.transformation.normalizer import transform_bronze_pib

    mock_pib_record = {
        "indicador": "pib_municipal_historico",
        "municipio_id": 3529401,
        "payload": [
            {
                "id": 46997,
                "indicador": "Produto Interno Bruto a preços correntes",
                "res": [
                    {
                        "localidade": "352940",
                        "res": {
                            "2021": "20776212.74",
                            "2022": "24111460.53",
                            "2023": None,  # Não deve ser imputado como 0
                        },
                    }
                ],
            }
        ],
    }

    df = transform_bronze_pib(mock_pib_record, validate=True)
    assert len(df) == 2
    assert set(df["ano_referencia"]) == {2021, 2022}
    assert df["valor"].iloc[0] > 0
    assert df["unidade"].iloc[0] == "Mil Reais"
    assert df["tipo_valor"].iloc[0] == "Corrente"


def test_transform_bronze_censitario() -> None:
    """Testa normalização de variáveis censitárias com categorias estratificadas."""
    from desafio_ibge.transformation.normalizer import transform_bronze_censitario

    mock_censitario_records = [
        {
            "indicador": "censo_pop_area_densidade",
            "payload": [
                {
                    "id": "6318",
                    "variavel": "Área territorial",
                    "unidade": "km²",
                    "resultados": [
                        {
                            "series": [
                                {
                                    "localidade": {"id": "3529401"},
                                    "serie": {"2022": "61.937"},
                                }
                            ]
                        }
                    ],
                }
            ],
        },
        {
            "indicador": "censo_sexo",
            "payload": [
                {
                    "id": "93",
                    "variavel": "População residente",
                    "unidade": "Pessoas",
                    "resultados": [
                        {
                            "classificacoes": [{"categoria": {"4": "Homens"}}],
                            "series": [
                                {
                                    "localidade": {"id": "3529401"},
                                    "serie": {"2022": "201348"},
                                }
                            ],
                        },
                        {
                            "classificacoes": [{"categoria": {"5": "Mulheres"}}],
                            "series": [
                                {
                                    "localidade": {"id": "3529401"},
                                    "serie": {"2022": "216913"},
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    ]

    df = transform_bronze_censitario(mock_censitario_records, validate=True)
    assert len(df) == 3
    assert set(df["categoria_classificacao"]) == {"Total", "Homens", "Mulheres"}
    assert "Área territorial" in df["variavel_nome"].values
    assert "População residente por sexo" in df["variavel_nome"].values


def test_transform_bronze_empty_payloads() -> None:
    """Testa robustez de funções de transformação com payloads nulos ou vazios."""
    from desafio_ibge.transformation.normalizer import (
        transform_bronze_censitario,
        transform_bronze_pib,
        transform_bronze_populacao,
    )

    df_pop = transform_bronze_populacao([])
    assert df_pop.empty
    assert list(df_pop.columns) == [
        "municipio_id",
        "ano_referencia",
        "populacao",
        "tipo_populacao",
        "unidade",
        "fonte_oficial",
        "bronze_indicador",
    ]

    df_pib = transform_bronze_pib({"payload": None})
    assert df_pib.empty

    df_cen = transform_bronze_censitario([{"payload": {}}])
    assert df_cen.empty


def test_transform_socioeconomico_from_bronze_integration(tmp_path: Any) -> None:
    """Testa leitura da camada Bronze do SQLite e transformação integrada."""
    from desafio_ibge.loading.storage import save_bronze_socioeconomico
    from desafio_ibge.transformation.normalizer import (
        transform_socioeconomico_from_bronze,
    )

    db_test = tmp_path / "test_socio.db"

    # Injeta mock na bronze
    save_bronze_socioeconomico(
        municipio_id=MAUA_IBGE_CODE,
        indicador="censo_pop_area_densidade",
        periodo_referencia="2022",
        fonte_oficial="IBGE",
        endpoint_url="http://test",
        raw_payload=[
            {
                "id": "93",
                "variavel": "População",
                "unidade": "Pessoas",
                "resultados": [
                    {
                        "series": [
                            {
                                "localidade": {"id": str(MAUA_IBGE_CODE)},
                                "serie": {"2022": "418261"},
                            }
                        ]
                    }
                ],
            }
        ],
        db_path=db_test,
    )

    res = transform_socioeconomico_from_bronze(db_path=db_test, validate=True)
    assert "populacao" in res
    assert "pib" in res
    assert "censitario" in res
    assert len(res["populacao"]) == 1


def test_validation_error_exceptions() -> None:
    """Testa que schemas Silver levantam IBGEValidationError em dados inválidos."""
    from desafio_ibge.validation.schema import (
        IBGEValidationError,
        validate_censitario_record,
        validate_pib_record,
        validate_populacao_record,
    )

    with pytest.raises(IBGEValidationError):
        validate_populacao_record({"municipio_id": "invalido"})

    with pytest.raises(IBGEValidationError):
        validate_pib_record({"municipio_id": 3529401, "valor": "invalido"})

    with pytest.raises(IBGEValidationError):
        validate_censitario_record({"municipio_id": 3529401, "variavel_id": "txt"})
