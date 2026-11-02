# Dashboard Interativo (Streamlit & Plotly)

> **Camada do Pipeline**: Apresentação & Visualização
> **Módulo**: `src/desafio_ibge/visualization/app.py`
> **Tecnologias**: Streamlit, Plotly Express, Pandas
> **Status**: Homologado e Publicado em Produção
> **Acesso Online**: [https://ibge-maua-dashboard.streamlit.app/](https://ibge-maua-dashboard.streamlit.app/)

---

## 1. Visão Geral da Camada de Visualização

O **Dashboard Interativo** do projeto **`desafio_IBGE`** materializa a camada de consumo analítico da *Medallion Architecture*.

Construído em **Streamlit** e enriquecido com gráficos dinâmicos do **Plotly Express**, o aplicativo consome exclusivamente as visões modeladas na camada Gold e as métricas operacionais da camada Silver/Bronze, proporcionando uma experiência de exploração abrangente sobre a realidade territorial, populacional, econômica e demográfica de **Mauá (SP)** (Código IBGE: `3529401`).

A aplicação está disponível publicamente em ambiente de produção através do Streamlit Community Cloud:
- 🌐 **URL de Produção**: [https://ibge-maua-dashboard.streamlit.app/](https://ibge-maua-dashboard.streamlit.app/)

```mermaid
flowchart TD
    subgraph Storage ["Camada Gold (SQLite)"]
        G_HIER["gold_vw_municipio_hierarquia"]
        G_AUD["gold_vw_qualidade_auditoria"]
        G_POP["gold_populacao_historica"]
        G_PIB["gold_pib_historico"]
        G_DEMO["gold_demografia_sexo"]
        G_RES["gold_resumo_socioeconomico"]
    end

    subgraph DataAccess ["Camada de Acesso a Dados (loading/storage.py)"]
        FnLoads["Funções de Consulta com Cache<br>@st.cache_data(ttl=60)"]
    end

    subgraph Tabs ["Dashboard Streamlit (5 Abas Analíticas)"]
        Tab1["Aba 1: Visão Geral"]
        Tab2["Aba 2: População Histórica"]
        Tab3["Aba 3: Economia & PIB"]
        Tab4["Aba 4: Demografia & Alfabetização"]
        Tab5["Aba 5: Governança & Auditoria"]
    end

    Storage --> DataAccess --> Tabs
```

---

## 2. Demonstração do Dashboard

Esta seção apresenta as visualizações e evidências gráficas das cinco abas analíticas que compõem o painel interativo. As imagens de referência encontram-se mapeadas no diretório `docs/assets/dashboard/`.

> [!NOTE]
> **Instruções para Captura e Atualização das Imagens**:
> 1. Acesse o dashboard oficial em [https://ibge-maua-dashboard.streamlit.app/](https://ibge-maua-dashboard.streamlit.app/).
> 2. Navegue individualmente por cada uma das cinco abas.
> 3. Realize a captura de tela da área analítica em resolução recomendada de 1920x1080 (proporção 16:9).
> 4. Salve os arquivos PNG correspondentes no diretório `docs/assets/dashboard/` respeitando a nomenclatura padronizada abaixo.

| Aba do Dashboard | Arquivo de Imagem | Destaques Visuais & Conteúdo Analítico |
| :--- | :--- | :--- |
| **1. Visão Geral** | `docs/assets/dashboard/01_visao_geral.png` | Cards de KPIs (População 418k, PIB R$ 25 bi, PIB per capita R$ 59,7k, Área 61,9 km², Alfabetização 96,7%), hierarquia territorial e tabela dinâmica com exportação CSV. |
| **2. População Histórica** | `docs/assets/dashboard/02_evolucao_populacional.png` | Gráfico de linhas Plotly comparando Censos vs Estimativas (2001–2026), controle de slider temporal e KPIs de variação absoluta/percentual acumulada. |
| **3. Economia & PIB** | `docs/assets/dashboard/03_economia_pib.png` | Série histórica do PIB nominal (1999–2023), curva de PIB per capita e gráfico de área com a composição setorial do VAB (Serviços, Indústria, Adm. Pública e Agropecuária). |
| **4. Demografia & Alfabetização** | `docs/assets/dashboard/04_demografia_alfabetizacao.png` | Gráfico de rosca e distribuição por sexo (51,86% feminino vs 48,14% masculino), razão de sexo oficial (92,82 H/100 M) e taxa de alfabetização (96,74%). |
| **5. Governança & Auditoria** | `docs/assets/dashboard/05_governanca_auditoria.png` | Volumetria Medallion completa (322 registros reais no SQLite distribuídos entre Territorial e Socioeconômico), taxa de conformidade (100%), latência e catálogo de metadados. |

---

## 3. Como Executar o Dashboard Localmente

Para iniciar a aplicação no ambiente virtual local:

```bash
# Execução direta via Streamlit
poetry run streamlit run src/desafio_ibge/visualization/app.py

# Ou via atalho Taskipy
poetry run task dashboard
```

O Streamlit disponibilizará a aplicação no navegador em `http://localhost:8501`.

---

## 4. Detalhamento das 5 Abas Analíticas

### 4.1. Aba 1 — Visão Geral Territorial & Socioeconômica
- **Cards Estratégicos**: Apresenta os indicadores-chave do município com seus respectivos anos e fontes oficiais:
  - População Censitária (418.261 hab — Censo 2022)
  - População Estimada Recente (429.064 hab — 2026)
  - PIB a Preços Correntes (R$ 25,00 bilhões — 2023)
  - PIB per capita (R$ 59.773,04 — 2023)
  - Área Territorial Oficial (61,937 km²)
  - Densidade Demográfica (6.753,01 hab/km²)
  - Taxa de Alfabetização (96,74%)
  - Razão de Sexo (92,82 homens por 100 mulheres)
- **Identificação Territorial**: Hierarquia completa de Mauá (Mesorregião Metropolitana, Microrregião de São Paulo, Regiões Imediata e Intermediária).
- **Tabela Analítica**: Exibição tabular interativa com mecanismo de busca e botão de exportação em **CSV**.

### 4.2. Aba 2 — População Histórica
- **Gráfico Temporal com Plotly**: Linha de evolução com marcadores distintos para contagens do Censo Demográfico versus Estimativas anuais de população (2001 a 2026).
- **Filtro Interativo**: Slider de intervalo de anos permitindo recorte temporal sob demanda.
- **Métricas de Dinâmica Populacional**: Variação absoluta e crescimento percentual acumulado no intervalo selecionado.
- **Aviso Metodológico**: Destaque para descontinuidades de amostragem entre operações censitárias e estimativas matemáticas.

### 4.3. Aba 3 — Economia & PIB
- **Gráficos Econômicos**:
  - Evolução do Produto Interno Bruto a preços correntes (1999–2023).
  - Evolução do PIB per capita em reais correntes.
  - Composição setorial do Valor Adicionado Bruto (Agropecuária, Indústria, Serviços e Administração Pública) em área empilhada percentual.
- **Governança de Defasagem**: Alerta explícito sobre a defasagem temporal de 2 anos nas Contas Regionais e distinção entre crescimento nominal versus real.

### 4.4. Aba 4 — Demografia & Alfabetização
- **Pirâmide e Distribuição por Sexo**: Gráfico de rosca e barras comparativas destacando 201.348 homens (48,14%) e 216.913 mulheres (51,86%).
- **Razão de Sexo Oficial**: Destaque para a proporção estatística de 92,82 homens para cada 100 mulheres.
- **Educação e Território**: Visualização da taxa de alfabetização da população com 15 anos ou mais (96,74%) e métricas de densidade urbana.

### 4.5. Aba 5 — Governança & Auditoria
- **Volumetria Medallion Integrada**: Gráfico e tabela discriminando o volume real de registros entre o domínio Territorial e o domínio Socioeconômico (totalizando **322 registros reais no SQLite**).
- **Métricas de Data Quality**: Taxa de conformidade do pipeline (100%), ausência de nulos em atributos mandatórios e integridade dos códigos IBGE.
- **Linhagem e Latência**: Carimbos UTC de captura na Bronze e transformação na Silver, com latência média de execução em segundos.
- **Catálogo de Metadados**: Relação de tabelas e views com descrições formais, chaves primárias e granularidade.

---

## 5. Performance, Resiliência e Testes de Interface

- **Cache Inteligente**: Decoração com `@st.cache_data(ttl=60)` em todas as funções de leitura, eliminando requisições repetidas ao banco de dados durante interações do usuário.
- **Botão de Atualização**: Gatilho na barra lateral que aciona `st.cache_data.clear()` e recarrega os dados imediatamente.
- **Restauração Automática via Snapshot SQL**: Através da função `ensure_database_ready()`, a aplicação recria todo o banco SQLite a partir de `data/snapshots/ibge_maua_snapshot.sql` em menos de 20 milissegundos caso o banco local não exista, garantindo operação imediata no Streamlit Community Cloud.
- **Degradação Suave (Graceful Fallback)**: Se o banco de dados ainda não foi criado ou se encontrar vazio, a aplicação intercepta a condição e exibe alertas amigáveis (`st.warning()`), instruindo o usuário a executar o pipeline sem quebrar a interface.
- **Testes Automatizados de Interface**: A suíte de testes em `tests/test_visualization.py` utiliza `streamlit.testing.v1.AppTest` para validar a inicialização, renderização de abas e componentes sob múltiplos cenários de banco de dados (banco inexistente, banco vazio, banco territorial e banco completo).
