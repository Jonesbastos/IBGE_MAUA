"""Dashboard Interativo do projeto desafio_IBGE em Streamlit & Plotly.

Consome os dados modelados da camada Gold no banco SQLite, apresentando
a hierarquia territorial do município de Mauá (SP) e as métricas de
governança e Data Quality da Medallion Architecture.
"""

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from desafio_ibge.config.settings import (
    DEFAULT_DB_PATH,
    IBGE_BASE_URL,
    MAUA_DIRECT_URL,
    MAUA_IBGE_CODE,
)
from desafio_ibge.loading import (
    get_kpis_geograficos,
    get_kpis_qualidade,
    read_gold_auditoria,
    read_gold_hierarquia,
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


def render_header() -> None:
    """Renderiza cabeçalho, introdução e metadados oficiais do projeto."""
    st.title("🗺️ Desafio IBGE — Análise Territorial & Governança")
    st.caption(
        "Engenharia de Dados com Medallion Architecture (Bronze, Silver e Gold) "
        "sobre dados oficiais do IBGE para o município de Mauá — SP."
    )
    st.divider()


def render_sidebar(db_path_str: str) -> None:
    """Renderiza a barra lateral com status, fontes oficiais e controles."""
    with st.sidebar:
        st.header("⚙️ Painel de Controle")
        st.info(f"**Banco SQLite:** `{Path(db_path_str).name}`")

        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.subheader("📚 Metadados Oficiais")
        st.markdown(
            f"""
            - **Município:** Mauá (SP)
            - **Código IBGE:** `{MAUA_IBGE_CODE}`
            - **Fonte de Dados:** [API Localidades IBGE]({IBGE_BASE_URL})
            - **Endpoint Direto:** [Consulta Mauá]({MAUA_DIRECT_URL})
            - **Arquitetura:** Medalhão (Bronze -> Silver -> Gold)
            """
        )
        st.divider()
        st.caption("Desenvolvido com Python, SQLite, Streamlit & Plotly.")


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

    # Segunda linha de divisões regionais (Divisão 2017)
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
    st.subheader("📋 Tabela Analítica (Camada Gold)")

    if df.empty:
        st.info("A tabela analítica está vazia no momento.")
        return

    # Renomeia colunas para visualização amigável
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

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Botão para exportação dos dados da visualização
    csv_data = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Baixar Dados da Camada Gold (CSV)",
        data=csv_data,
        file_name="ibge_maua_gold.csv",
        mime="text/csv",
    )


def render_governanca_qualidade(
    kpis_dq: dict[str, Any],
    df_auditoria: pd.DataFrame,
) -> None:
    """Exibe painel de métricas de qualidade de dados (Data Quality) e auditoria."""
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

    # Informações de frescor e integridade
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

    # Exibição do relatório atômico de auditoria
    if not df_auditoria.empty:
        with st.expander("🔍 Ver Detalhes do Log de Auditoria SQL"):
            st.dataframe(df_auditoria, use_container_width=True, hide_index=True)


def render_graficos(kpis_dq: dict[str, Any]) -> None:
    """Gera visualizações interativas com Plotly Express baseadas nos dados reais."""
    st.subheader("📊 Visualizações Analíticas")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        # Gráfico 1: Volume de Registros por Camada Medalhão
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
        st.plotly_chart(fig_camadas, use_container_width=True)

    with col_chart2:
        # Gráfico 2: Indicadores de Validação e Integridade
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
        st.plotly_chart(fig_dq, use_container_width=True)


def main(db_path: Path | str | None = None) -> None:
    """Ponto de entrada principal da aplicação Streamlit."""
    st.set_page_config(
        page_title="IBGE Mauá — Dashboard Territorial",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    resolved_db_path = str(db_path or os.environ.get("IBGE_DB_PATH") or DEFAULT_DB_PATH)

    render_header()
    render_sidebar(resolved_db_path)

    # Tratamento defensivo de ausência do banco ou erro operacional
    try:
        df_hierarquia = load_hierarquia_data(resolved_db_path)
        df_auditoria = load_auditoria_data(resolved_db_path)
        kpis_dq = load_kpis_qualidade(resolved_db_path)
    except Exception as exc:
        logger.exception("Falha ao consultar a camada analítica Gold: %s", exc)
        st.error(f"Erro ao inicializar ou consultar a camada Gold no SQLite: {exc}")
        return

    # Verificação de banco vazio
    if df_hierarquia.empty:
        st.warning(
            "⚠️ O banco SQLite local não possui registros na camada Gold.\n\n"
            "Por favor, execute a ingestão dos dados para visualizar o dashboard:\n"
            "```bash\n"
            'poetry run python -c "from desafio_ibge.extraction import '
            'get_municipio_maua; ..."\n'
            "```"
        )
        return

    # Renderização das seções estruturadas
    render_territorial_kpis(df_hierarquia)
    st.divider()

    tab_tabela, tab_dq, tab_graficos = st.tabs(
        [
            "📋 Tabela Analítica",
            "🛡️ Governança & Qualidade",
            "📊 Visualizações Gráficas",
        ]
    )

    with tab_tabela:
        render_tabela_analitica(df_hierarquia)

    with tab_dq:
        render_governanca_qualidade(kpis_dq, df_auditoria)

    with tab_graficos:
        render_graficos(kpis_dq)


if __name__ == "__main__":
    main()
