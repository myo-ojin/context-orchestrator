#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project Memory Pool

Manages pre-loaded memory embeddings for a project to optimize cache warming.
When a project is confirmed in a session, this pool loads all project memories
and their embeddings, allowing query-agnostic cache warming for the cross-encoder.

Requirements: Issue #2025-11-11-03 - Project Memory Pool
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, TYPE_CHECKING
import logging
import time

if TYPE_CHECKING:  # pragma: no cover
    from src.storage.vector_db import ChromaVectorDB
    from src.models import ModelRouter
    from src.services.rerankers import CrossEncoderReranker

logger = logging.getLogger(__name__)


class ProjectMemoryPool:
    """
    Pre-loads and caches memory embeddings for a project.

    This enables query-agnostic cache warming: when a project is confirmed,
    we load all project memories and their embeddings, then warm the
    cross-encoder's semantic cache. This optimizes for the common use case
    of personal developers working on a single project for extended periods.

    Attributes:
        vector_db: ChromaVectorDB for fetching project memories
        model_router: ModelRouter for generating embeddings
        max_memories_per_project: Maximum memories to load per project (default: 100)
        _pools: Cache of loaded pools {project_id -> pool_data}
    """

    def __init__(
        self,
        vector_db: "ChromaVectorDB",
        model_router: "ModelRouter",
        max_memories_per_project: int = 100,
        pool_ttl_seconds: int = 28800,  # 8 hours, matching cache TTL
    ):
        """
        Initialize ProjectMemoryPool

        Args:
            vector_db: ChromaVectorDB instance for fetching memories
            model_router: ModelRouter instance for generating embeddings
            max_memories_per_project: Maximum memories to load per project
            pool_ttl_seconds: How long to keep a loaded pool (seconds)
        """
        self.vector_db = vector_db
        self.model_router = model_router
        self.max_memories_per_project = max(1, max_memories_per_project)
        self.pool_ttl_seconds = max(0, pool_ttl_seconds)
        self._pools: Dict[str, Dict[str, Any]] = {}

        logger.info(
            "Initialized ProjectMemoryPool (max_memories=%d, ttl=%ds)",
            self.max_memories_per_project,
            self.pool_ttl_seconds
        )

    def load_project(self, project_id: str) -> Dict[str, Any]:
        """
        Load all memories for a project and generate their embeddings.

        Args:
            project_id: Project ID to load

        Returns:
            Pool data dict:
            {
                'project_id': str,
                'loaded_at': float (timestamp),
                'memory_count': int,
                'embeddings': {candidate_id: embedding_vector},
                'metadata': {candidate_id: metadata_dict}
            }
        """
        now = time.time()

        # Check if pool is already loaded and fresh
        if project_id in self._pools:
            pool = self._pools[project_id]
            age = now - pool['loaded_at']
            if age <= self.pool_ttl_seconds:
                logger.debug(
                    "Pool for project %s already loaded (age=%.1fs)",
                    project_id,
                    age
                )
                return pool

        logger.info("Loading memory pool for project %s", project_id)
        start = time.perf_counter()

        try:
            # Fetch all memory entries for this project
            memories = self.vector_db.list_by_metadata(
                filter_metadata={
                    'project_id': project_id,
                    'is_memory_entry': True
                },
                include_documents=True
            )

            if not memories:
                logger.warning("No memories found for project %s", project_id)
                return self._empty_pool(project_id, now)

            # Limit to max_memories_per_project (take most recent)
            memories_sorted = sorted(
                memories,
                key=lambda m: m.get('metadata', {}).get('created_at', ''),
                reverse=True
            )
            memories_limited = memories_sorted[:self.max_memories_per_project]

            # Generate embeddings for each memory
            embeddings: Dict[str, List[float]] = {}
            metadata_map: Dict[str, Dict[str, Any]] = {}

            for memory in memories_limited:
                candidate_id = memory.get('id')
                if not candidate_id:
                    continue

                content = memory.get('content', '')
                if not content:
                    continue

                try:
                    embedding = self.model_router.generate_embedding(content)
                    embeddings[candidate_id] = embedding
                    metadata_map[candidate_id] = memory.get('metadata', {})
                except Exception as exc:  # pragma: no cover
                    logger.warning(
                        "Failed to generate embedding for %s: %s",
                        candidate_id,
                        exc
                    )
                    continue

            pool = {
                'project_id': project_id,
                'loaded_at': now,
                'memory_count': len(embeddings),
                'embeddings': embeddings,
                'metadata': metadata_map
            }

            self._pools[project_id] = pool
            elapsed = (time.perf_counter() - start) * 1000

            logger.info(
                "Loaded pool for project %s: %d memories, %d embeddings in %.0fms",
                project_id,
                len(memories_limited),
                len(embeddings),
                elapsed
            )

            return pool

        except Exception as exc:  # pragma: no cover
            logger.error("Failed to load project pool %s: %s", project_id, exc)
            return self._empty_pool(project_id, now)

    def warm_cache(
        self,
        reranker: "CrossEncoderReranker",
        project_id: str
    ) -> Dict[str, Any]:
        """
        Warm the cross-encoder's semantic cache with project memory embeddings.

        This is the key optimization: by pre-loading embeddings into the L3
        semantic cache, we enable cache hits for any query that is semantically
        similar to project memories, regardless of exact query wording.

        Args:
            reranker: CrossEncoderReranker instance to warm
            project_id: Project ID to warm cache for

        Returns:
            Stats dict:
            {
                'project_id': str,
                'memories_loaded': int,
                'cache_entries_added': int,
                'elapsed_ms': float
            }
        """
        start = time.perf_counter()
        stats = {
            'project_id': project_id,
            'memories_loaded': 0,
            'cache_entries_added': 0,
            'elapsed_ms': 0.0
        }

        # Load project pool
        pool = self.load_project(project_id)
        stats['memories_loaded'] = pool.get('memory_count', 0)

        if stats['memories_loaded'] == 0:
            logger.warning("No memories to warm cache for project %s", project_id)
            return stats

        # Warm cache with pool embeddings
        embeddings = pool.get('embeddings', {})
        if not embeddings:
            return stats

        try:
            added = reranker.warm_semantic_cache_from_pool(embeddings)
            stats['cache_entries_added'] = added
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Failed to warm cache for project %s: %s",
                project_id,
                exc
            )
            return stats

        stats['elapsed_ms'] = (time.perf_counter() - start) * 1000
        logger.info(
            "Warmed cache for project %s: %d memories, %d cache entries in %.0fms",
            project_id,
            stats['memories_loaded'],
            stats['cache_entries_added'],
            stats['elapsed_ms']
        )

        return stats

    def get_pool_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a loaded pool.

        Args:
            project_id: Project ID

        Returns:
            Pool stats or None if not loaded
        """
        pool = self._pools.get(project_id)
        if not pool:
            return None

        now = time.time()
        age = now - pool['loaded_at']

        return {
            'project_id': project_id,
            'memory_count': pool.get('memory_count', 0),
            'age_seconds': age,
            'is_fresh': age <= self.pool_ttl_seconds
        }

    def clear_pool(self, project_id: str) -> bool:
        """
        Clear a loaded pool from cache.

        Args:
            project_id: Project ID

        Returns:
            True if pool was cleared, False if not found
        """
        if project_id in self._pools:
            del self._pools[project_id]
            logger.debug("Cleared pool for project %s", project_id)
            return True
        return False

    def clear_all_pools(self) -> int:
        """
        Clear all loaded pools.

        Returns:
            Number of pools cleared
        """
        count = len(self._pools)
        self._pools.clear()
        logger.info("Cleared all pools (%d projects)", count)
        return count

    def get_memory_ids(self, project_id: str) -> set:
        """
        Get the set of memory IDs for a project.

        This is used for candidate filtering in the graduated degradation workflow.
        When a project is confirmed, we can filter search candidates to only
        those memories that belong to the project pool.

        Note: Memory entries are stored with "-metadata" suffix in embeddings dict,
        but this method returns the base memory IDs without the suffix for easier
        comparison with chunk candidates.

        Args:
            project_id: Project ID

        Returns:
            Set of base memory IDs without "-metadata" suffix (empty set if pool not loaded)

        Example:
            >>> pool = ProjectMemoryPool(...)
            >>> pool.load_project("proj-123")
            >>> memory_ids = pool.get_memory_ids("proj-123")
            >>> len(memory_ids)  # e.g., 30
            30
        """
        pool = self._pools.get(project_id)
        if not pool:
            return set()

        embeddings = pool.get('embeddings', {})

        # Strip "-metadata" suffix from memory entry IDs
        memory_ids = set()
        for candidate_id in embeddings.keys():
            if candidate_id.endswith('-metadata'):
                memory_ids.add(candidate_id[:-9])  # Remove "-metadata" suffix
            else:
                memory_ids.add(candidate_id)

        return memory_ids

    def _empty_pool(self, project_id: str, timestamp: float) -> Dict[str, Any]:
        """Create an empty pool placeholder."""
        return {
            'project_id': project_id,
            'loaded_at': timestamp,
            'memory_count': 0,
            'embeddings': {},
            'metadata': {}
        }
