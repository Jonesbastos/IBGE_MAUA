"""Testes unitários para o módulo de extração da API do IBGE."""

from typing import Any

import pytest
import requests
import requests_mock as rm

from desafio_ibge.config.settings import (
    IBGE_BASE_URL,
    MAUA_IBGE_CODE,
    MAUA_NOME_ESPERADO,
)
from desafio_ibge.extraction.ibge_client import (
    IBGEClient,
    IBGEExtractionError,
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
