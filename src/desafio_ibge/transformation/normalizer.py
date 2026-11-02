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


# ---------------------------------------------------------------------------
# Mapeamentos e Transformações da Camada Silver Socioeconômica
# ---------------------------------------------------------------------------

PESQUISA_38_INDICADORES: dict[int, tuple[str, str, str]] = {
    # id: (indicador_nome, unidade, tipo_valor)
    46997: (
        "Produto Interno Bruto a preços correntes",
        "Mil Reais",
        "Corrente",
    ),
    47001: (
        "Produto Interno Bruto per capita",
        "Reais",
        "Per Capita",
    ),
    47004: (
        "Valor adicionado bruto a preços correntes total",
        "Mil Reais",
        "Corrente",
    ),
    47006: (
        "Valor adicionado bruto da agropecuária",
        "Mil Reais",
        "Corrente",
    ),
    47007: (
        "Valor adicionado bruto da indústria",
        "Mil Reais",
        "Corrente",
    ),
    47008: (
        "Valor adicionado bruto dos serviços",
        "Mil Reais",
        "Corrente",
    ),
    47009: (
        "Valor adicionado bruto da administração pública",
        "Mil Reais",
        "Corrente",
    ),
    47022: (
        "Impostos, líquidos de subsídios, sobre produtos a preços correntes",
        "Mil Reais",
        "Corrente",
    ),
    46999: (
        "Produto Interno Bruto a preços correntes (1999-2012)",
        "Mil Reais",
        "Corrente",
    ),
    47018: (
        "Valor adicionado bruto da agropecuária (1999-2012)",
        "Mil Reais",
        "Corrente",
    ),
    47019: (
        "Valor adicionado bruto da indústria (1999-2012)",
        "Mil Reais",
        "Corrente",
    ),
    47020: (
        "Valor adicionado bruto dos serviços (1999-2012)",
        "Mil Reais",
        "Corrente",
    ),
    47024: (
        "Impostos sobre produtos (1999-2012)",
        "Mil Reais",
        "Corrente",
    ),
    46998: (
        "Produto Interno Bruto a preços correntes (2002-2009)",
        "Mil Reais",
        "Corrente",
    ),
    47010: (
        "Valor adicionado bruto da agropecuária (2002-2009)",
        "Mil Reais",
        "Corrente",
    ),
    47012: (
        "Valor adicionado bruto da indústria (2002-2009)",
        "Mil Reais",
        "Corrente",
    ),
    47013: (
        "Valor adicionado bruto dos serviços (2002-2009)",
        "Mil Reais",
        "Corrente",
    ),
    47014: (
        "Valor adicionado bruto da administração pública (2002-2009)",
        "Mil Reais",
        "Corrente",
    ),
    47015: (
        "Valor adicionado bruto total (2002-2009)",
        "Mil Reais",
        "Corrente",
    ),
    47023: (
        "Impostos sobre produtos (2002-2009)",
        "Mil Reais",
        "Corrente",
    ),
    47002: (
        "Produto Interno Bruto per capita (2012)",
        "Reais",
        "Per Capita",
    ),
}

SILVER_POPULACAO_COLUMNS = [
    "municipio_id",
    "ano_referencia",
    "populacao",
    "tipo_populacao",
    "unidade",
    "fonte_oficial",
    "bronze_indicador",
]

SILVER_PIB_COLUMNS = [
    "municipio_id",
    "ano_referencia",
    "indicador_id",
    "indicador_nome",
    "valor",
    "unidade",
    "tipo_valor",
    "fonte_oficial",
    "bronze_indicador",
]

SILVER_CENSITARIO_COLUMNS = [
    "municipio_id",
    "ano_referencia",
    "variavel_id",
    "variavel_nome",
    "categoria_classificacao",
    "valor",
    "unidade",
    "fonte_oficial",
    "bronze_indicador",
]


def _is_valid_numeric_string(val: Any) -> bool:
    """Verifica se um valor retornado pelo IBGE representa um número válido."""
    if val is None:
        return False
    str_val = str(val).strip()
    if str_val in ("", "-", "...", "X", ".."):
        return False
    try:
        float(str_val)
        return True
    except (ValueError, TypeError):
        return False


def transform_bronze_populacao(
    bronze_records: list[dict[str, Any]],
    validate: bool = True,
) -> pd.DataFrame:
    """Normaliza registros de contagem e estimativa populacional para a Silver.

    Processa os payloads brutos dos agregados 4714 (Censo 2022) e 6579 (Estimativas
    anuais 2001-2026), desaninhando a série temporal em formato tabular longo.

    Args:
        bronze_records: Lista de dicionários da bronze_ibge_socioeconomico.
        validate: Se True, valida cada linha através do schema PopulacaoSilverSchema.

    Returns:
        DataFrame Pandas estruturado e tipado para a tabela silver_ibge_populacao.
    """
    from desafio_ibge.validation.schema import validate_populacao_record

    records: list[dict[str, Any]] = []

    for item in bronze_records:
        indicador_chave = item.get("indicador", "")
        payload = item.get("payload", item.get("payload_json"))
        if isinstance(payload, str):
            import json

            payload = json.loads(payload)

        if not isinstance(payload, list):
            continue

        for aggregated_var in payload:
            var_id = str(aggregated_var.get("id", ""))
            unidade = aggregated_var.get("unidade", "Pessoas")
            resultados = aggregated_var.get("resultados", [])

            for res in resultados:
                series_list = res.get("series", [])
                for serie_obj in series_list:
                    mun_id = int(serie_obj.get("localidade", {}).get("id", 0))
                    serie_dict = serie_obj.get("serie", {})

                    for ano_str, valor_raw in serie_dict.items():
                        if not _is_valid_numeric_string(valor_raw):
                            continue

                        ano = int(ano_str)
                        populacao_val = int(round(float(str(valor_raw))))

                        if indicador_chave == "censo_pop_area_densidade":
                            # No agregado 4714, a variável 93 é 'População residente'
                            if var_id != "93":
                                continue
                            tipo_pop = "Censo Demográfico"
                            fonte = "IBGE - Censo Demográfico 2022"
                        else:
                            tipo_pop = "Estimativa Populacional"
                            fonte = "IBGE - Estimativas de População"

                        row_dict = {
                            "municipio_id": mun_id,
                            "ano_referencia": ano,
                            "populacao": populacao_val,
                            "tipo_populacao": tipo_pop,
                            "unidade": unidade,
                            "fonte_oficial": fonte,
                            "bronze_indicador": indicador_chave,
                        }

                        if validate:
                            validate_populacao_record(row_dict)

                        records.append(row_dict)

    if not records:
        return pd.DataFrame(columns=SILVER_POPULACAO_COLUMNS)

    df = pd.DataFrame(records)[SILVER_POPULACAO_COLUMNS]
    df = df.drop_duplicates(subset=["municipio_id", "ano_referencia", "tipo_populacao"])
    df = df.sort_values(
        by=["municipio_id", "ano_referencia", "tipo_populacao"]
    ).reset_index(drop=True)

    df["municipio_id"] = df["municipio_id"].astype("int64")
    df["ano_referencia"] = df["ano_referencia"].astype("int64")
    df["populacao"] = df["populacao"].astype("int64")
    df["tipo_populacao"] = df["tipo_populacao"].astype("string")
    df["unidade"] = df["unidade"].astype("string")
    df["fonte_oficial"] = df["fonte_oficial"].astype("string")
    df["bronze_indicador"] = df["bronze_indicador"].astype("string")

    logger.info("Transformação Silver População: %d linha(s) geradas.", len(df))
    return df


def transform_bronze_pib(
    bronze_record: dict[str, Any],
    validate: bool = True,
) -> pd.DataFrame:
    """Normaliza a série temporal histórica da Pesquisa 38 (PIB Municipal).

    Desaninha todos os indicadores econômicos (PIB corrente, per capita, VABs
    setoriais e impostos) em formato longo relacional. Filtra valores ausentes
    sem imputação arbitrária de zero.

    Args:
        bronze_record: Dicionário do registro Bronze de pib_municipal_historico.
        validate: Se True, valida cada linha através do schema PIBSilverSchema.

    Returns:
        DataFrame Pandas estruturado e tipado para a tabela silver_ibge_pib.
    """
    from desafio_ibge.validation.schema import validate_pib_record

    payload = bronze_record.get("payload", bronze_record.get("payload_json"))
    if isinstance(payload, str):
        import json

        payload = json.loads(payload)

    if not isinstance(payload, list):
        return pd.DataFrame(columns=SILVER_PIB_COLUMNS)

    records: list[dict[str, Any]] = []
    fonte_oficial = "IBGE - Produto Interno Bruto dos Municípios"
    bronze_indicador = bronze_record.get("indicador", "pib_municipal_historico")
    mun_id_default = int(bronze_record.get("municipio_id", 3529401))

    for ind_item in payload:
        raw_id = ind_item.get("id")
        try:
            indicador_id = int(raw_id)
        except (ValueError, TypeError):
            continue

        raw_nome = ind_item.get("indicador")
        meta = PESQUISA_38_INDICADORES.get(indicador_id)

        if meta:
            indicador_nome, unidade, tipo_valor = meta
        else:
            indicador_nome = (
                str(raw_nome) if raw_nome else f"Indicador PIB {indicador_id}"
            )
            unidade_obj = ind_item.get("unidade")
            if isinstance(unidade_obj, dict):
                unidade = unidade_obj.get("classe", "Mil Reais")
            else:
                unidade = str(unidade_obj) if unidade_obj else "Mil Reais"
            tipo_valor = (
                "Per Capita" if "per capita" in indicador_nome.lower() else "Corrente"
            )

        # Suporta tanto formato da API de Pesquisas ('res') quanto Agregados ('series')
        localidade_list = ind_item.get("res", ind_item.get("series", []))
        if not isinstance(localidade_list, list):
            continue

        for loc_obj in localidade_list:
            serie_dict = loc_obj.get("res", loc_obj.get("serie", {}))
            if not isinstance(serie_dict, dict):
                continue

            for ano_str, valor_raw in serie_dict.items():
                if not _is_valid_numeric_string(valor_raw):
                    continue

                ano = int(ano_str)
                valor_float = float(str(valor_raw))

                row_dict = {
                    "municipio_id": mun_id_default,
                    "ano_referencia": ano,
                    "indicador_id": indicador_id,
                    "indicador_nome": indicador_nome,
                    "valor": valor_float,
                    "unidade": unidade,
                    "tipo_valor": tipo_valor,
                    "fonte_oficial": fonte_oficial,
                    "bronze_indicador": bronze_indicador,
                }

                if validate:
                    validate_pib_record(row_dict)

                records.append(row_dict)

    if not records:
        return pd.DataFrame(columns=SILVER_PIB_COLUMNS)

    df = pd.DataFrame(records)[SILVER_PIB_COLUMNS]
    df = df.drop_duplicates(subset=["municipio_id", "ano_referencia", "indicador_id"])
    df = df.sort_values(
        by=["municipio_id", "ano_referencia", "indicador_id"]
    ).reset_index(drop=True)

    df["municipio_id"] = df["municipio_id"].astype("int64")
    df["ano_referencia"] = df["ano_referencia"].astype("int64")
    df["indicador_id"] = df["indicador_id"].astype("int64")
    df["indicador_nome"] = df["indicador_nome"].astype("string")
    df["valor"] = df["valor"].astype("float64")
    df["unidade"] = df["unidade"].astype("string")
    df["tipo_valor"] = df["tipo_valor"].astype("string")
    df["fonte_oficial"] = df["fonte_oficial"].astype("string")
    df["bronze_indicador"] = df["bronze_indicador"].astype("string")

    logger.info("Transformação Silver PIB: %d linha(s) geradas.", len(df))
    return df


def transform_bronze_censitario(
    bronze_records: list[dict[str, Any]],
    validate: bool = True,
) -> pd.DataFrame:
    """Normaliza variáveis censitárias detalhadas do Censo 2022 para a Silver.

    Processa os agregados 4714 (Área e Densidade), 9543 (Alfabetização) e
    9514 (População por Sexo).

    Args:
        bronze_records: Lista de registros Bronze socioeconômicos.
        validate: Se True, valida cada registro via CensitarioSilverSchema.

    Returns:
        DataFrame Pandas estruturado e tipado para silver_ibge_censitario.
    """
    from desafio_ibge.validation.schema import validate_censitario_record

    records: list[dict[str, Any]] = []

    for item in bronze_records:
        indicador_chave = item.get("indicador", "")
        payload = item.get("payload", item.get("payload_json"))
        if isinstance(payload, str):
            import json

            payload = json.loads(payload)

        if not isinstance(payload, list):
            continue

        for agg_var in payload:
            raw_var_id = agg_var.get("id")
            try:
                var_id = int(raw_var_id)
            except (ValueError, TypeError):
                continue

            var_nome_raw = agg_var.get("variavel", "")
            unidade_default = agg_var.get("unidade", "")
            resultados = agg_var.get("resultados", [])

            for res in resultados:
                # Extrai categoria se presente (ex: Sexo -> Homens / Mulheres)
                categoria = "Total"
                classificacoes = res.get("classificacoes", [])
                if classificacoes:
                    cat_map = classificacoes[0].get("categoria", {})
                    if cat_map:
                        categoria = list(cat_map.values())[0]

                series_list = res.get("series", [])
                for serie_obj in series_list:
                    mun_id = int(serie_obj.get("localidade", {}).get("id", 0))
                    serie_dict = serie_obj.get("serie", {})

                    for ano_str, valor_raw in serie_dict.items():
                        if not _is_valid_numeric_string(valor_raw):
                            continue

                        ano = int(ano_str)
                        valor_float = float(str(valor_raw))

                        # Mapeamento semântico refinado por indicador
                        if indicador_chave == "censo_pop_area_densidade":
                            # Variável 93 é tratada na silver_ibge_populacao
                            if var_id == 93:
                                continue
                            if var_id == 6318:
                                nome_var = "Área territorial"
                                unidade = "km²"
                            elif var_id == 614:
                                nome_var = "Densidade demográfica"
                                unidade = "hab/km²"
                            else:
                                nome_var = var_nome_raw
                                unidade = unidade_default
                        elif indicador_chave == "censo_alfabetizacao":
                            nome_var = "Taxa de alfabetização"
                            unidade = "%"
                        elif indicador_chave == "censo_sexo":
                            nome_var = "População residente por sexo"
                            unidade = "Pessoas"
                        else:
                            nome_var = var_nome_raw
                            unidade = unidade_default

                        row_dict = {
                            "municipio_id": mun_id,
                            "ano_referencia": ano,
                            "variavel_id": var_id,
                            "variavel_nome": nome_var,
                            "categoria_classificacao": categoria,
                            "valor": valor_float,
                            "unidade": unidade,
                            "fonte_oficial": "IBGE - Censo Demográfico 2022",
                            "bronze_indicador": indicador_chave,
                        }

                        if validate:
                            validate_censitario_record(row_dict)

                        records.append(row_dict)

    if not records:
        return pd.DataFrame(columns=SILVER_CENSITARIO_COLUMNS)

    df = pd.DataFrame(records)[SILVER_CENSITARIO_COLUMNS]
    df = df.drop_duplicates(
        subset=[
            "municipio_id",
            "ano_referencia",
            "variavel_id",
            "categoria_classificacao",
        ]
    )
    df = df.sort_values(
        by=[
            "municipio_id",
            "ano_referencia",
            "variavel_id",
            "categoria_classificacao",
        ]
    ).reset_index(drop=True)

    df["municipio_id"] = df["municipio_id"].astype("int64")
    df["ano_referencia"] = df["ano_referencia"].astype("int64")
    df["variavel_id"] = df["variavel_id"].astype("int64")
    df["variavel_nome"] = df["variavel_nome"].astype("string")
    df["categoria_classificacao"] = df["categoria_classificacao"].astype("string")
    df["valor"] = df["valor"].astype("float64")
    df["unidade"] = df["unidade"].astype("string")
    df["fonte_oficial"] = df["fonte_oficial"].astype("string")
    df["bronze_indicador"] = df["bronze_indicador"].astype("string")

    logger.info("Transformação Silver Censitário: %d linha(s) geradas.", len(df))
    return df


def transform_socioeconomico_from_bronze(
    db_path: Any | None = None,
    validate: bool = True,
) -> dict[str, pd.DataFrame]:
    """Lê a camada Bronze do SQLite e gera todos os DataFrames da Silver Socioeconômica.

    Args:
        db_path: Caminho opcional do banco SQLite.
        validate: Se True, aplica validação Pydantic em cada linha gerada.

    Returns:
        Dicionário com DataFrames normalizados:
        {"populacao": df_populacao, "pib": df_pib, "censitario": df_censitario}
    """
    from desafio_ibge.loading.storage import (
        get_db_connection,
        read_bronze_socioeconomico,
    )

    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT DISTINCT municipio_id, indicador, periodo_referencia "
            "FROM bronze_ibge_socioeconomico;"
        )
        bronze_rows = cursor.fetchall()
    finally:
        conn.close()

    records_by_indicator: dict[str, dict[str, Any]] = {}
    for row in bronze_rows:
        mun_id = row["municipio_id"]
        ind = row["indicador"]
        per = row["periodo_referencia"]
        rec = read_bronze_socioeconomico(mun_id, ind, per, db_path=db_path)
        if rec:
            records_by_indicator[ind] = rec

    # 1. Transformação População (Censo 2022 + Estimativas 2001-2026)
    pop_records = []
    if "censo_pop_area_densidade" in records_by_indicator:
        pop_records.append(records_by_indicator["censo_pop_area_densidade"])
    if "populacao_estimada_historica" in records_by_indicator:
        pop_records.append(records_by_indicator["populacao_estimada_historica"])

    df_populacao = transform_bronze_populacao(pop_records, validate=validate)

    # 2. Transformação PIB Histórico (Pesquisa 38)
    pib_record = records_by_indicator.get("pib_municipal_historico", {})
    df_pib = transform_bronze_pib(pib_record, validate=validate)

    # 3. Transformação Censitário Detalhado
    censitario_records = []
    for key in ("censo_pop_area_densidade", "censo_alfabetizacao", "censo_sexo"):
        if key in records_by_indicator:
            censitario_records.append(records_by_indicator[key])

    df_censitario = transform_bronze_censitario(censitario_records, validate=validate)

    return {
        "populacao": df_populacao,
        "pib": df_pib,
        "censitario": df_censitario,
    }
