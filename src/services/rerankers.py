#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cross-encoder style reranker scaffold.

Uses the existing ModelRouter to score query/result pairs via an LLM prompt.
Designed as an interim solution until a dedicated cross-encoder model is
available (e.g., BGE). Keeps the contract simple: pass in candidates,
receive a re-ordered list with `cross_score`.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import logging
import time
from time import perf_counter
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock

from src.models import ModelRouter
from src.utils.keyword_extractor import extract_and_build_signature
from src.utils.vector_utils import cosine_similarity

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """LLM-backed reranker that assigns a 0-1 relevance score per candidate."""

    def __init__(
        self,
        model_router: ModelRouter,
        max_candidates: int = 5,
        enabled: bool = True,
        cache_max_entries: int = 128,
        cache_ttl_seconds: int = 900,
        log_interval: int = 50,
        max_parallel_reranks: int = 1,
        fallback_max_wait_ms: int = 0,
        fallback_mode: str = "heuristic",
        semantic_similarity_threshold: float = 0.80,  # Phase 4: Lowered from 0.85 to improve L3 hit rate
        skip_rerank_for_simple_queries: bool = True,  # Phase 4: Skip cross-encoder for low-complexity queries
        simple_query_max_words: int = 3  # Phase 4: Queries with ≤N words are considered simple
    ):
        self.model_router = model_router
        self.max_candidates = max_candidates
        self.enabled = enabled
        self.skip_rerank_for_simple_queries = skip_rerank_for_simple_queries
        self.simple_query_max_words = simple_query_max_words
        self.cache_max_entries = max(0, cache_max_entries)
        self.cache_ttl_seconds = max(0, cache_ttl_seconds)
        self.semantic_similarity_threshold = max(0.0, min(1.0, semantic_similarity_threshold))
        self._cache: "OrderedDict[str, Tuple[float, float]]" = OrderedDict()
        self._keyword_cache: "OrderedDict[str, Tuple[float, float]]" = OrderedDict()
        # L3: Semantic cache - stores (embedding, score, timestamp) per candidate_id
        self._semantic_cache: "Dict[str, List[Tuple[List[float], float, float]]]" = {}
        self._stats = {
            'pairs_scored': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'keyword_cache_hits': 0,
            'keyword_cache_misses': 0,
            'semantic_cache_hits': 0,
            'semantic_cache_misses': 0,
            'prefetch_requests': 0,
            'prefetch_cache_hits': 0,
            'prefetch_cache_misses': 0,
            'llm_calls': 0,
            'llm_failures': 0,
            'llm_latency_ms_total': 0.0,
            'llm_latency_ms_max': 0.0,
            'queue_wait_total_ms': 0.0,
            'queue_wait_max_ms': 0.0,
            'queue_rejections': 0,
            'backlogged_requests': 0,
        }
        self._log_interval = max(0, log_interval)
        self.max_parallel_reranks = max(1, max_parallel_reranks)
        self.fallback_max_wait_ms = max(0, fallback_max_wait_ms)
        self.fallback_mode = fallback_mode
        self._executor: Optional[ThreadPoolExecutor] = None
        self._queue_lock = Lock()
        if self.max_parallel_reranks > 1:
            self._executor = ThreadPoolExecutor(max_workers=self.max_parallel_reranks)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        prefetch: bool = False
    ) -> List[Dict[str, Any]]:
        if not self.enabled or not candidates or not query:
            return candidates

        # Phase 4: Skip reranking for simple queries (reduces LLM overhead)
        if self.skip_rerank_for_simple_queries and self._is_simple_query(query):
            logger.debug(
                "[SKIP_RERANK] Simple query detected (≤%d words), skipping cross-encoder: '%s'",
                self.simple_query_max_words,
                query[:50]
            )
            return candidates

        top_slice = candidates[: self.max_candidates]
        rescored: List[Dict[str, Any]] = []

        # Generate query embedding once for semantic cache (L3)
        # Only generate if cache is enabled
        query_embedding: Optional[List[float]] = None
        if self.cache_max_entries > 0 and self.cache_ttl_seconds > 0:
            try:
                query_embedding = self.model_router.generate_embedding(query)
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Failed to generate query embedding for semantic cache: {exc}")
                query_embedding = None

        if prefetch:
            self._stats['prefetch_requests'] += 1

        if self.max_parallel_reranks <= 1 or not self._executor:
            for entry in top_slice:
                score = self._score_with_cache(query, entry, query_embedding, prefetch=prefetch)
                enriched = entry.copy()
                enriched['cross_score'] = score
                rescored.append(enriched)
        else:
            futures: List[Tuple[Future, Dict[str, Any]]] = []
            for entry in top_slice:
                enqueued_at = perf_counter()
                future = self._executor.submit(
                    self._score_with_wait,
                    query,
                    entry,
                    query_embedding,
                    enqueued_at,
                    prefetch
                )
                futures.append((future, entry))

            for future, entry in futures:
                score, wait_ms = future.result()
                self._stats['queue_wait_total_ms'] += wait_ms
                if wait_ms > self._stats['queue_wait_max_ms']:
                    self._stats['queue_wait_max_ms'] = wait_ms
                if (
                    self.fallback_max_wait_ms
                    and wait_ms > self.fallback_max_wait_ms
                    and self.fallback_mode != "none"
                ):
                    self._stats['queue_rejections'] += 1
                    fallback_score = self._fallback_score(entry)
                    enriched = entry.copy()
                    enriched['cross_score'] = fallback_score
                    rescored.append(enriched)
                    continue
                enriched = entry.copy()
                enriched['cross_score'] = score
                rescored.append(enriched)

        rescored.sort(key=lambda item: item.get('cross_score', 0.0), reverse=True)

        return rescored + candidates[self.max_candidates :]

    def _score_with_cache(
        self,
        query: str,
        candidate: Dict[str, Any],
        query_embedding: Optional[List[float]],
        prefetch: bool = False
    ) -> float:
        cache_key = self._build_cache_key(query, candidate)
        keyword_cache_key = self._build_keyword_cache_key(query, candidate)
        candidate_id = self._extract_candidate_id(candidate)
        now = time.time()
        cache_enabled = (
            self.cache_max_entries > 0
            and self.cache_ttl_seconds > 0
            and cache_key is not None
        )

        # L1: Exact match cache
        if cache_enabled:
            cached = self._cache.get(cache_key)
            if cached:
                score, cached_at = cached
                if now - cached_at <= self.cache_ttl_seconds:
                    self._stats['pairs_scored'] += 1
                    self._stats['cache_hits'] += 1
                    if prefetch:
                        self._stats['prefetch_cache_hits'] += 1
                    self._cache.move_to_end(cache_key)
                    self._maybe_log_cache_stats()
                    return score
                else:
                    self._cache.pop(cache_key, None)
            self._stats['cache_misses'] += 1
            if prefetch:
                self._stats['prefetch_cache_misses'] += 1

        # L2: Keyword-based cache
        if cache_enabled and keyword_cache_key:
            cached_kw = self._keyword_cache.get(keyword_cache_key)
            if cached_kw:
                score, cached_at = cached_kw
                if now - cached_at <= self.cache_ttl_seconds:
                    self._stats['pairs_scored'] += 1
                    self._stats['keyword_cache_hits'] += 1
                    self._keyword_cache.move_to_end(keyword_cache_key)
                    # Also store in L1 for faster future access
                    self._cache[cache_key] = (score, now)
                    if len(self._cache) > self.cache_max_entries:
                        self._cache.popitem(last=False)
                    self._maybe_log_cache_stats()
                    return score
                else:
                    self._keyword_cache.pop(keyword_cache_key, None)
            self._stats['keyword_cache_misses'] += 1

        # L3: Semantic similarity cache
        # Design: When ProjectMemoryPool.warm_cache() pre-loads memory embeddings,
        # we compare query_embedding against memory_embedding. If similarity is high
        # (>= threshold), we estimate the relevance score using heuristics instead
        # of calling LLM. This enables query-agnostic cache warming.
        if cache_enabled and query_embedding and candidate_id:
            if candidate_id in self._semantic_cache:
                # Check all cached embeddings for this candidate
                for cached_emb, cached_score, cached_at in self._semantic_cache[candidate_id]:
                    if now - cached_at <= self.cache_ttl_seconds:
                        similarity = cosine_similarity(query_embedding, cached_emb)

                        # Phase 6: Adaptive threshold strategy
                        # Use staged confidence levels to improve cache hit rate from 2% → 50-60%
                        # Based on analysis: mean similarity 0.627, median 0.630
                        estimated_score = None
                        confidence = None

                        if similarity >= 0.80:
                            # High confidence: Top tier matches
                            estimated_score = similarity * 0.95
                            confidence = "high"
                        elif similarity >= 0.70:
                            # Medium confidence: Good matches (catches +14% more hits)
                            estimated_score = similarity * 0.90
                            confidence = "medium"
                        elif similarity >= 0.60:
                            # Low confidence: Acceptable matches (catches +50% more hits)
                            estimated_score = similarity * 0.85
                            confidence = "low"

                        if estimated_score is not None:
                            # L3 hit! Use staged confidence scoring
                            self._stats['pairs_scored'] += 1
                            self._stats['semantic_cache_hits'] += 1

                            # Store in L1 and L2 for faster future access
                            self._cache[cache_key] = (estimated_score, now)
                            if len(self._cache) > self.cache_max_entries:
                                self._cache.popitem(last=False)
                            if keyword_cache_key:
                                self._keyword_cache[keyword_cache_key] = (estimated_score, now)
                                if len(self._keyword_cache) > self.cache_max_entries:
                                    self._keyword_cache.popitem(last=False)

                            logger.info(
                                "[L3_HIT] candidate=%s similarity=%.3f confidence=%s estimated_score=%.3f",
                                candidate_id,
                                similarity,
                                confidence,
                                estimated_score
                            )
                            self._maybe_log_cache_stats()
                            return estimated_score
                        else:
                            # similarity < 0.60: Fall through to LLM
                            logger.info(
                                "[L3_MISS] candidate=%s similarity=%.3f below_threshold=0.60",
                                candidate_id,
                                similarity
                            )
                    else:
                        logger.debug(
                            "[DEBUG] L3 cached entry expired: candidate=%s age=%.1fs ttl=%ds",
                            candidate_id,
                            now - cached_at,
                            self.cache_ttl_seconds
                        )
            else:
                logger.debug("[DEBUG] L3 candidate not in semantic cache: %s", candidate_id)
            self._stats['semantic_cache_misses'] += 1

        # LLM: Call cross-encoder
        score, _, _ = self._score_pair(query, candidate.get('content', ''))
        self._stats['pairs_scored'] += 1

        # Store in L1, L2, and L3 caches
        if cache_enabled:
            # L1: Exact match
            self._cache[cache_key] = (score, now)
            if len(self._cache) > self.cache_max_entries:
                self._cache.popitem(last=False)

            # L2: Keyword match
            if keyword_cache_key:
                self._keyword_cache[keyword_cache_key] = (score, now)
                if len(self._keyword_cache) > self.cache_max_entries:
                    self._keyword_cache.popitem(last=False)

            # L3: Semantic match
            if query_embedding and candidate_id:
                if candidate_id not in self._semantic_cache:
                    self._semantic_cache[candidate_id] = []
                self._semantic_cache[candidate_id].append((query_embedding, score, now))
                # Limit embeddings per candidate (keep most recent N)
                if len(self._semantic_cache[candidate_id]) > 10:
                    self._semantic_cache[candidate_id] = self._semantic_cache[candidate_id][-10:]
                # Prune entire cache if too large
                if len(self._semantic_cache) > self.cache_max_entries:
                    # Remove oldest candidate entry
                    oldest_candidate = min(
                        self._semantic_cache.keys(),
                        key=lambda cid: min(ts for _, _, ts in self._semantic_cache[cid])
                    )
                    del self._semantic_cache[oldest_candidate]

        self._maybe_log_cache_stats()
        return score

    def _score_pair(self, query: str, candidate_text: str) -> Tuple[float, float, bool]:
        if not candidate_text:
            return 0.0, 0.0, False

        start = perf_counter()
        duration_ms = 0.0
        success = False
        prompt = (
            "You are a reranker that scores how well a retrieved passage answers a query.\n"
            "Return only a floating-point number between 0.0 (irrelevant) and 1.0 (perfect match).\n"
            f"Query:\n{query}\n\nCandidate Passage:\n{candidate_text[:2000]}\n\n"
            "Score (0.0-1.0):"
        )

        try:
            raw = self.model_router.route(
                task_type='short_summary',
                prompt=prompt,
                max_tokens=20,
                temperature=0.0
            )
            score = float(str(raw).strip().split()[0])
            if score < 0.0 or score > 1.5:
                raise ValueError("score out of range")
            success = True
            result = max(0.0, min(1.0, score))
        except Exception as exc:  # pragma: no cover - LLM/CLI failures
            logger.warning(f"Cross-encoder scoring failed: {exc}")
            result = 0.0
        finally:
            duration_ms = (perf_counter() - start) * 1000
            self._stats['llm_calls'] += 1
            self._stats['llm_latency_ms_total'] += duration_ms
            if duration_ms > self._stats['llm_latency_ms_max']:
                self._stats['llm_latency_ms_max'] = duration_ms
            if not success:
                self._stats['llm_failures'] += 1
        return result, duration_ms, success

    def _score_with_wait(
        self,
        query: str,
        candidate: Dict[str, Any],
        query_embedding: Optional[List[float]],
        enqueued_at: float,
        prefetch: bool = False
    ) -> Tuple[float, float]:
        wait_ms = (perf_counter() - enqueued_at) * 1000
        score = self._score_with_cache(query, candidate, query_embedding, prefetch=prefetch)
        return score, wait_ms

    def _fallback_score(self, candidate: Dict[str, Any]) -> float:
        """
        Return a heuristic score when reranker fallback is triggered.
        """
        if self.fallback_mode == "heuristic":
            components = candidate.get('components') or {}
            # Normalize several components to 0-1 range if present
            score = 0.0
            vector = components.get('vector_similarity') or components.get('vector', 0.0)
            bm25 = components.get('bm25_score') or components.get('bm25', 0.0)
            metadata = components.get('metadata_bonus') or components.get('metadata', 0.0)
            recency = components.get('recency', 0.0)
            score += 0.4 * float(vector or 0.0)
            score += 0.3 * float(bm25 or 0.0)
            score += 0.2 * float(metadata or 0.0)
            score += 0.1 * float(recency or 0.0)
            return max(0.0, min(1.0, score))
        return 0.0

    def _build_cache_key(self, query: str, candidate: Dict[str, Any]) -> Optional[str]:
        candidate_id = (
            candidate.get('id')
            or candidate.get('memory_id')
            or candidate.get('metadata', {}).get('memory_id')
        )
        if not candidate_id:
            return None
        metadata = candidate.get('metadata') or {}
        project_scope = metadata.get('project_id') or metadata.get('project')
        if project_scope:
            return f"{query}::{project_scope}::{candidate_id}"
        return f"{query}::{candidate_id}"

    def _extract_candidate_id(self, candidate: Dict[str, Any]) -> Optional[str]:
        """
        Extract candidate ID from candidate dict.

        Returns:
            Candidate ID string or None if not found
        """
        return (
            candidate.get('id')
            or candidate.get('memory_id')
            or candidate.get('metadata', {}).get('memory_id')
        )

    def _build_keyword_cache_key(self, query: str, candidate: Dict[str, Any]) -> Optional[str]:
        """
        Build keyword-based cache key for partial query matching.

        Extracts top 3 keywords from query and builds signature.
        Format: {keyword_signature}::{project_scope}::{candidate_id}

        Examples:
            "change feed ingestion errors" -> "change+errors+ingestion::proj123::mem456"
            "dashboard pilot deployment" -> "dashboard+deployment+pilot::mem789"
        """
        candidate_id = self._extract_candidate_id(candidate)
        if not candidate_id:
            return None

        # Extract keywords (top 3 by default)
        keyword_signature = extract_and_build_signature(query, top_n=3)
        if not keyword_signature:
            return None

        metadata = candidate.get('metadata') or {}
        project_scope = metadata.get('project_id') or metadata.get('project')
        if project_scope:
            return f"{keyword_signature}::{project_scope}::{candidate_id}"
        return f"{keyword_signature}::{candidate_id}"

    def _maybe_log_cache_stats(self) -> None:
        if not self._log_interval or not self._stats['pairs_scored']:
            return
        if self._stats['pairs_scored'] % self._log_interval == 0:
            metrics = self.get_metrics()
            if not metrics.get('enabled', True):
                return
            logger.info(
                "Cross-encoder cache stats: L1_hits=%d L1_miss=%d L2_hits=%d L2_miss=%d "
                "L3_hits=%d L3_miss=%d total_hit_rate=%.2f avg_llm=%.1fms",
                metrics['cache_hits'],
                metrics['cache_misses'],
                metrics['keyword_cache_hits'],
                metrics['keyword_cache_misses'],
                metrics['semantic_cache_hits'],
                metrics['semantic_cache_misses'],
                metrics['total_cache_hit_rate'],
                metrics['avg_llm_latency_ms']
            )

    def get_metrics(self) -> Dict[str, Any]:
        cache_events = self._stats['cache_hits'] + self._stats['cache_misses']
        keyword_cache_events = self._stats['keyword_cache_hits'] + self._stats['keyword_cache_misses']
        semantic_cache_events = self._stats['semantic_cache_hits'] + self._stats['semantic_cache_misses']
        llm_calls = self._stats['llm_calls']
        pairs_scored = self._stats['pairs_scored']

        # Count semantic cache entries (total embeddings stored)
        semantic_cache_embeddings = sum(len(embs) for embs in self._semantic_cache.values())

        # Total cache hit rate: percentage of pairs served from cache (not requiring LLM)
        # This is the most accurate measure of cache effectiveness
        total_cache_hit_rate = (
            1.0 - (llm_calls / pairs_scored) if pairs_scored > 0 else 0.0
        )

        return {
            'enabled': self.enabled,
            'pairs_scored': pairs_scored,
            'cache_entries': len(self._cache),
            'keyword_cache_entries': len(self._keyword_cache),
            'semantic_cache_candidates': len(self._semantic_cache),
            'semantic_cache_embeddings': semantic_cache_embeddings,
            'cache_size': self.cache_max_entries,
            'cache_ttl_seconds': self.cache_ttl_seconds,
            'semantic_similarity_threshold': self.semantic_similarity_threshold,
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'cache_hit_rate': (
                self._stats['cache_hits'] / cache_events if cache_events else 0.0
            ),
            'keyword_cache_hits': self._stats['keyword_cache_hits'],
            'keyword_cache_misses': self._stats['keyword_cache_misses'],
            'keyword_cache_hit_rate': (
                self._stats['keyword_cache_hits'] / keyword_cache_events if keyword_cache_events else 0.0
            ),
            'semantic_cache_hits': self._stats['semantic_cache_hits'],
            'semantic_cache_misses': self._stats['semantic_cache_misses'],
            'semantic_cache_hit_rate': (
                self._stats['semantic_cache_hits'] / semantic_cache_events if semantic_cache_events else 0.0
            ),
            'total_cache_hit_rate': total_cache_hit_rate,
            'prefetch_requests': self._stats['prefetch_requests'],
            'prefetch_cache_hits': self._stats['prefetch_cache_hits'],
            'prefetch_cache_misses': self._stats['prefetch_cache_misses'],
            'llm_calls': llm_calls,
            'llm_failures': self._stats['llm_failures'],
            'avg_llm_latency_ms': (
                self._stats['llm_latency_ms_total'] / llm_calls if llm_calls else 0.0
            ),
            'max_llm_latency_ms': self._stats['llm_latency_ms_max'],
            'queue_wait_avg_ms': (
                self._stats['queue_wait_total_ms'] / pairs_scored
                if pairs_scored > 0
                else 0.0
            ),
            'queue_wait_max_ms': self._stats['queue_wait_max_ms'],
            'queue_rejections': self._stats['queue_rejections'],
            'max_parallel_reranks': self.max_parallel_reranks,
        }

    def warm_semantic_cache_from_pool(
        self,
        embeddings: Dict[str, List[float]]
    ) -> int:
        """
        Warm the L3 semantic cache with pre-computed embeddings from a project pool.

        This is the key optimization for ProjectMemoryPool: instead of waiting for
        queries to populate the semantic cache organically, we pre-load memory
        embeddings for all project memories. This enables query-agnostic cache hits:
        when a query arrives, we compare its embedding against these pre-loaded
        memory embeddings. If similarity >= threshold (0.85), we use the similarity
        as a heuristic relevance score, avoiding the LLM call entirely.

        Design rationale:
        - Memory embeddings represent the semantic content of each candidate
        - Query embeddings represent the user's search intent
        - High similarity (cosine >= 0.85) indicates the memory is likely relevant
        - Using similarity as score provides reasonable ranking without LLM overhead

        Args:
            embeddings: Dict of {candidate_id: memory_embedding_vector}

        Returns:
            Number of cache entries added

        Requirements: Issue #2025-11-11-03 - Project Memory Pool
        """
        if not embeddings:
            return 0

        if self.cache_max_entries == 0 or self.cache_ttl_seconds == 0:
            logger.debug("Semantic cache disabled, skipping warm-up")
            return 0

        now = time.time()
        added = 0

        for candidate_id, embedding in embeddings.items():
            if not candidate_id or not embedding:
                continue

            # Initialize cache entry for this candidate if not present
            if candidate_id not in self._semantic_cache:
                self._semantic_cache[candidate_id] = []

            # Store memory embedding with dummy score (will use similarity as score on hit)
            # The embedding will be compared against query embeddings during searches
            self._semantic_cache[candidate_id].append((embedding, 0.0, now))
            added += 1
            if added <= 5:  # Log first 5 entries only
                logger.info(
                    "[WARM_CACHE] Stored embedding for %s, vector length: %d",
                    candidate_id,
                    len(embedding)
                )

        logger.info(
            "[WARM_CACHE] Warmed semantic cache with %d memory embeddings from project pool",
            added
        )
        return added

    def _is_simple_query(self, query: str) -> bool:
        """
        Determine if query is simple enough to skip cross-encoder reranking (Phase 4).

        Simple queries are those with few words and no complex structure.
        For such queries, hybrid search (vector + BM25) is usually sufficient.

        Criteria for simple query:
        - Word count ≤ simple_query_max_words (default: 3)
        - Examples: "timeline view", "auth error", "deployment guide"

        Args:
            query: Search query string

        Returns:
            True if query is simple, False otherwise

        Requirements: Phase 4 - Cache & Reranker Optimization
        """
        if not query:
            return True

        # Count words (split by whitespace, filter empty strings)
        words = [w for w in query.split() if w.strip()]
        word_count = len(words)

        # Simple if ≤ max_words threshold
        return word_count <= self.simple_query_max_words
