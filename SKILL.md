---
name: desafio-ibge
description: Diretrizes, padrões de arquitetura, qualidade de código e boas práticas obrigatórias para desenvolvimento com IA no projeto desafio_IBGE.
---

# SKILL.md — Diretrizes e Padrões Obrigatórios de Engenharia de Dados

> **Projeto**: `desafio_IBGE`
> **Status**: Ativo / Mandatório
> **Público-alvo**: Agentes de IA, Desenvolvedores e Engenheiros de Dados
> **Escopo**: Padronização arquitetural, qualidade de código, testes, governança e boas práticas operacionais.

---

## 1. Contexto do Projeto

O **`desafio_IBGE`** é uma solução de Engenharia de Dados desenvolvida em Python para ingestão, transformação, validação, enriquecimento e visualização de dados territoriais e socioeconômicos públicos oficiais do **IBGE**.

### 1.1. Metadados e Definições Centrais
- **Nome do Projeto**: `desafio_IBGE`
- **Origem / Inicialização**: Estrutura inicial via `poetry new desafio_IBGE`
- **Pacote Python Principal**: `desafio_ibge`
- **Localização dos Fontes**: `src/desafio_ibge/`
- **Fonte de Dados Primária**: API Oficial de Serviços de Dados do IBGE
- **Município de Referência**: **Mauá, São Paulo**
- **Código IBGE de Mauá**: `3529401`
- **Documentação Técnica Canônica**: [`docs/doc_api.md`](file:///c:/Users/Jones/projeto/desafio_IBGE/docs/doc_api.md)

> [!IMPORTANT]
> **Consulta Obrigatória à Documentação da API**:
> A IA ou desenvolvedor **DEVE OBRIGATORIAMENTE** consultar o arquivo [`docs/doc_api.md`](file:///c:/Users/Jones/projeto/desafio_IBGE/docs/doc_api.md) antes de propor, implementar ou modificar qualquer funcionalidade relacionada ao consumo de dados da API do IBGE. Nunca deduza ou invente campos, chaves ou comportamentos que divirjam do contrato documentado.

---

## 2. Gerenciamento de Ambiente e Dependências

A integridade do ambiente Python é um pilar inegociável da engenharia de software do projeto.

### 2.1. Regras de Ouro
1. **Pyenv**: Utilizado para gerenciar e fixar a versão local de runtime do Python (conforme definido em `pyproject.toml`, `>=3.13`).
2. **Poetry Exclusivo**: O Poetry é a **única** ferramenta autorizada para gerenciamento de ambientes virtuais e dependências.
3. **Proibição Absoluta do `pip`**: **NUNCA** execute `pip install` diretamente no ambiente do projeto. Todas as dependências devem ser registradas nos metadados do Poetry.
4. **Instalação de Pacotes de Produção**:
   ```bash
   poetry add <nome-do-pacote>
   ```
5. **Instalação de Pacotes de Desenvolvimento / Testes**:
   ```bash
   poetry add --group dev <nome-do-pacote>
   ```
6. **Execução de Ferramentas**: Todo comando Python, linter ou utilitário deve ser executado no contexto do ambiente virtual:
   ```bash
   poetry run <comando>
   ```
7. **Controle de Bloqueio**: O arquivo `poetry.lock` **deve ser versionado** obrigatoriamente no Git para garantir determinismo e reprodutibilidade do pipeline.
8. **Organização do `pyproject.toml`**: Manter o arquivo limpo, declarativo e com dependências categorizadas nos devidos grupos (`dependencies`, `group.dev.dependencies`).

---

## 3. Arquitetura e Modularização

O projeto adota uma arquitetura modular em camadas, orientada aos princípios de **Responsabilidade Única (Single Responsibility Principle - SRP)** e **Separação de Preocupações (Separation of Concerns - SoC)**.

### 3.1. Estrutura de Diretórios Canônica

```text
desafio_IBGE/
├── .gitignore
├── pyproject.toml
├── poetry.lock
├── README.md
├── SKILL.md
├── docs/
│   ├── doc_api.md
│   ├── doc_api.html
│   └── ...
├── src/
│   └── desafio_ibge/
│       ├── __init__.py
│       ├── config/           # Configurações, URLs, variáveis de ambiente e constantes
│       │   ├── __init__.py
│       │   └── settings.py
│       ├── extraction/       # Clientes HTTP, consumo e ingestão de APIs (Extract)
│       │   ├── __init__.py
│       │   └── ibge_client.py
│       ├── transformation/   # Normalização, saneamento, flattening e cálculos (Transform)
│       │   ├── __init__.py
│       │   └── normalizer.py
│       ├── validation/       # Contratos de dados, schemas Pydantic e checagens de qualidade
│       │   ├── __init__.py
│       │   └── schema.py
│       ├── loading/          # Persistência em banco/arquivos (Parquet, SQLite, DuckDB, etc.)
│       │   ├── __init__.py
│       │   └── storage.py
│       └── visualization/    # Interface com usuário / Dashboard (Streamlit ou similar)
│           ├── __init__.py
│           └── app.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_extraction.py
    ├── test_transformation.py
    └── test_validation.py
```

### 3.2. Padrões de Design de Código
- **Separação Rígida de Camadas**: Cada módulo atua exclusivamente em sua camada:
  - `extraction`: Apenas conecta, faz requisições, valida status HTTP e entrega dados brutos (Raw/Bronze).
  - `transformation`: Processa, limpa, achata nós aninhados e prepara dados tabulares (Silver/Gold).
  - `loading`: Grava e lê de mídias de armazenamento com idempotência.
  - `visualization`: Consome dados já tratados; **NÃO DEVE** conter lógica de negócio pesada, regras de transformação ou chamadas de API desgovernadas.
- **Imports Absolutos Obrigatórios**: Sempre utilize imports absolutos a partir da raiz do pacote:
  ```python
  # CORRETO:
  from desafio_ibge.config.settings import IBGE_BASE_URL
  from desafio_ibge.extraction.ibge_client import IBGEClient

  # PROIBIDO:
  from ..config.settings import IBGE_BASE_URL
  ```
- **Funções Pequenas, Testáveis e Reutilizáveis**: Evite funções monolíticas; aplique limite de complexidade ciclomática.
- **DRY (Don't Repeat Yourself)**: Evite código duplicado centralizando lógicas compartilhadas em módulos auxiliares utilitários.

---

## 4. Qualidade de Código e Formatação com Ruff

O **Ruff** é o linter e formatador oficial do projeto, substituindo Flake8, Black, isort e Pylint por sua extrema velocidade e consistência.

### 4.1. Regras de Estilo
- Conformidade estrita com a **PEP 8**.
- Organização e validação automática de imports (`isort` integrado).
- Remoção sistemática de código morto, imports não utilizados e variáveis orfãs.
- Linhas com limite de tamanho de 88 a 100 caracteres (conforme configurado no `pyproject.toml`).

### 4.2. Comandos Operacionais

```bash
# Análise de lint e checagem de erros estáticos
poetry run ruff check .

# Correção automática de erros aplicáveis
poetry run ruff check . --fix

# Formatação automática de código
poetry run ruff format .
```

### 4.3. Configuração Recomendada no `pyproject.toml`
```toml
[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort (ordenação de imports)
    "B",   # flake8-bugbear (bugs comuns)
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade (sintaxe moderna de Python)
]
ignore = []
```

---

## 5. Testes Automatizados e Cobertura

Todo código entregue deve ser acompanhado por testes automatizados com **Pytest**.

### 5.1. Diretrizes de Teste
- **Meta de Cobertura**: Garantir cobertura mínima de **50%** sobre as linhas de código contidas em `src/desafio_ibge/`.
- **Métricas via `pytest-cov`**: Aferir a cobertura executando a medição no diretório de testes.
- **Isolamento de Rede (Mocks Obrigatórios)**: Testes unitários **JAMAIS** dependem de conexão ativa com a internet. Toda chamada HTTP para a API do IBGE deve ser mockada utilizando `unittest.mock`, `requests_mock` ou `pytest-mock`.
- **Fixtures com Payloads Reais**: Criar fixtures de teste em `conftest.py` baseadas no JSON oficial de Mauá documentado em `docs/doc_api.md`.
- **Cobertura de Casos Negativos**: Testar cenários de sucesso, respostas 404/500 da API, timeouts e JSONs malformados.

### 5.2. Comandos de Execução de Testes
```bash
# Execução simples dos testes
poetry run pytest

# Execução com relatório de cobertura no terminal
poetry run pytest --cov=src/desafio_ibge --cov-report=term-missing

# Verificação estrita de barreira de cobertura (mínimo 50%)
poetry run pytest --cov=src/desafio_ibge --cov-fail-under=50
```

---

## 6. Documentação do Projeto

A documentação técnica é tratada como código de primeira classe no projeto.

### 6.1. Padrões de Documentação
- **Framework Oficial**: [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) para geração de site estático de documentação.
- **Diretório Central**: Toda documentação reside em `docs/`.
- **Preservação do Contrato da API**: Manter e enriquecer continuamente o arquivo [`docs/doc_api.md`](file:///c:/Users/Jones/projeto/desafio_IBGE/docs/doc_api.md).
- **Type Hints e Docstrings**:
  - Toda função pública, método e classe deve possuir **Type Hints** completos (Python typing: `Optional`, `Dict`, `List`, `Union`, etc.).
  - Docstrings no padrão **Google Style** ou **Sphinx**, detalhando `Args`, `Returns` e `Raises`.
- **Atualização Contínua**: Toda nova funcionalidade, alteração de parâmetros ou ajuste de pipeline deve ter sua respectiva página de documentação atualizada no mesmo PR/commit.

---

## 7. Boas Práticas de Engenharia de Dados

### 7.1. Conexões e Requisições HTTP Resilientes
- **Timeouts Explícitos**: Nunca fazer requisições sem parâmetros de timeout de conexão e leitura (ex.: `timeout=(3.05, 10.0)`).
- **Verificação de Status HTTP**: Sempre invocar `response.raise_for_status()` ou inspecionar `status_code` explicitamente.
- **Retries e Backoff Exponencial**: Implementar re-tentativas automáticas para erros temporários de servidor (HTTP 500, 502, 503, 504) e rate-limiting (HTTP 429).
- **Reuso de Sessões**: Utilizar `requests.Session()` para habilitar HTTP Keep-Alive e otimizar pool de conexões TCP.

### 7.2. Logging vs. Print
- **PROIBIDO O USO DE `print()`** em código de produção ou módulos do pacote `desafio_ibge`.
- **Utilizar o Módulo `logging`**:
  ```python
  import logging

  logger = logging.getLogger(__name__)

  logger.info("Iniciando extração do município IBGE: %s", municipio_id)
  logger.warning("Falha temporária ao consultar IBGE, acionando retry...")
  logger.error("Erro crítico na conversão do DataFrame: %s", exc, exc_info=True)
  ```

### 7.3. Qualidade de Dados (Data Quality) e Integridade
- **Validação de Tipos e Nulos**: Checar tipagem de colunas e garantir que chaves identificadoras (`id`, `nome`, `sigla_uf`) nunca sejam nulas.
- **Integridade da Chave Natural**: Validar se o código IBGE municipal possui exatamente 7 dígitos numéricos e se pertence ao estado de SP (início `35`).
- **Tratamento de Chaves Especiais**: As chaves aninhadas do IBGE `regiao-imediata` e `regiao-intermediaria` contêm hífens; devem ser convertidas compulsoriamente para `regiao_imediata` e `regiao_intermediaria`.
- **Idempotência na Carga**: A execução repetida do pipeline com os mesmos parâmetros de entrada deve produzir o mesmo estado final no storage, sem gerar registros duplicados (Upsert / Overwrite particionado).
- **Fidelidade da Informação**: **NUNCA INVENTAR OU SIMULAR** dados que não existam na API oficial. Respeitar as limitações conhecidas (a API de Localidades não fornece PIB ou População; métricas adicionais devem advir do SIDRA).
- **Segurança e Variáveis de Ambiente**: Nunca expor credenciais, tokens, segredos ou caminhos absolutos hardcoded no código; utilizar `python-dotenv` ou `pydantic-settings`.

---

## 8. Versionamento com Git e Pre-commit

### 8.1. Higiene de Repositório
- **Arquivo `.gitignore` Completo**: Deve bloquear obrigatoriamente:
  - Ambientes virtuais (`.venv/`, `venv/`, `env/`)
  - Caches de bytecode (`__pycache__/`, `*.py[cod]`)
  - Caches de ferramentas (`.ruff_cache/`, `.pytest_cache/`, `.coverage`, `htmlcov/`)
  - Arquivos de configuração local e segredos (`.env`, `*.secret`, `*.pem`)
  - Arquivos temporários de IDEs (`.vscode/`, `.idea/`, `.DS_Store`)
- **Pre-commit Hooks**: Configurar hooks com `pre-commit` para rodar `ruff check` e `ruff format` automaticamente antes de cada commit.
- **Convenção de Commits**: Adotar mensagens no padrão Conventional Commits (ex.: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).

---

## 9. Regras Mandatórias para Agentes de IA

Qualquer IA que opere neste repositório deve obedecer estritamente aos seguintes postulados:

1. **Leitura Prévia Obrigatória**: Antes de escrever qualquer linha de código ou sugerir alterações, consulte este `SKILL.md` e o [`docs/doc_api.md`](file:///c:/Users/Jones/projeto/desafio_IBGE/docs/doc_api.md).
2. **Respeito à Arquitetura**: Não quebre a estrutura de diretórios `src/desafio_ibge/`. Novos módulos devem ser justificados e inseridos na camada apropriada (`config`, `extraction`, `transformation`, `validation`, `loading`, `visualization`).
3. **Poetry Only**: Nunca sugira ou execute comandos `pip`. Use sempre `poetry add`, `poetry add --group dev` e `poetry run`.
4. **Sem Dependências Supérfluas**: Não instale bibliotecas desnecessárias ou redundantes. Prefira a biblioteca padrão ou as ferramentas já homologadas no projeto.
5. **Simplicidade e Modularidade (KISS)**: Priorize soluções limpas, legíveis e de fácil manutenção sobre abstrações excessivas.
6. **Justificativa Técnica**: Explique as decisões de arquitetura e design adotadas, fundamentando-as em boas práticas de engenharia de software e de dados.
7. **Verificação Real de Qualidade**: Quando o ambiente permitir execução de comandos:
   - Execute `poetry run ruff check .` e `poetry run ruff format .`.
   - Execute `poetry run pytest`.
   - **NUNCA alucine ou afirme que os testes passaram sem tê-los de fato executado.**
8. **Restrição de Escopo**: Modifique estritamente os arquivos e objetivos solicitados na tarefa atual, sem refatorações não solicitadas em outros módulos.

---

## 10. Checklist de Validação Rápida para Tarefas

Antes de finalizar qualquer tarefa, verifique:

- [ ] A documentação da API em `docs/doc_api.md` foi consultada e respeitada?
- [ ] O código reside na pasta correta dentro de `src/desafio_ibge/`?
- [ ] Foram utilizados imports absolutos (`from desafio_ibge....`)?
- [ ] Funções possuem Type Hints e Docstrings adequados?
- [ ] Foram utilizados logs com `logging` em vez de `print()`?
- [ ] Não há chamadas diretas a `pip`?
- [ ] O código foi verificado e aprovado pelo Ruff (`check` e `format`)?
- [ ] Há testes unitários associados com cobertura >= 50% e mocks nas chamadas HTTP?
- [ ] Nenhuma credencial ou dado sensível foi inserido no repositório?
