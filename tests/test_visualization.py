"""Testes unitários e de integração para o Dashboard Streamlit."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from desafio_ibge.config.settings import MAUA_IBGE_CODE
from desafio_ibge.loading.storage import (
    init_db,
    save_bronze,
    save_silver,
)
from desafio_ibge.transformation.normalizer import json_to_dataframe
from desafio_ibge.visualization.app import (
    load_auditoria_data,
    load_hierarquia_data,
    load_kpis_geograficos,
    load_kpis_qualidade,
    main,
    render_governanca_qualidade,
    render_graficos,
    render_header,
    render_sidebar,
    render_tabela_analitica,
    render_territorial_kpis,
)


@pytest.fixture
def populated_db_path(tmp_path: Path, maua_raw_payload: dict[str, Any]) -> Path:
    """Cria um banco SQLite temporário populado com o registro de Mauá (SP)."""
    db_file = tmp_path / "test_populated.db"
    init_db(db_path=db_file)

    url = (
        "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/"
        f"{MAUA_IBGE_CODE}"
    )
    save_bronze(maua_raw_payload, endpoint_url=url, db_path=db_file)
    df_maua = json_to_dataframe(maua_raw_payload)
    save_silver(df_maua, db_path=db_file)
    return db_file


@pytest.fixture
def empty_db_path(tmp_path: Path) -> Path:
    """Cria um banco SQLite temporário inicializado, porém sem dados."""
    db_file = tmp_path / "test_empty.db"
    init_db(db_path=db_file)
    return db_file


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


# ---------------------------------------------------------------------------
# Testes Unitários dos Componentes Visuais
# ---------------------------------------------------------------------------


def test_render_territorial_kpis_with_data(populated_db_path: Path) -> None:
    """Testa renderização das métricas territoriais sem levantar exceções."""
    df = load_hierarquia_data(str(populated_db_path))
    # Execução direta dentro de contexto de teste
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


def test_render_graficos_plotly(populated_db_path: Path) -> None:
    """Valida a construção e renderização dos gráficos Plotly."""
    db_str = str(populated_db_path)
    kpis = load_kpis_qualidade(db_str)
    render_graficos(kpis)


def test_render_header_and_sidebar() -> None:
    """Testa componentes estruturais de cabeçalho e barra lateral."""
    render_header()
    render_sidebar("dummy_path/test.db")


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
    # Verifica que o alerta de banco sem dados foi exibido
    assert len(at.warning) > 0
    warning_texts = " ".join([w.value for w in at.warning])
    assert "não possui registros" in warning_texts


def test_apptest_populated_database(
    populated_db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa o ciclo de vida do app com dados completos de Mauá carregados."""
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
    # Título principal renderizado
    assert len(at.title) > 0
    assert "Desafio IBGE" in at.title[0].value

    # Cards de métricas renderizados
    assert len(at.metric) >= 4
    metric_labels = [m.label for m in at.metric]
    assert "Município" in metric_labels
    assert "Estado (UF)" in metric_labels

    # Abas e tabelas renderizadas
    assert len(at.tabs) > 0
    assert len(at.dataframe) > 0


def test_main_error_handling_graceful() -> None:
    """Verifica que erro na consulta ao banco exibe st.error sem derrubar o app."""
    with patch(
        "desafio_ibge.visualization.app.load_hierarquia_data",
        side_effect=RuntimeError("Falha de I/O forçada"),
    ):
        # Execução direta de main() com mock de erro
        main("dummy_corrupted.db")
