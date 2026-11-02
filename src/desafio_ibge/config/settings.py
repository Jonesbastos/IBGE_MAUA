"""Módulo de configurações e constantes do projeto desafio_ibge."""

import os
from pathlib import Path

# Raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Diretório de dados local e banco padrão (configurável via variável de ambiente)
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = Path(os.environ.get("IBGE_DB_PATH", str(DATA_DIR / "ibge_maua.db")))

# Snapshot SQL versionado para deploy e portabilidade (somente leitura)
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
DEFAULT_SNAPSHOT_PATH = Path(
    os.environ.get("IBGE_SNAPSHOT_PATH", str(SNAPSHOTS_DIR / "ibge_maua_snapshot.sql"))
)

# Parâmetros oficiais do IBGE para Mauá (SP)
# Conforme especificado em docs/doc_api.md
IBGE_BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
IBGE_ESTADOS_SP_URL = f"{IBGE_BASE_URL}/estados/35/municipios"
MAUA_IBGE_CODE = 3529401
MAUA_DIRECT_URL = f"{IBGE_BASE_URL}/municipios/{MAUA_IBGE_CODE}"
MAUA_NOME_ESPERADO = "Mauá"
MAUA_UF_SIGLA_ESPERADA = "SP"
MAUA_UF_ID_ESPERADO = 35

# URLs de Agregados e Pesquisas do IBGE (Socioeconômico — FASE 10)
IBGE_AGREGADOS_BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"
IBGE_PESQUISAS_BASE_URL = "https://servicodados.ibge.gov.br/api/v1/pesquisas"

# Endpoints oficiais homologados para Mauá (SP)
MAUA_CENSO_2022_URL = (
    f"{IBGE_AGREGADOS_BASE_URL}/4714/periodos/2022/variaveis/93|6318|614"
    f"?localidades=N6[{MAUA_IBGE_CODE}]"
)
MAUA_POPULACAO_ESTIMADA_URL = (
    f"{IBGE_AGREGADOS_BASE_URL}/6579/periodos/all/variaveis/9324"
    f"?localidades=N6[{MAUA_IBGE_CODE}]"
)
MAUA_PIB_URL = f"{IBGE_PESQUISAS_BASE_URL}/38/resultados/{MAUA_IBGE_CODE}"
MAUA_ALFABETIZACAO_URL = (
    f"{IBGE_AGREGADOS_BASE_URL}/9543/periodos/2022/variaveis/2513"
    f"?localidades=N6[{MAUA_IBGE_CODE}]"
)
MAUA_POPULACAO_SEXO_URL = (
    f"{IBGE_AGREGADOS_BASE_URL}/9514/periodos/2022/variaveis/93"
    f"?localidades=N6[{MAUA_IBGE_CODE}]&classificacao=2[4,5]|287[100362]"
)

# Configurações de rede
DEFAULT_HTTP_TIMEOUT = (3.05, 10.0)
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
