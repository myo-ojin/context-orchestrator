#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search Service

Provides hybrid search (vector + BM25) with reranking.

Search pipeline:
1. Generate query embedding (local LLM)
2. Vector search (Chroma) → top 100 candidates (Phase 3)
3. BM25 search → top 50 candidates (Phase 3)
4. Merge and deduplicate results
5. Rerank by rule-based scoring → top 10 results

Requirements: Requirement 8 (MVP - Hybrid Search), Phase 3 (Chunk/Vector Retrieval Tuning)
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import math
from concurrent.futures import ThreadPoolExecutor

from src.models import ModelRouter
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index
from src.services.project_manager import ProjectManager
from src.services.query_attributes import QueryAttributeExtractor, QueryAttributes
from src.services.rerankers import CrossEncoderReranker
from src.services.project_memory_pool import ProjectMemoryPool

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
        vector_candidate_count: Optional[int] = None,
        bm25_candidate_count: Optional[int] = None,
        result_count: int = 10,
        recency_half_life_hours: Optional[float] = None,
        project_manager: Optional[ProjectManager] = None,
        query_attribute_extractor: Optional[QueryAttributeExtractor] = None,
        query_attribute_min_confidence: float = 0.4,
        query_attribute_llm_enabled: bool = True,
        cross_encoder_reranker: Optional[CrossEncoderReranker] = None,
        rerank_weights: Optional[Dict[str, float]] = None,
        project_memory_pool: Optional[ProjectMemoryPool] = None,
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
        self.vector_candidate_count = vector_candidate_count or candidate_count
        self.bm25_candidate_count = bm25_candidate_count or candidate_count
        self.result_count = result_count
        self.recency_half_life_hours = recency_half_life_hours or 24.0
        self.project_manager = project_manager
        if query_attribute_extractor:
            self.query_attribute_extractor = query_attribute_extractor
        else:
            self.query_attribute_extractor = QueryAttributeExtractor(
                model_router=model_router,
                min_llm_confidence=query_attribute_min_confidence,
                llm_enabled=query_attribute_llm_enabled
            )
        self.cross_encoder_reranker = cross_encoder_reranker
        self.rerank_weights = self._prepare_rerank_weights(rerank_weights)
        self.project_memory_pool = project_memory_pool

        logger.info(
            "Initialized SearchService (vector_candidates=%d, bm25_candidates=%d, "
            "final_results=%d, recency_half_life=%.1fh, memory_pool=%s)",
            self.vector_candidate_count,
            self.bm25_candidate_count,
            result_count,
            self.recency_half_life_hours,
            "enabled" if project_memory_pool else "disabled"
        )

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        prefetch: bool = False,
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

            log_fn = logger.debug if prefetch else logger.info
            log_fn(f"Searching for: '{query[:100]}...' (top_k={result_limit}, prefetch={prefetch})")
            start_time = datetime.now()

            # Step 1: Generate query embedding
            query_embedding = self._generate_query_embedding(query)
            logger.debug("Generated query embedding")

            # Step 2 & 3: Vector search (embedding) + BM25 search in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                vector_future = executor.submit(
                    self._vector_search,
                    query_embedding,
                    self.vector_candidate_count,
                    filters
                )
                bm25_future = executor.submit(
                    self._bm25_search,
                    query,
                    self.bm25_candidate_count
                )
                vector_results = vector_future.result()
                bm25_results = bm25_future.result()

            logger.debug(f"Vector search returned {len(vector_results)} results")
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
            final_results = self._apply_cross_encoder_rerank(
                query,
                final_results,
                prefetch=prefetch
            )

            # Calculate search time
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            log_fn(f"Search completed in {elapsed:.0f}ms, returned {len(final_results)} results (prefetch={prefetch})")

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
        # DISABLED: QAM extraction causes timeout in mcp_replay due to LLM fallback
        # 各検索クエリでLLM fallbackが発生し、28クエリ×3.3s/call で累積遅延が発生
        # 現状のVector+BM25でPrecision 71.2%を達成しており、QAMメタデータなしでも十分機能している
        # See: タイムアウト調査 2025-11-11
        return None

        # 以下のコードは保持（将来の再有効化に備える）
        # if not self.query_attribute_extractor or not query:
        #     return None
        # try:
        #     return self.query_attribute_extractor.extract(query)
        # except Exception as exc:  # pragma: no cover - safeguard
        #     logger.warning(f"Attribute extraction failed: {exc}")
        #     return None

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
        results: List[Dict[str, Any]],
        prefetch: bool = False
    ) -> List[Dict[str, Any]]:
        if not self.cross_encoder_reranker or not results:
            return results
        try:
            prioritized = self._prioritize_for_cross_encoder(results)
            reranked = self.cross_encoder_reranker.rerank(
                query,
                prioritized,
                prefetch=prefetch
            )
            return reranked if reranked else results
        except Exception as exc:
            logger.warning(f"Cross-encoder rerank failed: {exc}")
            return results

    @staticmethod
    def _prioritize_for_cross_encoder(
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        memory_entries: List[Dict[str, Any]] = []
        others: List[Dict[str, Any]] = []

        for item in results:
            metadata = item.get('metadata', {})
            if metadata.get('is_memory_entry'):
                memory_entries.append(item)
            else:
                others.append(item)

        return memory_entries + others if memory_entries else results

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
            w = self.rerank_weights
            combined_score = (
                memory_strength * w['memory_strength'] +
                recency_score * w['recency'] +
                refs_reliability * w['refs_reliability'] +
                normalized_bm25 * w['bm25_score'] +
                vector_sim * w['vector_similarity'] +
                metadata_bonus * w['metadata_bonus']
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
                'bm25_score': normalized_bm25,
                'vector': vector_sim,
                'vector_similarity': vector_sim,
                'metadata': metadata_bonus,
                'metadata_bonus': metadata_bonus
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

        source = str(metadata.get('source', '') or '').lower()
        if source == 'session':
            bonus -= 0.05

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
        filtered = [
            item for item in results
            if item.get('metadata', {}).get('is_memory_entry') and item.get('content')
        ]
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
        if (
            existing_candidate and
            not existing_candidate.get('content') and
            candidate.get('content')
        ):
            existing_candidate['content'] = candidate['content']
            existing_candidate['metadata'] = existing_candidate.get('metadata', {})

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
        additional_filters: Optional[Dict[str, Any]] = None,
        prefetch: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search memories within a specific project using graduated degradation workflow.

        Workflow A (Graduated Degradation):
        1. Try memory pool search (if pool loaded)
        2. If results sufficient → return
        3. If results insufficient → fallback to full search

        Args:
            project_id: Project ID to filter by
            query: Search query string
            top_k: Number of results to return (overrides default)
            additional_filters: Optional additional metadata filters
                (e.g., {'schema_type': 'Incident'})
            prefetch: Prefetch flag (for cache warming)

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

        Requirements: Issue #2025-11-11-03 - Workflow A (Graduated Degradation)
        """
        try:
            log_fn = logger.debug if prefetch else logger.info
            log_fn(
                "[Workflow A] Searching in project %s: '%s...' (prefetch=%s)",
                project_id,
                query[:100],
                prefetch
            )

            start_time = datetime.now()
            final_top_k = top_k or self.result_count

            # Step 1: Get project memory pool
            memory_ids = set()
            if self.project_memory_pool:
                memory_ids = self.project_memory_pool.get_memory_ids(project_id)
                log_fn("[Workflow A] Memory pool size: %d memories", len(memory_ids))

            # Step 2a: Search within memory pool
            pool_results = []
            if memory_ids:
                pool_results = self._search_within_pool(
                    query=query,
                    memory_ids=memory_ids,
                    top_k=final_top_k,
                    additional_filters=additional_filters,
                    prefetch=prefetch
                )
                log_fn("[Workflow A] Pool search returned %d results", len(pool_results))

            # Step 3: Check if results are sufficient
            if self._is_result_sufficient(pool_results, final_top_k):
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                log_fn(
                    "[Workflow A] Sufficient results from pool in %.0fms",
                    elapsed
                )
                return pool_results

            # Step 2b: Fallback to full search
            log_fn(
                "[Workflow A] Insufficient results (%d), falling back to full search",
                len(pool_results)
            )

            filters = {'project_id': project_id}
            if additional_filters:
                filters.update(additional_filters)

            full_results = self.search(
                query=query,
                top_k=final_top_k,
                filters=filters,
                prefetch=prefetch
            )

            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            log_fn(
                "[Workflow A] Full search completed in %.0fms, returned %d results",
                elapsed,
                len(full_results)
            )

            return full_results

        except Exception as e:
            logger.error(f"Project search failed: {e}", exc_info=True)
            return []

    def prefetch_project(
        self,
        project_id: str,
        queries: List[str],
        top_k: Optional[int] = None,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Warm up search/reranker caches for a project.

        Workflow:
        1. Load project memory pool and warm L3 semantic cache (query-agnostic)
        2. Execute prefetch queries for L1/L2 cache warming (query-specific)

        This dual strategy ensures both query-agnostic (memory pool) and
        query-specific (prefetch queries) cache warming.
        """
        stats = {
            'project_id': project_id,
            'project_name': project_name,
            'queries_requested': len(queries or []),
            'queries_executed': 0,
            'total_results': 0,
            'reranker_delta': {},
            'pool_stats': {},
        }
        if not project_id:
            return stats

        # Step 1: Warm L3 semantic cache with memory pool (query-agnostic)
        if self.project_memory_pool and self.cross_encoder_reranker:
            try:
                pool_stats = self.project_memory_pool.warm_cache(
                    reranker=self.cross_encoder_reranker,
                    project_id=project_id
                )
                stats['pool_stats'] = pool_stats
                logger.info(
                    "[Prefetch] Warmed L3 cache for project %s: %d memories, %d cache entries in %.0fms",
                    project_id,
                    pool_stats.get('memories_loaded', 0),
                    pool_stats.get('cache_entries_added', 0),
                    pool_stats.get('elapsed_ms', 0)
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "[Prefetch] Failed to warm cache for project %s: %s",
                    project_id,
                    exc
                )
                stats['pool_stats'] = {'error': str(exc)}

        # Step 2: Execute prefetch queries for L1/L2 cache warming (query-specific)
        if not queries:
            return stats

        before_metrics = self.get_reranker_metrics().get('metrics', {}) if self.cross_encoder_reranker else {}

        for query in queries:
            trimmed = (query or "").strip()
            if not trimmed:
                continue
            stats['queries_executed'] += 1
            results = self.search_in_project(
                project_id=project_id,
                query=trimmed,
                top_k=top_k,
                prefetch=True
            )
            stats['total_results'] += len(results)

        if self.cross_encoder_reranker:
            after_metrics = self.cross_encoder_reranker.get_metrics()
            stats['reranker_delta'] = {
                key: after_metrics.get(key, 0) - before_metrics.get(key, 0)
                for key in (
                    'cache_hits',
                    'cache_misses',
                    'prefetch_cache_hits',
                    'prefetch_cache_misses',
                    'prefetch_requests',
                    'pairs_scored',
                )
            }

        logger.info(
            "[Prefetch] Completed for project %s (%s): %d/%d queries executed, pool=%d memories, cache hits +%s",
            project_id,
            project_name or project_id,
            stats['queries_executed'],
            stats['queries_requested'],
            stats['pool_stats'].get('memories_loaded', 0),
            stats['reranker_delta'].get('cache_hits', 0)
        )
        return stats

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

    def get_reranker_metrics(self) -> Dict[str, Any]:
        """
        Return cross-encoder reranker metrics (cache hit rate, latency, etc.).
        """
        if not self.cross_encoder_reranker:
            return {'enabled': False}
        return {
            'enabled': self.cross_encoder_reranker.enabled,
            'metrics': self.cross_encoder_reranker.get_metrics()
        }

    @staticmethod
    def _prepare_rerank_weights(
        weights: Optional[Dict[str, float]]
    ) -> Dict[str, float]:
        defaults = {
            'memory_strength': 0.3,
            'recency': 0.2,
            'refs_reliability': 0.1,
            'bm25_score': 0.2,
            'vector_similarity': 0.2,
            'metadata_bonus': 1.0,
        }
        if not weights:
            return defaults
        merged = defaults.copy()
        for key, value in weights.items():
            if key not in merged:
                continue
            try:
                merged[key] = float(value)
            except (TypeError, ValueError):
                continue
        return merged

    def _get_memory_id_from_candidate(self, candidate: Dict[str, Any]) -> str:
        """
        Extract memory ID from a search candidate.

        Candidates can be either chunks or memory entries:
        - Chunks: Have metadata.memory_id pointing to parent memory
        - Memory entries: Have is_memory_entry=True and ID is the memory ID (with -metadata suffix)

        Args:
            candidate: Search candidate dict

        Returns:
            Memory ID (empty string if not found)

        Requirements: Issue #2025-11-11-03 - Workflow A candidate filtering
        """
        # Check if it's a chunk with memory_id
        memory_id = candidate.get('metadata', {}).get('memory_id')
        if memory_id:
            return memory_id

        # Check if it's a memory entry itself
        if candidate.get('metadata', {}).get('is_memory_entry'):
            candidate_id = candidate.get('id', '')
            # Memory entries have "-metadata" suffix, strip it for comparison
            if candidate_id.endswith('-metadata'):
                return candidate_id[:-9]  # Remove "-metadata" suffix
            return candidate_id

        return ''

    def _is_result_sufficient(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
        min_score_threshold: float = 0.3
    ) -> bool:
        """
        Determine if search results are sufficient.

        Criteria:
        1. Result count >= top_k
        2. Minimum score >= threshold

        Args:
            results: Search results list
            top_k: Expected number of results
            min_score_threshold: Minimum acceptable score

        Returns:
            True if sufficient, False otherwise

        Requirements: Issue #2025-11-11-03 - Workflow A result sufficiency check
        """
        if len(results) < top_k:
            return False

        # Check minimum score
        if results:
            min_score = min(r.get('score', 0.0) for r in results)
            if min_score < min_score_threshold:
                logger.debug(
                    "Results insufficient: min_score=%.3f < %.3f",
                    min_score,
                    min_score_threshold
                )
                return False

        return True

    def _search_within_pool(
        self,
        query: str,
        memory_ids: set,
        top_k: int,
        additional_filters: Optional[Dict[str, Any]],
        prefetch: bool
    ) -> List[Dict[str, Any]]:
        """
        Search within a project memory pool.

        Workflow:
        1. Generate query embedding
        2. Run hybrid search (vector + BM25) to get candidates
        3. Filter candidates by memory_ids
        4. Rerank filtered candidates with cross-encoder

        Args:
            query: Search query
            memory_ids: Set of memory IDs to filter by
            top_k: Number of results to return
            additional_filters: Optional metadata filters
            prefetch: Prefetch flag

        Returns:
            Reranked results list

        Requirements: Issue #2025-11-11-03 - Workflow A pool search
        """
        log_fn = logger.debug if prefetch else logger.info

        # Step 1: Generate query embedding
        query_embedding = self._generate_query_embedding(query)

        # Step 2: Hybrid search (parallel)
        with ThreadPoolExecutor(max_workers=2) as executor:
            vector_future = executor.submit(
                self._vector_search,
                query_embedding,
                self.vector_candidate_count,
                additional_filters
            )
            bm25_future = executor.submit(
                self._bm25_search,
                query,
                self.bm25_candidate_count
            )

            vector_results = vector_future.result()
            bm25_results = bm25_future.result()

        # Step 3: Merge candidates
        all_candidates = self._merge_results(vector_results, bm25_results)

        # Step 4: Filter by memory pool
        pool_candidates = [
            c for c in all_candidates
            if self._get_memory_id_from_candidate(c) in memory_ids
        ]

        log_fn(
            "Pool filtering: %d → %d candidates",
            len(all_candidates),
            len(pool_candidates)
        )

        # Step 5: Rerank (rule-based)
        reranked = self._rerank(
            candidates=pool_candidates,
            query=query,
            top_k=top_k,
            filters=additional_filters
        )

        # Step 6: Cross-encoder rerank
        reranked = self._apply_cross_encoder_rerank(
            query=query,
            results=reranked,
            prefetch=prefetch
        )

        return reranked
