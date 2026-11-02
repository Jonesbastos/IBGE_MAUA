"""Testes unitários e de integração para o Dashboard Streamlit."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from desafio_ibge.config.settings import MAUA_IBGE_CODE
from desafio_ibge.visualization.app import (
    load_auditoria_data,
    load_demografia_sexo_data,
    load_hierarquia_data,
    load_kpis_geograficos,
    load_kpis_qualidade,
    load_kpis_socioeconomicos,
    load_metadados_governanca,
    load_pib_historico_data,
    load_populacao_historica_data,
    load_resumo_socioeconomico_data,
    load_tabelas_contagem,
    load_volumetria_governanca,
    main,
    render_governanca_qualidade,
    render_graficos,
    render_header,
    render_sidebar,
    render_tab_demografia_alfabetizacao,
    render_tab_economia_pib,
    render_tab_evolucao_populacional,
    render_tab_governanca_auditoria,
    render_tab_visao_geral,
    render_tabela_analitica,
    render_territorial_kpis,
)

# ---------------------------------------------------------------------------
# Testes de Carga de Dados e Cache
# ---------------------------------------------------------------------------


def test_load_functions_with_populated_database(populated_db_path: Path) -> None:
    """Verifica que as funções de carregamento retornam os dados esperados de Mauá."""
    db_str = str(populated_db_path)

    df_hierarquia = load_hierarquia_data(db_str)
    assert not df_hierarquia.empty
    assert len(df_hierarquia) == 1
    assert df_hierarquia.iloc[0]["municipio_id"] == MAUA_IBGE_CODE
    assert df_hierarquia.iloc[0]["municipio_nome"] == "Mauá"

    df_auditoria = load_auditoria_data(db_str)
    assert not df_auditoria.empty
    assert df_auditoria.iloc[0]["status_integracao"] == "CONFORME"

    kpis_geo = load_kpis_geograficos(db_str)
    assert kpis_geo["total_municipios"] == 1
    assert kpis_geo["municipios_por_uf"] == {"SP": 1}

    kpis_dq = load_kpis_qualidade(db_str)
    assert kpis_dq["taxa_conformidade_pct"] == 100.0
    assert kpis_dq["total_conforme"] == 1


def test_load_functions_with_fully_populated_database(
    fully_populated_db_path: Path,
) -> None:
    """Verifica carregamento de dados nas 4 novas views socioeconômicas."""
    db_str = str(fully_populated_db_path)

    df_pop = load_populacao_historica_data(db_str)
    assert len(df_pop) == 2

    df_pib = load_pib_historico_data(db_str)
    assert len(df_pib) == 2

    df_demo = load_demografia_sexo_data(db_str)
    assert len(df_demo) == 1
    assert df_demo.iloc[0]["populacao_masculina"] == 201348

    df_resumo = load_resumo_socioeconomico_data(db_str)
    assert not df_resumo.empty

    kpis_socio = load_kpis_socioeconomicos(db_str)
    assert kpis_socio["populacao_censo_2022"] == 418261
    assert kpis_socio["taxa_alfabetizacao_pct"] == 96.74

    df_contagens = load_tabelas_contagem(db_str)
    assert not df_contagens.empty
    assert "Nome do Objeto" in df_contagens.columns

    df_vol = load_volumetria_governanca(db_str)
    assert not df_vol.empty
    assert "dominio" in df_vol.columns
    assert "descricao_granularidade" in df_vol.columns
    assert set(df_vol["camada"]) == {"Bronze", "Silver", "Gold"}

    meta_gov = load_metadados_governanca(db_str)
    assert meta_gov["total_bronze"] >= 1
    assert meta_gov["total_silver"] >= 4
    assert meta_gov["total_gold"] >= 2


def test_load_functions_with_empty_database(empty_db_path: Path) -> None:
    """Verifica comportamento das funções de carga quando o banco está sem registros."""
    db_str = str(empty_db_path)

    df_hierarquia = load_hierarquia_data(db_str)
    assert isinstance(df_hierarquia, pd.DataFrame)
    assert df_hierarquia.empty

    df_auditoria = load_auditoria_data(db_str)
    assert isinstance(df_auditoria, pd.DataFrame)
    assert df_auditoria.empty

    kpis_geo = load_kpis_geograficos(db_str)
    assert kpis_geo["total_municipios"] == 0

    kpis_dq = load_kpis_qualidade(db_str)
    assert kpis_dq["total_registros_auditados"] == 0
    assert kpis_dq["taxa_conformidade_pct"] == 0.0

    df_pop = load_populacao_historica_data(db_str)
    assert df_pop.empty

    df_pib = load_pib_historico_data(db_str)
    assert df_pib.empty

    df_demo = load_demografia_sexo_data(db_str)
    assert df_demo.empty

    df_resumo = load_resumo_socioeconomico_data(db_str)
    assert df_resumo.empty

    kpis_socio = load_kpis_socioeconomicos(db_str)
    assert kpis_socio["populacao_censo_2022"] is None

    df_cont = load_tabelas_contagem(db_str)
    assert not df_cont.empty


def test_load_tabelas_contagem_nonexistent_path(tmp_path: Path) -> None:
    """Testa inventário de tabelas com caminho de banco inexistente."""
    fake_path = tmp_path / "non_existent.db"
    df = load_tabelas_contagem(str(fake_path))
    assert df.empty
    assert list(df.columns) == ["Tipo", "Nome do Objeto", "Total Registros"]


# ---------------------------------------------------------------------------
# Testes Unitários dos Componentes Visuais
# ---------------------------------------------------------------------------


def test_render_territorial_kpis_with_data(populated_db_path: Path) -> None:
    """Testa renderização das métricas territoriais sem levantar exceções."""
    df = load_hierarquia_data(str(populated_db_path))
    render_territorial_kpis(df)


def test_render_territorial_kpis_empty() -> None:
    """Testa renderização defensiva com DataFrame vazio."""
    render_territorial_kpis(pd.DataFrame())


def test_render_tabela_analitica_with_data(populated_db_path: Path) -> None:
    """Testa renderização da tabela analítica com dados reais."""
    df = load_hierarquia_data(str(populated_db_path))
    render_tabela_analitica(df)


def test_render_tabela_analitica_empty() -> None:
    """Testa renderização da tabela quando vazia."""
    render_tabela_analitica(pd.DataFrame())


def test_render_governanca_qualidade(populated_db_path: Path) -> None:
    """Testa exibição de governança e métricas de qualidade."""
    db_str = str(populated_db_path)
    kpis = load_kpis_qualidade(db_str)
    df_audit = load_auditoria_data(db_str)
    render_governanca_qualidade(kpis, df_audit)


def test_render_graficos_plotly(fully_populated_db_path: Path) -> None:
    """Valida a construção e renderização dos gráficos Plotly com e sem volumetria."""
    db_str = str(fully_populated_db_path)
    kpis = load_kpis_qualidade(db_str)
    df_vol = load_volumetria_governanca(db_str)

    # Chamada tradicional (com kpis_dq apenas)
    render_graficos(kpis)

    # Chamada enriquecida (com kpis_dq e df_volumetria)
    render_graficos(kpis, df_vol)

    # Chamada com volumetria vazia
    render_graficos(kpis, pd.DataFrame())


def test_render_header_and_sidebar() -> None:
    """Testa componentes estruturais de cabeçalho e barra lateral."""
    render_header()
    render_sidebar("dummy_path/test.db")


# ---------------------------------------------------------------------------
# Testes Unitários das Novas Abas
# ---------------------------------------------------------------------------


def test_render_tab_visao_geral(fully_populated_db_path: Path) -> None:
    """Valida renderização da Aba 1 com dados completos e vazios."""
    db_str = str(fully_populated_db_path)
    df_hierarquia = load_hierarquia_data(db_str)
    kpis_socio = load_kpis_socioeconomicos(db_str)
    df_resumo = load_resumo_socioeconomico_data(db_str)

    # Com dados
    render_tab_visao_geral(df_hierarquia, kpis_socio, df_resumo)

    # Com dados vazios
    render_tab_visao_geral(pd.DataFrame(), {}, pd.DataFrame())


def test_render_tab_evolucao_populacional(fully_populated_db_path: Path) -> None:
    """Valida renderização da Aba 2 com série histórica e vazia."""
    db_str = str(fully_populated_db_path)
    df_pop = load_populacao_historica_data(db_str)

    render_tab_evolucao_populacional(df_pop)
    render_tab_evolucao_populacional(pd.DataFrame())


def test_render_tab_economia_pib(fully_populated_db_path: Path) -> None:
    """Valida renderização da Aba 3 com dados de PIB, VAB e vazia."""
    db_str = str(fully_populated_db_path)
    df_pib = load_pib_historico_data(db_str)

    render_tab_economia_pib(df_pib)
    render_tab_economia_pib(pd.DataFrame())


def test_render_tab_demografia_alfabetizacao(fully_populated_db_path: Path) -> None:
    """Valida renderização da Aba 4 com dados censitários e vazia."""
    db_str = str(fully_populated_db_path)
    df_demo = load_demografia_sexo_data(db_str)
    kpis_socio = load_kpis_socioeconomicos(db_str)

    render_tab_demografia_alfabetizacao(df_demo, kpis_socio)
    render_tab_demografia_alfabetizacao(pd.DataFrame(), {})


def test_render_tab_governanca_auditoria(fully_populated_db_path: Path) -> None:
    """Valida renderização da Aba 5 com governança, volumetria e metadados."""
    db_str = str(fully_populated_db_path)
    kpis = load_kpis_qualidade(db_str)
    df_audit = load_auditoria_data(db_str)
    df_vol = load_volumetria_governanca(db_str)
    meta_gov = load_metadados_governanca(db_str)

    # Chamada completa com metadados
    render_tab_governanca_auditoria(kpis, df_audit, df_vol, meta_gov)

    # Chamada apenas com 3 parâmetros
    render_tab_governanca_auditoria(kpis, df_audit, df_vol)

    # Chamada com dados vazios
    render_tab_governanca_auditoria({}, pd.DataFrame(), pd.DataFrame(), {})


# ---------------------------------------------------------------------------
# Testes de Integração com Streamlit AppTest
# ---------------------------------------------------------------------------


def test_apptest_empty_database(
    empty_db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa o ciclo de vida completo do app quando o banco está vazio."""
    app_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "desafio_ibge"
        / "visualization"
        / "app.py"
    )

    monkeypatch.setenv("IBGE_DB_PATH", str(empty_db_path))
    at = AppTest.from_file(str(app_path)).run()
    assert not at.exception
    assert len(at.warning) > 0
    warning_texts = " ".join([w.value for w in at.warning])
    assert "não possui registros" in warning_texts


def test_apptest_populated_database(
    populated_db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa o ciclo de vida do app com dados territoriais de Mauá carregados."""
    app_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "desafio_ibge"
        / "visualization"
        / "app.py"
    )

    monkeypatch.setenv("IBGE_DB_PATH", str(populated_db_path))
    at = AppTest.from_file(str(app_path)).run()
    assert not at.exception
    assert len(at.title) > 0
    assert "Desafio IBGE" in at.title[0].value
    assert len(at.tabs) >= 5
    assert len(at.dataframe) > 0


def test_apptest_fully_populated_database(
    fully_populated_db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa ciclo de vida do app com dados socioeconômicos e territoriais completos."""
    app_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "desafio_ibge"
        / "visualization"
        / "app.py"
    )

    monkeypatch.setenv("IBGE_DB_PATH", str(fully_populated_db_path))
    at = AppTest.from_file(str(app_path)).run()
    assert not at.exception
    assert len(at.title) > 0
    assert "Desafio IBGE" in at.title[0].value

    # Confirmação das 5 Abas
    assert len(at.tabs) >= 5

    # Cards de métricas renderizados em abundância
    assert len(at.metric) >= 8

    # Gráficos e tabelas
    assert len(at.dataframe) >= 2


def test_main_error_handling_graceful() -> None:
    """Verifica que erro na consulta ao banco exibe st.error sem derrubar o app."""
    with patch(
        "desafio_ibge.visualization.app.load_hierarquia_data",
        side_effect=RuntimeError("Falha de I/O forçada"),
    ):
        main("dummy_corrupted.db")


def test_apptest_restores_from_snapshot_in_cloud_deploy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que o AppTest inicializa com sucesso em ambiente limpo de deploy."""
    app_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "desafio_ibge"
        / "visualization"
        / "app.py"
    )

    db_deploy = tmp_path / "deploy_simulated.db"
    assert not db_deploy.exists()

    monkeypatch.setenv("IBGE_DB_PATH", str(db_deploy))
    monkeypatch.setenv("IBGE_AUTO_RESTORE", "1")

    at = AppTest.from_file(str(app_path)).run()
    assert not at.exception
    assert db_deploy.exists()
    assert len(at.title) > 0
    assert "Desafio IBGE" in at.title[0].value
    assert len(at.tabs) >= 5
    assert len(at.metric) >= 8
