"""Dashboard Interativo do projeto desafio_IBGE em Streamlit & Plotly.

Consome os dados modelados da camada Gold no banco SQLite, apresentando
a hierarquia territorial, evolução populacional, indicadores econômicos de PIB,
demografia censitária e governança da Medallion Architecture para Mauá (SP).
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

# Garantir que o diretório 'src' esteja acessível no sys.path em ambientes de deploy
_SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from desafio_ibge.config.settings import (  # noqa: E402
    DEFAULT_DB_PATH,
    IBGE_BASE_URL,
    MAUA_DIRECT_URL,
    MAUA_IBGE_CODE,
)
from desafio_ibge.loading import (  # noqa: E402
    ensure_database_ready,
    get_kpis_geograficos,
    get_kpis_qualidade,
    get_kpis_socioeconomicos,
    get_metadados_governanca,
    get_volumetria_medallion,
    read_gold_auditoria,
    read_gold_demografia_sexo,
    read_gold_hierarquia,
    read_gold_pib_historico,
    read_gold_populacao_historica,
    read_gold_resumo_socioeconomico,
)

logger = logging.getLogger(__name__)

# Mapeamento de colunas para exibição legível na interface
COLUMNS_FRIENDLY_MAP: dict[str, str] = {
    "municipio_id": "Código IBGE",
    "municipio_nome": "Município",
    "uf_id": "Código UF",
    "uf_sigla": "UF",
    "uf_nome": "Estado",
    "regiao_id": "Código Região",
    "regiao_sigla": "Sigla Região",
    "regiao_nome": "Macrorregião",
    "regiao_imediata_id": "Cód. Região Imediata",
    "regiao_imediata_nome": "Região Imediata (2017)",
    "regiao_intermediaria_id": "Cód. Região Intermediária",
    "regiao_intermediaria_nome": "Região Intermediária (2017)",
    "microrregiao_id": "Cód. Microrregião",
    "microrregiao_nome": "Microrregião (1989)",
    "mesorregiao_id": "Cód. Mesorregião",
    "mesorregiao_nome": "Mesorregião (1989)",
    "transformed_at": "Última Carga (UTC)",
}


# =============================================================================
# Funções de Carregamento com Cache Streamlit (TTL = 60s)
# =============================================================================


@st.cache_data(ttl=60)
def load_hierarquia_data(db_path: str | None = None) -> pd.DataFrame:
    """Carrega dados da View Gold de hierarquia com cache TTL de 60 segundos."""
    return read_gold_hierarquia(db_path=db_path)


@st.cache_data(ttl=60)
def load_auditoria_data(db_path: str | None = None) -> pd.DataFrame:
    """Carrega dados da View Gold de auditoria com cache TTL de 60 segundos."""
    return read_gold_auditoria(db_path=db_path)


@st.cache_data(ttl=60)
def load_kpis_geograficos(db_path: str | None = None) -> dict[str, Any]:
    """Carrega agregações territoriais Gold com cache TTL de 60 segundos."""
    return get_kpis_geograficos(db_path=db_path)


@st.cache_data(ttl=60)
def load_kpis_qualidade(db_path: str | None = None) -> dict[str, Any]:
    """Carrega indicadores de qualidade da camada Gold com cache de 60s."""
    return get_kpis_qualidade(db_path=db_path)


@st.cache_data(ttl=60)
def load_populacao_historica_data(db_path: str | None = None) -> pd.DataFrame:
    """Carrega série histórica de população da camada Gold."""
    return read_gold_populacao_historica(db_path=db_path)


@st.cache_data(ttl=60)
def load_pib_historico_data(db_path: str | None = None) -> pd.DataFrame:
    """Carrega série histórica de PIB e VAB da camada Gold."""
    return read_gold_pib_historico(db_path=db_path)


@st.cache_data(ttl=60)
def load_demografia_sexo_data(db_path: str | None = None) -> pd.DataFrame:
    """Carrega distribuição demográfica por sexo da camada Gold."""
    return read_gold_demografia_sexo(db_path=db_path)


@st.cache_data(ttl=60)
def load_resumo_socioeconomico_data(db_path: str | None = None) -> pd.DataFrame:
    """Carrega resumo consolidado de indicadores socioeconômicos Gold."""
    return read_gold_resumo_socioeconomico(db_path=db_path)


@st.cache_data(ttl=60)
def load_kpis_socioeconomicos(db_path: str | None = None) -> dict[str, Any]:
    """Carrega dicionário com os principais KPIs socioeconômicos calculados."""
    return get_kpis_socioeconomicos(db_path=db_path)


@st.cache_data(ttl=60)
def load_volumetria_governanca(db_path: str | None = None) -> pd.DataFrame:
    """Carrega a volumetria detalhada por camada e domínio de dados no SQLite."""
    return get_volumetria_medallion(db_path=db_path)


@st.cache_data(ttl=60)
def load_metadados_governanca(db_path: str | None = None) -> dict[str, Any]:
    """Carrega metadados analíticos de governança, períodos e indicadores."""
    return get_metadados_governanca(db_path=db_path)


@st.cache_data(ttl=60)
def load_tabelas_contagem(db_path: str | None = None) -> pd.DataFrame:
    """Obtém contagem física de registros de cada tabela e view do SQLite."""
    df_vol = get_volumetria_medallion(db_path=db_path)
    if df_vol.empty:
        return pd.DataFrame(columns=["Tipo", "Nome do Objeto", "Total Registros"])

    return df_vol[["tipo_objeto", "objeto", "total_registros"]].rename(
        columns={
            "tipo_objeto": "Tipo",
            "objeto": "Nome do Objeto",
            "total_registros": "Total Registros",
        }
    )


# =============================================================================
# Componentes Visuais Comuns (Header & Sidebar)
# =============================================================================


def render_header() -> None:
    """Renderiza cabeçalho, introdução e metadados oficiais do projeto."""
    st.title("🗺️ Desafio IBGE — Inteligência Territorial & Socioeconômica")
    st.caption(
        "Engenharia de Dados com Medallion Architecture (Bronze, Silver e Gold) "
        "sobre dados oficiais do IBGE para o município de Mauá — SP "
        f"(Código IBGE `{MAUA_IBGE_CODE}`)."
    )
    st.divider()


def render_sidebar(db_path_str: str) -> None:
    """Renderiza a barra lateral com status, fontes oficiais e controles."""
    with st.sidebar:
        st.header("⚙️ Painel de Controle")
        st.info(f"**Banco SQLite:** `{Path(db_path_str).name}`")

        if st.button("🔄 Atualizar Dados", width="stretch"):
            st.cache_data.clear()
            st.rerun()

        st.subheader("📚 Metadados Oficiais")
        st.markdown(
            f"""
            - **Município:** Mauá (SP)
            - **Código IBGE:** `{MAUA_IBGE_CODE}`
            - **Fonte Principal:** [Portal IBGE]({IBGE_BASE_URL})
            - **Endpoint Direto:** [Consulta Mauá]({MAUA_DIRECT_URL})
            - **Arquitetura:** Medallion (Bronze -> Silver -> Gold)
            - **Pesquisas Oficiais:**
              - API de Localidades
              - Censo Demográfico 2022
              - Estimativas Populacionais (2001–2026)
              - Contas Regionais / PIB Municipal (1999–2023)
            """
        )
        st.divider()
        st.caption("Desenvolvido com Python, SQLite, Streamlit & Plotly.")


# =============================================================================
# Funções de Compatibilidade Retroativa
# =============================================================================


def render_territorial_kpis(df: pd.DataFrame) -> None:
    """Renderiza cards com os principais atributos territoriais de Mauá."""
    st.subheader("📍 Identificação Territorial")

    if df.empty:
        st.warning("Nenhum dado territorial disponível para exibição de métricas.")
        return

    row = df.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Município",
            value=str(row.get("municipio_nome", "N/A")),
        )
        st.caption(f"Código IBGE: `{row.get('municipio_id', 'N/A')}`")

    with col2:
        st.metric(
            label="Estado (UF)",
            value=f"{row.get('uf_nome', 'N/A')} ({row.get('uf_sigla', 'N/A')})",
        )
        st.caption(f"Código UF: `{row.get('uf_id', 'N/A')}`")

    with col3:
        st.metric(
            label="Macrorregião",
            value=str(row.get("regiao_nome", "N/A")),
        )
        st.caption(f"Sigla: `{row.get('regiao_sigla', 'N/A')}`")

    with col4:
        st.metric(
            label="Mesorregião (1989)",
            value=str(row.get("mesorregiao_nome", "N/A")),
        )
        st.caption(f"Microrregião: `{row.get('microrregiao_nome', 'N/A')}`")

    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.markdown(
            f"**Região Geográfica Imediata (2017):** "
            f"`{row.get('regiao_imediata_nome', 'N/A')}` "
            f"*(Cód. {row.get('regiao_imediata_id', 'N/A')})*"
        )
    with subcol2:
        st.markdown(
            f"**Região Geográfica Intermediária (2017):** "
            f"`{row.get('regiao_intermediaria_nome', 'N/A')}` "
            f"*(Cód. {row.get('regiao_intermediaria_id', 'N/A')})*"
        )


def render_tabela_analitica(df: pd.DataFrame) -> None:
    """Renderiza tabela analítica com campos amigáveis e filtros contextuais."""
    st.subheader("📋 Tabela Territorial Analítica (Camada Gold)")

    if df.empty:
        st.info("A tabela analítica está vazia no momento.")
        return

    display_df = df.rename(columns=COLUMNS_FRIENDLY_MAP)

    search_query = st.text_input(
        "🔍 Buscar município ou código IBGE:",
        placeholder="Digite o nome ou código...",
    )

    if search_query:
        mask = display_df["Município"].astype(str).str.contains(
            search_query, case=False, na=False
        ) | display_df["Código IBGE"].astype(str).str.contains(search_query, na=False)
        display_df = display_df[mask]

    st.dataframe(display_df, width="stretch", hide_index=True)

    csv_data = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Baixar Dados Territoriais (CSV)",
        data=csv_data,
        file_name="ibge_maua_territorial_gold.csv",
        mime="text/csv",
    )


def render_governanca_qualidade(
    kpis_dq: dict[str, Any],
    df_auditoria: pd.DataFrame,
) -> None:
    """Exibe painel de métricas de qualidade de dados e auditoria."""
    st.subheader("🛡️ Governança & Data Quality (Auditoria)")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Taxa de Conformidade",
            value=f"{kpis_dq.get('taxa_conformidade_pct', 0.0)}%",
        )
        st.caption("Registros sincronizados entre camadas")

    with col2:
        st.metric(
            label="Registros na Bronze",
            value=kpis_dq.get("total_presente_bronze", 0),
        )
        st.caption("JSONs brutos oficiais ingeridos")

    with col3:
        st.metric(
            label="Registros na Silver",
            value=kpis_dq.get("total_presente_silver", 0),
        )
        st.caption("Linhas normalizadas e tipadas")

    with col4:
        st.metric(
            label="Falhas de Qualidade",
            value=kpis_dq.get("total_falhas_qualidade", 0),
        )
        st.caption("Nulos e inconsistências detectadas")

    subcol1, subcol2, subcol3 = st.columns(3)
    with subcol1:
        st.markdown(
            f"**Última Ingestão (Bronze):** "
            f"`{kpis_dq.get('ultima_ingestao_utc') or 'N/A'}`"
        )
    with subcol2:
        st.markdown(
            f"**Última Transformação (Silver):** "
            f"`{kpis_dq.get('ultima_transformacao_utc') or 'N/A'}`"
        )
    with subcol3:
        lat = kpis_dq.get("latencia_media_segundos")
        lat_text = f"{lat}s" if lat is not None else "N/A"
        st.markdown(f"**Latência Média de Carga:** `{lat_text}`")

    if not df_auditoria.empty:
        with st.expander("🔍 Ver Detalhes do Log de Auditoria SQL"):
            st.dataframe(df_auditoria, width="stretch", hide_index=True)


def render_graficos(
    kpis_dq: dict[str, Any],
    df_volumetria: pd.DataFrame | None = None,
) -> None:
    """Gera visualizações interativas com Plotly Express baseadas nos dados reais.

    Apresenta a volumetria por camada (Bronze, Silver e Gold) discriminando
    os domínios Territorial e Socioeconômico, preservando o gráfico de
    regras de qualidade.
    """
    st.subheader("📊 Visualizações Analíticas de Governança")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        if (
            df_volumetria is not None
            and not df_volumetria.empty
            and "camada" in df_volumetria.columns
            and "dominio" in df_volumetria.columns
        ):
            agg_df = df_volumetria.groupby(["camada", "dominio"], as_index=False)[
                "total_registros"
            ].sum()
            fig_camadas = px.bar(
                agg_df,
                x="camada",
                y="total_registros",
                color="dominio",
                barmode="group",
                text="total_registros",
                title="Volume de Registros por Camada e Domínio de Dados",
                labels={
                    "camada": "Camada",
                    "total_registros": "Registros no SQLite",
                    "dominio": "Domínio",
                },
                color_discrete_map={
                    "Territorial": "#00897b",
                    "Socioeconômico": "#1e88e5",
                },
                category_orders={"camada": ["Bronze", "Silver", "Gold"]},
            )
            fig_camadas.update_traces(textposition="outside")
            fig_camadas.update_layout(yaxis_title="Quantidade de Registros")
            st.plotly_chart(fig_camadas, width="stretch")
        else:
            camadas_df = pd.DataFrame(
                [
                    {
                        "Camada": "Bronze (Raw)",
                        "Registros": kpis_dq.get("total_presente_bronze", 0),
                    },
                    {
                        "Camada": "Silver (Cleansed)",
                        "Registros": kpis_dq.get("total_presente_silver", 0),
                    },
                    {
                        "Camada": "Gold (Conforme)",
                        "Registros": kpis_dq.get("total_conforme", 0),
                    },
                ]
            )

            fig_camadas = px.bar(
                camadas_df,
                x="Camada",
                y="Registros",
                color="Camada",
                text="Registros",
                title="Volume de Registros por Camada da Arquitetura",
                color_discrete_sequence=["#cd7f32", "#c0c0c0", "#ffd700"],
            )
            fig_camadas.update_traces(textposition="outside")
            fig_camadas.update_layout(showlegend=False, yaxis_title="Quantidade")
            st.plotly_chart(fig_camadas, width="stretch")

    with col_chart2:
        validacoes_df = pd.DataFrame(
            [
                {
                    "Validação": "Código IBGE Válido",
                    "Aprovados": kpis_dq.get("total_codigos_validos", 0),
                },
                {
                    "Validação": "Checksum SHA-256 Íntegro",
                    "Aprovados": kpis_dq.get("total_checksums_validos", 0),
                },
                {
                    "Validação": "Resposta HTTP 200 OK",
                    "Aprovados": kpis_dq.get("total_http_ok", 0),
                },
                {
                    "Validação": "Consistência Geográfica",
                    "Aprovados": kpis_dq.get("total_consistencia_geografica", 0),
                },
            ]
        )

        fig_dq = px.bar(
            validacoes_df,
            x="Aprovados",
            y="Validação",
            orientation="h",
            text="Aprovados",
            title="Conformidade das Regras de Data Quality",
            color="Aprovados",
            color_continuous_scale="Greens",
        )
        fig_dq.update_traces(textposition="outside")
        fig_dq.update_layout(xaxis_title="Registros Conformes", yaxis_title="")
        st.plotly_chart(fig_dq, width="stretch")


# =============================================================================
# Aba 1 — Visão Geral Territorial e Socioeconômica
# =============================================================================


def render_tab_visao_geral(
    df_hierarquia: pd.DataFrame,
    kpis_socio: dict[str, Any],
    df_resumo: pd.DataFrame,
) -> None:
    """Renderiza a Aba 1 com indicadores territoriais, socioeconômicos e tabela."""
    st.subheader("📌 Indicadores Estratégicos de Mauá (SP)")

    # Cards Principais de Indicadores (Linha 1)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pop_censo = kpis_socio.get("populacao_censo_2022")
        val_censo = f"{pop_censo:,.0f}".replace(",", ".") if pop_censo else "N/A"
        st.metric(label="População (Censo 2022)", value=f"{val_censo} hab.")
        st.caption("Ano: 2022 | Fonte: IBGE — Censo Demográfico")

    with col2:
        pop_est = kpis_socio.get("populacao_estimada_recente")
        ano_est = kpis_socio.get("ano_estimativa_recente", "2026")
        val_est = f"{pop_est:,.0f}".replace(",", ".") if pop_est else "N/A"
        st.metric(label=f"População Estimada ({ano_est})", value=f"{val_est} hab.")
        st.caption(f"Ano: {ano_est} | Fonte: IBGE — Estimativas")

    with col3:
        pib_corr = kpis_socio.get("pib_corrente_mil_reais")
        ano_pib = kpis_socio.get("ano_pib_corrente", "2023")
        if pib_corr is not None:
            val_pib_bi = (pib_corr * 1000.0) / 1e9
            val_pib_str = f"R$ {val_pib_bi:.2f} Bi"
        else:
            val_pib_str = "N/A"
        st.metric(label=f"PIB Corrente ({ano_pib})", value=val_pib_str)
        st.caption(f"Ano: {ano_pib} | Fonte: IBGE — Contas Regionais")

    with col4:
        pib_pc = kpis_socio.get("pib_per_capita_reais")
        ano_pc = kpis_socio.get("ano_pib_per_capita", "2023")
        val_pc_str = (
            f"R$ {pib_pc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if pib_pc
            else "N/A"
        )
        st.metric(label=f"PIB per capita ({ano_pc})", value=val_pc_str)
        st.caption(f"Ano: {ano_pc} | Fonte: IBGE — Contas Regionais")

    # Linha 2 de Cards
    sub1, sub2, sub3, sub4 = st.columns(4)

    with sub1:
        area = kpis_socio.get("area_territorial_km2")
        val_area = f"{area:.3f} km²" if area else "N/A"
        st.metric(label="Área Territorial", value=val_area)
        st.caption("Ano: 2022 | Fonte: IBGE — Censo Demográfico")

    with sub2:
        dens = kpis_socio.get("densidade_demografica")
        val_dens = (
            f"{dens:,.2f} hab/km²".replace(",", "X").replace(".", ",").replace("X", ".")
            if dens
            else "N/A"
        )
        st.metric(label="Densidade Demográfica", value=val_dens)
        st.caption("Ano: 2022 | Fonte: IBGE — Censo Demográfico")

    with sub3:
        alfab = kpis_socio.get("taxa_alfabetizacao_pct")
        val_alfab = f"{alfab:.2f}%" if alfab else "N/A"
        st.metric(label="Taxa de Alfabetização", value=val_alfab)
        st.caption("Ano: 2022 | Fonte: IBGE — Censo Demográfico")

    with sub4:
        razao = kpis_socio.get("razao_sexo")
        val_razao = f"{razao:.2f}" if razao else "N/A"
        st.metric(label="Razão de Sexo (H/100 M)", value=val_razao)
        st.caption("Ano: 2022 | Fonte: IBGE — Censo Demográfico")

    st.divider()

    # Identificação territorial estruturada
    render_territorial_kpis(df_hierarquia)
    st.divider()

    # Tabela de Resumo Consolidado Socioeconômico
    if not df_resumo.empty:
        st.subheader("📑 Matriz Consolidada de Indicadores Oficiais")
        df_exibir = df_resumo[
            ["tema", "indicador", "valor", "unidade", "ano_referencia", "fonte_oficial"]
        ].rename(
            columns={
                "tema": "Tema",
                "indicador": "Indicador",
                "valor": "Valor",
                "unidade": "Unidade",
                "ano_referencia": "Ano",
                "fonte_oficial": "Fonte Oficial",
            }
        )
        st.dataframe(df_exibir, width="stretch", hide_index=True)

    st.divider()
    render_tabela_analitica(df_hierarquia)


# =============================================================================
# Aba 2 — Evolução Populacional
# =============================================================================


def render_tab_evolucao_populacional(df_pop: pd.DataFrame) -> None:
    """Renderiza a série histórica populacional com Plotly, filtros e avisos."""
    st.subheader("👥 Série Histórica da População de Mauá (SP)")

    if df_pop.empty:
        st.info("Nenhum dado de evolução populacional disponível no banco.")
        return

    # Garante ordenação cronológica
    df_sorted = df_pop.sort_values(by="ano_referencia").reset_index(drop=True)
    anos_disponiveis = sorted(df_sorted["ano_referencia"].unique().tolist())
    min_ano, max_ano = int(min(anos_disponiveis)), int(max(anos_disponiveis))

    col_filtro, _ = st.columns([2, 1])
    with col_filtro:
        intervalo_anos = st.slider(
            "Selecione o intervalo de anos para análise:",
            min_value=min_ano,
            max_value=max_ano,
            value=(min_ano, max_ano),
            step=1,
        )

    # Filtragem pelo intervalo selecionado
    df_filtrado = df_sorted[
        (df_sorted["ano_referencia"] >= intervalo_anos[0])
        & (df_sorted["ano_referencia"] <= intervalo_anos[1])
    ].copy()

    if df_filtrado.empty:
        st.warning("Nenhum registro para o intervalo selecionado.")
        return

    # Métricas do período filtrado
    pop_inicial = df_filtrado.iloc[0]["populacao"]
    ano_inicial = int(df_filtrado.iloc[0]["ano_referencia"])
    pop_final = df_filtrado.iloc[-1]["populacao"]
    ano_final = int(df_filtrado.iloc[-1]["ano_referencia"])

    var_abs = pop_final - pop_inicial
    var_pct = ((pop_final - pop_inicial) / pop_inicial) * 100.0 if pop_inicial else 0.0

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric(
            label=f"População Inicial ({ano_inicial})",
            value=f"{pop_inicial:,.0f}".replace(",", "."),
        )
    with mc2:
        st.metric(
            label=f"População Final ({ano_final})",
            value=f"{pop_final:,.0f}".replace(",", "."),
        )
    with mc3:
        st.metric(
            label="Variação Absoluta no Período",
            value=f"{var_abs:+,.0f}".replace(",", "."),
        )
    with mc4:
        st.metric(
            label="Variação Percentual Acumulada",
            value=f"{var_pct:+.2f}%",
        )

    # Gráfico interativo com Plotly Express
    fig_pop = px.line(
        df_filtrado,
        x="ano_referencia",
        y="populacao",
        color="tipo_populacao",
        markers=True,
        title="Evolução Populacional de Mauá: Censo vs Estimativas (2001–2026)",
        labels={
            "ano_referencia": "Ano de Referência",
            "populacao": "População Residente",
            "tipo_populacao": "Tipo de Dado",
        },
        color_discrete_map={
            "Censo Demográfico": "#e65100",
            "Estimativa de População": "#1976d2",
        },
    )
    fig_pop.update_traces(
        line={"width": 3},
        marker={"size": 9},
    )
    fig_pop.update_layout(
        yaxis_title="Habitantes",
        xaxis={"tickmode": "linear", "dtick": 2},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        hovermode="x unified",
    )
    st.plotly_chart(fig_pop, width="stretch")

    # Alerta Metodológico Oficial
    st.info(
        "ℹ️ **Nota Metodológica Oficial do IBGE:**\n"
        "- **Diferença de Fontes:** As *Estimativas de População* resultam de "
        "projeções matemáticas anuais, enquanto o *Censo Demográfico* realiza "
        "recenseamento completo dos domicílios. Em decorrência do intervalo "
        "entre censos (2010 a 2022), pode haver ajuste de patamar.\n"
        "- **Continuidade:** Variações entre anos não consecutivos ou entre "
        "metodologias distintas não devem ser interpretadas como taxa "
        "anualizada de crescimento. A coluna `flag_anos_consecutivos` indica "
        "comparações de anos sequenciais."
    )

    # Tabela detalhada
    with st.expander("📋 Ver Tabela Detalhada da Série Histórica"):
        tabela_pop = df_filtrado[
            [
                "ano_referencia",
                "populacao",
                "tipo_populacao",
                "variacao_absoluta_anterior",
                "variacao_percentual_anterior",
                "flag_anos_consecutivos",
                "fonte_oficial",
            ]
        ].rename(
            columns={
                "ano_referencia": "Ano",
                "populacao": "População",
                "tipo_populacao": "Fonte/Tipo",
                "variacao_absoluta_anterior": "Var. Absoluta",
                "variacao_percentual_anterior": "Var. %",
                "flag_anos_consecutivos": "Anos Consecutivos?",
                "fonte_oficial": "Fonte Oficial",
            }
        )
        st.dataframe(tabela_pop, width="stretch", hide_index=True)

        csv_pop = tabela_pop.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar Série Histórica de População (CSV)",
            data=csv_pop,
            file_name="ibge_maua_populacao_historica.csv",
            mime="text/csv",
        )


# =============================================================================
# Aba 3 — Economia: PIB e PIB per capita
# =============================================================================


def render_tab_economia_pib(df_pib: pd.DataFrame) -> None:
    """Renderiza a série histórica de PIB e VAB setorial com notas e gráficos."""
    st.subheader("💰 Indicadores Econômicos: PIB e Contas Regionais")

    if df_pib.empty:
        st.info("Nenhum dado de PIB disponível no banco.")
        return

    df_sorted = df_pib.sort_values(by="ano_referencia").reset_index(drop=True)
    anos_pib = sorted(df_sorted["ano_referencia"].unique().tolist())
    min_ano_pib, max_ano_pib = int(min(anos_pib)), int(max(anos_pib))

    col_filtro, _ = st.columns([2, 1])
    with col_filtro:
        intervalo_pib = st.slider(
            "Selecione o intervalo de anos para análise econômica:",
            min_value=min_ano_pib,
            max_value=max_ano_pib,
            value=(min_ano_pib, max_ano_pib),
            step=1,
            key="slider_pib",
        )

    df_filtrado = df_sorted[
        (df_sorted["ano_referencia"] >= intervalo_pib[0])
        & (df_sorted["ano_referencia"] <= intervalo_pib[1])
    ].copy()

    # Identificação do último registro com PIB corrente válido
    df_pib_valid = df_filtrado.dropna(subset=["pib_corrente_mil_reais"])
    if not df_pib_valid.empty:
        pib_ini = df_pib_valid.iloc[0]["pib_corrente_mil_reais"]
        ano_pib_ini = int(df_pib_valid.iloc[0]["ano_referencia"])
        pib_fim = df_pib_valid.iloc[-1]["pib_corrente_mil_reais"]
        ano_pib_fim = int(df_pib_valid.iloc[-1]["ano_referencia"])

        var_nom_pct = ((pib_fim - pib_ini) / pib_ini) * 100.0 if pib_ini else 0.0
        pib_fim_bi = (pib_fim * 1000.0) / 1e9

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                label=f"PIB Corrente ({ano_pib_fim})",
                value=f"R$ {pib_fim_bi:.2f} Bi",
            )
        with c2:
            st.metric(
                label=f"Crescimento Nominal Acumulado ({ano_pib_ini}–{ano_pib_fim})",
                value=f"{var_nom_pct:+.2f}%",
            )
        with c3:
            df_pc_valid = df_filtrado.dropna(subset=["pib_per_capita_reais"])
            if not df_pc_valid.empty:
                pc_fim = df_pc_valid.iloc[-1]["pib_per_capita_reais"]
                ano_pc_fim = int(df_pc_valid.iloc[-1]["ano_referencia"])
                st.metric(
                    label=f"PIB per capita ({ano_pc_fim})",
                    value=f"R$ {pc_fim:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", "."),
                )

    # Nota Metodológica Explicativa sobre Preços Correntes vs Reais
    st.warning(
        "⚠️ **Aviso Metodológico — Preços Correntes (Crescimento Nominal):**\n"
        "Os dados divulgados pelo IBGE nas Contas Regionais estão expressos a "
        "**preços correntes**. O crescimento nominal reflete tanto o aumento na "
        "produção de riquezas quanto a variação dos níveis de preços (inflação "
        "acumulada). Não representam o crescimento econômico real deflacionado."
    )

    # Gráficos de PIB e PIB per capita
    gcol1, gcol2 = st.columns(2)

    with gcol1:
        fig_pib = px.line(
            df_filtrado.dropna(subset=["pib_corrente_mil_reais"]),
            x="ano_referencia",
            y="pib_corrente_mil_reais",
            markers=True,
            title="Evolução do PIB a Preços Correntes (Mil Reais)",
            labels={
                "ano_referencia": "Ano",
                "pib_corrente_mil_reais": "PIB (Mil R$)",
            },
            color_discrete_sequence=["#2e7d32"],
        )
        fig_pib.update_layout(yaxis_title="Mil R$", hovermode="x unified")
        st.plotly_chart(fig_pib, width="stretch")

    with gcol2:
        df_plot_pc = df_filtrado.dropna(subset=["pib_per_capita_reais"])
        fig_pc = px.line(
            df_plot_pc,
            x="ano_referencia",
            y="pib_per_capita_reais",
            markers=True,
            title="Evolução do PIB per capita (Reais)",
            labels={
                "ano_referencia": "Ano",
                "pib_per_capita_reais": "PIB per capita (R$)",
            },
            color_discrete_sequence=["#0288d1"],
        )
        fig_pc.update_layout(yaxis_title="R$ correntes", hovermode="x unified")
        st.plotly_chart(fig_pc, width="stretch")

    # Gráfico de Composição Setorial do VAB (2002–2021)
    df_vab = df_filtrado.dropna(subset=["vab_total_mil_reais"]).copy()
    if not df_vab.empty:
        st.subheader("🏭 Composição Setorial do Valor Adicionado Bruto (VAB)")
        st.caption(
            "Evolução da contribuição dos setores econômicos (Agropecuária, Indústria, "
            "Serviços e Administração Pública) para a economia de Mauá."
        )

        vab_long = pd.melt(
            df_vab,
            id_vars=["ano_referencia"],
            value_vars=[
                "vab_agropecuaria_mil_reais",
                "vab_industria_mil_reais",
                "vab_servicos_mil_reais",
                "vab_administracao_publica_mil_reais",
            ],
            var_name="Setor",
            value_name="Valor_Mil_Reais",
        )
        vab_labels = {
            "vab_agropecuaria_mil_reais": "Agropecuária",
            "vab_industria_mil_reais": "Indústria",
            "vab_servicos_mil_reais": "Serviços (Exceto Adm. Pública)",
            "vab_administracao_publica_mil_reais": "Administração Pública",
        }
        vab_long["Setor"] = vab_long["Setor"].map(vab_labels)

        fig_vab = px.bar(
            vab_long,
            x="ano_referencia",
            y="Valor_Mil_Reais",
            color="Setor",
            title="Valor Adicionado Bruto (VAB) por Setor de Atividade Econômica",
            labels={
                "ano_referencia": "Ano",
                "Valor_Mil_Reais": "VAB (Mil R$)",
                "Setor": "Setor Econômico",
            },
            barmode="stack",
            color_discrete_sequence=["#8bc34a", "#ff9800", "#3f51b5", "#009688"],
        )
        fig_vab.update_layout(hovermode="x unified", yaxis_title="Mil R$")
        st.plotly_chart(fig_vab, width="stretch")

    with st.expander("📋 Ver Dados Econômicos Completos"):
        st.dataframe(df_filtrado, width="stretch", hide_index=True)
        csv_pib = df_filtrado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar Dados de PIB e VAB (CSV)",
            data=csv_pib,
            file_name="ibge_maua_pib_historico.csv",
            mime="text/csv",
        )


# =============================================================================
# Aba 4 — Demografia e Alfabetização
# =============================================================================


def render_tab_demografia_alfabetizacao(
    df_demografia: pd.DataFrame,
    kpis_socio: dict[str, Any],
) -> None:
    """Renderiza a estrutura demográfica por sexo, razão de sexo e alfabetização."""
    st.subheader("📊 Perfil Demográfico e Censitário — Censo 2022")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        razao = kpis_socio.get("razao_sexo")
        val_razao = f"{razao:.2f}" if razao is not None else "N/A"
        st.metric(label="Razão de Sexo Oficial", value=val_razao)
        st.caption("92,82 homens para cada 100 mulheres (Censo 2022)")

    with col2:
        alfab = kpis_socio.get("taxa_alfabetizacao_pct")
        val_alfab = f"{alfab:.2f}%" if alfab is not None else "N/A"
        st.metric(label="Taxa de Alfabetização", value=val_alfab)
        st.caption("População com 15 anos ou mais de idade")

    with col3:
        area = kpis_socio.get("area_territorial_km2")
        val_area = f"{area:.3f} km²" if area is not None else "N/A"
        st.metric(label="Área Territorial Oficial", value=val_area)
        st.caption("Resolução IBGE — Malha Municipal")

    with col4:
        dens = kpis_socio.get("densidade_demografica")
        val_dens = (
            f"{dens:,.2f} hab/km²".replace(",", "X").replace(".", ",").replace("X", ".")
            if dens is not None
            else "N/A"
        )
        st.metric(
            label="Densidade Demográfica",
            value=val_dens,
        )
        st.caption("Habitantes por quilômetro quadrado")

    st.divider()

    # Visualização da Distribuição Populacional por Sexo
    if df_demografia.empty:
        st.info("Nenhum registro de distribuição por sexo disponível no banco.")
        return

    row_demo = df_demografia.iloc[0]
    pop_masc = int(row_demo.get("populacao_masculina", 0))
    pop_fem = int(row_demo.get("populacao_feminina", 0))
    part_masc = float(row_demo.get("participacao_masculina_pct", 48.14))
    part_fem = float(row_demo.get("participacao_feminina_pct", 51.86))
    razao_val = float(row_demo.get("razao_sexo", 92.82))

    c_chart1, c_chart2 = st.columns(2)

    with c_chart1:
        df_sexo_chart = pd.DataFrame(
            [
                {
                    "Sexo": "Homens",
                    "População": pop_masc,
                    "Participação": f"{part_masc:.2f}%",
                },
                {
                    "Sexo": "Mulheres",
                    "População": pop_fem,
                    "Participação": f"{part_fem:.2f}%",
                },
            ]
        )
        fig_sexo = px.pie(
            df_sexo_chart,
            names="Sexo",
            values="População",
            hole=0.45,
            title="Distribuição da População por Sexo (Censo 2022)",
            color="Sexo",
            color_discrete_map={"Homens": "#1565c0", "Mulheres": "#ad1457"},
        )
        fig_sexo.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="%{label}: %{value:,.0f} pessoas (%{percent})",
        )
        st.plotly_chart(fig_sexo, width="stretch")

    with c_chart2:
        fig_bar_sexo = px.bar(
            df_sexo_chart,
            x="Sexo",
            y="População",
            color="Sexo",
            text="População",
            title="População Residente Absoluta por Sexo",
            color_discrete_map={"Homens": "#1565c0", "Mulheres": "#ad1457"},
        )
        fig_bar_sexo.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
        )
        fig_bar_sexo.update_layout(yaxis_title="Habitantes", showlegend=False)
        st.plotly_chart(fig_bar_sexo, width="stretch")

    st.info(
        "📌 **Interpretação Demográfica:**\n"
        f"- **População Masculina:** {pop_masc:,.0f} hab. ({part_masc:.2f}%).\n"
        f"- **População Feminina:** {pop_fem:,.0f} hab. ({part_fem:.2f}%).\n"
        f"- **Excedente Feminino:** Há {pop_fem - pop_masc:,.0f} mulheres a mais "
        f"que homens em Mauá (Razão de Sexo = **{razao_val:.2f}**), "
        "padrão demográfico característico das regiões metropolitanas."
    )


# =============================================================================
# Aba 5 — Governança e Auditoria
# =============================================================================


def render_tab_governanca_auditoria(
    kpis_dq: dict[str, Any],
    df_auditoria: pd.DataFrame,
    df_volumetria: pd.DataFrame,
    metadados_gov: dict[str, Any] | None = None,
) -> None:
    """Renderiza a aba de governança com auditoria, linhagem e contagens SQLite."""
    st.subheader("🛡️ Governança, Linhagem e Qualidade de Dados (Medallion)")

    if metadados_gov is None:
        metadados_gov = load_metadados_governanca()

    # Se df_volumetria não tiver a coluna 'camada', recarrega a volumetria
    if df_volumetria.empty or "camada" not in df_volumetria.columns:
        df_volumetria = load_volumetria_governanca()

    # 1. Alerta Metodológico Oficial de Granularidade
    st.info(
        "ℹ️ **Aviso Metodológico de Granularidade e Governança:**\n"
        "As contagens volumétricas das tabelas e views no SQLite representam "
        "granularidades distintas conforme a camada e domínio:\n"
        "- **Territorial:** 1 registro por município (Mauá — SP);\n"
        "- **População:** 1 registro por ano de referência (Censo 2022 e "
        "Estimativas 2001–2026);\n"
        "- **PIB e Contas Regionais:** múltiplos registros por indicador econômico e "
        "setor do VAB em cada ano;\n"
        "- **Censitário:** 1 registro por variável demográfica (sexo, alfabetização, "
        "área, densidade).\n\n"
        "Os totais de linhas quantificam o volume físico de fatos, séries e "
        "dimensões armazenados, **não devendo ser somados para representar "
        "quantidade de municípios**."
    )

    # 2. Cards de Resumo Global de Volumetria por Camada
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Total Camada Bronze",
            value=f"{metadados_gov.get('total_bronze', 0):,}".replace(",", "."),
        )
        st.caption("JSONs brutos oficiais persistidos")

    with col2:
        st.metric(
            label="Total Camada Silver",
            value=f"{metadados_gov.get('total_silver', 0):,}".replace(",", "."),
        )
        st.caption("Registros normalizados e tipados")

    with col3:
        st.metric(
            label="Total Camada Gold",
            value=f"{metadados_gov.get('total_gold', 0):,}".replace(",", "."),
        )
        st.caption("Registros em views analíticas")

    with col4:
        st.metric(
            label="Taxa de Conformidade",
            value=f"{kpis_dq.get('taxa_conformidade_pct', 0.0)}%",
        )
        st.caption("Qualidade de dados e integridade")

    # 3. Cards de Períodos Históricos Cobertos e Catálogo de Indicadores
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        p_min = metadados_gov.get("populacao_min_ano")
        p_max = metadados_gov.get("populacao_max_ano")
        val_pop = f"{p_min} a {p_max}" if p_min and p_max else "N/A"
        st.metric(label="Série Temporal de População", value=val_pop)
        st.caption(
            f"{metadados_gov.get('populacao_total_anos', 0)} anos cobertos "
            "(Censo 2022 e Projeções)"
        )

    with sc2:
        pib_min = metadados_gov.get("pib_min_ano")
        pib_max = metadados_gov.get("pib_max_ano")
        val_pib = f"{pib_min} a {pib_max}" if pib_min and pib_max else "N/A"
        st.metric(label="Série Temporal de PIB / VAB", value=val_pib)
        st.caption(
            f"{metadados_gov.get('pib_total_anos', 0)} anos cobertos (Contas Regionais)"
        )

    with sc3:
        st.metric(
            label="Indicadores Econômicos / VAB",
            value=metadados_gov.get("pib_total_indicadores", 0),
        )
        st.caption("Séries setoriais e agregados municipais")

    with sc4:
        st.metric(
            label="Indicadores Estratégicos (Gold)",
            value=metadados_gov.get("gold_total_indicadores", 0),
        )
        temas = ", ".join(metadados_gov.get("gold_temas", []))
        st.caption(f"Temas: {temas}" if temas else "Múltiplos temas")

    st.divider()

    # 4. Métricas de frescor e integridade
    render_governanca_qualidade(kpis_dq, df_auditoria)
    st.divider()

    # 5. Gráficos Analíticos de Governança
    render_graficos(kpis_dq, df_volumetria)
    st.divider()

    # 6. Volumetria Detalhada por Objeto (Tabelas Físicas e Views Analíticas)
    if not df_volumetria.empty:
        st.subheader("📦 Inventário e Volumetria de Objetos no SQLite")
        st.caption(
            "Detalhamento registro a registro de cada tabela e view "
            "da Medallion Architecture no banco relacional local."
        )

        col_filtro, _ = st.columns([2, 2])
        with col_filtro:
            filtro_camada = st.selectbox(
                "Filtrar objetos por Camada Medallion:",
                options=["Todas as Camadas", "Bronze", "Silver", "Gold"],
                index=0,
            )

        df_exibir = df_volumetria.copy()
        if filtro_camada != "Todas as Camadas":
            df_exibir = df_exibir[df_exibir["camada"] == filtro_camada]

        col_tabela, col_grafico = st.columns([1, 1])

        with col_tabela:
            cols_show = [
                c
                for c in [
                    "camada",
                    "objeto",
                    "tipo_objeto",
                    "dominio",
                    "total_registros",
                    "descricao_granularidade",
                ]
                if c in df_exibir.columns
            ]
            tabela_apresentacao = df_exibir[cols_show].rename(
                columns={
                    "camada": "Camada",
                    "objeto": "Objeto",
                    "tipo_objeto": "Tipo",
                    "dominio": "Domínio",
                    "total_registros": "Total Registros",
                    "descricao_granularidade": "Granularidade / Descrição",
                }
            )
            st.dataframe(tabela_apresentacao, width="stretch", hide_index=True)

            csv_vol = tabela_apresentacao.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Baixar Inventário de Governança (CSV)",
                data=csv_vol,
                file_name="ibge_maua_volumetria_governanca.csv",
                mime="text/csv",
            )

        with col_grafico:
            y_col = "objeto" if "objeto" in df_exibir.columns else df_exibir.columns[0]
            color_col = "dominio" if "dominio" in df_exibir.columns else "Tipo"
            fig_cont = px.bar(
                df_exibir,
                x="total_registros",
                y=y_col,
                color=color_col,
                orientation="h",
                text="total_registros",
                title=f"Volumetria por Objeto ({filtro_camada})",
                labels={
                    "total_registros": "Total de Registros",
                    "objeto": "Tabela / View",
                    "dominio": "Domínio",
                },
                color_discrete_map={
                    "Territorial": "#00897b",
                    "Socioeconômico": "#1e88e5",
                },
            )
            fig_cont.update_traces(textposition="outside")
            fig_cont.update_layout(yaxis={"autorange": "reversed"})
            st.plotly_chart(fig_cont, width="stretch")

    # 7. Quadro Informativo de Fontes e Metodologias Oficiais
    st.divider()
    st.subheader("📚 Catálogo Oficial de Fontes e Referências")
    st.markdown(
        """
        - **API de Localidades:** Divisão Territorial Brasileira (Vigente 2017/1989).
        - **Censo Demográfico 2022:** Recenseamento domiciliar universal.
        - **Estimativas de População:** Projeções demográficas anuais (2001–2026).
        - **Contas Regionais / PIB:** Contabilidade social municipal (1999–2023).
        """
    )


# =============================================================================
# Ponto de Entrada Principal da Aplicação
# =============================================================================


def main(db_path: Path | str | None = None) -> None:
    """Ponto de entrada principal da aplicação Streamlit."""
    st.set_page_config(
        page_title="IBGE Mauá — Dashboard Integrado",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    resolved_db_path = str(db_path or os.environ.get("IBGE_DB_PATH") or DEFAULT_DB_PATH)

    # Garante disponibilidade dos dados via snapshot versionado (sem rede)
    ensure_database_ready(resolved_db_path)

    render_header()
    render_sidebar(resolved_db_path)

    # Tratamento defensivo de ausência do banco ou erro operacional
    try:
        df_hierarquia = load_hierarquia_data(resolved_db_path)
        df_auditoria = load_auditoria_data(resolved_db_path)
        kpis_dq = load_kpis_qualidade(resolved_db_path)
        df_pop = load_populacao_historica_data(resolved_db_path)
        df_pib = load_pib_historico_data(resolved_db_path)
        df_demografia = load_demografia_sexo_data(resolved_db_path)
        df_resumo = load_resumo_socioeconomico_data(resolved_db_path)
        kpis_socio = load_kpis_socioeconomicos(resolved_db_path)
        df_volumetria = load_volumetria_governanca(resolved_db_path)
        metadados_gov = load_metadados_governanca(resolved_db_path)
    except Exception as exc:
        logger.exception("Falha ao consultar a camada analítica Gold: %s", exc)
        st.error(f"Erro ao inicializar ou consultar a camada Gold no SQLite: {exc}")
        return

    # Verificação de banco vazio
    if df_hierarquia.empty:
        st.warning(
            "⚠️ O banco SQLite local não possui registros na camada Gold.\n\n"
            "Por favor, execute o pipeline completo para visualizar o dashboard:\n"
            "```bash\n"
            "poetry run python -m desafio_ibge.main\n"
            "```"
        )
        return

    # 5 Abas Estruturadas
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "🗺️ Visão Geral",
            "👥 Evolução Populacional",
            "💰 Economia (PIB)",
            "📊 Demografia & Alfabetização",
            "🛡️ Governança & Auditoria",
        ]
    )

    with tab1:
        render_tab_visao_geral(df_hierarquia, kpis_socio, df_resumo)

    with tab2:
        render_tab_evolucao_populacional(df_pop)

    with tab3:
        render_tab_economia_pib(df_pib)

    with tab4:
        render_tab_demografia_alfabetizacao(df_demografia, kpis_socio)

    with tab5:
        render_tab_governanca_auditoria(
            kpis_dq, df_auditoria, df_volumetria, metadados_gov
        )


if __name__ == "__main__":
    main()
