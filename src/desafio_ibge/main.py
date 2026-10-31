"""Orquestrador principal do pipeline de Engenharia de Dados desafio_IBGE.

Coordena a execução unificada das etapas do pipeline segundo a Medallion Architecture:
Extração -> Validação -> Camada Bronze -> Camada Silver -> Camada Gold.
"""

import logging
import sys
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
    init_db,
    read_gold_hierarquia,
    save_bronze,
    save_silver,
)
from desafio_ibge.transformation.normalizer import json_to_dataframe
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


def run_pipeline(
    db_path: Path | str | None = None,
    client: IBGEClient | None = None,
) -> int:
    """Executa o pipeline completo de dados de ponta a ponta com controle de falha.

    Sequência obrigatória:
    1. Extração: Coleta do payload bruto da API oficial do IBGE para Mauá (SP).
    2. Validação: Aferição de contratos de dados e Data Quality com Pydantic v2.
    3. Camada Bronze: Ingestão do JSON bruto com metadados e checksum SHA-256.
    4. Transformação & Camada Silver: Achatamento tabular e persistência relacional.
    5. Camada Gold & Auditoria: Validação analítica e cálculo de conformidade.

    Args:
        db_path: Caminho opcional para o banco SQLite (padrão: data/ibge_maua.db).
        client: Cliente HTTP opcional para injeção de dependência e testes.

    Returns:
        0 em caso de sucesso absoluto, 1 em caso de falha em qualquer etapa.
    """
    target_db = Path(db_path or DEFAULT_DB_PATH)
    logger.info("============================================================")
    logger.info("INICIANDO PIPELINE DE ENGENHARIA DE DADOS — DESAFIO IBGE")
    logger.info("Alvo: Município de Mauá (SP) | Código IBGE: %d", MAUA_IBGE_CODE)
    logger.info("Banco SQLite de Destino: %s", target_db)
    logger.info("============================================================")

    # Inicialização preventiva do schema do banco
    try:
        init_db(db_path=target_db)
    except Exception as exc:
        logger.exception("Falha crítica ao inicializar o banco SQLite: %s", exc)
        return 1

    # -----------------------------------------------------------------------
    # ETAPA 1: Extração de Dados da API do IBGE
    # -----------------------------------------------------------------------
    logger.info("[ETAPA 1/5] Extraindo dados da API de Localidades do IBGE...")
    try:
        if client is not None:
            raw_payload = client.fetch_municipio_by_id(MAUA_IBGE_CODE)
        else:
            with IBGEClient() as active_client:
                raw_payload = active_client.fetch_municipio_by_id(MAUA_IBGE_CODE)

        logger.info(
            "Extração concluída com sucesso. Município obtido: '%s' (ID %s)",
            raw_payload.get("nome"),
            raw_payload.get("id"),
        )
    except IBGEExtractionError as exc:
        logger.error("Falha na Etapa 1 (Extração): %s. Pipeline interrompido.", exc)
        return 1
    except Exception as exc:
        logger.exception(
            "Erro inesperado durante a extração: %s. Pipeline interrompido.",
            exc,
        )
        return 1

    # -----------------------------------------------------------------------
    # ETAPA 2: Validação de Schema e Data Quality (Pydantic v2)
    # -----------------------------------------------------------------------
    logger.info("[ETAPA 2/5] Validando integridade e contrato do payload...")
    try:
        validated_schema = validate_maua_payload(raw_payload)
        logger.info(
            "Validação aprovada: %s (ID %d, UF %s)",
            validated_schema.nome,
            validated_schema.id,
            validated_schema.microrregiao.mesorregiao.uf.sigla,
        )
    except IBGEValidationError as exc:
        logger.error(
            "Falha na Etapa 2 (Validação): Violação de contrato de dados: %s. "
            "Pipeline interrompido.",
            exc,
        )
        return 1
    except Exception as exc:
        logger.exception(
            "Erro inesperado durante a validação: %s. Pipeline interrompido.",
            exc,
        )
        return 1

    # -----------------------------------------------------------------------
    # ETAPA 3: Persistência na Camada Bronze (Raw Ingestion)
    # -----------------------------------------------------------------------
    logger.info("[ETAPA 3/5] Persistindo dados brutos na Camada Bronze...")
    try:
        checksum = save_bronze(
            raw_payload=raw_payload,
            endpoint_url=MAUA_DIRECT_URL,
            http_status=200,
            db_path=target_db,
        )
        logger.info(
            "Camada Bronze atualizada com sucesso. Checksum SHA-256: %s",
            checksum,
        )
    except IBGEStorageError as exc:
        logger.error("Falha na Etapa 3 (Bronze): %s. Pipeline interrompido.", exc)
        return 1
    except Exception as exc:
        logger.exception(
            "Erro inesperado na Camada Bronze: %s. Pipeline interrompido.", exc
        )
        return 1

    # -----------------------------------------------------------------------
    # ETAPA 4: Transformação Tabular e Persistência na Camada Silver
    # -----------------------------------------------------------------------
    logger.info("[ETAPA 4/5] Normalizando dados e persistindo na Camada Silver...")
    try:
        df_silver = json_to_dataframe(validated_schema, validate=False)
        records_saved = save_silver(df=df_silver, db_path=target_db)
        logger.info(
            "Camada Silver atualizada com sucesso: %d registro(s) persistido(s) "
            "com 22 colunas padronizadas.",
            records_saved,
        )
    except (IBGEValidationError, IBGEStorageError) as exc:
        logger.error("Falha na Etapa 4 (Silver): %s. Pipeline interrompido.", exc)
        return 1
    except Exception as exc:
        logger.exception(
            "Erro inesperado na Camada Silver: %s. Pipeline interrompido.", exc
        )
        return 1

    # -----------------------------------------------------------------------
    # ETAPA 5: Sincronização e Auditoria na Camada Gold
    # -----------------------------------------------------------------------
    logger.info("[ETAPA 5/5] Auditando conciliação e indicadores na Camada Gold...")
    try:
        df_gold = read_gold_hierarquia(
            municipio_id=MAUA_IBGE_CODE,
            db_path=target_db,
        )
        if df_gold.empty:
            logger.error(
                "Falha na Etapa 5 (Gold): Nenhum registro encontrado na View analítica."
            )
            return 1

        kpis = get_kpis_qualidade(db_path=target_db)
        taxa = kpis.get("taxa_conformidade_pct", 0.0)
        falhas = kpis.get("total_falhas_qualidade", 0)

        logger.info("Auditoria Gold concluída:")
        logger.info(
            "  - Registros Auditados: %d",
            kpis.get("total_registros_auditados", 0),
        )
        logger.info("  - Taxa de Conformidade: %.2f%%", taxa)
        logger.info("  - Falhas de Qualidade / Nulos: %d", falhas)
        logger.info("  - Latência Média: %s s", kpis.get("latencia_media_segundos"))

        if falhas > 0 or taxa < 100.0:
            logger.error(
                "Falhas de qualidade detectadas na camada Gold. "
                "Taxa: %.2f%%, Falhas: %d",
                taxa,
                falhas,
            )
            return 1

    except Exception as exc:
        logger.exception("Erro inesperado na verificação da Camada Gold: %s", exc)
        return 1

    logger.info("============================================================")
    logger.info("PIPELINE CONCLUÍDO COM SUCESSO ABSOLUTO (STATUS: 100% OK)")
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
