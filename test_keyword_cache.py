#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test to verify keyword cache is working
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.rerankers import CrossEncoderReranker

class MockRouter:
    def __init__(self):
        self.call_count = 0

    def route(self, task_type: str, **kwargs):
        self.call_count += 1
        print(f"  LLM call #{self.call_count}")
        return "0.75"

def test_keyword_cache():
    print("=" * 60)
    print("Keyword Cache Test")
    print("=" * 60)

    router = MockRouter()
    reranker = CrossEncoderReranker(
        model_router=router,
        max_candidates=5,
        cache_max_entries=64,
        cache_ttl_seconds=3600,
        log_interval=0  # Disable automatic logging
    )

    # Test 1: First query - should call LLM
    print("\n[Test 1] First query: 'change feed ingestion errors'")
    candidates1 = [
        {
            "id": "mem-001",
            "content": "Ingestion pipeline details",
            "metadata": {"memory_id": "mem-001"}
        }
    ]
    result1 = reranker.rerank("change feed ingestion errors", candidates1)
    print(f"  Result: cross_score={result1[0]['cross_score']}")
    print(f"  LLM calls so far: {router.call_count}")

    # Test 2: Exact same query - should hit L1
    print("\n[Test 2] Exact same query: 'change feed ingestion errors'")
    result2 = reranker.rerank("change feed ingestion errors", candidates1)
    print(f"  Result: cross_score={result2[0]['cross_score']}")
    print(f"  LLM calls so far: {router.call_count} (should be 1 - L1 hit)")

    # Test 3: Different query, same keywords -> should hit L2
    print("\n[Test 3] Different query, same keywords: 'ingestion errors in change feed'")
    result3 = reranker.rerank("ingestion errors in change feed", candidates1)
    print(f"  Result: cross_score={result3[0]['cross_score']}")
    print(f"  LLM calls so far: {router.call_count} (should be 1 - L2 hit)")

    # Test 4: Completely different query -> should call LLM
    print("\n[Test 4] Different query: 'dashboard pilot deployment'")
    result4 = reranker.rerank("dashboard pilot deployment", candidates1)
    print(f"  Result: cross_score={result4[0]['cross_score']}")
    print(f"  LLM calls so far: {router.call_count} (should be 2 - new LLM call)")

    # Show metrics
    print("\n" + "=" * 60)
    print("Cache Metrics:")
    print("=" * 60)
    metrics = reranker.get_metrics()
    print(f"L1 Cache (Exact Match):")
    print(f"  Hits: {metrics['cache_hits']}")
    print(f"  Misses: {metrics['cache_misses']}")
    print(f"  Hit Rate: {metrics['cache_hit_rate']:.2%}")
    print(f"\nL2 Cache (Keyword Match):")
    print(f"  Hits: {metrics['keyword_cache_hits']}")
    print(f"  Misses: {metrics['keyword_cache_misses']}")
    print(f"  Hit Rate: {metrics['keyword_cache_hit_rate']:.2%}")
    print(f"\nTotal:")
    print(f"  Hit Rate: {metrics['total_cache_hit_rate']:.2%}")
    print(f"  LLM Calls: {metrics['llm_calls']}")
    print(f"  L1 Entries: {metrics['cache_entries']}")
    print(f"  L2 Entries: {metrics['keyword_cache_entries']}")

    # Verify expectations
    print("\n" + "=" * 60)
    print("Verification:")
    print("=" * 60)
    success = True

    if router.call_count != 2:
        print(f"❌ Expected 2 LLM calls, got {router.call_count}")
        success = False
    else:
        print(f"✓ LLM calls correct: {router.call_count}")

    if metrics['cache_hits'] < 1:
        print(f"❌ Expected at least 1 L1 hit, got {metrics['cache_hits']}")
        success = False
    else:
        print(f"✓ L1 hits: {metrics['cache_hits']}")

    if metrics['keyword_cache_hits'] < 1:
        print(f"❌ Expected at least 1 L2 hit, got {metrics['keyword_cache_hits']}")
        success = False
    else:
        print(f"✓ L2 hits: {metrics['keyword_cache_hits']}")

    if metrics['total_cache_hit_rate'] < 0.4:
        print(f"❌ Expected hit rate >= 40%, got {metrics['total_cache_hit_rate']:.2%}")
        success = False
    else:
        print(f"✓ Total hit rate: {metrics['total_cache_hit_rate']:.2%}")

    if success:
        print("\n✓✓✓ All tests passed! Keyword cache is working.")
    else:
        print("\n❌❌❌ Some tests failed.")

    return success

if __name__ == "__main__":
    test_keyword_cache()
