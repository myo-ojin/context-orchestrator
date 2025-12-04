#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Context Orchestrator Main Entry Point

Initializes all components and starts the MCP protocol handler.
Includes nightly consolidation scheduler.

Requirements: Requirements 6, 11, 13
"""

import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from dataclasses import asdict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import load_config, Config
from src.utils.logger import setup_root_logger, get_logger
from src.utils.errors import (
    OllamaConnectionError,
    ModelNotFoundError,
    DatabaseError,
    ConfigurationError
)

# Import storage layer
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index
from src.storage.project_storage import ProjectStorage  # Phase 15
from src.storage.bookmark_storage import BookmarkStorage  # Phase 15

# Import processing layer
from src.processing.classifier import SchemaClassifier
from src.processing.chunker import Chunker
from src.processing.indexer import Indexer

# Import models
from src.models.router import ModelRouter
from src.models.local_llm import LocalLLMClient
from src.models.cli_llm import CLILLMClient

# Import services
from src.services.ingestion import IngestionService
from src.services.search import SearchService
from src.services.consolidation import ConsolidationService
from src.services.session_manager import SessionManager, ProjectPrefetchSettings
from src.services.session_log_collector import SessionLogCollector
from src.services.session_summary import SessionSummaryWorker
from src.services.obsidian_watcher import ObsidianWatcher
from src.services.project_manager import ProjectManager  # Phase 15
from src.services.bookmark_manager import BookmarkManager  # Phase 15
from src.services.query_attributes import QueryAttributeExtractor
from src.services.rerankers import CrossEncoderReranker
from src.services.project_memory_pool import ProjectMemoryPool  # Issue #2025-11-11-03

# Import MCP handler
from src.mcp.protocol_handler import MCPProtocolHandler

logger = get_logger(__name__)

# Ensure stdio uses UTF-8 (avoids BOM mishandling when invoked from PowerShell)
try:
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def init_storage(config: Config) -> tuple[ChromaVectorDB, BM25Index]:
    """
    Initialize storage layer

    Args:
        config: Configuration object

    Returns:
        Tuple of (vector_db, bm25_index)

    Raises:
        DatabaseError: If storage initialization fails
    """
    try:
        # Ensure data directory exists
        data_dir = Path(config.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Chroma DB
        chroma_path = data_dir / 'chroma_db'
        vector_db = ChromaVectorDB(
            collection_name='context_orchestrator',
            persist_directory=str(chroma_path)
        )

        logger.info(f"Initialized Chroma DB: {chroma_path}")

        # Initialize BM25 Index
        bm25_path = data_dir / 'bm25_index.pkl'
        bm25_index = BM25Index(persist_path=str(bm25_path))

        logger.info(f"Initialized BM25 Index: {bm25_path}")

        return vector_db, bm25_index

    except Exception as e:
        raise DatabaseError(f"Failed to initialize storage: {e}")


def init_models(config: Config) -> ModelRouter:
    """
    Initialize model router

    Args:
        config: Configuration object

    Returns:
        ModelRouter instance

    Raises:
        OllamaConnectionError: If Ollama is not accessible
        ModelNotFoundError: If required models are not installed
    """
    try:
        # Initialize Local LLM Client
        local_llm = LocalLLMClient(
            ollama_url=config.ollama.url,
            embedding_model=config.ollama.embedding_model,
            inference_model=config.ollama.inference_model
        )

        logger.info(f"Connected to Ollama: {config.ollama.url}")

        # Initialize CLI LLM Client
        cli_llm = CLILLMClient(
            cli_command=config.cli.command
        )

        logger.info(f"Initialized CLI LLM: {config.cli.command}")

        # Initialize Model Router
        model_router = ModelRouter(
            local_llm_client=local_llm,
            cli_llm_client=cli_llm
        )

        logger.info("Initialized Model Router")

        return model_router

    except OllamaConnectionError:
        raise

    except Exception as e:
        raise ConfigurationError(f"Failed to initialize models: {e}")


def init_processing(model_router: ModelRouter, vector_db: ChromaVectorDB, bm25_index: BM25Index) -> tuple[SchemaClassifier, Chunker, Indexer]:
    """
    Initialize processing components

    Args:
        model_router: ModelRouter instance
        vector_db: VectorDB instance
        bm25_index: BM25Index instance

    Returns:
        Tuple of (classifier, chunker, indexer)
    """
    # Initialize Schema Classifier
    classifier = SchemaClassifier(model_router=model_router)

    # Initialize Chunker
    chunker = Chunker(max_tokens=512)

    # Initialize Indexer
    indexer = Indexer(
        vector_db=vector_db,
        bm25_index=bm25_index,
        model_router=model_router
    )

    logger.info("Initialized processing components")

    return classifier, chunker, indexer


def init_services(
    config: Config,
    model_router: ModelRouter,
    vector_db: ChromaVectorDB,
    bm25_index: BM25Index,
    classifier: SchemaClassifier,
    chunker: Chunker,
    indexer: Indexer
) -> tuple[IngestionService, SearchService, ConsolidationService, Optional[SessionManager], Optional[ObsidianWatcher], Optional[ProjectManager], Optional[BookmarkManager]]:
    """
    Initialize core services

    Args:
        config: Configuration object
        model_router: ModelRouter instance
        vector_db: VectorDB instance
        bm25_index: BM25Index instance
        classifier: SchemaClassifier instance
        chunker: Chunker instance
        indexer: Indexer instance

    Returns:
        Tuple of (ingestion_service, search_service, consolidation_service, session_manager, obsidian_watcher, project_manager, bookmark_manager)
    """
    # Initialize Ingestion Service
    ingestion_service = IngestionService(
        vector_db=vector_db,
        classifier=classifier,
        chunker=chunker,
        indexer=indexer,
        model_router=model_router,
        supported_languages=config.languages.supported_local,
        language_fallback_strategy=config.languages.fallback_strategy,
        summary_max_tokens=config.router.mid_summary_max_tokens,
        hierarchical_max_tokens=config.router.mid_summary_max_tokens,
    )

    logger.info("Initialized IngestionService")

    # Initialize Phase 15: Project Management
    project_manager = None
    bookmark_manager = None
    query_attribute_extractor = QueryAttributeExtractor(
        model_router=model_router,
        min_llm_confidence=config.search.query_attribute_min_confidence,
        llm_enabled=config.search.query_attribute_llm_enabled
    )
    cross_encoder_reranker = None

    try:
        # Initialize Project Storage
        project_storage_path = Path(config.data_dir) / 'projects.json'
        project_storage = ProjectStorage(persist_path=str(project_storage_path))
        logger.info(f"Initialized ProjectStorage: {project_storage_path}")

        # Initialize Project Manager
        project_manager = ProjectManager(
            project_storage=project_storage,
            model_router=model_router
        )
        logger.info("Initialized ProjectManager")

        # Initialize Bookmark Storage
        bookmark_storage_path = Path(config.data_dir) / 'bookmarks.json'
        bookmark_storage = BookmarkStorage(persist_path=str(bookmark_storage_path))
        logger.info(f"Initialized BookmarkStorage: {bookmark_storage_path}")

        # Initialize Bookmark Manager
        bookmark_manager = BookmarkManager(
            bookmark_storage=bookmark_storage
        )
        logger.info("Initialized BookmarkManager")

    except Exception as e:
        logger.error(f"Failed to initialize Phase 15 components: {e}")
        logger.warning("Project and bookmark management will not be available")
        project_manager = None
        bookmark_manager = None

    # Initialize ProjectMemoryPool (Issue #2025-11-11-03)
    # Must be initialized before SearchService
    project_memory_pool = ProjectMemoryPool(
        vector_db=vector_db,
        model_router=model_router,
        max_memories_per_project=100,  # Can be made configurable later
        pool_ttl_seconds=config.search.cross_encoder_cache_ttl_seconds  # Match cache TTL
    )
    logger.info("Initialized ProjectMemoryPool")

    # Initialize Search Service
    if config.search.cross_encoder_enabled:
        cross_encoder_reranker = CrossEncoderReranker(
            model_router=model_router,
            max_candidates=config.search.cross_encoder_top_k,
            enabled=True,
            cache_max_entries=config.search.cross_encoder_cache_size,
            cache_ttl_seconds=config.search.cross_encoder_cache_ttl_seconds,
            max_parallel_reranks=config.search.cross_encoder_max_parallel
        )

    search_service = SearchService(
        vector_db=vector_db,
        bm25_index=bm25_index,
        model_router=model_router,
        candidate_count=config.search.candidate_count,
        vector_candidate_count=config.search.vector_candidate_count,
        bm25_candidate_count=config.search.bm25_candidate_count,
        result_count=config.search.result_count,
        recency_half_life_hours=float(config.working_memory.retention_hours),
        project_manager=project_manager,
        query_attribute_extractor=query_attribute_extractor,
        query_attribute_min_confidence=config.search.query_attribute_min_confidence,
        query_attribute_llm_enabled=config.search.query_attribute_llm_enabled,
        cross_encoder_reranker=cross_encoder_reranker,
        rerank_weights=asdict(config.reranking_weights),
        project_memory_pool=project_memory_pool
    )

    logger.info("Initialized SearchService")

    # Initialize Consolidation Service
    consolidation_service = ConsolidationService(
        vector_db=vector_db,
        indexer=indexer,
        model_router=model_router,
        similarity_threshold=config.clustering.similarity_threshold,
        min_cluster_size=config.clustering.min_cluster_size,
        age_threshold_days=config.forgetting.age_threshold_days,
        importance_threshold=config.forgetting.importance_threshold,
        working_memory_retention_hours=config.working_memory.retention_hours
    )

    logger.info("Initialized ConsolidationService")

    # Initialize Session Log Collector
    session_log_collector = SessionLogCollector(
        log_dir=config.logging.session_log_dir,
        max_log_size_mb=config.logging.max_log_size_mb
    )
    logger.info(f"Session logs directory: {session_log_collector.log_dir}")

    # Initialize Session Manager (available even without Obsidian vault)
    session_manager = SessionManager(
        ingestion_service=ingestion_service,
        model_router=model_router,
        obsidian_vault_path=config.obsidian_vault_path,
        query_attribute_extractor=query_attribute_extractor,
        project_manager=project_manager,
        search_service=search_service,
        project_prefetch_settings=ProjectPrefetchSettings(
            enabled=config.search.project_prefetch_enabled,
            min_confidence=config.search.project_prefetch_min_confidence,
            top_k=config.search.project_prefetch_top_k,
            max_queries=config.search.project_prefetch_max_queries,
            queries=list(config.search.project_prefetch_queries or []),
        ),
        project_memory_pool=project_memory_pool,
        session_log_collector=session_log_collector,
    )
    if config.obsidian_vault_path:
        logger.info(f"Initialized SessionManager with Obsidian vault: {config.obsidian_vault_path}")
    else:
        logger.info("Initialized SessionManager (no Obsidian vault configured)")

    # Initialize Obsidian Watcher (optional) - Requirement 1.5
    obsidian_watcher = None
    if config.obsidian_vault_path:
        try:
            obsidian_watcher = ObsidianWatcher(
                vault_path=config.obsidian_vault_path,
                ingestion_service=ingestion_service
            )
            logger.info(f"Initialized ObsidianWatcher for vault: {config.obsidian_vault_path}")
        except ValueError as e:
            logger.warning(f"Failed to initialize ObsidianWatcher: {e}")
            obsidian_watcher = None

    return ingestion_service, search_service, consolidation_service, session_manager, obsidian_watcher, project_manager, bookmark_manager


def check_and_run_consolidation(consolidation_service, data_dir: str) -> None:
    """
    Check if consolidation was missed (>24h) and run if needed

    Args:
        consolidation_service: ConsolidationService instance
        data_dir: Data directory path

    This function:
    1. Checks the last consolidation timestamp
    2. If >24 hours have passed, runs consolidation
    3. Updates the timestamp file
    """
    try:
        last_consolidation_file = Path(data_dir) / 'last_consolidation'

        # Check if we have a previous consolidation timestamp
        if last_consolidation_file.exists():
            try:
                last_time_str = last_consolidation_file.read_text(encoding='utf-8').strip()
                last_time = datetime.fromisoformat(last_time_str)

                time_since_last = datetime.now() - last_time

                if time_since_last > timedelta(hours=24):
                    logger.warning(f"Consolidation missed for {time_since_last.total_seconds() / 3600:.1f} hours, running now...")
                    stats = consolidation_service.consolidate()
                    logger.info(f"Missed consolidation completed: {stats}")

                    # Update timestamp
                    last_consolidation_file.write_text(datetime.now().isoformat(), encoding='utf-8')
                else:
                    logger.debug(f"Last consolidation was {time_since_last.total_seconds() / 3600:.1f} hours ago")

            except (ValueError, OSError) as e:
                logger.warning(f"Failed to read last consolidation timestamp: {e}")
                # Reset timestamp
                last_consolidation_file.write_text(datetime.now().isoformat(), encoding='utf-8')
        else:
            # First run, create timestamp file
            logger.info("First run, creating consolidation timestamp")
            last_consolidation_file.write_text(datetime.now().isoformat(), encoding='utf-8')

    except Exception as e:
        logger.error(f"Failed to check/run consolidation: {e}")


def main(config_path: Optional[str] = None) -> None:
    """
    Main entry point

    Args:
        config_path: Optional path to config file

    Raises:
        SystemExit: On fatal errors
    """
    try:
        # Load configuration
        config = load_config(config_path)

        # Setup logging
        log_file = Path(config.data_dir) / 'app.log'
        setup_root_logger(config.logging.level, str(log_file))

        logger.info("=" * 60)
        logger.info("Context Orchestrator Starting")
        logger.info("=" * 60)

        # Initialize storage
        vector_db, bm25_index = init_storage(config)

        # Initialize models
        model_router = init_models(config)

        # Initialize processing
        classifier, chunker, indexer = init_processing(model_router, vector_db, bm25_index)

        # Initialize services
        ingestion_service, search_service, consolidation_service, session_manager, obsidian_watcher, project_manager, bookmark_manager = init_services(
            config,
            model_router,
            vector_db,
            bm25_index,
            classifier,
            chunker,
            indexer
        )

        # Check and run missed consolidation
        check_and_run_consolidation(consolidation_service, config.data_dir)

        # Initialize scheduler for nightly consolidation
        scheduler = None
        if config.consolidation.auto_enabled:
            try:
                scheduler = BackgroundScheduler()

                # Parse cron schedule
                trigger = CronTrigger.from_crontab(config.consolidation.schedule)

                # Add consolidation job with timestamp update wrapper
                def run_consolidation_with_timestamp():
                    """Wrapper to update timestamp after consolidation"""
                    try:
                        stats = consolidation_service.consolidate()
                        logger.info(f"Scheduled consolidation completed: {stats}")

                        # Update last consolidation timestamp
                        last_consolidation_file = Path(config.data_dir) / 'last_consolidation'
                        last_consolidation_file.write_text(datetime.now().isoformat(), encoding='utf-8')
                    except Exception as e:
                        logger.error(f"Scheduled consolidation failed: {e}", exc_info=True)

                scheduler.add_job(
                    func=run_consolidation_with_timestamp,
                    trigger=trigger,
                    id='nightly_consolidation',
                    name='Nightly Memory Consolidation',
                    misfire_grace_time=3600  # Allow 1 hour grace period for missed jobs
                )

                scheduler.start()
                logger.info(f"Scheduled nightly consolidation: {config.consolidation.schedule}")

            except Exception as e:
                logger.error(f"Failed to initialize scheduler: {e}")
                scheduler = None

        # Start Obsidian Watcher (if configured) - Requirement 1.5
        if obsidian_watcher is not None:
            try:
                obsidian_watcher.start()
                logger.info("Started ObsidianWatcher")

                # Optional: Scan existing notes on startup
                # Uncomment the line below to enable initial vault scan
                # obsidian_watcher.scan_existing_notes()

            except Exception as e:
                logger.error(f"Failed to start ObsidianWatcher: {e}")
                obsidian_watcher = None

        # Initialize MCP Protocol Handler
        handler = MCPProtocolHandler(
            ingestion_service=ingestion_service,
            search_service=search_service,
            consolidation_service=consolidation_service,
            session_manager=session_manager,
            project_manager=project_manager,  # Phase 15
            bookmark_manager=bookmark_manager  # Phase 15
        )

        logger.info("MCP Protocol Handler initialized")
        logger.info("Ready to accept requests on stdin")
        logger.info("=" * 60)

        # Start handler (blocks)
        try:
            handler.start()
        finally:
            # Graceful shutdown: stop Obsidian Watcher
            if obsidian_watcher is not None:
                logger.info("Shutting down ObsidianWatcher...")
                obsidian_watcher.stop()
                logger.info("ObsidianWatcher stopped")

            # Graceful shutdown: stop scheduler
            if scheduler is not None:
                logger.info("Shutting down scheduler...")
                scheduler.shutdown(wait=False)
                logger.info("Scheduler stopped")

    except OllamaConnectionError as e:
        logger.error(f"Ollama connection error: {e}")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except ModelNotFoundError as e:
        logger.error(f"Model not found: {e}")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    # Check for config file argument
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(config_path)
