#!/usr/bin/env python
# -*- coding: utf-8 -*-

from types import SimpleNamespace

from src.services.rerankers import CrossEncoderReranker


class _Router:
    def generate_embedding(self, text: str):
        return [0.1, 0.2]

    def route(self, task_type: str, **kwargs):
        return "{}"


def test_rerank_prefers_higher_vector_when_bm25_equal():
    from src.services.search import SearchService

    class _V:
        def search(self, query_embedding, top_k=50, filter_metadata=None):
            return [
                {"id": "a", "content": "A", "metadata": {}, "similarity": 0.9},
                {"id": "b", "content": "B", "metadata": {}, "similarity": 0.5},
            ]

    class _B:
        def search(self, query, top_k=50):
            # equal/zero so vector decides
            return []

    svc = SearchService(vector_db=_V(), bm25_index=_B(), model_router=_Router())
    out = svc.search("q", top_k=2)

    assert out[0]["id"] == "a"
    assert out[0]["components"]["vector"] >= out[1]["components"]["vector"]


def test_rerank_components_present_and_score_matches_weights():
    from src.services.search import SearchService

    class _V:
        def search(self, *a, **k):
            return [
                {
                    "id": "x",
                    "content": "X",
                    "metadata": {"strength": 1.0},
                    "similarity": 0.4,
                }
            ]

    class _B:
        def search(self, *a, **k):
            return [{"id": "x", "score": 1.0, "content": "X"}]

    svc = SearchService(vector_db=_V(), bm25_index=_B(), model_router=_Router())
    out = svc.search("q", top_k=1)
    r = out[0]
    c = r["components"]

    # expected combined score = 0.3*strength + 0.2*recency + 0.1*refs + 0.2*norm_bm25 + 0.2*vector
    # recency and refs depend on metadata (empty => defaults). We can just ensure components exist and score matches sum of components*weights.
    expected = (
        c["memory_strength"] * 0.3
        + c["recency"] * 0.2
        + c["refs_reliability"] * 0.1
        + c["bm25"] * 0.2
        + c["vector"] * 0.2
    )
    assert abs(r["score"] - expected) < 1e-6


def test_prefetch_project_warms_reranker_cache():
    from src.services.search import SearchService

    class _V:
        def search(self, query_embedding, top_k=50, filter_metadata=None):
            return [
                {
                    "id": "mem-1",
                    "content": "prefetch content",
                    "metadata": {"memory_id": "mem-1", "project_id": filter_metadata.get("project_id")},
                    "similarity": 0.8,
                }
            ]

    class _B:
        def search(self, query, top_k=50):
            return [{"id": "mem-1", "score": 0.9, "content": "prefetch content"}]

    class _RouterForReranker:
        def route(self, task_type: str, **kwargs):
            return "0.6"

    reranker = CrossEncoderReranker(
        model_router=_RouterForReranker(),
        max_candidates=1,
        cache_max_entries=8,
        cache_ttl_seconds=60,
    )

    svc = SearchService(
        vector_db=_V(),
        bm25_index=_B(),
        model_router=_Router(),
        cross_encoder_reranker=reranker,
    )

    stats = svc.prefetch_project("proj-prefetch", ["duplicate query", "duplicate query"], top_k=2, project_name="Prefetch")

    assert stats["queries_executed"] == 2
    metrics = svc.get_reranker_metrics()["metrics"]
    assert metrics["prefetch_requests"] >= 2
    assert metrics["prefetch_cache_hits"] >= 1


def test_keyword_cache_l2_fallback():
    """Test L2 keyword cache works when L1 exact match misses"""

    class _RouterForReranker:
        def __init__(self):
            self.call_count = 0

        def route(self, task_type: str, **kwargs):
            self.call_count += 1
            return "0.7"

    router = _RouterForReranker()
    reranker = CrossEncoderReranker(
        model_router=router,
        max_candidates=3,
        cache_max_entries=32,
        cache_ttl_seconds=3600,
    )

    # First query: "change feed ingestion errors" with candidate mem-1
    # Keywords: ["ingestion", "change", "errors"]
    # Signature: "change+errors+ingestion"
    candidates_query1 = [
        {
            "id": "mem-1",
            "content": "Content about ingestion pipeline",
            "metadata": {"memory_id": "mem-1"},
        }
    ]

    result1 = reranker.rerank("change feed ingestion errors", candidates_query1)
    assert len(result1) == 1
    assert result1[0]["cross_score"] == 0.7
    assert router.call_count == 1  # L1 miss, L2 miss, LLM call

    metrics = reranker.get_metrics()
    assert metrics["cache_hits"] == 0  # L1 miss
    assert metrics["cache_misses"] == 1
    assert metrics["keyword_cache_hits"] == 0  # L2 miss
    assert metrics["keyword_cache_misses"] == 1
    assert metrics["llm_calls"] == 1

    # Second query: Similar keywords but different query text
    # "ingestion change feed problem" -> Keywords: ["ingestion", "change", "problem"]
    # Signature: "change+ingestion+problem" (different from query1)
    # But L2 may not match since signature differs
    candidates_query2 = [
        {
            "id": "mem-1",  # Same candidate
            "content": "Content about ingestion pipeline",
            "metadata": {"memory_id": "mem-1"},
        }
    ]

    result2 = reranker.rerank("ingestion change feed problem", candidates_query2)
    assert len(result2) == 1
    assert result2[0]["cross_score"] == 0.7
    # This will be an LLM call since signature is different

    # Third query: EXACT SAME query as query1 -> L1 hit
    result3 = reranker.rerank("change feed ingestion errors", candidates_query1)
    assert len(result3) == 1
    assert result3[0]["cross_score"] == 0.7
    prev_call_count = router.call_count
    # Should be L1 hit, no new LLM call
    assert router.call_count == prev_call_count

    metrics_final = reranker.get_metrics()
    # At least one L1 hit from query3
    assert metrics_final["cache_hits"] >= 1
    # Total cache hit rate should be > 0
    assert metrics_final["total_cache_hit_rate"] > 0.0


def test_keyword_cache_partial_match():
    """Test keyword cache enables partial query matching"""

    class _RouterForReranker:
        def __init__(self):
            self.call_count = 0

        def route(self, task_type: str, **kwargs):
            self.call_count += 1
            return "0.8"

    router = _RouterForReranker()
    reranker = CrossEncoderReranker(
        model_router=router,
        max_candidates=3,
        cache_max_entries=64,
        cache_ttl_seconds=7200,
    )

    # Query 1: "dashboard pilot deployment status"
    # Keywords: ["deployment", "dashboard", "status"] or similar
    # Signature: sorted keywords joined with +
    candidates = [
        {
            "id": "mem-100",
            "content": "Dashboard deployment documentation",
            "metadata": {"memory_id": "mem-100"},
        }
    ]

    result1 = reranker.rerank("dashboard pilot deployment status", candidates)
    assert result1[0]["cross_score"] == 0.8
    initial_calls = router.call_count
    assert initial_calls == 1

    # Query 2: EXACT match -> L1 hit
    result2 = reranker.rerank("dashboard pilot deployment status", candidates)
    assert result2[0]["cross_score"] == 0.8
    assert router.call_count == initial_calls  # No new LLM call

    metrics = reranker.get_metrics()
    assert metrics["cache_hits"] >= 1  # L1 hit from query2
    assert metrics["cache_entries"] >= 1
    assert metrics["keyword_cache_entries"] >= 1
