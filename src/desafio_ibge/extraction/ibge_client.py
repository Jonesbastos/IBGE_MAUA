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
    IBGE_BASE_URL,
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
