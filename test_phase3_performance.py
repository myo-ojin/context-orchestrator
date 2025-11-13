#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 3 Performance Test - Real Ollama embeddings
Measure L1/L2/L3 cache hit rates with actual semantic similarity
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import Config
from models.router import ModelRouter
from models.local_llm import LocalLLMClient
from models.cli_llm import CLILLMClient
from services.rerankers import CrossEncoderReranker

# Initialize real components
config = Config()
local_llm = LocalLLMClient(config)
cli_llm = CLILLMClient(config)
router = ModelRouter(config, local_llm, cli_llm)

# Create reranker with Phase 3 settings
reranker = CrossEncoderReranker(
    model_router=router,
    cache_max_entries=256,
    cache_ttl_seconds=28800,  # 8 hours
    semantic_similarity_threshold=0.85,
    log_interval=0
)

print("=" * 70)
print("Phase 3: Real-world Performance Test")
print("=" * 70)
print(f"Cache size: {reranker.cache_max_entries}")
print(f"TTL: {reranker.cache_ttl_seconds}s ({reranker.cache_ttl_seconds / 3600}h)")
print(f"Semantic threshold: {reranker.semantic_similarity_threshold}")
print()

# Test candidates
candidates = [
    {
        'id': 'mem_001',
        'content': 'Change feed ingestion process handles data stream errors',
        'metadata': {'project_id': 'proj_alpha', 'memory_id': 'mem_001'}
    },
    {
        'id': 'mem_002',
        'content': 'Dashboard deployment pipeline configuration',
        'metadata': {'project_id': 'proj_alpha', 'memory_id': 'mem_002'}
    },
]

# Test queries - mix of exact, keyword, and semantic matches
test_cases = [
    ("change feed ingestion errors", "Q1: Original query (LLM call expected)"),
    ("change feed ingestion errors", "Q2: Exact repeat (L1 hit expected)"),
    ("ingestion errors in change feed", "Q3: Word order changed (L2 hit expected)"),
    ("problems with change feed data ingestion", "Q4: Semantic similarity (L3 hit expected)"),
    ("issues consuming data from change feed", "Q5: Semantic similarity (L3 hit expected)"),
    ("errors in change feed ingestion process", "Q6: Semantic similarity (L3 hit expected)"),
    ("dashboard pilot deployment", "Q7: Different topic (LLM call expected)"),
    ("dashboard deployment pilot", "Q8: Word order (L2 hit expected)"),
]

print("Running test queries...")
print("=" * 70)

for i, (query, description) in enumerate(test_cases, 1):
    print(f"\n{description}")
    print(f"  Query: '{query}'")

    try:
        results = reranker.rerank(query, candidates.copy())
        metrics = reranker.get_metrics()

        print(f"  L1 hits: {metrics['cache_hits']}")
        print(f"  L2 hits: {metrics['keyword_cache_hits']}")
        print(f"  L3 hits: {metrics['semantic_cache_hits']}")
        print(f"  LLM calls: {metrics['llm_calls']}")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

# Final metrics
print("\n" + "=" * 70)
print("Final Metrics")
print("=" * 70)

metrics = reranker.get_metrics()

print(f"\nCache Statistics:")
print(f"  L1 cache entries: {metrics['cache_entries']}")
print(f"  L2 cache entries: {metrics['keyword_cache_entries']}")
print(f"  L3 cache candidates: {metrics['semantic_cache_candidates']}")
print(f"  L3 cache embeddings: {metrics['semantic_cache_embeddings']}")

print(f"\nHit Rates:")
print(f"  L1 (exact) hits: {metrics['cache_hits']}")
print(f"  L1 (exact) misses: {metrics['cache_misses']}")
print(f"  L1 hit rate: {metrics['cache_hit_rate'] * 100:.1f}%")

print(f"\n  L2 (keyword) hits: {metrics['keyword_cache_hits']}")
print(f"  L2 (keyword) misses: {metrics['keyword_cache_misses']}")
print(f"  L2 hit rate: {metrics['keyword_cache_hit_rate'] * 100:.1f}%")

print(f"\n  L3 (semantic) hits: {metrics['semantic_cache_hits']}")
print(f"  L3 (semantic) misses: {metrics['semantic_cache_misses']}")
print(f"  L3 hit rate: {metrics['semantic_cache_hit_rate'] * 100:.1f}%")

print(f"\n  Total cache hit rate: {metrics['total_cache_hit_rate'] * 100:.1f}%")

print(f"\nLLM Performance:")
print(f"  Total pairs scored: {metrics['pairs_scored']}")
print(f"  LLM calls: {metrics['llm_calls']}")
print(f"  LLM failures: {metrics['llm_failures']}")
print(f"  Avg LLM latency: {metrics['avg_llm_latency_ms']:.1f}ms")
print(f"  Max LLM latency: {metrics['max_llm_latency_ms']:.1f}ms")

# Calculate improvement
baseline_hit_rate = 11.0  # From initial measurement
phase2_hit_rate = 28.57  # From Phase 2
phase3_hit_rate = metrics['total_cache_hit_rate'] * 100

print(f"\nImprovement Summary:")
print(f"  Baseline (Phase 0): {baseline_hit_rate:.1f}%")
print(f"  Phase 2 (L1+L2): {phase2_hit_rate:.1f}%")
print(f"  Phase 3 (L1+L2+L3): {phase3_hit_rate:.1f}%")
print(f"  Total improvement: {phase3_hit_rate - baseline_hit_rate:.1f} percentage points")
print(f"  Improvement vs Phase 2: {phase3_hit_rate - phase2_hit_rate:.1f} percentage points")

# Success criteria
print(f"\nSuccess Criteria (Target: 70-80%):")
if phase3_hit_rate >= 70:
    print(f"  [OK] PASS - Achieved {phase3_hit_rate:.1f}% hit rate")
else:
    print(f"  [X] Target not met - {phase3_hit_rate:.1f}% (need {70 - phase3_hit_rate:.1f}% more)")

print()
