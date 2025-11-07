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

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import math

from src.models import ModelRouter
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index

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

    def __init__(
        self,
        vector_db: ChromaVectorDB,
        bm25_index: BM25Index,
        model_router: ModelRouter,
        candidate_count: int = 50,
        result_count: int = 10
    ):
        """
        Initialize Search Service

        Args:
            vector_db: ChromaVectorDB instance
            bm25_index: BM25Index instance
            model_router: ModelRouter instance
            candidate_count: Number of candidates to retrieve
            result_count: Number of final results to return
        """
        self.vector_db = vector_db
        self.bm25_index = bm25_index
        self.model_router = model_router
        self.candidate_count = candidate_count
        self.result_count = result_count

        logger.info(f"Initialized SearchService (candidates={candidate_count}, results={result_count})")

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
            final_results = self._rerank(merged_results, query, result_limit)

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

    def _rerank(
        self,
        candidates: List[Dict[str, Any]],
        query: str,
        top_k: int
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

            # Combined score
            combined_score = (
                memory_strength * 0.3 +
                recency_score * 0.2 +
                refs_reliability * 0.1 +
                normalized_bm25 * 0.2 +
                vector_sim * 0.2
            )

            # Add scores to result
            result = candidate.copy()
            result['score'] = combined_score
            result['combined_score'] = combined_score
            result['components'] = {
                'memory_strength': memory_strength,
                'recency': recency_score,
                'refs_reliability': refs_reliability,
                'bm25': normalized_bm25,
                'vector': vector_sim
            }

            scored_results.append(result)

        # Sort by score (descending)
        scored_results.sort(key=lambda x: x['score'], reverse=True)

        # Return top_k
        final_results = scored_results[:top_k]

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
            age_days = (datetime.now() - created_at).days

            # Exponential decay: score = e^(-age/30)
            # 30 days = half-life
            score = math.exp(-age_days / 30.0)
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
