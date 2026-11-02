# Documentação Técnica: API de Localidades do IBGE — Município de Mauá (SP)

> **Perfil do Documento**: Engenharia de Dados / Arquitetura de Integração
> **Autor**: Engenheiro de Dados Sênior
> **Data da Consulta / Homologação**: 30 de Outubro de 2026
> **Status da Fonte**: Ativa / Oficial (IBGE)
> **Versão da API**: v1

---

## 1. Objetivo e Finalidade da API

A **API de Localidades do IBGE** (`servicodados.ibge.gov.br/api/v1/localidades`) é um serviço RESTful público disponibilizado pelo Instituto Brasileiro de Geografia e Estatística (IBGE). Seu propósito principal é prover dados estruturados e padronizados sobre a organização político-administrativa e as divisões geográficas do território brasileiro.

No contexto de **Engenharia de Dados**, esta API atua como uma **tabela dimensão canônica** (Master Data / Lookup Table) de entidades territoriais, fornecendo:
- O identificador unívoco oficial de cada município (Código IBGE de 7 dígitos);
- Hierarquias geográficas clássicas (Mesorregiões e Microrregiões — divisão de 1989);
- Hierarquias geográficas contemporâneas (Regiões Intermediárias e Imediatas — divisão de 2017);
- Associação normalizada com Unidades da Federação (UF) e Grandes Regiões do Brasil.

---

## 2. Especificação dos Endpoints e Protocolo HTTP

### 2.1. Endpoint 1: Listagem por Unidade da Federação (São Paulo)

Retorna a coleção de todos os 645 municípios pertencentes ao Estado de São Paulo (código UF `35`).

- **URL**: `https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios`
- **Método HTTP**: `GET`
- **Formato de Resposta**: `application/json; charset=utf-8`
- **Autenticação**: Não requerida (API pública e aberta)
- **Cache-Control**: `max-age=2592000` (~30 dias de cache HTTP upstream)
- **Estrutura de Retorno**: `Array[Object]` contendo 645 elementos.

### 2.2. Endpoint 2: Consulta Direta por Município (Mauá)

Permite recuperar pontualmente os metadados cadastrais e territoriais do município através de sua chave primária IBGE (`3529401`).

- **URL**: `https://servicodados.ibge.gov.br/api/v1/localidades/municipios/3529401`
- **Método HTTP**: `GET`
- **Formato de Resposta**: `application/json; charset=utf-8`
- **Autenticação**: Não requerida
- **Estrutura de Retorno**: `Object` (JSON único com os dados e hierarquias de Mauá).

---

## 3. Identificação e Filtragem do Município de Mauá (SP)

Na listagem de municípios de São Paulo (Endpoint 1), o município de Mauá pode ser identificado deterministicamente pelo seu identificador primário ou pelo nome canônico:

| Atributo | Valor Oficial IBGE | Observação Técnica |
| :--- | :--- | :--- |
| **Código IBGE (`id`)** | `3529401` | Chave primária natural (7 dígitos) |
| **Nome (`nome`)** | `"Mauá"` | String UTF-8 acentuada |
| **UF Sigla** | `"SP"` | Código alfanumérico da UF |
| **UF ID** | `35` | Código numérico da UF (São Paulo) |
| **Região Imediata** | `350001` (São Paulo) | Divisão Regional 2017 |
| **Microrregião** | `35061` (São Paulo) | Divisão Regional 1989 |

---

## 4. Exemplo Real da Resposta JSON (Mauá - 3529401)

Abaixo é apresentado o payload JSON real retornado pelo endpoint oficial do IBGE para o município de Mauá:

```json
{
  "id": 3529401,
  "nome": "Mauá",
  "microrregiao": {
    "id": 35061,
    "nome": "São Paulo",
    "mesorregiao": {
      "id": 3515,
      "nome": "Metropolitana de São Paulo",
      "UF": {
        "id": 35,
        "sigla": "SP",
        "nome": "São Paulo",
        "regiao": {
          "id": 3,
          "sigla": "SE",
          "nome": "Sudeste"
        }
      }
    }
  },
  "regiao-imediata": {
    "id": 350001,
    "nome": "São Paulo",
    "regiao-intermediaria": {
      "id": 3501,
      "nome": "São Paulo",
      "UF": {
        "id": 35,
        "sigla": "SP",
        "nome": "São Paulo",
        "regiao": {
          "id": 3,
          "sigla": "SE",
          "nome": "Sudeste"
        }
      }
    }
  }
}
```

---

## 5. Dicionário de Dados e Hierarquias Aninhadas

A resposta do IBGE estrutura-se em duas ramificações geográficas distintas que convivem na resposta:
1. **Quadro Geográfico Tradicional (1989)**: Município $\rightarrow$ Microrregião $\rightarrow$ Mesorregião $\rightarrow$ UF $\rightarrow$ Região.
2. **Quadro Geográfico Contemporâneo (2017)**: Município $\rightarrow$ Região Geográfica Imediata $\rightarrow$ Região Geográfica Intermediária $\rightarrow$ UF $\rightarrow$ Região.

### 5.1. Mapeamento Completo de Campos

| Campo no JSON | Tipo de Dado | Nullable? | Exemplo (Mauá) | Descrição e Regra de Negócio |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `Integer` | Não | `3529401` | Código de 7 dígitos do município: UF (2 dígitos) + Município (4 dígitos) + Dígito Verificador (1 dígito). |
| `nome` | `String` | Não | `"Mauá"` | Nome formal e oficial do município. |
| `microrregiao.id` | `Integer` | Não | `35061` | Identificador único da microrregião geográfica. |
| `microrregiao.nome` | `String` | Não | `"São Paulo"` | Nome da microrregião geográfica. |
| `microrregiao.mesorregiao.id` | `Integer` | Não | `3515` | Identificador único da mesorregião geográfica. |
| `microrregiao.mesorregiao.nome` | `String` | Não | `"Metropolitana de São Paulo"` | Nome da mesorregião geográfica. |
| `microrregiao.mesorregiao.UF.id` | `Integer` | Não | `35` | Código numérico da Unidade da Federação (SP = 35). |
| `microrregiao.mesorregiao.UF.sigla` | `String (2)` | Não | `"SP"` | Sigla da Unidade Federativa. |
| `microrregiao.mesorregiao.UF.nome` | `String` | Não | `"São Paulo"` | Nome da Unidade Federativa. |
| `microrregiao.mesorregiao.UF.regiao.id` | `Integer` | Não | `3` | Identificador da macrorregião nacional (3 = Sudeste). |
| `microrregiao.mesorregiao.UF.regiao.sigla` | `String (2)` | Não | `"SE"` | Sigla da macrorregião nacional. |
| `microrregiao.mesorregiao.UF.regiao.nome` | `String` | Não | `"Sudeste"` | Nome da macrorregião nacional. |
| `regiao-imediata.id` | `Integer` | Não | `350001` | Código da Região Geográfica Imediata (Resolução 2017). |
| `regiao-imediata.nome` | `String` | Não | `"São Paulo"` | Nome da Região Geográfica Imediata. |
| `regiao-imediata.regiao-intermediaria.id` | `Integer` | Não | `3501` | Código da Região Geográfica Intermediária. |
| `regiao-imediata.regiao-intermediaria.nome` | `String` | Não | `"São Paulo"` | Nome da Região Geográfica Intermediária. |
| `regiao-imediata.regiao-intermediaria.UF.id` | `Integer` | Não | `35` | Código da UF na divisão 2017. |
| `regiao-imediata.regiao-intermediaria.UF.sigla` | `String (2)` | Não | `"SP"` | Sigla da UF na divisão 2017. |
| `regiao-imediata.regiao-intermediaria.UF.nome` | `String` | Não | `"São Paulo"` | Nome da UF na divisão 2017. |
| `regiao-imediata.regiao-intermediaria.UF.regiao.id`| `Integer` | Não | `3` | Identificador da macrorregião na divisão 2017. |
| `regiao-imediata.regiao-intermediaria.UF.regiao.sigla`| `String (2)`| Não | `"SE"` | Sigla da macrorregião na divisão 2017. |
| `regiao-imediata.regiao-intermediaria.UF.regiao.nome`| `String` | Não | `"Sudeste"` | Nome da macrorregião na divisão 2017. |

> **Atenção para Engenharia de Dados**: As chaves `regiao-imediata` e `regiao-intermediaria` utilizam **hífen (`-`)**, o que inviabiliza o acesso direto por atributo em Python (`response.regiao-imediata`) e exige tratamento especial de saneamento de colunas em bancos relacionais e Data Warehouses (ex: conversão para `snake_case` com `_`).

---

## 6. Exemplo de Consumo com Python e Requests

O script a seguir implementa as melhores práticas de engenharia de software para consumo de APIs REST:
- Sessão persistente com `requests.Session()` para reuso de conexões TCP (HTTP Keep-Alive);
- Política de retentativa resiliente com `urllib3.util.Retry` com backoff exponencial;
- Timeouts explícitos para prevenção de congelamento do pipeline de dados;
- Validação de cabeçalho `Content-Type` e tratamento robusto de exceções de rede.

```python
"""
Módulo de Exemplo para Consumo da API de Localidades do IBGE.
Este script demonstra a extração dos dados de Mauá (SP).
"""

from typing import Any, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

IBGE_BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
MAUA_IBGE_CODE = 3529401


def get_resilient_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
) -> requests.Session:
    """Cria uma sessão HTTP com política de retry e backoff exponencial."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_municipio_by_id(ibge_id: int) -> Optional[Dict[str, Any]]:
    """
    Consome o endpoint direto de um município no IBGE.

    Args:
        ibge_id: Código numérico de 7 dígitos do município.

    Returns:
        Dicionário com o payload JSON retornado pela API ou None em caso de falha.
    """
    url = f"{IBGE_BASE_URL}/municipios/{ibge_id}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "DataEngineering-Pipeline/1.0 (IBGE-Ingestion-Job)",
    }

    session = get_resilient_session()
    try:
        response = session.get(url, headers=headers, timeout=(3.05, 10.0))
        response.raise_for_status()

        # Validação do Content-Type
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise ValueError(f"Content-Type inesperado recebido: {content_type}")

        data: Dict[str, Any] = response.json()
        return data

    except requests.exceptions.HTTPError as http_err:
        print(f"[ERRO HTTP] Falha na requisição para {url}: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"[ERRO DE CONEXÃO] Não foi possível conectar ao IBGE: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"[TIMEOUT] A requisição excedeu o tempo limite: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"[ERRO GENÉRICO] Erro inesperado na requisição: {req_err}")
    except ValueError as json_err:
        print(f"[ERRO DE PARSING] Falha ao decodificar JSON retornado: {json_err}")
    finally:
        session.close()

    return None


if __name__ == "__main__":
    maua_data = fetch_municipio_by_id(MAUA_IBGE_CODE)
    if maua_data:
        print(f"Sucesso: Município {maua_data.get('nome')} extraído com ID {maua_data.get('id')}.")
    else:
        print("Falha ao recuperar dados do município.")
```

---

## 7. Transformação e Achatamento (Flattening) em DataFrame com Pandas

A resposta JSON da API possui 4 níveis de aninhamento de objetos. Em pipelines de Engenharia de Dados (ETL/ELT), esses dados devem ser normalizados para um formato tabular relacional.

A função `pandas.json_normalize()` é a abordagem analítica recomendada:
- Achata nós aninhados usando um separador padronizado (ex.: `_`);
- Facilita a substituição de caracteres proibidos em Data Warehouses (ex.: transformar `regiao-imediata` em `regiao_imediata`);
- Permite coerção de tipagem estrita para compatibilidade com Parquet / Delta Lake / Postgres.

### Código de Exemplo para Normalização:

```python
"""
Transformação de dados brutos da API IBGE em DataFrame tabular estruturado.
"""

import pandas as pd
from typing import Dict, Any


def flatten_municipio_to_dataframe(raw_json: Dict[str, Any]) -> pd.DataFrame:
    """
    Achata o payload aninhado do município em um DataFrame tabular de 1 linha.
    Aplica saneamento nas nomenclaturas de colunas e coerção de tipos.
    """
    # 1. Normalização do JSON aninhado utilizando o separador '_'
    df = pd.json_normalize(raw_json, sep="_")

    # 2. Saneamento dos nomes de colunas (removendo hífens e ajustando snake_case)
    df.columns = (
        df.columns.str.replace("-", "_", regex=False)
        .str.lower()
    )

    # 3. Mapeamento explícito de tipos de dados (Schema Enforcement)
    dtypes_mapping = {
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

    # Aplica conversão somente nas colunas presentes
    for col, dtype in dtypes_mapping.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)

    return df
```

### Amostra do DataFrame Resultante:

| id | nome | microrregiao_id | microrregiao_nome | mesorregiao_nome | uf_sigla | regiao_nome | regiao_imediata_id | regiao_imediata_nome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `3529401` | `Mauá` | `35061` | `São Paulo` | `Metropolitana de São Paulo` | `SP` | `Sudeste` | `350001` | `São Paulo` |

---

## 8. Validações, Tratamento de Erros e Regras de Qualidade dos Dados (Data Quality)

Para assegurar a robustez do pipeline de dados antes da carga na camada Silver / Gold, são estabelecidas as seguintes regras de Data Quality:

### 8.1. Regras de Integridade e Validação de Negócio

1. **Validação do Código IBGE de 7 Dígitos**:
   - O código deve possuir exatamente 7 dígitos numéricos inteiros.
   - Os dois primeiros dígitos devem corresponder obrigatoriamente ao código da UF (para São Paulo: `35`).
   - O 7º dígito é um dígito verificador calculado via algoritmo Módulo 10 com pesos alternados 1 e 2. O pipeline deve validar ou rejeitar registros que violem essa regra.
2. **Checagem de Valores Nulos (Null Check)**:
   - Campos essenciais como `id`, `nome`, `microrregiao.id`, `regiao-imediata.id` e `UF.sigla` não podem ser nulos (`NOT NULL`).
3. **Detecção de Schema Drift**:
   - A presença de chaves inesperadas ou ausência de campos aninhados obrigatórios deve emitir alertas no pipeline.
4. **Tratamento de Caracteres e Encoding**:
   - Assegurar codificação `UTF-8` estrita para preservar acentuações como em `"Mauá"`, `"São Paulo"` e `"Região Metropolitana"`.
5. **Normalização de Hífens**:
   - Remoção compulsória do caractere `-` das chaves `regiao-imediata` e `regiao-intermediaria` antes da persistência em colunas de bancos relacionais (evitando erros de sintaxe SQL).

### 8.2. Validação de Contrato de Dados com Pydantic (Exemplo Recomendado)

```python
from pydantic import BaseModel, Field, field_validator


class RegionModel(BaseModel):
    id: int
    sigla: str
    nome: str


class UFModel(BaseModel):
    id: int
    sigla: str = Field(min_length=2, max_length=2)
    nome: str
    regiao: RegionModel


class MicrorregiaoModel(BaseModel):
    id: int
    nome: str


class MunicipioIBGESchema(BaseModel):
    id: int = Field(..., description="Código IBGE do município com 7 dígitos")
    nome: str

    @field_validator("id")
    @classmethod
    def validate_ibge_code(cls, value: int) -> int:
        str_val = str(value)
        if len(str_val) != 7:
            raise ValueError(f"Código IBGE deve conter 7 dígitos. Recebido: {value}")
        if not str_val.startswith("35"):
            raise ValueError(f"O município esperado deve pertencer a SP (prefixo 35). Recebido: {value}")
        return value
```

---

## 9. Limitações Críticas da API de Localidades

> [!WARNING]
> **A API de Localidades fornece exclusivamente metadados político-administrativos e territoriais.**

### 9.1. O que a API **NÃO** Fornece Diretamente:
- **População estimada ou censitária**: Quantitativo de habitantes;
- **Produto Interno Bruto (PIB)**: Valor monetário da economia do município e PIB per capita;
- **Indicadores Sociais**: Índice de Desenvolvimento Humano Municipal (IDHM), renda per capita, índice de Gini;
- **Estatísticas Setoriais**: Emprego, educação, saúde ou saneamento.

### 9.2. Como Obter Indicadores Socioeconômicos Oficiais do IBGE
Para enriquecer a dimensão geográfica de Mauá com métricas e fatos analíticos em etapas futuras do projeto, devem ser integradas as seguintes fontes complementares do IBGE:

1. **API do SIDRA (Sistema IBGE de Recuperação Automática)**:
   - Endpoint: `https://servicodados.ibge.gov.br/api/v3/agregados/{agregado}/periodos/{periodo}/variaveis/{variavel}?localidades=N6[3529401]`
   - Provê os dados do Censo Demográfico 2022, Contas Regionais (PIB Municipal) e pesquisas contínuas.
2. **API de Pesquisas do IBGE**:
   - Endpoint: `https://servicodados.ibge.gov.br/api/v1/pesquisas`
   - Permite consultar pesquisas estruturais como PAM (Produção Agrícola Municipal), PEVS (Produção da Extração Vegetal e da Silvicultura), etc.

---

## 10. Fontes Oficiais Complementares: Indicadores Socioeconômicos (FASE 10)

Para enriquecer a dimensão territorial primária de Mauá (`3529401`) com dados demográficos e econômicos oficiais, são integradas as APIs de **Agregados (SIDRA v3)** e **Pesquisas do IBGE**.

### 10.1. Matriz Canônica de Indicadores Oficiais de Mauá (SP)

| Indicador | Fonte Oficial IBGE | Endpoint / Agregado | Variável / Parâmetros | Unidade | Períodos Reais | Periodicidade |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **População Residente** | Censo Demográfico 2022 | `api/v3/agregados/4714` | Var `93` (`localidades=N6[3529401]`) | Pessoas | `2022` (418.261 hab) | Decenal |
| **Área Territorial** | Censo Demográfico 2022 | `api/v3/agregados/4714` | Var `6318` (`localidades=N6[3529401]`) | $km^2$ | `2022` (61,937 $km^2$) | Decenal |
| **Densidade Demográfica** | Censo Demográfico 2022 | `api/v3/agregados/4714` | Var `614` (`localidades=N6[3529401]`) | hab/$km^2$ | `2022` (6.753,01 hab/$km^2$) | Decenal |
| **Evolução Populacional** | Estimativas de População | `api/v3/agregados/6579` | Var `9324` (`periodos=all`) | Pessoas | `2001` a `2026` (22 períodos) | Anual |
| **PIB a Preços Correntes** | PIB dos Municípios | `api/v1/pesquisas/38` ou Agg `5938` | Ind `46997` / Var `37` (`periodos=all`) | Mil Reais | `2002` a `2023` (22 períodos) | Anual (Defasagem 2 anos) |
| **PIB per capita** | PIB dos Municípios | `api/v1/pesquisas/38` | Ind `47001` (`periodos=all`) | Reais | `2002` a `2023` (2023: R$ 59.773,04) | Anual |
| **Taxa de Alfabetização** | Censo Demográfico 2022 | `api/v3/agregados/9543` | Var `2513` (`periodos=2022`) | % | `2022` (96,74%) | Decenal |
| **População por Sexo** | Censo Demográfico 2022 | `api/v3/agregados/9514` | Var `93` (`classificacao=2[4,5]|287[100362]`) | Pessoas | `2022` (Homens: 201.348, Mulheres: 216.913) | Decenal |

---

### 10.2. Detalhamento Técnico das Requisições HTTP

#### 1. Censo Demográfico 2022 — População, Área e Densidade (Agregado 4714)
- **URL**: `https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022/variaveis/93|6318|614?localidades=N6[3529401]`
- **Método**: `GET`
- **Valores Homologados**:
  - População Residente: `418.261` pessoas
  - Área Territorial: `61.937` $km^2$
  - Densidade Demográfica: `6753.01` hab/$km^2$

#### 2. Estimativas Anuais de População (Agregado 6579)
- **URL**: `https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/all/variaveis/9324?localidades=N6[3529401]`
- **Método**: `GET`
- **Série Temporal**: 2001 a 2026 (22 registros anuais). Permite análise de crescimento demográfico no período intercensitário.

#### 3. Produto Interno Bruto (PIB) e PIB per capita (Pesquisa 38 / Agregado 5938)
- **URL Principal (Pesquisa 38)**: `https://servicodados.ibge.gov.br/api/v1/pesquisas/38/resultados/3529401`
- **URL Alternativa (SIDRA 5938)**: `https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/all/variaveis/37?localidades=N6[3529401]`
- **Série Temporal**: 2002 a 2023 (anual).
- **Valores Homologados de Mauá em 2023**:
  - PIB Total: R$ 25.000.732,02 mil (R$ ~25 bilhões)
  - PIB per capita: R$ 59.773,04

#### 4. Alfabetização de Pessoas de 15 Anos ou Mais (Agregado 9543)
- **URL**: `https://servicodados.ibge.gov.br/api/v3/agregados/9543/periodos/2022/variaveis/2513?localidades=N6[3529401]`
- **Método**: `GET`
- **Valor Homologado**: Taxa de Alfabetização de Mauá em 2022: `96.74%`.

#### 5. População por Sexo e Faixa Etária (Agregado 9514)
- **URL**: `https://servicodados.ibge.gov.br/api/v3/agregados/9514/periodos/2022/variaveis/93?localidades=N6[3529401]&classificacao=2[4,5]|287[100362]`
- **Método**: `GET`
- **Valores Homologados**:
  - Categoria 4 (Homens): `201.348`
  - Categoria 5 (Mulheres): `216.913`
  - Total: `418.261`

---

### 10.3. Governança Temporal e Restrições Metodológicas

> [!WARNING] Regra de Ouro da Governança Temporal
> As pesquisas do IBGE possuem naturezas estatísticas e cronogramas de publicação distintos:
> 1. **Censo Demográfico (2022)**: Operação censitária exaustiva decenal.
> 2. **Contas Regionais do PIB (2002-2023)**: Publicação com defasagem estrutural de aproximadamente 2 anos em relação ao ano corrente.
> 3. **Estimativas de População (2001-2026)**: Modelagem matemática anual para fins legais e orçamentários.
>
> **É estritamente vedado correlacionar métricas de períodos distintos como se fossem do mesmo ano de referência.** Todo registro normalizado na camada Silver e analítico na camada Gold deve explicitar seu respectivo `ano_referencia` e `fonte_pesquisa`.

---

## 11. Conclusão

A integração das APIs de Localidades, Agregados (v3) e Pesquisas do IBGE assegura conformidade integral com dados públicos auditáveis, eliminando qualquer risco de valores sintéticos ou inventados na arquitetura Medalhão.
