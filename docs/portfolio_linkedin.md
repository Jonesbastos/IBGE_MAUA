# Publicação Técnica de Portfólio — LinkedIn

> **Objetivo**: Apresentação profissional do projeto **`desafio_IBGE`** para recrutadores, tech leads e comunidade de Engenharia de Dados.
> **Status do Projeto**: Concluído, homologado e publicado em produção.
> **Links Canônicos**:
> - 💻 **Repositório GitHub**: [https://github.com/Jonesbastos/IBGE_MAUA](https://github.com/Jonesbastos/IBGE_MAUA)
> - 📊 **Dashboard Interativo**: [https://ibge-maua-dashboard.streamlit.app/](https://ibge-maua-dashboard.streamlit.app/)
> - 📚 **Documentação Técnica Completa**: [https://jonesbastos.github.io/IBGE_MAUA/](https://jonesbastos.github.io/IBGE_MAUA/)

---

## Versão Completa (Artigo Técnico / Post Estruturado)

### Como construí um pipeline resiliente de Engenharia de Dados com Arquitetura Medalhão e dados públicos do IBGE

Trabalhar com dados públicos abertos é um dos melhores testes de maturidade para um Engenheiro de Dados. Quem já consumiu APIs governamentais conhece bem os desafios: payloads JSON profundamente aninhados, documentações com discrepâncias de nomenclatura, variações metodológicas entre pesquisas e, frequentemente, lentidão ou intermitência nos serviços upstream.

Para demonstrar na prática como transformar dados brutos heterogêneos em uma solução analítica profissional, desenvolvi o **`desafio_IBGE`** — um pipeline de dados ponta a ponta focado no município de **Mauá (SP)** (Código IBGE: `3529401`), integrando três fontes oficiais distintas do IBGE:
1. **API de Localidades (v1)**: Malha territorial e hierarquia político-administrativa (divisões regionais de 1989 e 2017).
2. **API de Agregados / SIDRA (v3)**: Resultados do Censo Demográfico 2022 (população, densidade, alfabetização e gênero) e Estimativas Anuais de População (2001–2026).
3. **API de Pesquisas (v1)**: Série histórica de Contas Regionais do PIB e Valores Adicionados Brutos setoriais (1999–2023).

---

### A Arquitetura da Solução: Padrão Medalhão em SQLite

Em vez de soluções superdimensionadas para um volume municipal de escopo específico, optei por uma engenharia enxuta, determinística e altamente performática: a **Medallion Architecture (Bronze, Silver e Gold)** implementada sobre o **SQLite local**:

- **🥉 Camada Bronze (Raw Ingestion)**:
  - Clientes HTTP com pooling de conexão (`requests.Session`), retries com backoff exponencial e timeouts explícitos.
  - Armazenamento integral do payload JSON bruto acompanhado de metadados de auditoria: URL consultada, status HTTP, timestamp UTC e hash criptográfico **SHA-256** para garantia de integridade e imutabilidade.
  - Ingestão idempotente via `UPSERT` nativo (`ON CONFLICT DO UPDATE`).

- **🥈 Camada Silver (Conformed & Cleansed)**:
  - Validação rigorosa de contratos de dados (Data Contracts) com **Pydantic v2**, verificando conformidade de tipos, códigos municipais de 7 dígitos e valores numéricos válidos.
  - Achatamento e normalização com **Pandas** no padrão `snake_case`, sanitizando caracteres especiais.
  - Separação em quatro modelos relacionais tipados (`silver_municipio`, `silver_ibge_populacao`, `silver_ibge_pib`, `silver_ibge_censitario`), preservando nulos oficiais e abolindo imputações arbitrárias de zero.

- **🥇 Camada Gold (Business Ready / Analytical Views)**:
  - Construída inteiramente sobre **6 SQL Views declarativas**, com **custo zero de redundância em disco**.
  - Janelamento temporal (`LAG()`) particionado por metodologia para calcular crescimento anual populacional.
  - Cálculos de participações setoriais do PIB protegidos contra divisão por zero via `NULLIF()`.
  - View de governança e auditoria operacional comparando Bronze vs. Silver com semântica de `FULL OUTER JOIN`, expondo taxas de conformidade e latência em segundos.

---

### Camada de Apresentação e Deploy na Nuvem

Para consumo dos indicadores, desenvolvi um dashboard reativo desacoplado com **Streamlit** e **Plotly Express**, dividido em 5 abas temáticas:
1. **Visão Geral Territorial & Socioeconômica**: Síntese executiva dos principais indicadores municipais.
2. **Evolução Populacional**: Comparativo histórico entre contagens censitárias e estimativas populacionais (2001–2026).
3. **Economia & PIB**: Análise do PIB nominal, PIB per capita e composição setorial do VAB (1999–2023).
4. **Demografia & Alfabetização**: Estrutura por sexo, cálculo da razão estatística de gênero (92,82 homens por 100 mulheres) e taxa de alfabetização (96,74%).
5. **Governança & Auditoria**: Inventário volumétrico dos 322 registros consolidados e auditoria de qualidade.

**A decisão de deploy**: O dashboard está publicado no **Streamlit Community Cloud**. Para resolver o desafio de manter os dados acessíveis sem reexecutar o pipeline de extração na abertura do app (evitando latência e rate limits da API), criei uma rotina de auto-restauração baseada em um **snapshot SQL versionado (~98 KB)**. Ao iniciar o container, o banco relacional é montado localmente em menos de **20 milissegundos**, assegurando total portabilidade ("clone and run") sem demandar credenciais ou serviços pagos de nuvem.

---

### Engenharia de Software e Qualidade de Código

- **Gerenciamento com Poetry**: Dependências de produção e desenvolvimento rigorosamente isoladas em Python 3.13.13, sem arquivos `requirements.txt` soltos.
- **Testes Automatizados**: **152 testes** automatizados via **Pytest**, atingindo **93,44% de cobertura de código**, incluindo testes com `requests_mock` e testes de interface com `streamlit.testing.v1.AppTest`.
- **Linting & Formatação**: Conformidade estrita com as regras modernas do **Ruff** e hooks de **pre-commit**.
- **Documentação & CI/CD**: Documentação técnica completa compilada com **MkDocs Material** (`--strict`) e publicada automaticamente no **GitHub Pages** via **GitHub Actions**.

---

### Principais Aprendizados Técnicos

1. **Governança Temporal**: Pesquisas governamentais possuem naturezas metodológicas e cronogramas distintos (Censo decenal, Estimativas anuais, PIB com 2 anos de defasagem). Misturar esses períodos sem rotulagem explícita gera distorções analíticas graves.
2. **Idempotência como Princípio**: Um pipeline de dados confiável deve ser capaz de rodar 1 ou 100 vezes consecutivas sobre a mesma base de dados produzindo exatamente os mesmos resultados e a mesma volumetria.
3. **Equilíbrio Arquitetural**: Projetar uma arquitetura enxuta baseada em arquivos relacionais SQLite com snapshots SQL mostrou-se ordens de grandeza mais simples, barato e confiável do que conectar infraestruturas de nuvem desnecessárias para o escopo do projeto.

---

### Onde Acessar

- 🚀 **Dashboard em Produção**: [https://ibge-maua-dashboard.streamlit.app/](https://ibge-maua-dashboard.streamlit.app/)
- 📖 **Documentação Técnica (GitHub Pages)**: [https://jonesbastos.github.io/IBGE_MAUA/](https://jonesbastos.github.io/IBGE_MAUA/)
- 📦 **Código Fonte no GitHub**: [https://github.com/Jonesbastos/IBGE_MAUA](https://github.com/Jonesbastos/IBGE_MAUA)

Fique à vontade para explorar, testar e enviar seu feedback ou sugestões de melhoria!

---

## Versão Resumida (Para Post Direto no Feed do LinkedIn)

```text
Como construir um pipeline de Engenharia de Dados resiliente com dados públicos do IBGE? 📊

Trabalhar com dados governamentais é sempre um exercício prático de qualidade de dados: APIs com formatos heterogêneos, JSONs aninhados e diferentes granularidades temporais.

Para demonstrar boas práticas de Engenharia de Dados, desenvolvi o desafio_IBGE — um projeto completo de extração, tratamento, modelagem e visualização de indicadores do município de Mauá (SP):

🔹 Arquitetura Medalhão (Bronze, Silver e Gold) implementada sobre SQLite;
🔹 Ingestão resiliente com pooling de conexões, retry exponencial e auditoria por hash SHA-256;
🔹 Validação rigorosa de contratos de dados (Data Contracts) com Pydantic v2;
🔹 Normalização tabular e séries temporais com Pandas;
🔹 Modelagem analítica via 6 SQL Views na Camada Gold (com LAG, cálculo de participações setoriais e divisão protegida por NULLIF);
🔹 Dashboard interativo com Streamlit e Plotly Express em 5 abas analíticas;
🔹 152 testes automatizados com Pytest atingindo 93,44% de cobertura de código;
🔹 CI/CD com GitHub Actions e documentação técnica no GitHub Pages via MkDocs Material;
🔹 Deploy otimizado no Streamlit Cloud com carga instantânea (<20ms) via snapshot SQL versionado.

Confira o projeto nos links:
🌐 Dashboard: https://ibge-maua-dashboard.streamlit.app/
📚 Documentação Técnica: https://jonesbastos.github.io/IBGE_MAUA/
💻 Repositório GitHub: https://github.com/Jonesbastos/IBGE_MAUA

Feedback, conexões e sugestões são sempre muito bem-vindos!

#DataEngineering #Python #Streamlit #SQL #Pandas #Pydantic #DataQuality #IBGE #Portfolio
```
