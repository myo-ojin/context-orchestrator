#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Consolidation Service

Handles memory consolidation, clustering, and forgetting:
1. Migrate working memory to short-term memory
2. Cluster similar memories (similarity >= 0.9)
3. Select representative memory per cluster
4. Forget old memories (age > 30 days, importance < 0.3)

Runs automatically at 3:00 AM (configurable) or manually via CLI.

Requirements: Requirements 5, 6, 7 (MVP - Clustering, Consolidation, Forgetting)
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import logging
import math

from src.models import ModelRouter, MemoryType
from src.storage.vector_db import ChromaVectorDB
from src.processing.indexer import Indexer

logger = logging.getLogger(__name__)


class ConsolidationService:
    """
    Service for memory consolidation and forgetting

    Manages the lifecycle of memories:
    - Working memory (hours) → Short-term memory (days/weeks)
    - Short-term memory → Long-term memory (permanent) or deletion
    - Clusters similar memories and selects representatives
    - Forgets old, low-importance memories

    Attributes:
        vector_db: ChromaVectorDB instance
        indexer: Indexer instance for deletion operations
        model_router: ModelRouter for LLM tasks
        similarity_threshold: Clustering threshold (default: 0.9)
        min_cluster_size: Minimum cluster size for consolidation (default: 2)
        age_threshold_days: Age threshold for forgetting (default: 30)
        importance_threshold: Importance threshold for forgetting (default: 0.3)
        working_memory_retention_hours: Working memory retention (default: 8)
    """

    def __init__(
        self,
        vector_db: ChromaVectorDB,
        indexer: Indexer,
        model_router: ModelRouter,
        similarity_threshold: float = 0.9,
        min_cluster_size: int = 2,
        age_threshold_days: int = 30,
        importance_threshold: float = 0.3,
        working_memory_retention_hours: int = 8
    ):
        """
        Initialize Consolidation Service

        Args:
            vector_db: ChromaVectorDB instance
            indexer: Indexer instance
            model_router: ModelRouter instance
            similarity_threshold: Clustering similarity threshold (0-1)
            min_cluster_size: Minimum cluster size for consolidation
            age_threshold_days: Age threshold for forgetting (days)
            importance_threshold: Importance threshold for forgetting (0-1)
            working_memory_retention_hours: Working memory retention (hours)
        """
        self.vector_db = vector_db
        self.indexer = indexer
        self.model_router = model_router
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.age_threshold_days = age_threshold_days
        self.importance_threshold = importance_threshold
        self.working_memory_retention_hours = working_memory_retention_hours

        logger.info(f"Initialized ConsolidationService (similarity={similarity_threshold}, "
                   f"min_cluster={min_cluster_size}, age={age_threshold_days}d, importance={importance_threshold})")

    def consolidate(self) -> Dict[str, Any]:
        """
        Run full consolidation process

        Steps:
        1. Migrate working memory to short-term
        2. Cluster similar memories
        3. Select representative memories
        4. Forget old, low-importance memories

        Returns:
            Statistics dict:
                {
                    'migrated_count': int,
                    'clusters_created': int,
                    'memories_compressed': int,
                    'memories_deleted': int,
                    'duration_seconds': float
                }

        Example:
            >>> service = ConsolidationService(...)
            >>> stats = service.consolidate()
            >>> print(f"Migrated: {stats['migrated_count']}, Deleted: {stats['memories_deleted']}")
        """
        logger.info("Starting memory consolidation...")
        start_time = datetime.now(timezone.utc)

        stats = {
            'migrated_count': 0,
            'clusters_created': 0,
            'memories_compressed': 0,
            'memories_deleted': 0,
            'duration_seconds': 0.0
        }

        try:
            # Step 1: Migrate working memory
            migrated = self._migrate_working_memory()
            stats['migrated_count'] = len(migrated)
            logger.info(f"Migrated {len(migrated)} memories from working to short-term")

            # Step 2: Cluster similar memories
            clusters = self._cluster_similar_memories()
            stats['clusters_created'] = len(clusters)
            logger.info(f"Created {len(clusters)} memory clusters")

            # Step 3: Process clusters (select representatives, compress others)
            compressed = self._process_clusters(clusters)
            stats['memories_compressed'] = compressed
            logger.info(f"Compressed {compressed} memories in clusters")

            # Step 4: Forget old memories
            deleted = self._forget_old_memories()
            stats['memories_deleted'] = deleted
            logger.info(f"Deleted {deleted} old memories")

            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            stats['duration_seconds'] = duration

            logger.info(f"Consolidation completed in {duration:.1f}s: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Consolidation failed: {e}", exc_info=True)
            stats['duration_seconds'] = (datetime.now(timezone.utc) - start_time).total_seconds()
            return stats

    def _migrate_working_memory(self) -> List[str]:
        """
        Migrate completed working memory to short-term memory

        Criteria: Working memory older than retention period (default: 8 hours)

        Returns:
            List of migrated memory IDs
        """
        logger.debug("Migrating working memory...")

        try:
            entries = self.vector_db.list_by_metadata(
                {
                    'is_memory_entry': True,
                    'memory_type': MemoryType.WORKING.value
                }
            )

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.working_memory_retention_hours)
            migrated_ids: List[str] = []

            for entry in entries:
                metadata = entry.get('metadata', {})
                memory_id = metadata.get('memory_id')
                if not memory_id:
                    continue

                timestamp = metadata.get('updated_at') or metadata.get('created_at')
                created_at = self._parse_timestamp(timestamp)

                if created_at is None or created_at > cutoff_time:
                    continue

                updated_metadata = metadata.copy()
                now_iso = datetime.now(timezone.utc).isoformat()
                updated_metadata['memory_type'] = MemoryType.SHORT_TERM.value
                updated_metadata['updated_at'] = now_iso
                updated_metadata['migrated_at'] = now_iso

                entry_id = entry.get('id') or f"{memory_id}-metadata"
                self.vector_db.update_metadata(entry_id, updated_metadata)
                migrated_ids.append(memory_id)

            if migrated_ids:
                logger.info(f"Migrated {len(migrated_ids)} memories from working to short-term")

            return migrated_ids

        except Exception as e:
            logger.error(f"Failed to migrate working memory: {e}")
            return []

    def _cluster_similar_memories(self) -> List[List[str]]:
        """
        Cluster similar memories (similarity >= threshold)

        Uses cosine similarity from embeddings.
        Greedy clustering: iterate through memories and group similar ones.

        Returns:
            List of clusters, where each cluster is a list of memory IDs

        Example:
            [
                ['mem-1', 'mem-2', 'mem-3'],  # Cluster 1
                ['mem-4', 'mem-5']            # Cluster 2
            ]
        """
        logger.debug(f"Clustering memories (threshold={self.similarity_threshold})...")

        try:
            entries = self.vector_db.list_by_metadata(
                {'is_memory_entry': True},
                include_embeddings=True
            )

            memory_embeddings: List[Tuple[str, List[float]]] = []

            for entry in entries:
                metadata = entry.get('metadata', {})
                memory_id = metadata.get('memory_id')
                embedding = entry.get('embedding')

                if not memory_id or embedding is None:
                    continue

                memory_embeddings.append((memory_id, embedding))

            visited = set()
            clusters: List[List[str]] = []

            for i, (memory_id, embedding) in enumerate(memory_embeddings):
                if memory_id in visited:
                    continue

                cluster = [memory_id]
                visited.add(memory_id)

                for j in range(i + 1, len(memory_embeddings)):
                    other_id, other_embedding = memory_embeddings[j]
                    if other_id in visited:
                        continue

                    similarity = self._cosine_similarity(embedding, other_embedding)
                    if similarity >= self.similarity_threshold:
                        cluster.append(other_id)
                        visited.add(other_id)

                clusters.append(cluster)

            return clusters

        except Exception as e:
            logger.error(f"Failed to cluster memories: {e}")
            return []

    def _process_clusters(self, clusters: List[List[str]]) -> int:
        """
        Process memory clusters

        For each cluster:
        1. Select representative memory (most detailed or recent)
        2. Compress other memories (mark as non-representative)

        Args:
            clusters: List of clusters (each cluster is list of memory IDs)

        Returns:
            Number of memories compressed
        """
        logger.debug(f"Processing {len(clusters)} clusters...")

        compressed_count = 0

        for cluster in clusters:
            if len(cluster) < self.min_cluster_size:
                continue  # Skip clusters smaller than min_cluster_size

            try:
                # Select representative
                representative_id = self._select_representative_memory(cluster)
                logger.debug(f"Cluster representative: {representative_id}")

                # Mark representative
                self._mark_as_representative(representative_id, cluster)

                # Compress others
                for memory_id in cluster:
                    if memory_id != representative_id:
                        self._compress_memory(memory_id)
                        compressed_count += 1

            except Exception as e:
                logger.error(f"Failed to process cluster: {e}")

        return compressed_count

    def _select_representative_memory(self, cluster: List[str]) -> str:
        """
        Select representative memory from cluster

        Criteria:
        1. Most detailed (longest content)
        2. Most recent (if tied on length)
        3. Highest importance score

        Args:
            cluster: List of memory IDs

        Returns:
            Representative memory ID
        """
        try:
            # Get all memories in cluster
            memories = []
            for memory_id in cluster:
                metadata_entry = self.vector_db.get(f"{memory_id}-metadata")
                if metadata_entry:
                    memories.append({
                        'id': memory_id,
                        'content': metadata_entry.get('content', ''),
                        'metadata': metadata_entry.get('metadata', {})
                    })

            if not memories:
                return cluster[0]  # Fallback

            # Score each memory
            def score_memory(memory):
                content_length = len(memory['content'])
                metadata = memory['metadata']

                # Recency score
                created_at_str = metadata.get('created_at')
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        age_days = (datetime.now(timezone.utc) - created_at).days
                        recency = 1.0 / (1.0 + age_days)
                    except:
                        recency = 0.5
                else:
                    recency = 0.5

                # Importance score
                importance = metadata.get('importance', 0.5)

                # Combined score
                return (
                    content_length * 0.5 +
                    recency * 1000 * 0.3 +
                    importance * 1000 * 0.2
                )

            # Select memory with highest score
            best_memory = max(memories, key=score_memory)
            return best_memory['id']

        except Exception as e:
            logger.error(f"Failed to select representative: {e}")
            return cluster[0]  # Fallback to first

    def _mark_as_representative(self, memory_id: str, cluster: List[str]) -> None:
        """
        Mark a memory as representative of a cluster

        Updates metadata with cluster_id and is_representative flag.

        Args:
            memory_id: Representative memory ID
            cluster: Full cluster (list of memory IDs)
        """
        try:
            cluster_id = f"cluster-{memory_id}"

            # Update representative
            self.vector_db.update_metadata(
                f"{memory_id}-metadata",
                {
                    'cluster_id': cluster_id,
                    'is_representative': True,
                    'cluster_size': len(cluster)
                }
            )

            logger.debug(f"Marked {memory_id} as representative of {cluster_id}")

        except Exception as e:
            logger.error(f"Failed to mark representative: {e}")

    def _compress_memory(self, memory_id: str) -> None:
        """
        Compress a memory (non-representative in cluster)

        For MVP: just mark as compressed in metadata.
        Phase 2: actually compress content to summary only.

        Args:
            memory_id: Memory ID to compress
        """
        try:
            # For MVP: mark as compressed
            self.vector_db.update_metadata(
                f"{memory_id}-metadata",
                {
                    'is_compressed': True,
                    'compressed_at': datetime.now(timezone.utc).isoformat()
                }
            )

            logger.debug(f"Compressed memory: {memory_id}")

        except Exception as e:
            logger.error(f"Failed to compress memory: {e}")

    def _forget_old_memories(self) -> int:
        """
        Delete or compress old, low-importance memories

        Criteria:
        - Age > age_threshold_days (default: 30 days)
        - Importance < importance_threshold (default: 0.3)

        Returns:
            Number of memories deleted
        """
        logger.debug(f"Forgetting old memories (age>{self.age_threshold_days}d, "
                    f"importance<{self.importance_threshold})...")

        deleted_count = 0

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.age_threshold_days)
            entries = self.vector_db.list_by_metadata({'is_memory_entry': True})

            for entry in entries:
                metadata = entry.get('metadata', {})
                memory_id = metadata.get('memory_id')
                if not memory_id:
                    continue

                importance = metadata.get('importance', 0.5)
                try:
                    importance_value = float(importance)
                except (TypeError, ValueError):
                    importance_value = 0.5

                if importance_value >= self.importance_threshold:
                    continue

                created_at = self._parse_timestamp(metadata.get('created_at'))
                if created_at is None or created_at > cutoff_date:
                    continue

                if self._delete_memory(memory_id):
                    deleted_count += 1

            if deleted_count:
                logger.info(f"Forgot {deleted_count} old memories")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to forget old memories: {e}")
            return deleted_count

    def _delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory and all its chunks

        Args:
            memory_id: Memory ID

        Returns:
            True if successful
        """
        try:
            # Delete memory metadata
            self.vector_db.delete(f"{memory_id}-metadata")

            # Delete all chunks
            self.indexer.delete_by_memory_id(memory_id)

            logger.debug(f"Deleted memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    @staticmethod
    def _parse_timestamp(timestamp: Optional[str]) -> Optional[datetime]:
        if not timestamp:
            return None

        try:
            parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            else:
                parsed = parsed.astimezone(timezone.utc)
            return parsed
        except Exception:
            logger.warning(f"Failed to parse timestamp: {timestamp}")
            return None

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if vec_a is None or vec_b is None:
            return 0.0
        if len(vec_a) == 0 or len(vec_b) == 0 or len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


    def calculate_importance_score(
        self,
        memory_id: str,
        access_count: int = 0,
        refs_count: int = 0
    ) -> float:
        """
        Calculate importance score for a memory

        Factors:
        - Access frequency (how often retrieved)
        - Recency (when created)
        - Refs reliability (number of refs)
        - Success experience (TODO: Phase 2)
        - Centrality in memory graph (TODO: Phase 2)

        Args:
            memory_id: Memory ID
            access_count: Number of times accessed
            refs_count: Number of refs

        Returns:
            Importance score (0-1)

        Example:
            >>> service = ConsolidationService(...)
            >>> importance = service.calculate_importance_score("mem-123", access_count=5, refs_count=3)
            >>> print(importance)
            0.75
        """
        try:
            # Get memory metadata
            memory = self.vector_db.get(f"{memory_id}-metadata")
            if not memory:
                return 0.5  # Default

            metadata = memory.get('metadata', {})

            # Access frequency score
            # Logarithmic scaling: score = log(1 + count) / log(101)
            access_score = math.log(1 + access_count) / math.log(101)

            # Recency score
            created_at_str = metadata.get('created_at')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    age_days = (datetime.now(timezone.utc) - created_at).days
                    recency_score = math.exp(-age_days / 30.0)  # 30-day half-life
                except:
                    recency_score = 0.5
            else:
                recency_score = 0.5

            # Refs reliability score
            refs_score = math.log(1 + refs_count) / math.log(11)  # 10 refs = 1.0

            # Combined importance
            importance = (
                access_score * 0.4 +
                recency_score * 0.3 +
                refs_score * 0.3
            )

            return max(0.0, min(1.0, importance))

        except Exception as e:
            logger.error(f"Failed to calculate importance: {e}")
            return 0.5

    def update_memory_strength(
        self,
        memory_id: str,
        access_boost: float = 0.1
    ) -> bool:
        """
        Update memory strength (Ebbinghaus forgetting curve)

        Each access boosts strength, but strength decays over time.

        Args:
            memory_id: Memory ID
            access_boost: Boost amount per access (default: 0.1)

        Returns:
            True if successful

        Example:
            >>> service = ConsolidationService(...)
            >>> service.update_memory_strength("mem-123", access_boost=0.2)
        """
        try:
            memory = self.vector_db.get(f"{memory_id}-metadata")
            if not memory:
                logger.warning(f"Memory not found: {memory_id}")
                return False

            metadata = memory.get('metadata', {})

            # Get current strength
            current_strength = metadata.get('strength', 0.5)

            # Boost strength
            new_strength = min(1.0, current_strength + access_boost)

            # Update metadata
            self.vector_db.update_metadata(
                f"{memory_id}-metadata",
                {
                    'strength': new_strength,
                    'last_accessed': datetime.now(timezone.utc).isoformat()
                }
            )

            logger.debug(f"Updated strength for {memory_id}: {current_strength:.2f} → {new_strength:.2f}")
            return True

        except Exception as e:
            logger.error(f"Failed to update memory strength: {e}")
            return False

    def get_consolidation_stats(self) -> Dict[str, Any]:
        """
        Get consolidation statistics

        Returns:
            Dict with statistics

        Example:
            >>> service = ConsolidationService(...)
            >>> stats = service.get_consolidation_stats()
            >>> print(stats)
            {'working_memory_count': 50, 'short_term_count': 200, ...}
        """
        try:
            # Query memory counts by type
            # Requires metadata query support

            stats = {
                'working_memory_count': 0,
                'short_term_count': 0,
                'long_term_count': 0,
                'total_clusters': 0,
                'compressed_count': 0
            }

            logger.warning("Consolidation stats require metadata query support")
            return stats

        except Exception as e:
            logger.error(f"Failed to get consolidation stats: {e}")
            return {}
