#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test semantic similarity cache (L3) functionality
Phase 3 verification - similar queries should hit L3 cache
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.rerankers import CrossEncoderReranker
import hashlib

class MockRouter:
    """Mock router with embedding generation for semantic cache testing"""
    def __init__(self):
        self.call_count = 0

    def route(self, task_type: str, **kwargs):
        """Mock LLM route call - returns fixed score"""
        self.call_count += 1
        return "0.75"

    def generate_embedding(self, text: str):
        """
        Generate deterministic embedding based on text content.
        Similar texts produce similar embeddings (cosine similarity).
        """
        import math

        # Start with a fixed base vector for all queries
        # This ensures semantic similarity is based on keyword overlap
        base = [0.01] * 384  # Small baseline value

        # Extract keywords
        keywords = set(text.lower().split())

        # Strong boost for "change feed" topic
        if 'change' in keywords or 'feed' in keywords:
            for i in range(0, 100):
                base[i] += 5.0

        # Strong boost for "ingestion/consuming/data" concepts
        if 'ingestion' in keywords or 'consuming' in keywords or 'data' in keywords:
            for i in range(0, 100):
                base[i] += 5.0

        # Strong boost for "errors/problems/issues" concepts
        if 'errors' in keywords or 'problems' in keywords or 'issues' in keywords:
            for i in range(0, 100):
                base[i] += 5.0

        # Strong boost for "dashboard" topic (different semantic space)
        if 'dashboard' in keywords:
            for i in range(200, 300):
                base[i] += 5.0

        # Strong boost for "deployment/pilot" concepts
        if 'deployment' in keywords or 'pilot' in keywords:
            for i in range(200, 300):
                base[i] += 5.0

        # Normalize to unit length
        magnitude = math.sqrt(sum(x * x for x in base))
        if magnitude > 0:
            base = [x / magnitude for x in base]

        return base

# Initialize
router = MockRouter()
reranker = CrossEncoderReranker(
    model_router=router,
    cache_max_entries=256,
    cache_ttl_seconds=28800,  # 8 hours
    semantic_similarity_threshold=0.85,
    log_interval=0  # Disable automatic logging
)

# Test candidates
candidates = [
    {
        'id': 'mem_001',
        'content': 'Change feed ingestion process for handling data streams',
        'metadata': {'project_id': 'proj_alpha'}
    },
    {
        'id': 'mem_002',
        'content': 'Dashboard deployment configuration and setup',
        'metadata': {'project_id': 'proj_alpha'}
    },
]

print("=" * 70)
print("Phase 3: Semantic Cache (L3) Test")
print("=" * 70)
print(f"Threshold: {reranker.semantic_similarity_threshold}")
print(f"TTL: {reranker.cache_ttl_seconds}s ({reranker.cache_ttl_seconds / 3600}h)")
print()

# Query 1: "change feed ingestion errors" - LLM call
print("Query 1: 'change feed ingestion errors'")
results1 = reranker.rerank("change feed ingestion errors", candidates.copy())
metrics1 = reranker.get_metrics()
print(f"  L1 hits: {metrics1['cache_hits']}")
print(f"  L2 hits: {metrics1['keyword_cache_hits']}")
print(f"  L3 hits: {metrics1['semantic_cache_hits']}")
print(f"  LLM calls: {metrics1['llm_calls']}")
print(f"  Semantic cache candidates: {metrics1['semantic_cache_candidates']}")
print(f"  Semantic cache embeddings: {metrics1['semantic_cache_embeddings']}")
print()

# Query 2: "change feed ingestion errors" - L1 hit (exact match)
print("Query 2: 'change feed ingestion errors' (exact repeat)")
results2 = reranker.rerank("change feed ingestion errors", candidates.copy())
metrics2 = reranker.get_metrics()
print(f"  L1 hits: {metrics2['cache_hits']}")
print(f"  L2 hits: {metrics2['keyword_cache_hits']}")
print(f"  L3 hits: {metrics2['semantic_cache_hits']}")
print(f"  LLM calls: {metrics2['llm_calls']}")
print(f"  [OK] L1 hit!" if metrics2['cache_hits'] > metrics1['cache_hits'] else "  [X] Expected L1 hit")
print()

# Query 3: "ingestion errors in change feed" - L2 hit (keyword match)
print("Query 3: 'ingestion errors in change feed' (word order changed)")
results3 = reranker.rerank("ingestion errors in change feed", candidates.copy())
metrics3 = reranker.get_metrics()
print(f"  L1 hits: {metrics3['cache_hits']}")
print(f"  L2 hits: {metrics3['keyword_cache_hits']}")
print(f"  L3 hits: {metrics3['semantic_cache_hits']}")
print(f"  LLM calls: {metrics3['llm_calls']}")
print(f"  [OK] L2 hit!" if metrics3['keyword_cache_hits'] > metrics2['keyword_cache_hits'] else "  [X] Expected L2 hit")
print()

# Query 4: "problems with change feed data ingestion" - L3 hit (semantic similarity)
print("Query 4: 'problems with change feed data ingestion' (semantic similarity)")
results4 = reranker.rerank("problems with change feed data ingestion", candidates.copy())
metrics4 = reranker.get_metrics()
print(f"  L1 hits: {metrics4['cache_hits']}")
print(f"  L2 hits: {metrics4['keyword_cache_hits']}")
print(f"  L3 hits: {metrics4['semantic_cache_hits']}")
print(f"  LLM calls: {metrics4['llm_calls']}")
print(f"  [OK] L3 hit!" if metrics4['semantic_cache_hits'] > metrics3['semantic_cache_hits'] else "  [X] Expected L3 hit")
print()

# Query 5: "issues consuming data from change feed" - L3 hit (semantic similarity)
print("Query 5: 'issues consuming data from change feed' (semantic similarity)")
results5 = reranker.rerank("issues consuming data from change feed", candidates.copy())
metrics5 = reranker.get_metrics()
print(f"  L1 hits: {metrics5['cache_hits']}")
print(f"  L2 hits: {metrics5['keyword_cache_hits']}")
print(f"  L3 hits: {metrics5['semantic_cache_hits']}")
print(f"  LLM calls: {metrics5['llm_calls']}")
print(f"  [OK] L3 hit!" if metrics5['semantic_cache_hits'] > metrics4['semantic_cache_hits'] else "  [X] Expected L3 hit")
print()

# Query 6: "dashboard pilot deployment" - LLM call (different topic)
print("Query 6: 'dashboard pilot deployment' (different topic)")
results6 = reranker.rerank("dashboard pilot deployment", candidates.copy())
metrics6 = reranker.get_metrics()
print(f"  L1 hits: {metrics6['cache_hits']}")
print(f"  L2 hits: {metrics6['keyword_cache_hits']}")
print(f"  L3 hits: {metrics6['semantic_cache_hits']}")
print(f"  LLM calls: {metrics6['llm_calls']}")
print(f"  New LLM calls: {metrics6['llm_calls'] - metrics5['llm_calls']}")
print()

# Summary
print("=" * 70)
print("Summary")
print("=" * 70)
print(f"Total queries: 6")
print(f"Total LLM calls: {metrics6['llm_calls']}")
print(f"Expected LLM calls: 2 (Query 1 + Query 6)")
print(f"L1 hits: {metrics6['cache_hits']}")
print(f"L2 hits: {metrics6['keyword_cache_hits']}")
print(f"L3 hits: {metrics6['semantic_cache_hits']}")
print(f"Total cache hits: {metrics6['cache_hits'] + metrics6['keyword_cache_hits'] + metrics6['semantic_cache_hits']}")
print(f"Total cache hit rate: {metrics6['total_cache_hit_rate'] * 100:.1f}%")
print()
print(f"Semantic cache candidates: {metrics6['semantic_cache_candidates']}")
print(f"Semantic cache embeddings: {metrics6['semantic_cache_embeddings']}")
print()

# Verification
l1_worked = metrics2['cache_hits'] > metrics1['cache_hits']
l2_worked = metrics3['keyword_cache_hits'] > metrics2['keyword_cache_hits']
l3_worked = (
    metrics4['semantic_cache_hits'] > metrics3['semantic_cache_hits']
    and metrics5['semantic_cache_hits'] > metrics4['semantic_cache_hits']
)
total_llm_calls = metrics6['llm_calls']

print("=" * 70)
print("Verification")
print("=" * 70)
print(f"L1 (exact match) cache: {'[OK] PASS' if l1_worked else '[X] FAIL'}")
print(f"L2 (keyword) cache: {'[OK] PASS' if l2_worked else '[X] FAIL'}")
print(f"L3 (semantic) cache: {'[OK] PASS' if l3_worked else '[X] FAIL'}")
print(f"LLM call reduction: {'[OK] PASS' if total_llm_calls == 2 else f'[X] FAIL (expected 2, got {total_llm_calls})'}")
print()

if l1_worked and l2_worked and l3_worked and total_llm_calls == 2:
    print("[OK] ALL TESTS PASSED - Multi-tier cache working correctly!")
else:
    print("[X] SOME TESTS FAILED - Review cache implementation")
