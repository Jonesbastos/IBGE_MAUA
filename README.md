# Desafio IBGE — Engenharia de Dados (Mauá - SP)

Pipeline de Engenharia de Dados desenvolvido em Python utilizando dados oficiais do IBGE sobre o município de **Mauá (SP)** (Código IBGE: `3529401`), implementado com arquitetura modular, **Medallion Architecture (Bronze, Silver e Gold)** no **SQLite**, e interface analítica em **Streamlit** e **Plotly**.

## 1. Tecnologias Utilizadas

- **Python**: 3.13.13 gerenciado via Pyenv.
- **Poetry**: Gerenciamento estrito de ambiente virtual e dependências.
- **Requests**: Extração resiliente com retries exponenciais e timeout.
- **Pydantic v2**: Validação estrita de contratos de dados (Data Quality).
- **Pandas**: Achatamento de JSONs aninhados e normalização tabular em `snake_case`.
- **SQLite**: Banco de dados relacional local com persistência Medalhão e Views analíticas.
- **Streamlit & Plotly**: Dashboard interativo de visualização e governança.
- **Ruff & Pytest**: Qualidade de código, linting e cobertura $\ge 50\%$ (atualmente $>98\%$).
- **MkDocs Material**: Documentação técnica estruturada e hospedada localmente.

## 2. Como Executar

### 2.1. Instalação do Ambiente
```powershell
poetry install
```

### 2.2. Executar o Dashboard Streamlit
```powershell
poetry run streamlit run src/desafio_ibge/visualization/app.py
# ou
poetry run task dashboard
```

### 2.3. Executar Testes Automatizados e Cobertura
```powershell
poetry run pytest --cov=desafio_ibge --cov-fail-under=50
```

### 2.4. Visualizar Documentação MkDocs
```powershell
poetry run task docs
```
