#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration Management

Loads configuration from YAML file and provides typed Config object.

Requirements: Requirement 13 (Configuration Management)
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Ollama configuration"""
    url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    inference_model: str = "qwen2.5:7b"


@dataclass
class CLIConfig:
    """CLI LLM configuration"""
    command: str = "claude"  # or "codex"


@dataclass
class SearchConfig:
    """Search configuration"""
    candidate_count: int = 50
    result_count: int = 10
    timeout_seconds: int = 2
    cross_encoder_enabled: bool = True
    cross_encoder_top_k: int = 3
    cross_encoder_cache_size: int = 128
    cross_encoder_cache_ttl_seconds: int = 900
    cross_encoder_max_parallel: int = 3
    cross_encoder_fallback_max_wait_ms: int = 500
    cross_encoder_fallback_mode: str = "heuristic"
    vector_candidate_count: int = 100
    bm25_candidate_count: int = 30
    query_attribute_min_confidence: float = 0.4
    query_attribute_llm_enabled: bool = True
    project_prefetch_enabled: bool = True
    project_prefetch_min_confidence: float = 0.75
    project_prefetch_queries: List[str] = field(
        default_factory=lambda: [
            "project status",
            "open issues",
            "risk summary",
        ]
    )
    project_prefetch_top_k: int = 5
    project_prefetch_max_queries: int = 3


@dataclass
class ClusteringConfig:
    """Clustering configuration"""
    similarity_threshold: float = 0.9
    min_cluster_size: int = 2


@dataclass
class ForgettingConfig:
    """Forgetting configuration"""
    age_threshold_days: int = 30
    importance_threshold: float = 0.3
    compression_enabled: bool = True


@dataclass
class WorkingMemoryConfig:
    """Working memory configuration"""
    retention_hours: int = 8
    auto_consolidate: bool = True


@dataclass
class ConsolidationConfig:
    """Consolidation configuration"""
    schedule: str = "0 3 * * *"  # cron format (3:00 AM daily)
    auto_enabled: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    session_log_dir: str = "~/.context-orchestrator/logs"
    max_log_size_mb: int = 10
    summary_model: str = "qwen2.5:7b"
    level: str = "INFO"


@dataclass
class RouterConfig:
    """Routing thresholds/configuration"""
    short_summary_max_tokens: int = 100
    long_summary_min_tokens: int = 500


@dataclass
class LanguageConfig:
    """Language handling configuration"""
    supported_local: List[str] = field(default_factory=lambda: ["en", "ja", "es"])
    fallback_strategy: str = "cloud"  # 'cloud' or 'local'


@dataclass
class RerankingWeightsConfig:
    """Weights applied during SearchService reranking."""
    memory_strength: float = 0.3
    recency: float = 0.2
    refs_reliability: float = 0.1
    bm25_score: float = 0.2
    vector_similarity: float = 0.2
    metadata_bonus: float = 1.0


@dataclass
class Config:
    """
    System configuration

    Attributes:
        data_dir: Data directory path
        obsidian_vault_path: Optional Obsidian vault path
        ollama: Ollama configuration
        cli: CLI LLM configuration
        search: Search configuration
        clustering: Clustering configuration
        forgetting: Forgetting configuration
        working_memory: Working memory configuration
        consolidation: Consolidation configuration
        logging: Logging configuration
    """
    data_dir: str = "~/.context-orchestrator"
    obsidian_vault_path: Optional[str] = None

    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    forgetting: ForgettingConfig = field(default_factory=ForgettingConfig)
    working_memory: WorkingMemoryConfig = field(default_factory=WorkingMemoryConfig)
    consolidation: ConsolidationConfig = field(default_factory=ConsolidationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    reranking_weights: RerankingWeightsConfig = field(default_factory=RerankingWeightsConfig)
    router: RouterConfig = field(default_factory=RouterConfig)
    languages: LanguageConfig = field(default_factory=LanguageConfig)

    def __post_init__(self):
        """Expand paths after initialization"""
        self.data_dir = os.path.expanduser(self.data_dir)

        if self.obsidian_vault_path:
            self.obsidian_vault_path = os.path.expanduser(self.obsidian_vault_path)

        self.logging.session_log_dir = os.path.expanduser(self.logging.session_log_dir)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file

    Args:
        config_path: Optional path to config file. If None, searches in:
            1. $CONTEXT_ORCHESTRATOR_CONFIG
            2. ~/.context-orchestrator/config.yaml
            3. ./config.yaml

    Returns:
        Config object

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If config file is invalid

    Example:
        >>> config = load_config()
        >>> print(config.ollama.url)
        http://localhost:11434
    """
    # Determine config file path
    if config_path:
        config_file = Path(config_path)
    elif os.environ.get('CONTEXT_ORCHESTRATOR_CONFIG'):
        config_file = Path(os.environ['CONTEXT_ORCHESTRATOR_CONFIG'])
    else:
        # Search in default locations
        search_paths = [
            Path.home() / '.context-orchestrator' / 'config.yaml',
            Path('config.yaml')
        ]

        config_file = None
        for path in search_paths:
            if path.exists():
                config_file = path
                break

    # If no config file found, use defaults
    if not config_file or not config_file.exists():
        logger.warning("Config file not found, using defaults")
        return Config()

    # Load YAML
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)

        if not yaml_data:
            logger.warning("Config file is empty, using defaults")
            return Config()

        # Parse config
        config = _parse_config(yaml_data)

        logger.info(f"Loaded config from: {config_file}")
        return config

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    except Exception as e:
        raise ValueError(f"Failed to load config: {e}")


def _parse_config(data: Dict[str, Any]) -> Config:
    """
    Parse config data from YAML

    Args:
        data: YAML data dict

    Returns:
        Config object
    """
    # Parse nested configs
    ollama_data = data.get('ollama', {})
    cli_data = data.get('cli', {})
    search_data = data.get('search', {})
    clustering_data = data.get('clustering', {})
    forgetting_data = data.get('forgetting', {})
    working_memory_data = data.get('working_memory', {})
    consolidation_data = data.get('consolidation', {})
    logging_data = data.get('logging', {})
    router_data = data.get('router', {})
    language_data = data.get('languages', {})
    reranking_data = data.get('reranking_weights', {})

    default_language = LanguageConfig()
    default_reranking = RerankingWeightsConfig()

    # Create config object
    config = Config(
        data_dir=data.get('data_dir', Config.data_dir),
        obsidian_vault_path=data.get('obsidian_vault_path'),

        ollama=OllamaConfig(
            url=ollama_data.get('url', OllamaConfig.url),
            embedding_model=ollama_data.get('embedding_model', OllamaConfig.embedding_model),
            inference_model=ollama_data.get('inference_model', OllamaConfig.inference_model)
        ),

        cli=CLIConfig(
            command=cli_data.get('command', CLIConfig.command)
        ),

        search=SearchConfig(
            candidate_count=search_data.get('candidate_count', SearchConfig.candidate_count),
            result_count=search_data.get('result_count', SearchConfig.result_count),
            timeout_seconds=search_data.get('timeout_seconds', SearchConfig.timeout_seconds),
            cross_encoder_enabled=search_data.get('cross_encoder_enabled', SearchConfig.cross_encoder_enabled),
            cross_encoder_top_k=search_data.get('cross_encoder_top_k', SearchConfig.cross_encoder_top_k),
            cross_encoder_cache_size=search_data.get(
                'cross_encoder_cache_size',
                SearchConfig.cross_encoder_cache_size
            ),
            cross_encoder_cache_ttl_seconds=search_data.get(
                'cross_encoder_cache_ttl_seconds',
                SearchConfig.cross_encoder_cache_ttl_seconds
            ),
            cross_encoder_max_parallel=search_data.get(
                'cross_encoder_max_parallel',
                SearchConfig.cross_encoder_max_parallel
            ),
            cross_encoder_fallback_max_wait_ms=search_data.get(
                'cross_encoder_fallback_max_wait_ms',
                SearchConfig.cross_encoder_fallback_max_wait_ms
            ),
            cross_encoder_fallback_mode=search_data.get(
                'cross_encoder_fallback_mode',
                SearchConfig.cross_encoder_fallback_mode
            ),
            vector_candidate_count=search_data.get('vector_candidate_count', SearchConfig.vector_candidate_count),
            bm25_candidate_count=search_data.get('bm25_candidate_count', SearchConfig.bm25_candidate_count),
            query_attribute_min_confidence=search_data.get(
                'query_attribute_min_confidence',
                SearchConfig.query_attribute_min_confidence
            ),
            query_attribute_llm_enabled=search_data.get(
                'query_attribute_llm_enabled',
                SearchConfig.query_attribute_llm_enabled
            ),
            project_prefetch_enabled=search_data.get(
                'project_prefetch_enabled',
                SearchConfig.project_prefetch_enabled
            ),
            project_prefetch_min_confidence=search_data.get(
                'project_prefetch_min_confidence',
                SearchConfig.project_prefetch_min_confidence
            ),
            project_prefetch_queries=search_data.get(
                'project_prefetch_queries',
                ["project status", "open issues", "risk summary"]
            ),
            project_prefetch_top_k=search_data.get(
                'project_prefetch_top_k',
                SearchConfig.project_prefetch_top_k
            ),
            project_prefetch_max_queries=search_data.get(
                'project_prefetch_max_queries',
                SearchConfig.project_prefetch_max_queries
            ),
        ),

        clustering=ClusteringConfig(
            similarity_threshold=clustering_data.get('similarity_threshold', ClusteringConfig.similarity_threshold),
            min_cluster_size=clustering_data.get('min_cluster_size', ClusteringConfig.min_cluster_size)
        ),

        forgetting=ForgettingConfig(
            age_threshold_days=forgetting_data.get('age_threshold_days', ForgettingConfig.age_threshold_days),
            importance_threshold=forgetting_data.get('importance_threshold', ForgettingConfig.importance_threshold),
            compression_enabled=forgetting_data.get('compression_enabled', ForgettingConfig.compression_enabled)
        ),

        working_memory=WorkingMemoryConfig(
            retention_hours=working_memory_data.get('retention_hours', WorkingMemoryConfig.retention_hours),
            auto_consolidate=working_memory_data.get('auto_consolidate', WorkingMemoryConfig.auto_consolidate)
        ),

        consolidation=ConsolidationConfig(
            schedule=consolidation_data.get('schedule', ConsolidationConfig.schedule),
            auto_enabled=consolidation_data.get('auto_enabled', ConsolidationConfig.auto_enabled)
        ),

        logging=LoggingConfig(
            session_log_dir=logging_data.get('session_log_dir', LoggingConfig.session_log_dir),
            max_log_size_mb=logging_data.get('max_log_size_mb', LoggingConfig.max_log_size_mb),
            summary_model=logging_data.get('summary_model', LoggingConfig.summary_model),
            level=logging_data.get('level', LoggingConfig.level)
        ),

        router=RouterConfig(
            short_summary_max_tokens=router_data.get('short_summary_max_tokens', RouterConfig.short_summary_max_tokens),
            long_summary_min_tokens=router_data.get('long_summary_min_tokens', RouterConfig.long_summary_min_tokens),
        ),

        languages=LanguageConfig(
            supported_local=language_data.get('supported_local', default_language.supported_local),
            fallback_strategy=language_data.get('fallback_strategy', default_language.fallback_strategy),
        ),

        reranking_weights=RerankingWeightsConfig(
            memory_strength=reranking_data.get('memory_strength', default_reranking.memory_strength),
            recency=reranking_data.get('recency', default_reranking.recency),
            refs_reliability=reranking_data.get('refs_reliability', default_reranking.refs_reliability),
            bm25_score=reranking_data.get('bm25_score', default_reranking.bm25_score),
            vector_similarity=reranking_data.get('vector_similarity', default_reranking.vector_similarity),
            metadata_bonus=reranking_data.get('metadata_bonus', default_reranking.metadata_bonus),
        )
    )

    return config


def save_config(config: Config, config_path: Optional[str] = None) -> None:
    """
    Save configuration to YAML file

    Args:
        config: Config object
        config_path: Optional path to save config. If None, uses default location.

    Example:
        >>> config = Config()
        >>> save_config(config, '~/.context-orchestrator/config.yaml')
    """
    # Determine config file path
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = Path.home() / '.context-orchestrator' / 'config.yaml'

    # Ensure directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Build YAML data
    yaml_data = {
        'data_dir': config.data_dir,
        'obsidian_vault_path': config.obsidian_vault_path,

        'ollama': {
            'url': config.ollama.url,
            'embedding_model': config.ollama.embedding_model,
            'inference_model': config.ollama.inference_model
        },

        'cli': {
            'command': config.cli.command
        },

        'search': {
            'candidate_count': config.search.candidate_count,
            'result_count': config.search.result_count,
            'timeout_seconds': config.search.timeout_seconds,
            'cross_encoder_enabled': config.search.cross_encoder_enabled,
            'cross_encoder_top_k': config.search.cross_encoder_top_k,
            'cross_encoder_cache_size': config.search.cross_encoder_cache_size,
            'cross_encoder_cache_ttl_seconds': config.search.cross_encoder_cache_ttl_seconds,
            'cross_encoder_max_parallel': config.search.cross_encoder_max_parallel,
            'vector_candidate_count': config.search.vector_candidate_count,
            'bm25_candidate_count': config.search.bm25_candidate_count,
            'query_attribute_min_confidence': config.search.query_attribute_min_confidence,
            'query_attribute_llm_enabled': config.search.query_attribute_llm_enabled,
            'project_prefetch_enabled': config.search.project_prefetch_enabled,
            'project_prefetch_min_confidence': config.search.project_prefetch_min_confidence,
            'project_prefetch_queries': config.search.project_prefetch_queries,
            'project_prefetch_top_k': config.search.project_prefetch_top_k,
            'project_prefetch_max_queries': config.search.project_prefetch_max_queries,
        },

        'clustering': {
            'similarity_threshold': config.clustering.similarity_threshold,
            'min_cluster_size': config.clustering.min_cluster_size
        },

        'forgetting': {
            'age_threshold_days': config.forgetting.age_threshold_days,
            'importance_threshold': config.forgetting.importance_threshold,
            'compression_enabled': config.forgetting.compression_enabled
        },

        'working_memory': {
            'retention_hours': config.working_memory.retention_hours,
            'auto_consolidate': config.working_memory.auto_consolidate
        },

        'consolidation': {
            'schedule': config.consolidation.schedule,
            'auto_enabled': config.consolidation.auto_enabled
        },

        'logging': {
            'session_log_dir': config.logging.session_log_dir,
            'max_log_size_mb': config.logging.max_log_size_mb,
            'summary_model': config.logging.summary_model,
            'level': config.logging.level
        },

        'router': {
            'short_summary_max_tokens': config.router.short_summary_max_tokens,
            'long_summary_min_tokens': config.router.long_summary_min_tokens,
        },

        'languages': {
            'supported_local': config.languages.supported_local,
            'fallback_strategy': config.languages.fallback_strategy,
        },

        'reranking_weights': {
            'memory_strength': config.reranking_weights.memory_strength,
            'recency': config.reranking_weights.recency,
            'refs_reliability': config.reranking_weights.refs_reliability,
            'bm25_score': config.reranking_weights.bm25_score,
            'vector_similarity': config.reranking_weights.vector_similarity,
            'metadata_bonus': config.reranking_weights.metadata_bonus,
        },
    }

    # Write YAML
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info(f"Saved config to: {config_file}")
