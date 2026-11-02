"""Cliente HTTP para extração e consumo da API oficial de Localidades do IBGE.

Este módulo implementa sessões resilientes com HTTPAdapter e Retry, timeouts
explícitos, validação de payload e logging estruturado para coleta de dados
municipais do IBGE.
"""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from desafio_ibge.config.settings import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    IBGE_AGREGADOS_BASE_URL,
    IBGE_BASE_URL,
    IBGE_PESQUISAS_BASE_URL,
    MAUA_IBGE_CODE,
    RETRY_STATUS_CODES,
)

logger = logging.getLogger(__name__)


class IBGEExtractionError(Exception):
    """Exceção customizada lançada quando ocorre falha na extração de dados do IBGE."""


class IBGEClient:
    """Cliente HTTP dedicado ao consumo dos endpoints de Localidades do IBGE.

    Gerencia o ciclo de vida da sessão HTTP, implementa estratégias de retry com
    backoff exponencial e garante timeouts estritos para evitar bloqueio do pipeline.
    """

    def __init__(
        self,
        base_url: str = IBGE_BASE_URL,
        timeout: tuple[float, float] = DEFAULT_HTTP_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        """Inicializa o cliente com parâmetros de conexão e tolerância a falhas.

        Args:
            base_url: URL base do serviço de dados do IBGE.
            timeout: Tupla contendo timeout de conexão e de leitura em segundos.
            max_retries: Quantidade máxima de tentativas em caso de erro temporário.
            backoff_factor: Fator de multiplicação para o backoff exponencial.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = self._create_resilient_session(max_retries, backoff_factor)

    @staticmethod
    def _create_resilient_session(
        retries: int,
        backoff_factor: float,
    ) -> requests.Session:
        """Cria e configura uma requests.Session com pool e política de retry.

        Args:
            retries: Número de tentativas para erros temporários de servidor.
            backoff_factor: Fator de backoff exponencial entre retries.

        Returns:
            Sessão configurada com HTTPAdapter montado em http:// e https://.
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=list(RETRY_STATUS_CODES),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def fetch_municipio_by_id(self, municipio_id: int) -> dict[str, Any]:
        """Consulta o endpoint direto de um município a partir de seu código IBGE.

        Endpoint oficial:
        https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{id}

        Args:
            municipio_id: Código numérico de 7 dígitos do município no IBGE.

        Returns:
            Dicionário com o payload JSON desaninhado/hierárquico do município.

        Raises:
            IBGEExtractionError: Se ocorrer erro de conexão, timeout ou dados inválidos.
        """
        url = f"{self.base_url}/municipios/{municipio_id}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "DesafioIBGE-DataPipeline/1.0",
        }

        logger.info(
            "Iniciando requisição ao IBGE para município ID: %s (%s)",
            municipio_id,
            url,
        )

        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                msg = f"Content-Type inesperado recebido da API do IBGE: {content_type}"
                logger.error(msg)
                raise IBGEExtractionError(msg)

            data: Any = response.json()

            if not isinstance(data, dict):
                type_name = type(data).__name__
                msg = (
                    "Formato de resposta inesperado. "
                    f"Esperado dict, recebido {type_name}"
                )
                logger.error(msg)
                raise IBGEExtractionError(msg)

            retrieved_id = data.get("id")
            if retrieved_id != municipio_id:
                msg = (
                    f"Divergência de identificador: solicitado {municipio_id}, "
                    f"retornado {retrieved_id}"
                )
                logger.error(msg)
                raise IBGEExtractionError(msg)

            logger.info(
                "Extração realizada com sucesso: %s (ID %s)",
                data.get("nome"),
                retrieved_id,
            )
            return data

        except requests.exceptions.HTTPError as exc:
            msg = f"Erro HTTP ao consultar município {municipio_id}: {exc}"
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc
        except requests.exceptions.Timeout as exc:
            msg = (
                f"Timeout ({self.timeout}s) ao consultar "
                f"município {municipio_id}: {exc}"
            )
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc
        except (requests.exceptions.JSONDecodeError, ValueError) as exc:
            msg = f"Falha ao decodificar JSON para município {municipio_id}: {exc}"
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc
        except requests.exceptions.RequestException as exc:
            msg = f"Falha de rede ao consultar município {municipio_id}: {exc}"
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc

    def fetch_municipios_by_uf(self, uf_id: int | str = 35) -> list[dict[str, Any]]:
        """Recupera a lista completa de municípios de uma Unidade Federativa.

        Endpoint oficial:
        https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF}/municipios

        Args:
            uf_id: Código numérico (ex: 35) ou sigla (ex: "SP") da UF.

        Returns:
            Lista de dicionários, cada um representando um município da UF.

        Raises:
            IBGEExtractionError: Caso ocorra falha de comunicação ou resposta inválida.
        """
        url = f"{self.base_url}/estados/{uf_id}/municipios"
        headers = {
            "Accept": "application/json",
            "User-Agent": "DesafioIBGE-DataPipeline/1.0",
        }

        logger.info("Consultando municípios do estado UF %s em: %s", uf_id, url)

        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            data: Any = response.json()
            if not isinstance(data, list):
                msg = f"Esperado list de municípios, recebido {type(data).__name__}"
                logger.error(msg)
                raise IBGEExtractionError(msg)

            logger.info(
                "Total de municípios retornados para UF %s: %d",
                uf_id,
                len(data),
            )
            return data

        except (requests.exceptions.RequestException, ValueError) as exc:
            msg = f"Erro ao consultar municípios da UF {uf_id}: {exc}"
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc

    def fetch_maua_from_uf_list(
        self,
        uf_id: int = 35,
        municipio_id: int = MAUA_IBGE_CODE,
    ) -> dict[str, Any]:
        """Extrai os dados de Mauá filtrando a partir da listagem completa da UF.

        Args:
            uf_id: Código da UF (padrão: 35 para São Paulo).
            municipio_id: Código IBGE de Mauá (padrão: 3529401).

        Returns:
            Dicionário com os dados cadastrais e territoriais de Mauá.

        Raises:
            IBGEExtractionError: Caso Mauá não seja localizado na lista retornada.
        """
        municipios = self.fetch_municipios_by_uf(uf_id=uf_id)
        for item in municipios:
            if item.get("id") == municipio_id:
                logger.info(
                    "Município de Mauá identificado com sucesso na listagem da UF %s.",
                    uf_id,
                )
                return item

        msg = f"Município {municipio_id} não encontrado na listagem da UF {uf_id}."
        logger.error(msg)
        raise IBGEExtractionError(msg)

    def fetch_json_endpoint(self, url: str, description: str = "endpoint") -> Any:
        """Executa requisição GET resiliente a um endpoint IBGE e retorna JSON.

        Args:
            url: URL completa do endpoint.
            description: Descrição amigável para fins de log e mensagens de erro.

        Returns:
            Estrutura JSON decodificada (list ou dict).

        Raises:
            IBGEExtractionError: Em caso de falha de conexão, HTTP ou JSON inválido.
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "DesafioIBGE-DataPipeline/1.0",
        }
        logger.info("Iniciando requisição para %s em: %s", description, url)
        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                msg = (
                    f"Content-Type inesperado ao consultar {description}: "
                    f"{content_type}"
                )
                logger.error(msg)
                raise IBGEExtractionError(msg)

            data: Any = response.json()
            if not isinstance(data, (dict, list)):
                msg = (
                    f"Formato inválido retornado para {description}: "
                    f"{type(data).__name__}"
                )
                logger.error(msg)
                raise IBGEExtractionError(msg)

            logger.info("Requisição para %s concluída com sucesso.", description)
            return data

        except requests.exceptions.HTTPError as exc:
            msg = f"Erro HTTP ao consultar {description}: {exc}"
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc
        except requests.exceptions.Timeout as exc:
            msg = f"Timeout ({self.timeout}s) ao consultar {description}: {exc}"
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc
        except (requests.exceptions.JSONDecodeError, ValueError) as exc:
            msg = f"Falha ao decodificar JSON para {description}: {exc}"
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc
        except requests.exceptions.RequestException as exc:
            msg = f"Falha de rede ao consultar {description}: {exc}"
            logger.error(msg)
            raise IBGEExtractionError(msg) from exc

    def fetch_censo_demografico_basico(
        self, municipio_id: int = MAUA_IBGE_CODE
    ) -> list[dict[str, Any]]:
        """Extrai População, Área e Densidade demográfica (Censo 2022).

        Agregado 4714 / Variáveis 93, 6318, 614.
        """
        url = (
            f"{IBGE_AGREGADOS_BASE_URL}/4714/periodos/2022/variaveis/93|6318|614"
            f"?localidades=N6[{municipio_id}]"
        )
        data = self.fetch_json_endpoint(
            url, f"Censo 2022 Pop/Área/Densidade ({municipio_id})"
        )
        if not isinstance(data, list):
            raise IBGEExtractionError(
                f"Esperado list no Censo 2022, recebido {type(data).__name__}"
            )
        return data

    def fetch_populacao_estimada_historica(
        self, municipio_id: int = MAUA_IBGE_CODE
    ) -> list[dict[str, Any]]:
        """Extrai a série temporal de População residente estimada (2001-2026).

        Agregado 6579 / Variável 9324.
        """
        url = (
            f"{IBGE_AGREGADOS_BASE_URL}/6579/periodos/all/variaveis/9324"
            f"?localidades=N6[{municipio_id}]"
        )
        data = self.fetch_json_endpoint(
            url, f"Estimativas População 2001-2026 ({municipio_id})"
        )
        if not isinstance(data, list):
            type_name = type(data).__name__
            raise IBGEExtractionError(
                f"Esperado list nas estimativas de população, recebido {type_name}"
            )
        return data

    def fetch_pib_historico(
        self, municipio_id: int = MAUA_IBGE_CODE
    ) -> list[dict[str, Any]]:
        """Extrai histórico de PIB e PIB per capita a preços correntes (2002-2023).

        Pesquisa 38 (PIB dos Municípios).
        """
        url = f"{IBGE_PESQUISAS_BASE_URL}/38/resultados/{municipio_id}"
        data = self.fetch_json_endpoint(
            url, f"PIB Municipal e per capita ({municipio_id})"
        )
        if not isinstance(data, list):
            raise IBGEExtractionError(
                f"Esperado list no PIB dos municípios, recebido {type(data).__name__}"
            )
        return data

    def fetch_alfabetizacao(
        self, municipio_id: int = MAUA_IBGE_CODE
    ) -> list[dict[str, Any]]:
        """Extrai a Taxa de Alfabetização de pessoas de 15 anos ou mais (Censo 2022).

        Agregado 9543 / Variável 2513.
        """
        url = (
            f"{IBGE_AGREGADOS_BASE_URL}/9543/periodos/2022/variaveis/2513"
            f"?localidades=N6[{municipio_id}]"
        )
        data = self.fetch_json_endpoint(
            url, f"Taxa de Alfabetização Censo 2022 ({municipio_id})"
        )
        if not isinstance(data, list):
            type_name = type(data).__name__
            raise IBGEExtractionError(
                f"Esperado list na Taxa de Alfabetização, recebido {type_name}"
            )
        return data

    def fetch_populacao_por_sexo(
        self, municipio_id: int = MAUA_IBGE_CODE
    ) -> list[dict[str, Any]]:
        """Extrai a População residente por sexo (Censo 2022).

        Agregado 9514 / Variável 93 / Classificação 2 (Categorias 4 e 5).
        """
        url = (
            f"{IBGE_AGREGADOS_BASE_URL}/9514/periodos/2022/variaveis/93"
            f"?localidades=N6[{municipio_id}]&classificacao=2[4,5]|287[100362]"
        )
        data = self.fetch_json_endpoint(
            url, f"População por Sexo Censo 2022 ({municipio_id})"
        )
        if not isinstance(data, list):
            raise IBGEExtractionError(
                f"Esperado list na População por Sexo, recebido {type(data).__name__}"
            )
        return data

    def fetch_all_socioeconomico_maua(
        self, municipio_id: int = MAUA_IBGE_CODE
    ) -> dict[str, dict[str, Any]]:
        """Extrai todos os indicadores socioeconômicos homologados de Mauá.

        Args:
            municipio_id: Código IBGE do município (padrão: MAUA_IBGE_CODE).

        Returns:
            Dicionário com os indicadores socioeconômicos e metadados.
        """
        return fetch_all_socioeconomico_maua(client=self, municipio_id=municipio_id)

    def close(self) -> None:
        """Fecha a sessão HTTP subjacente liberando recursos de conexão."""
        self.session.close()

    def __enter__(self) -> "IBGEClient":
        """Suporte a context manager (with IBGEClient() as client)."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Fecha a sessão ao sair do bloco with."""
        self.close()


def get_municipio_maua() -> dict[str, Any]:
    """Função utilitária de conveniência para extração direta dos dados de Mauá (SP).

    Returns:
        Dicionário com o payload oficial de Mauá (ID 3529401).
    """
    with IBGEClient() as client:
        return client.fetch_municipio_by_id(MAUA_IBGE_CODE)


def fetch_all_socioeconomico_maua(
    client: IBGEClient | None = None,
    municipio_id: int = MAUA_IBGE_CODE,
) -> dict[str, dict[str, Any]]:
    """Extrai todos os indicadores socioeconômicos homologados de Mauá (SP).

    Retorna um dicionário indexado pelos nomes canônicos dos indicadores,
    contendo os payloads brutos e os metadados de auditoria.

    Args:
        client: Instância opcional de IBGEClient.
        municipio_id: Código IBGE do município (padrão: 3529401).

    Returns:
        Dict mapeando o nome do indicador ao seu payload bruto e metadados.
    """
    should_close = False
    if client is None:
        client = IBGEClient()
        should_close = True

    try:
        censo_basico_url = (
            f"{IBGE_AGREGADOS_BASE_URL}/4714/periodos/2022/variaveis/93|6318|614"
            f"?localidades=N6[{municipio_id}]"
        )
        pop_estimada_url = (
            f"{IBGE_AGREGADOS_BASE_URL}/6579/periodos/all/variaveis/9324"
            f"?localidades=N6[{municipio_id}]"
        )
        pib_url = f"{IBGE_PESQUISAS_BASE_URL}/38/resultados/{municipio_id}"
        alfabetizacao_url = (
            f"{IBGE_AGREGADOS_BASE_URL}/9543/periodos/2022/variaveis/2513"
            f"?localidades=N6[{municipio_id}]"
        )
        sexo_url = (
            f"{IBGE_AGREGADOS_BASE_URL}/9514/periodos/2022/variaveis/93"
            f"?localidades=N6[{municipio_id}]&classificacao=2[4,5]|287[100362]"
        )

        return {
            "censo_pop_area_densidade": {
                "municipio_id": municipio_id,
                "indicador": "censo_pop_area_densidade",
                "periodo_referencia": "2022",
                "fonte_oficial": "Censo Demográfico 2022 (Agregado 4714)",
                "endpoint_url": censo_basico_url,
                "payload": client.fetch_censo_demografico_basico(municipio_id),
            },
            "populacao_estimada_historica": {
                "municipio_id": municipio_id,
                "indicador": "populacao_estimada_historica",
                "periodo_referencia": "2001-2026",
                "fonte_oficial": "Estimativas de População (Agregado 6579)",
                "endpoint_url": pop_estimada_url,
                "payload": client.fetch_populacao_estimada_historica(municipio_id),
            },
            "pib_municipal_historico": {
                "municipio_id": municipio_id,
                "indicador": "pib_municipal_historico",
                "periodo_referencia": "2002-2023",
                "fonte_oficial": "Produto Interno Bruto dos Municípios (Pesquisa 38)",
                "endpoint_url": pib_url,
                "payload": client.fetch_pib_historico(municipio_id),
            },
            "censo_alfabetizacao": {
                "municipio_id": municipio_id,
                "indicador": "censo_alfabetizacao",
                "periodo_referencia": "2022",
                "fonte_oficial": "Censo Demográfico 2022 (Agregado 9543)",
                "endpoint_url": alfabetizacao_url,
                "payload": client.fetch_alfabetizacao(municipio_id),
            },
            "censo_sexo": {
                "municipio_id": municipio_id,
                "indicador": "censo_sexo",
                "periodo_referencia": "2022",
                "fonte_oficial": "Censo Demográfico 2022 (Agregado 9514)",
                "endpoint_url": sexo_url,
                "payload": client.fetch_populacao_por_sexo(municipio_id),
            },
        }
    finally:
        if should_close:
            client.close()
