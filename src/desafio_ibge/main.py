"""Orquestrador principal do pipeline de Engenharia de Dados desafio_IBGE.

Coordena a execução unificada dos fluxos territorial e socioeconômico segundo
a Medallion Architecture:
Extração -> Validação -> Camada Bronze -> Camada Silver -> Camada Gold.
"""

import logging
import sys
import time
from pathlib import Path

from desafio_ibge.config.settings import (
    DEFAULT_DB_PATH,
    MAUA_DIRECT_URL,
    MAUA_IBGE_CODE,
)
from desafio_ibge.extraction.ibge_client import IBGEClient, IBGEExtractionError
from desafio_ibge.loading.storage import (
    IBGEStorageError,
    get_kpis_qualidade,
    get_kpis_socioeconomicos,
    init_db,
    read_gold_demografia_sexo,
    read_gold_hierarquia,
    read_gold_pib_historico,
    read_gold_populacao_historica,
    read_gold_resumo_socioeconomico,
    save_all_socioeconomico_bronze,
    save_all_socioeconomico_silver,
    save_bronze,
    save_silver,
)
from desafio_ibge.transformation.normalizer import (
    json_to_dataframe,
    transform_socioeconomico_from_bronze,
)
from desafio_ibge.validation.schema import (
    IBGEValidationError,
    validate_maua_payload,
)

logger = logging.getLogger("desafio_ibge.main")


def configure_logging(level: int = logging.INFO) -> None:
    """Configura o sistema de log para execução em linha de comando."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _run_territorial_flow(target_db: Path, client: IBGEClient) -> bool:
    """Executa o pipeline territorial (Localidades -> Bronze -> Silver -> Gold).

    Args:
        target_db: Caminho do banco SQLite de destino.
        client: Instância ativa do cliente IBGE.

    Returns:
        True em caso de sucesso absoluto, False se houver falhas.
    """
    logger.info("------------------------------------------------------------")
    logger.info("INICIANDO FLUXO 1: DADOS TERRITORIAIS (API DE LOCALIDADES)")
    logger.info("------------------------------------------------------------")
    t0 = time.perf_counter()

    # 1. Extração Territorial
    logger.info("[FLUXO 1 - ETAPA 1/5] Extraindo dados de Localidades do IBGE...")
    try:
        raw_payload = client.fetch_municipio_by_id(MAUA_IBGE_CODE)
        logger.info(
            "Extração territorial concluída: '%s' (ID %s).",
            raw_payload.get("nome"),
            raw_payload.get("id"),
        )
    except IBGEExtractionError as exc:
        logger.error("Falha na Extração Territorial: %s", exc)
        return False
    except Exception as exc:
        logger.exception("Erro inesperado na Extração Territorial: %s", exc)
        return False

    # 2. Validação Territorial
    logger.info("[FLUXO 1 - ETAPA 2/5] Validando contrato de dados Pydantic v2...")
    try:
        validated_schema = validate_maua_payload(raw_payload)
        logger.info(
            "Contrato territorial validado com sucesso: %s (ID %d).",
            validated_schema.nome,
            validated_schema.id,
        )
    except IBGEValidationError as exc:
        logger.error("Violação de contrato territorial: %s", exc)
        return False
    except Exception as exc:
        logger.exception("Erro inesperado na Validação Territorial: %s", exc)
        return False

    # 3. Bronze Territorial
    logger.info(
        "[FLUXO 1 - ETAPA 3/5] Persistindo dados brutos na Bronze Territorial..."
    )
    try:
        checksum = save_bronze(
            raw_payload=raw_payload,
            endpoint_url=MAUA_DIRECT_URL,
            http_status=200,
            db_path=target_db,
        )
        logger.info(
            "Bronze Territorial persistida. Hash SHA-256: %s...",
            checksum[:12],
        )
    except IBGEStorageError as exc:
        logger.error("Falha na Bronze Territorial: %s", exc)
        return False
    except Exception as exc:
        logger.exception("Erro inesperado na Bronze Territorial: %s", exc)
        return False

    # 4. Silver Territorial
    logger.info("[FLUXO 1 - ETAPA 4/5] Normalizando e persistindo na Silver...")
    try:
        df_silver = json_to_dataframe(validated_schema, validate=False)
        records_saved = save_silver(df=df_silver, db_path=target_db)
        logger.info(
            "Silver Territorial persistida: %d registro(s) normalizado(s).",
            records_saved,
        )
    except (IBGEValidationError, IBGEStorageError) as exc:
        logger.error("Falha na Silver Territorial: %s", exc)
        return False
    except Exception as exc:
        logger.exception("Erro inesperado na Silver Territorial: %s", exc)
        return False

    # 5. Gold Territorial & Auditoria
    logger.info("[FLUXO 1 - ETAPA 5/5] Auditando conciliação na Gold Territorial...")
    try:
        df_gold = read_gold_hierarquia(
            municipio_id=MAUA_IBGE_CODE,
            db_path=target_db,
        )
        if df_gold.empty:
            logger.error("View gold_vw_municipio_hierarquia vazia.")
            return False

        kpis = get_kpis_qualidade(db_path=target_db)
        taxa = kpis.get("taxa_conformidade_pct", 0.0)
        falhas = kpis.get("total_falhas_qualidade", 0)

        logger.info(
            "Auditoria Territorial Gold: Conformidade: %.2f%%, Falhas: %d, "
            "Latência Média: %s s.",
            taxa,
            falhas,
            kpis.get("latencia_media_segundos"),
        )
        if falhas > 0 or taxa < 100.0:
            logger.error("Inconsistência de qualidade na Gold Territorial.")
            return False
    except Exception as exc:
        logger.exception("Erro inesperado na auditoria Gold Territorial: %s", exc)
        return False

    dur = time.perf_counter() - t0
    logger.info("Fluxo 1 (Territorial) concluído com sucesso em %.2f s.", dur)
    return True


def _run_socioeconomico_flow(target_db: Path, client: IBGEClient) -> bool:
    """Executa o pipeline socioeconômico.

    Fluxo: Agregados/Pesquisas -> Bronze -> Silver -> Gold.

    Args:
        target_db: Caminho do banco SQLite de destino.
        client: Instância ativa do cliente IBGE.

    Returns:
        True em caso de sucesso absoluto, False se houver falhas.
    """
    logger.info("------------------------------------------------------------")
    logger.info("INICIANDO FLUXO 2: DADOS SOCIOECONÔMICOS (SIDRA & PESQUISAS)")
    logger.info("------------------------------------------------------------")
    t0 = time.perf_counter()

    # 1. Extração Socioeconômica
    logger.info("[FLUXO 2 - ETAPA 1/5] Extraindo séries do SIDRA v3 e Pesquisa 38...")
    try:
        socio_data = client.fetch_all_socioeconomico_maua()
        logger.info(
            "Extração socioeconômica concluída: %d indicador(es) coletado(s).",
            len(socio_data),
        )
    except IBGEExtractionError as exc:
        logger.error("Falha na Extração Socioeconômica: %s", exc)
        return False
    except Exception as exc:
        logger.exception("Erro inesperado na Extração Socioeconômica: %s", exc)
        return False

    # 2. Bronze Socioeconômica
    logger.info("[FLUXO 2 - ETAPA 2/5] Persistindo na Bronze Socioeconômica...")
    try:
        checksums = save_all_socioeconomico_bronze(
            socioeconomico_dict=socio_data,
            db_path=target_db,
        )
        logger.info(
            "Bronze Socioeconômica persistida: %d indicador(es) gravados.",
            len(checksums),
        )
    except IBGEStorageError as exc:
        logger.error("Falha na Bronze Socioeconômica: %s", exc)
        return False
    except Exception as exc:
        logger.exception("Erro inesperado na Bronze Socioeconômica: %s", exc)
        return False

    # 3. Transformação & Validação Silver Socioeconômica
    logger.info("[FLUXO 2 - ETAPA 3/5] Desaninhando e validando contratos Silver...")
    try:
        dfs_silver = transform_socioeconomico_from_bronze(
            db_path=target_db,
            validate=True,
        )
        pop_count = len(dfs_silver.get("populacao", []))
        pib_count = len(dfs_silver.get("pib", []))
        cen_count = len(dfs_silver.get("censitario", []))
        logger.info(
            "Normalização concluída com validação Pydantic aprovada: "
            "População: %d linhas, PIB: %d linhas, Censitário: %d linhas.",
            pop_count,
            pib_count,
            cen_count,
        )
    except (IBGEValidationError, IBGEStorageError) as exc:
        logger.error("Falha na validação/transformação Silver Socioeconômica: %s", exc)
        return False
    except Exception as exc:
        logger.exception(
            "Erro inesperado na transformação Silver Socioeconômica: %s", exc
        )
        return False

    # 4. Persistência Silver Socioeconômica
    logger.info("[FLUXO 2 - ETAPA 4/5] Persistindo tabelas da Silver Socioeconômica...")
    try:
        counts = save_all_socioeconomico_silver(
            dfs=dfs_silver,
            db_path=target_db,
        )
        logger.info("Silver Socioeconômica atualizada: %s.", counts)
    except IBGEStorageError as exc:
        logger.error("Falha na persistência da Silver Socioeconômica: %s", exc)
        return False
    except Exception as exc:
        logger.exception(
            "Erro inesperado na gravação da Silver Socioeconômica: %s", exc
        )
        return False

    # 5. Sincronização e Validação Gold Socioeconômica
    logger.info("[FLUXO 2 - ETAPA 5/5] Validando Views Analíticas da Camada Gold...")
    try:
        df_pop = read_gold_populacao_historica(MAUA_IBGE_CODE, db_path=target_db)
        df_pib = read_gold_pib_historico(MAUA_IBGE_CODE, db_path=target_db)
        df_sex = read_gold_demografia_sexo(MAUA_IBGE_CODE, db_path=target_db)
        df_res = read_gold_resumo_socioeconomico(MAUA_IBGE_CODE, db_path=target_db)
        kpis = get_kpis_socioeconomicos(MAUA_IBGE_CODE, db_path=target_db)

        if df_pop.empty or df_pib.empty or df_sex.empty or df_res.empty:
            logger.error("Uma ou mais views analíticas socioeconômicas estão vazias.")
            return False

        logger.info("Views Gold Socioeconômicas validadas com sucesso:")
        logger.info("  - gold_populacao_historica: %d registro(s)", len(df_pop))
        logger.info("  - gold_pib_historico: %d registro(s)", len(df_pib))
        logger.info("  - gold_demografia_sexo: %d registro(s)", len(df_sex))
        logger.info("  - gold_resumo_socioeconomico: %d registro(s)", len(df_res))
        logger.info(
            "  - KPIs: Censo 2022: %s | PIB 2023: %s | Razão Sexo: %s",
            kpis.get("populacao_censo_2022"),
            kpis.get("pib_corrente_mil_reais"),
            kpis.get("razao_sexo"),
        )
    except Exception as exc:
        logger.exception("Erro inesperado na validação Gold Socioeconômica: %s", exc)
        return False

    dur = time.perf_counter() - t0
    logger.info("Fluxo 2 (Socioeconômico) concluído com sucesso em %.2f s.", dur)
    return True


def run_pipeline(
    db_path: Path | str | None = None,
    client: IBGEClient | None = None,
) -> int:
    """Executa o pipeline completo de ponta a ponta com controle de falha.

    Coordena o Fluxo Territorial (Localidades) e o Fluxo Socioeconômico
    (Agregados e Pesquisas) garantindo integridade, idempotência e governança.

    Args:
        db_path: Caminho opcional para o banco SQLite (padrão: data/ibge_maua.db).
        client: Cliente HTTP opcional para injeção de dependência e testes.

    Returns:
        0 em caso de sucesso absoluto, 1 em caso de falha em qualquer etapa.
    """
    total_start = time.perf_counter()
    target_db = Path(db_path or DEFAULT_DB_PATH)

    logger.info("============================================================")
    logger.info("INICIANDO PIPELINE DE ENGENHARIA DE DADOS — DESAFIO IBGE")
    logger.info("Alvo: Município de Mauá (SP) | Código IBGE: %d", MAUA_IBGE_CODE)
    logger.info("Banco SQLite de Destino: %s", target_db)
    logger.info("Arquitetura: Medallion (Bronze -> Silver -> Gold)")
    logger.info("============================================================")

    # 1. Inicialização preventiva do schema do banco SQLite
    try:
        init_db(db_path=target_db)
    except Exception as exc:
        logger.exception("Falha crítica ao inicializar o banco SQLite: %s", exc)
        return 1

    # 2. Execução dos fluxos com controle de dependências (Fail-Fast)
    if client is not None:
        ok_territorial = _run_territorial_flow(target_db=target_db, client=client)
        if not ok_territorial:
            logger.error("Fluxo Territorial falhou. Pipeline interrompido.")
            return 1

        ok_socio = _run_socioeconomico_flow(target_db=target_db, client=client)
        if not ok_socio:
            logger.error("Fluxo Socioeconômico falhou. Pipeline interrompido.")
            return 1
    else:
        with IBGEClient() as active_client:
            ok_territorial = _run_territorial_flow(
                target_db=target_db, client=active_client
            )
            if not ok_territorial:
                logger.error("Fluxo Territorial falhou. Pipeline interrompido.")
                return 1

            ok_socio = _run_socioeconomico_flow(
                target_db=target_db, client=active_client
            )
            if not ok_socio:
                logger.error("Fluxo Socioeconômico falhou. Pipeline interrompido.")
                return 1

    total_duration = time.perf_counter() - total_start
    logger.info("============================================================")
    logger.info("PIPELINE CONCLUÍDO COM SUCESSO ABSOLUTO (STATUS: 100% OK)")
    logger.info("Duração total de processamento: %.2f segundos.", total_duration)
    logger.info("Dados prontos para consumo analítico e visualização.")
    logger.info("============================================================")
    return 0


def main() -> None:
    """Ponto de entrada de linha de comando para execução do pipeline."""
    configure_logging()
    exit_code = run_pipeline()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
