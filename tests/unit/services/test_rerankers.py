#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src.services.rerankers import CrossEncoderReranker


class _Router:
    def __init__(self, result: str = "0.5"):
        self._result = result
        self.calls = 0
        self.embedding_calls = 0

    def route(self, *args, **kwargs):
        self.calls += 1
        return self._result

    def generate_embedding(self, text: str):
        """Mock embedding generation for semantic cache"""
        self.embedding_calls += 1
        # Return a dummy embedding
        return [0.1] * 768

    def invoke_task(self, task_type: str, prompt: str):
        """Mock LLM invocation for cross-encoder scoring"""
        self.calls += 1
        return self._result


def _candidates(count: int = 1):
    return [
        {
            "id": f"mem-{i}",
            "content": f"answer {i}",
            "metadata": {"memory_id": f"mem-{i}", "is_memory_entry": True},
        }
        for i in range(count)
    ]


def test_cross_encoder_cache_hits_reduce_llm_calls():
    router = _Router(result="0.9")
    reranker = CrossEncoderReranker(
        model_router=router,
        max_candidates=1,
        cache_max_entries=16,
        cache_ttl_seconds=60,
        skip_rerank_for_simple_queries=False,  # Disable skip to force reranking
    )

    query = "どうやってリリースを進める？具体的な手順を教えてください"  # Longer query
    candidates = _candidates()

    reranker.rerank(query, candidates)
    first_calls = router.calls

    # Re-running with the same query/memory should hit the cache
    reranker.rerank(query, candidates)
    assert router.calls == first_calls  # No new LLM calls due to cache hit

    metrics = reranker.get_metrics()
    assert metrics["cache_hits"] >= 1
    assert metrics["cache_hit_rate"] > 0.0


def test_cross_encoder_metrics_include_latency():
    router = _Router(result="0.3")
    reranker = CrossEncoderReranker(
        model_router=router,
        max_candidates=1,
        cache_max_entries=0,  # disable cache to force LLM call
        cache_ttl_seconds=0,
        skip_rerank_for_simple_queries=False,  # Disable skip to force reranking
    )

    reranker.rerank("Need deployment checklist for production release", _candidates())
    stats = reranker.get_metrics()

    assert stats["llm_calls"] == 1
    assert stats["avg_llm_latency_ms"] >= 0.0


def test_cross_encoder_cache_scoped_by_project():
    """Test that cache key generation includes project_id"""
    router = _Router(result="0.4")
    reranker = CrossEncoderReranker(
        model_router=router,
        max_candidates=1,
        cache_max_entries=16,
        cache_ttl_seconds=60,
        skip_rerank_for_simple_queries=False,
    )

    query = "status timeline for project deployment"
    candidate_a = {
        "id": "mem-1",
        "content": "timeline guide",
        "metadata": {"memory_id": "mem-1", "is_memory_entry": True, "project_id": "proj-a"},
    }
    candidate_b = {
        "id": "mem-1",
        "content": "timeline guide",
        "metadata": {"memory_id": "mem-1", "is_memory_entry": True, "project_id": "proj-b"},
    }

    # Build cache keys manually to verify they differ by project_id
    key_a = reranker._build_cache_key(query, candidate_a)
    key_b = reranker._build_cache_key(query, candidate_b)

    # Cache keys should be different because project_id differs
    assert key_a != key_b, f"Cache keys should differ by project_id: {key_a} vs {key_b}"
    assert "proj-a" in key_a
    assert "proj-b" in key_b


def test_prefetch_stats_accumulate_and_hit_cache():
    router = _Router(result="0.7")
    reranker = CrossEncoderReranker(
        model_router=router,
        max_candidates=1,
        cache_max_entries=16,
        cache_ttl_seconds=60,
        skip_rerank_for_simple_queries=False,  # Disable skip to test prefetch
    )

    query = "prefetch me for deployment testing"  # Longer query
    candidates = _candidates()

    # First run should miss cache
    reranker.rerank(query, candidates, prefetch=True)
    # Second run reuses the cached score
    reranker.rerank(query, candidates, prefetch=True)

    metrics = reranker.get_metrics()
    assert metrics["prefetch_requests"] == 2
    assert metrics["prefetch_cache_hits"] >= 1
    assert metrics["prefetch_cache_misses"] >= 1
