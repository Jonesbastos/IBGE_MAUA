"""Testes unitários das configurações e constantes do projeto."""

from desafio_ibge.config.settings import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_DB_PATH,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    IBGE_BASE_URL,
    MAUA_IBGE_CODE,
    MAUA_NOME_ESPERADO,
    MAUA_UF_ID_ESPERADO,
    MAUA_UF_SIGLA_ESPERADA,
    PROJECT_ROOT,
    RETRY_STATUS_CODES,
)


def test_settings_constants():
    """Valida se as constantes oficiais de Mauá e do IBGE estão corretas."""
    assert MAUA_IBGE_CODE == 3529401
    assert MAUA_NOME_ESPERADO == "Mauá"
    assert MAUA_UF_SIGLA_ESPERADA == "SP"
    assert MAUA_UF_ID_ESPERADO == 35
    assert "https://servicodados.ibge.gov.br/api/v1/localidades" in IBGE_BASE_URL
    assert PROJECT_ROOT.exists()
    assert DEFAULT_DB_PATH.name == "ibge_maua.db"


def test_network_settings():
    """Valida se as configurações padrão de rede são adequadas."""
    assert DEFAULT_HTTP_TIMEOUT == (3.05, 10.0)
    assert DEFAULT_MAX_RETRIES == 3
    assert DEFAULT_BACKOFF_FACTOR == 0.5
    assert 429 in RETRY_STATUS_CODES
    assert 500 in RETRY_STATUS_CODES
