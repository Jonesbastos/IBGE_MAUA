"""Testes unitários para o módulo de extração da API do IBGE."""

from typing import Any

import pytest
import requests
import requests_mock as rm

from desafio_ibge.config.settings import (
    IBGE_AGREGADOS_BASE_URL,
    IBGE_BASE_URL,
    IBGE_PESQUISAS_BASE_URL,
    MAUA_IBGE_CODE,
    MAUA_NOME_ESPERADO,
)
from desafio_ibge.extraction.ibge_client import (
    IBGEClient,
    IBGEExtractionError,
    fetch_all_socioeconomico_maua,
    get_municipio_maua,
)

JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}


def test_fetch_municipio_by_id_success(
    requests_mock: rm.Mocker,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa extração bem-sucedida pelo endpoint direto do município."""
    url = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
    requests_mock.get(
        url,
        json=maua_raw_payload,
        headers=JSON_HEADERS,
        status_code=200,
    )

    with IBGEClient() as client:
        result = client.fetch_municipio_by_id(MAUA_IBGE_CODE)

    assert result["id"] == MAUA_IBGE_CODE
    assert result["nome"] == MAUA_NOME_ESPERADO
    assert "microrregiao" in result
    assert "regiao-imediata" in result


def test_fetch_municipio_divergent_id(
    requests_mock: rm.Mocker,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa falha quando a API retorna um ID divergente do solicitado."""
    url = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
    corrupted_payload = dict(maua_raw_payload)
    corrupted_payload["id"] = 9999999

    requests_mock.get(
        url,
        json=corrupted_payload,
        headers=JSON_HEADERS,
        status_code=200,
    )

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Divergência de identificador"):
            client.fetch_municipio_by_id(MAUA_IBGE_CODE)


def test_fetch_municipio_http_error(requests_mock: rm.Mocker) -> None:
    """Testa tratamento de erro HTTP 404/500."""
    url = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
    requests_mock.get(url, status_code=500)

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Erro HTTP ao consultar"):
            client.fetch_municipio_by_id(MAUA_IBGE_CODE)


def test_fetch_municipio_timeout(requests_mock: rm.Mocker) -> None:
    """Testa tratamento de timeout de rede."""
    url = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
    requests_mock.get(
        url,
        exc=requests.exceptions.ConnectTimeout("Tempo limite esgotado"),
    )

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Timeout"):
            client.fetch_municipio_by_id(MAUA_IBGE_CODE)


def test_fetch_municipio_invalid_content_type(requests_mock: rm.Mocker) -> None:
    """Testa resposta com Content-Type que não seja JSON."""
    url = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
    requests_mock.get(
        url,
        text="<html>Erro do Gateway</html>",
        headers={"Content-Type": "text/html"},
        status_code=200,
    )

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Content-Type inesperado"):
            client.fetch_municipio_by_id(MAUA_IBGE_CODE)


def test_fetch_municipio_invalid_json(requests_mock: rm.Mocker) -> None:
    """Testa resposta que falha no parsing JSON."""
    url = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
    requests_mock.get(
        url,
        text="{json quebrado...",
        headers={"Content-Type": "application/json"},
        status_code=200,
    )

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Falha ao decodificar JSON"):
            client.fetch_municipio_by_id(MAUA_IBGE_CODE)


def test_fetch_municipio_non_dict_json(requests_mock: rm.Mocker) -> None:
    """Testa resposta JSON válida mas que não é um dicionário."""
    url = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
    requests_mock.get(
        url,
        json=["item1", "item2"],
        headers=JSON_HEADERS,
        status_code=200,
    )

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Formato de resposta inesperado"):
            client.fetch_municipio_by_id(MAUA_IBGE_CODE)


def test_fetch_municipios_by_uf_success(
    requests_mock: rm.Mocker,
    sp_municipios_payload: list[dict[str, Any]],
) -> None:
    """Testa consulta da lista de municípios de um estado."""
    url = f"{IBGE_BASE_URL}/estados/35/municipios"
    requests_mock.get(
        url,
        json=sp_municipios_payload,
        headers=JSON_HEADERS,
        status_code=200,
    )

    with IBGEClient() as client:
        result = client.fetch_municipios_by_uf(35)

    assert isinstance(result, list)
    assert len(result) == 2


def test_fetch_municipios_by_uf_invalid_format(requests_mock: rm.Mocker) -> None:
    """Testa erro quando retorno de municípios por UF não é lista."""
    url = f"{IBGE_BASE_URL}/estados/35/municipios"
    requests_mock.get(
        url,
        json={"erro": "objeto invalido"},
        headers=JSON_HEADERS,
        status_code=200,
    )

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Esperado list de municípios"):
            client.fetch_municipios_by_uf(35)


def test_fetch_maua_from_uf_list_success(
    requests_mock: rm.Mocker,
    sp_municipios_payload: list[dict[str, Any]],
) -> None:
    """Testa extração de Mauá a partir do filtro na lista do Estado."""
    url = f"{IBGE_BASE_URL}/estados/35/municipios"
    requests_mock.get(
        url,
        json=sp_municipios_payload,
        headers=JSON_HEADERS,
        status_code=200,
    )

    with IBGEClient() as client:
        maua = client.fetch_maua_from_uf_list(uf_id=35, municipio_id=MAUA_IBGE_CODE)

    assert maua["id"] == MAUA_IBGE_CODE
    assert maua["nome"] == MAUA_NOME_ESPERADO


def test_fetch_maua_from_uf_list_not_found(requests_mock: rm.Mocker) -> None:
    """Testa erro quando município não consta na lista do estado."""
    url = f"{IBGE_BASE_URL}/estados/35/municipios"
    requests_mock.get(
        url,
        json=[{"id": 1111111, "nome": "Outro"}],
        headers=JSON_HEADERS,
        status_code=200,
    )

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="não encontrado na listagem"):
            client.fetch_maua_from_uf_list(uf_id=35, municipio_id=MAUA_IBGE_CODE)


def test_get_municipio_maua_convenience_function(
    requests_mock: rm.Mocker,
    maua_raw_payload: dict[str, Any],
) -> None:
    """Testa a função de conveniência get_municipio_maua."""
    url = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
    requests_mock.get(
        url,
        json=maua_raw_payload,
        headers=JSON_HEADERS,
        status_code=200,
    )

    data = get_municipio_maua()
    assert data["id"] == MAUA_IBGE_CODE
    assert data["nome"] == MAUA_NOME_ESPERADO


def test_fetch_censo_demografico_basico_success(requests_mock: rm.Mocker) -> None:
    """Testa extração de População, Área e Densidade (Censo 2022)."""
    url = (
        f"{IBGE_AGREGADOS_BASE_URL}/4714/periodos/2022/variaveis/93|6318|614"
        f"?localidades=N6[{MAUA_IBGE_CODE}]"
    )
    mock_payload = [
        {
            "id": "93",
            "variavel": "População residente",
            "unidade": "Pessoas",
            "resultados": [],
        },
        {
            "id": "6318",
            "variavel": "Área da unidade territorial",
            "unidade": "km²",
            "resultados": [],
        },
        {
            "id": "614",
            "variavel": "Densidade demográfica",
            "unidade": "hab/km²",
            "resultados": [],
        },
    ]
    requests_mock.get(url, json=mock_payload, headers=JSON_HEADERS, status_code=200)

    with IBGEClient() as client:
        res = client.fetch_censo_demografico_basico(MAUA_IBGE_CODE)
    assert len(res) == 3
    assert res[0]["id"] == "93"


def test_fetch_populacao_estimada_historica_success(requests_mock: rm.Mocker) -> None:
    """Testa extração da série de População estimada (Agregado 6579)."""
    url = (
        f"{IBGE_AGREGADOS_BASE_URL}/6579/periodos/all/variaveis/9324"
        f"?localidades=N6[{MAUA_IBGE_CODE}]"
    )
    mock_payload = [
        {"id": "9324", "variavel": "População residente estimada", "resultados": []}
    ]
    requests_mock.get(url, json=mock_payload, headers=JSON_HEADERS, status_code=200)

    with IBGEClient() as client:
        res = client.fetch_populacao_estimada_historica(MAUA_IBGE_CODE)
    assert len(res) == 1
    assert res[0]["id"] == "9324"


def test_fetch_pib_historico_success(requests_mock: rm.Mocker) -> None:
    """Testa extração de PIB e PIB per capita (Pesquisa 38)."""
    url = f"{IBGE_PESQUISAS_BASE_URL}/38/resultados/{MAUA_IBGE_CODE}"
    mock_payload = [
        {"id": 46997, "indicador": "PIB a preços correntes", "res": []},
        {"id": 47001, "indicador": "PIB per capita", "res": []},
    ]
    requests_mock.get(url, json=mock_payload, headers=JSON_HEADERS, status_code=200)

    with IBGEClient() as client:
        res = client.fetch_pib_historico(MAUA_IBGE_CODE)
    assert len(res) == 2
    assert res[0]["id"] == 46997


def test_fetch_alfabetizacao_success(requests_mock: rm.Mocker) -> None:
    """Testa extração da Taxa de Alfabetização (Agregado 9543)."""
    url = (
        f"{IBGE_AGREGADOS_BASE_URL}/9543/periodos/2022/variaveis/2513"
        f"?localidades=N6[{MAUA_IBGE_CODE}]"
    )
    mock_payload = [
        {"id": "2513", "variavel": "Taxa de alfabetização", "resultados": []}
    ]
    requests_mock.get(url, json=mock_payload, headers=JSON_HEADERS, status_code=200)

    with IBGEClient() as client:
        res = client.fetch_alfabetizacao(MAUA_IBGE_CODE)
    assert len(res) == 1
    assert res[0]["id"] == "2513"


def test_fetch_populacao_por_sexo_success(requests_mock: rm.Mocker) -> None:
    """Testa extração de População por Sexo (Agregado 9514)."""
    url = (
        f"{IBGE_AGREGADOS_BASE_URL}/9514/periodos/2022/variaveis/93"
        f"?localidades=N6[{MAUA_IBGE_CODE}]&classificacao=2[4,5]|287[100362]"
    )
    mock_payload = [
        {"id": "93", "variavel": "População residente por sexo", "resultados": []}
    ]
    requests_mock.get(url, json=mock_payload, headers=JSON_HEADERS, status_code=200)

    with IBGEClient() as client:
        res = client.fetch_populacao_por_sexo(MAUA_IBGE_CODE)
    assert len(res) == 1


def test_fetch_json_endpoint_invalid_content_type(requests_mock: rm.Mocker) -> None:
    """Testa erro de Content-Type inesperado no endpoint genérico."""
    url = "https://servicodados.ibge.gov.br/api/v3/teste"
    requests_mock.get(
        url,
        text="<html>error</html>",
        headers={"Content-Type": "text/html"},
        status_code=200,
    )

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Content-Type inesperado"):
            client.fetch_json_endpoint(url, "teste")


def test_fetch_json_endpoint_invalid_payload_type(requests_mock: rm.Mocker) -> None:
    """Testa erro quando retorno não é lista nem dict (ex: int primitivo)."""
    url = "https://servicodados.ibge.gov.br/api/v3/teste_primitivo"
    requests_mock.get(url, text="12345", headers=JSON_HEADERS, status_code=200)

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Formato inválido retornado"):
            client.fetch_json_endpoint(url, "teste_primitivo")


def test_fetch_json_endpoint_http_error(requests_mock: rm.Mocker) -> None:
    """Testa captura de erro HTTP 500 no endpoint genérico."""
    url = "https://servicodados.ibge.gov.br/api/v3/erro"
    requests_mock.get(url, status_code=500)

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Erro HTTP ao consultar"):
            client.fetch_json_endpoint(url, "teste_erro")


def test_fetch_json_endpoint_timeout(requests_mock: rm.Mocker) -> None:
    """Testa captura de timeout no endpoint genérico."""
    url = "https://servicodados.ibge.gov.br/api/v3/timeout"
    requests_mock.get(url, exc=requests.exceptions.Timeout("Timeout excedido"))

    with IBGEClient() as client:
        with pytest.raises(IBGEExtractionError, match="Timeout"):
            client.fetch_json_endpoint(url, "teste_timeout")


def test_fetch_all_socioeconomico_maua_success(requests_mock: rm.Mocker) -> None:
    """Testa a extração consolidada de todos os indicadores de Mauá."""
    u1 = (
        f"{IBGE_AGREGADOS_BASE_URL}/4714/periodos/2022/variaveis/93|6318|614"
        f"?localidades=N6[{MAUA_IBGE_CODE}]"
    )
    u2 = (
        f"{IBGE_AGREGADOS_BASE_URL}/6579/periodos/all/variaveis/9324"
        f"?localidades=N6[{MAUA_IBGE_CODE}]"
    )
    u3 = f"{IBGE_PESQUISAS_BASE_URL}/38/resultados/{MAUA_IBGE_CODE}"
    u4 = (
        f"{IBGE_AGREGADOS_BASE_URL}/9543/periodos/2022/variaveis/2513"
        f"?localidades=N6[{MAUA_IBGE_CODE}]"
    )
    u5 = (
        f"{IBGE_AGREGADOS_BASE_URL}/9514/periodos/2022/variaveis/93"
        f"?localidades=N6[{MAUA_IBGE_CODE}]&classificacao=2[4,5]|287[100362]"
    )

    requests_mock.get(u1, json=[{"id": "4714"}], headers=JSON_HEADERS)
    requests_mock.get(u2, json=[{"id": "6579"}], headers=JSON_HEADERS)
    requests_mock.get(u3, json=[{"id": "38"}], headers=JSON_HEADERS)
    requests_mock.get(u4, json=[{"id": "9543"}], headers=JSON_HEADERS)
    requests_mock.get(u5, json=[{"id": "9514"}], headers=JSON_HEADERS)

    result = fetch_all_socioeconomico_maua()
    assert len(result) == 5
    assert "censo_pop_area_densidade" in result
    assert "populacao_estimada_historica" in result
    assert "pib_municipal_historico" in result
    assert "censo_alfabetizacao" in result
    assert "censo_sexo" in result
    assert result["censo_pop_area_densidade"]["municipio_id"] == MAUA_IBGE_CODE
