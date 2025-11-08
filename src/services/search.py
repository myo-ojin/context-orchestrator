#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search Service

Provides hybrid search (vector + BM25) with reranking.

Search pipeline:
1. Generate query embedding (local LLM)
2. Vector search (Chroma) → top 50 candidates
3. BM25 search → top 50 candidates
4. Merge and deduplicate results
5. Rerank by rule-based scoring → top 10 results

Requirements: Requirement 8 (MVP - Hybrid Search)
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import math

from src.models import ModelRouter
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index
from src.services.project_manager import ProjectManager
from src.services.query_attributes import QueryAttributeExtractor, QueryAttributes
from src.services.rerankers import CrossEncoderReranker

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for hybrid search and retrieval

    Combines vector similarity search and keyword matching (BM25)
    with rule-based reranking for optimal results.

    Attributes:
        vector_db: ChromaVectorDB instance
        bm25_index: BM25Index instance
        model_router: ModelRouter for embedding generation
        candidate_count: Number of candidates to retrieve (default: 50)
        result_count: Number of final results (default: 10)
    """

    _TIER_HALF_LIFE_MULTIPLIER = {
        'working': 1.0,
        'short_term': 3.0,
        'long_term': 6.0
    }

    def __init__(
        self,
        vector_db: ChromaVectorDB,
        bm25_index: BM25Index,
        model_router: ModelRouter,
        candidate_count: int = 50,
        result_count: int = 10,
        recency_half_life_hours: Optional[float] = None,
        project_manager: Optional[ProjectManager] = None,
        query_attribute_extractor: Optional[QueryAttributeExtractor] = None,
        cross_encoder_reranker: Optional[CrossEncoderReranker] = None,
    ):
        """
        Initialize Search Service

        Args:
            vector_db: ChromaVectorDB instance
            bm25_index: BM25Index instance
            model_router: ModelRouter instance
            candidate_count: Number of candidates to retrieve
            result_count: Number of final results to return
            recency_half_life_hours: Half-life (hours) for recency decay (default: 24h)
            recency_half_life_hours: Half-life (hours) for recency decay (default: 24h)
            project_manager: Optional ProjectManager for project-name -> ID mapping
            query_attribute_extractor: Optional extractor for query hints
            cross_encoder_reranker: Optional reranker for LLM-based scoring
        """
        self.vector_db = vector_db
        self.bm25_index = bm25_index
        self.model_router = model_router
        self.candidate_count = candidate_count
        self.result_count = result_count
        self.recency_half_life_hours = recency_half_life_hours or 24.0
        self.project_manager = project_manager
        self.query_attribute_extractor = query_attribute_extractor or QueryAttributeExtractor()
        self.cross_encoder_reranker = cross_encoder_reranker

        logger.info(
            f"Initialized SearchService (candidates={candidate_count}, results={result_count}, "
            f"recency_half_life={self.recency_half_life_hours}h)"
        )

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories using hybrid search

        Args:
            query: Search query string
            top_k: Number of results to return (overrides default)
            filters: Optional metadata filters (e.g., {'schema_type': 'Incident'})

        Returns:
            List of search result dicts, sorted by relevance:
                {
                    'id': str,
                    'content': str,
                    'metadata': dict,
                    'score': float,
                    'vector_similarity': float,
                    'bm25_score': float,
                    'combined_score': float
                }

        Example:
            >>> service = SearchService(...)
            >>> results = service.search("How to fix TypeError?", top_k=5)
            >>> for result in results:
            ...     print(f"{result['score']:.2f}: {result['content'][:100]}")
        """
        try:
            result_limit = top_k if top_k is not None else self.result_count
            query_attributes = self._extract_query_attributes(query)
            filters = self._prepare_filters(filters, query_attributes)

            logger.info(f"Searching for: '{query[:100]}...' (top_k={result_limit})")
            start_time = datetime.now()

            # Step 1: Generate query embedding
            query_embedding = self._generate_query_embedding(query)
            logger.debug("Generated query embedding")

            # Step 2: Vector search
            vector_results = self._vector_search(
                query_embedding,
                top_k=self.candidate_count,
                filters=filters
            )
            logger.debug(f"Vector search returned {len(vector_results)} results")

            # Step 3: BM25 search
            bm25_results = self._bm25_search(
                query,
                top_k=self.candidate_count
            )
            logger.debug(f"BM25 search returned {len(bm25_results)} results")

            # Step 4: Merge results
            merged_results = self._merge_results(vector_results, bm25_results)
            logger.debug(f"Merged to {len(merged_results)} candidates")

            # Step 5: Rerank
            final_results = self._rerank(
                merged_results,
                query,
                result_limit,
                filters=filters,
                query_attributes=query_attributes
            )
            final_results = self._apply_cross_encoder_rerank(query, final_results)

            # Calculate search time
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Search completed in {elapsed:.0f}ms, returned {len(final_results)} results")

            return final_results

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []

    def _generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding vector for query

        Uses local LLM (nomic-embed-text) for privacy.

        Args:
            query: Search query

        Returns:
            Embedding vector (list of floats)
        """
        try:
            return self.model_router.generate_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search vector DB for similar memories

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            filters: Optional metadata filters

        Returns:
            List of result dicts with 'vector_similarity' score
        """
        try:
            results = self.vector_db.search(
                query_embedding=query_embedding,
                top_k=top_k,
                filter_metadata=filters
            )

            # Add vector_similarity field
            for result in results:
                result['vector_similarity'] = result.get('similarity', 0.0)

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _bm25_search(
        self,
        query: str,
        top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search BM25 index for keyword matches

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of result dicts with 'bm25_score'
        """
        try:
            results = self.bm25_index.search(query, top_k=top_k)

            # Enrich with content from vector DB
            enriched_results = []
            for result in results:
                chunk_id = result['id']
                chunk_data = self.vector_db.get(chunk_id)

                if chunk_data:
                    enriched_results.append({
                        'id': chunk_id,
                        'content': chunk_data.get('content', ''),
                        'metadata': chunk_data.get('metadata', {}),
                        'bm25_score': result['score'],
                        'vector_similarity': 0.0  # No vector search done
                    })

            return enriched_results

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def _merge_results(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge and deduplicate results from both searches

        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search

        Returns:
            Merged list of unique results
        """
        # Use dict to deduplicate by ID
        merged = {}

        # Add vector results
        for result in vector_results:
            chunk_id = result['id']
            merged[chunk_id] = result

        # Add or merge BM25 results
        for result in bm25_results:
            chunk_id = result['id']

            if chunk_id in merged:
                # Already exists, merge scores
                merged[chunk_id]['bm25_score'] = result.get('bm25_score', 0.0)
            else:
                # New result from BM25 only
                merged[chunk_id] = result

        return list(merged.values())

    def _extract_query_attributes(self, query: str) -> Optional[QueryAttributes]:
        if not self.query_attribute_extractor or not query:
            return None
        try:
            return self.query_attribute_extractor.extract(query)
        except Exception as exc:  # pragma: no cover - safeguard
            logger.warning(f"Attribute extraction failed: {exc}")
            return None

    def _prepare_filters(
        self,
        filters: Optional[Dict[str, Any]],
        query_attributes: Optional[QueryAttributes]
    ) -> Optional[Dict[str, Any]]:
        if filters:
            combined = dict(filters)
        else:
            combined = {}

        if query_attributes and query_attributes.has_hints():
            self._apply_attribute_filters(combined, query_attributes)

        return combined if combined else None

    def _apply_attribute_filters(
        self,
        filters: Dict[str, Any],
        query_attributes: QueryAttributes
    ) -> None:
        if not self.project_manager or 'project_id' in filters:
            return

        project_name = query_attributes.project_name
        if not project_name:
            return

        try:
            project = self.project_manager.get_project_by_name(project_name)
            if project:
                filters['project_id'] = project.id
                logger.debug(
                    "Applied project filter from query attributes: %s -> %s",
                    project_name,
                    project.id
                )
        except Exception as exc:
            logger.warning(f"Failed to map project hint '{project_name}': {exc}")

    def _apply_cross_encoder_rerank(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not self.cross_encoder_reranker or not results:
            return results
        try:
            reranked = self.cross_encoder_reranker.rerank(query, results)
            return reranked if reranked else results
        except Exception as exc:
            logger.warning(f"Cross-encoder rerank failed: {exc}")
            return results

    def _rerank(
        self,
        candidates: List[Dict[str, Any]],
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
        query_attributes: Optional[QueryAttributes] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using rule-based scoring

        Scoring formula:
            score = (
                memory_strength * 0.3 +
                recency_score * 0.2 +
                refs_reliability * 0.1 +
                bm25_score * 0.2 +
                vector_similarity * 0.2
            )

        Args:
            candidates: List of candidate results
            query: Original query (for context)
            top_k: Number of results to return

        Returns:
            Reranked list of top_k results
        """
        logger.debug(f"Reranking {len(candidates)} candidates...")

        scored_results = []

        for candidate in candidates:
            metadata = candidate.get('metadata', {})

            # Extract scores
            vector_sim = candidate.get('vector_similarity', 0.0)
            bm25_score = candidate.get('bm25_score', 0.0)

            # Normalize BM25 score (BM25 scores can be large)
            normalized_bm25 = self._normalize_bm25(bm25_score)

            # Calculate component scores
            memory_strength = metadata.get('strength', 0.5)
            recency_score = self._calculate_recency_score(metadata)
            refs_reliability = self._calculate_refs_reliability(metadata)
            metadata_bonus = self._calculate_metadata_alignment(
                metadata,
                query,
                filters,
                query_attributes
            )
            # Slightly prioritize fresher tiers (working -> short -> long)
            priority_score = self._memory_priority(metadata)

            # Combined score
            combined_score = (
                memory_strength * 0.3 +
                recency_score * 0.2 +
                refs_reliability * 0.1 +
                normalized_bm25 * 0.2 +
                vector_sim * 0.2 +
                metadata_bonus
            )
            combined_score = max(0.0, min(1.0, combined_score))

            # Add scores to result
            result = candidate.copy()
            result['score'] = combined_score
            result['combined_score'] = combined_score
            result['components'] = {
                'memory_strength': memory_strength,
                'recency': recency_score,
                'refs_reliability': refs_reliability,
                'bm25': normalized_bm25,
                'vector': vector_sim,
                'metadata': metadata_bonus
            }
            result['_priority'] = priority_score

            scored_results.append(result)

        # Sort by score (descending)
        scored_results.sort(key=lambda x: x['score'], reverse=True)

        final_results = self._deduplicate_results(scored_results, top_k)

        logger.debug(f"Reranked to top {len(final_results)} results")
        return final_results

    def _normalize_bm25(self, score: float) -> float:
        """
        Normalize BM25 score to [0, 1] range

        BM25 scores can be arbitrarily large, so we use a sigmoid-like function.

        Args:
            score: Raw BM25 score

        Returns:
            Normalized score in [0, 1]
        """
        if score <= 0:
            return 0.0

        # Sigmoid normalization: 1 / (1 + e^(-k*x))
        # Use k=0.1 for gradual normalization
        normalized = 1.0 / (1.0 + math.exp(-0.1 * score))
        return normalized

    def _calculate_recency_score(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate recency score based on creation time

        Recent memories get higher scores.

        Args:
            metadata: Chunk metadata

        Returns:
            Recency score in [0, 1]
        """
        try:
            created_at_str = metadata.get('created_at')
            if not created_at_str:
                return 0.5  # Default for unknown

            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            age_hours = max(
                0.0,
                (datetime.now() - created_at).total_seconds() / 3600.0
            )

            memory_type = str(metadata.get('memory_type', 'working')).lower()
            multiplier = self._TIER_HALF_LIFE_MULTIPLIER.get(memory_type, 4.0)
            half_life = max(self.recency_half_life_hours * multiplier, 1.0)
            score = math.exp(-age_hours / half_life)
            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.warning(f"Failed to calculate recency score: {e}")
            return 0.5

    def _calculate_refs_reliability(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate reliability score based on refs count

        More refs = more reliable (verified from multiple sources).

        Args:
            metadata: Chunk metadata

        Returns:
            Reliability score in [0, 1]
        """
        refs = metadata.get('refs', [])
        ref_count = len(refs) if isinstance(refs, list) else 0

        # Logarithmic scaling: score = log(1 + count) / log(11)
        # 0 refs = 0.0, 10 refs = 1.0
        if ref_count == 0:
            return 0.0

        score = math.log(1 + ref_count) / math.log(11)
        return min(1.0, score)

    def _calculate_metadata_alignment(
        self,
        metadata: Dict[str, Any],
        query: str,
        filters: Optional[Dict[str, Any]],
        query_attributes: Optional[QueryAttributes]
    ) -> float:
        """
        Heuristic bonus based on metadata alignment with the query/filters.
        Positive bonus for matching topic/severity/project, slight penalty for mismatches.
        """
        bonus = 0.0
        query_lc = (query or "").lower()

        topic = metadata.get('topic')
        if topic:
            topic_lc = str(topic).lower()
            if topic_lc and topic_lc in query_lc:
                bonus += 0.05
            else:
                bonus -= 0.01

        severity = metadata.get('severity')
        if severity and str(severity).lower() == 'high':
            if any(keyword in query_lc for keyword in ('incident', 'inc', 'bug', 'sev', 'pager')):
                bonus += 0.05

        if filters and filters.get('project_id'):
            if metadata.get('project_id') == filters['project_id']:
                bonus += 0.03
            else:
                bonus -= 0.05

        if query_attributes:
            if query_attributes.topic:
                if topic and str(topic).lower() == query_attributes.topic.lower():
                    bonus += 0.05
                elif topic:
                    bonus -= 0.01
            if query_attributes.doc_type:
                doc_type = metadata.get('type')
                if doc_type and str(doc_type).lower() == query_attributes.doc_type.lower():
                    bonus += 0.03
            if query_attributes.severity and severity:
                if str(severity).lower() == query_attributes.severity.lower():
                    bonus += 0.02

        return bonus

    def _memory_priority(self, metadata: Dict[str, Any]) -> int:
        """
        Lower numbers mean higher priority when collapsing duplicates.
        Prefers working/short_term memories and metadata entries over raw chunks.
        """
        memory_type = str(metadata.get('memory_type', 'working')).lower()
        type_priority = {
            'working': 0,
            'short_term': 1,
            'long_term': 2
        }
        priority = type_priority.get(memory_type, 3)

        if not metadata.get('is_memory_entry'):
            if 'chunk_index' in metadata:
                priority += 1
            else:
                priority += 2

        return priority

    def _deduplicate_results(
        self,
        scored_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Collapse duplicate memories (metadata vs chunk, short_term vs long_term copies).
        """
        selected: List[Dict[str, Any]] = []
        memory_index: Dict[Any, int] = {}
        semantic_index: Dict[Any, int] = {}

        for candidate in scored_results:
            metadata = candidate.get('metadata', {})
            memory_key = metadata.get('memory_id')
            semantic_key = None
            semantic_fields = (
                metadata.get('project_id'),
                metadata.get('topic'),
                metadata.get('source'),
                metadata.get('created_at')
            )
            if any(semantic_fields):
                semantic_key = semantic_fields

            if self._should_skip_candidate(candidate, memory_index, memory_key, selected):
                continue

            if self._should_skip_candidate(candidate, semantic_index, semantic_key, selected):
                continue

            selected.append(candidate)
            idx = len(selected) - 1
            if memory_key:
                memory_index[memory_key] = idx
            if semantic_key:
                semantic_index[semantic_key] = idx

        unique_results: List[Dict[str, Any]] = []
        seen_ids = set()
        for item in selected:
            item_id = item.get('id')
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            unique_results.append(item)

        trimmed = unique_results[:top_k]
        trimmed = self._filter_memory_entries(trimmed)
        for item in trimmed:
            item.pop('_priority', None)
        return trimmed

    def _filter_memory_entries(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = [item for item in results if item.get('metadata', {}).get('is_memory_entry')]
        return filtered if filtered else results

    def _should_skip_candidate(
        self,
        candidate: Dict[str, Any],
        index_map: Dict[Any, int],
        key: Any,
        selected: List[Dict[str, Any]]
    ) -> bool:
        """
        Return True if candidate should be skipped due to an existing better entry for the same key.
        """
        if key is None:
            return False

        existing_idx = index_map.get(key)
        if existing_idx is None or existing_idx >= len(selected):
            return False

        existing_candidate = selected[existing_idx]
        if self._is_better_candidate(candidate, existing_candidate):
            selected[existing_idx] = candidate
            index_map[key] = existing_idx
            return True

        return True

    @staticmethod
    def _is_better_candidate(new: Dict[str, Any], existing: Dict[str, Any]) -> bool:
        """
        Decide whether `new` should replace `existing` when deduplicating.
        """
        new_priority = new.get('_priority', 999)
        existing_priority = existing.get('_priority', 999)

        if new_priority != existing_priority:
            return new_priority < existing_priority

        return new.get('score', 0.0) > existing.get('score', 0.0)

    def search_by_metadata(
        self,
        filters: Dict[str, Any],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search by metadata filters only (no query text)

        Args:
            filters: Metadata filters (e.g., {'schema_type': 'Incident'})
            top_k: Number of results

        Returns:
            List of matching results

        Example:
            >>> service = SearchService(...)
            >>> results = service.search_by_metadata({'schema_type': 'Incident'}, top_k=20)
        """
        # This requires metadata filtering in vector DB
        # For now, return empty (implement in production)
        logger.warning("search_by_metadata not fully implemented")
        return []

    def get_related_memories(
        self,
        memory_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find memories related to a given memory

        Uses embedding similarity.

        Args:
            memory_id: Source memory ID
            top_k: Number of related memories to return

        Returns:
            List of related memory dicts

        Example:
            >>> service = SearchService(...)
            >>> related = service.get_related_memories("mem-abc123", top_k=3)
        """
        try:
            # Get source memory
            source = self.vector_db.get(f"{memory_id}-metadata")
            if not source:
                logger.warning(f"Memory not found: {memory_id}")
                return []

            # Search by embedding
            embedding = source.get('embedding')
            if not embedding:
                logger.warning(f"No embedding for memory: {memory_id}")
                return []

            results = self._vector_search(
                embedding,
                top_k=top_k + 1,
                filters={'is_memory_entry': True}
            )  # +1 to exclude self

            # Filter out the source memory itself
            related = [r for r in results if r['id'] != f"{memory_id}-metadata"]

            return related[:top_k]

        except Exception as e:
            logger.error(f"Failed to get related memories: {e}")
            return []

    def get_search_stats(self) -> Dict[str, Any]:
        """
        Get search statistics

        Returns:
            Dict with search statistics

        Example:
            >>> service = SearchService(...)
            >>> stats = service.get_search_stats()
            >>> print(stats)
            {'total_indexed': 450, 'vector_count': 450, 'bm25_count': 450}
        """
        try:
            stats = {
                'total_indexed': self.vector_db.count(),
                'vector_count': self.vector_db.count(),
                'bm25_count': self.bm25_index.count()
            }
            return stats

        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            return {}

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific memory by ID

        Args:
            memory_id: Memory ID to retrieve

        Returns:
            Memory dict with content and metadata, or None if not found

        Example:
            >>> memory = service.get_memory('mem-123')
            >>> print(memory['content'])
        """
        try:
            # Get memory entry from vector DB
            result = self.vector_db.get(f"{memory_id}")

            if not result:
                logger.warning(f"Memory not found: {memory_id}")
                return None

            # Get all chunks for this memory
            chunks_results = self.vector_db.list_by_metadata(
                {'memory_id': memory_id},
                include_documents=True
            )

            # Build response
            memory_data = {
                'memory_id': memory_id,
                'content': result.get('content', ''),
                'metadata': result.get('metadata', {}),
                'chunks': [
                    {
                        'id': chunk.get('id'),
                        'content': chunk.get('content'),
                        'metadata': chunk.get('metadata', {})
                    }
                    for chunk in chunks_results
                ]
            }

            logger.debug(f"Retrieved memory: {memory_id} with {len(chunks_results)} chunks")
            return memory_data

        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None

    def list_recent(
        self,
        limit: int = 20,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List recent memories in chronological order

        Args:
            limit: Maximum number of memories to return
            filter_metadata: Optional metadata filter

        Returns:
            List of memory dicts with summary and metadata

        Example:
            >>> memories = service.list_recent(limit=10)
            >>> for mem in memories:
            >>>     print(f"{mem['memory_id']}: {mem['summary']}")
        """
        try:
            # Build filter
            filter_dict = {'is_memory_entry': True}
            if filter_metadata:
                filter_dict.update(filter_metadata)

            # Get memory entries
            results = self.vector_db.list_by_metadata(
                filter_dict,
                include_documents=True
            )

            # Sort by timestamp (newest first)
            results_sorted = sorted(
                results,
                key=lambda x: x.get('metadata', {}).get('timestamp', ''),
                reverse=True
            )

            # Limit results
            results_limited = results_sorted[:limit]

            # Build response
            memories = []
            for item in results_limited:
                memory_id = item.get('id', 'unknown')
                metadata = item.get('metadata', {})
                content = item.get('content', '')

                memories.append({
                    'memory_id': memory_id,
                    'summary': content[:200] + '...' if len(content) > 200 else content,
                    'schema_type': metadata.get('schema_type', 'Unknown'),
                    'timestamp': metadata.get('timestamp', 'Unknown'),
                    'metadata': metadata
                })

            logger.info(f"Listed {len(memories)} recent memories (limit={limit})")
            return memories

        except Exception as e:
            logger.error(f"Error listing recent memories: {e}")
            return []

    def search_in_project(
        self,
        project_id: str,
        query: str,
        top_k: Optional[int] = None,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories within a specific project

        Args:
            project_id: Project ID to filter by
            query: Search query string
            top_k: Number of results to return (overrides default)
            additional_filters: Optional additional metadata filters
                (e.g., {'schema_type': 'Incident'})

        Returns:
            List of search result dicts, sorted by relevance (same as search())

        Example:
            >>> service = SearchService(...)
            >>> results = service.search_in_project(
            ...     project_id="proj-abc123",
            ...     query="React hooks error",
            ...     additional_filters={"schema_type": "Incident"}
            ... )
            >>> for result in results:
            ...     print(f"{result['score']:.2f}: {result['content'][:100]}")

        Requirements: Phase 15 - Project Management
        """
        try:
            logger.info(f"Searching in project {project_id}: '{query[:100]}...'")

            # Build filters with project_id
            filters = {'project_id': project_id}

            if additional_filters:
                filters.update(additional_filters)

            # Use standard search with project filter
            results = self.search(query=query, top_k=top_k, filters=filters)

            logger.info(f"Project search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Project search failed: {e}", exc_info=True)
            return []

    def list_project_memories(
        self,
        project_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        List recent memories in a specific project

        Args:
            project_id: Project ID to filter by
            limit: Maximum number of memories to return (default: 20)

        Returns:
            List of memory dicts with summary and metadata,
            sorted by timestamp (newest first)

        Example:
            >>> service = SearchService(...)
            >>> memories = service.list_project_memories("proj-abc123", limit=10)
            >>> for mem in memories:
            ...     print(f"{mem['memory_id']}: {mem['summary']}")

        Requirements: Phase 15 - Project Management
        """
        try:
            logger.info(f"Listing memories for project {project_id} (limit={limit})")

            # Use list_recent with project filter
            return self.list_recent(
                limit=limit,
                filter_metadata={'project_id': project_id}
            )

        except Exception as e:
            logger.error(f"Failed to list project memories: {e}")
            return []
