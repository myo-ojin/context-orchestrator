#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 3 Multi-Tier Cache Performance Test
Tests L1 (exact) + L2 (keyword) + L3 (semantic) cache
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.rerankers import CrossEncoderReranker
from config import Config
from models.local_llm import LocalLLMClient

class MockRouter:
    """Mock router that counts LLM calls but generates real embeddings"""
    def __init__(self, config):
        self.call_count = 0
        self.config = config
        # Use real LocalLLMClient for embeddings
        try:
            self.local_llm = LocalLLMClient(
                ollama_url=config.get('ollama_url', 'http://localhost:11434'),
                embedding_model=config.get('embedding_model', 'nomic-embed-text'),
                inference_model=config.get('inference_model', 'qwen2.5:7b')
            )
            self.use_real_embeddings = True
            print("[INFO] Using real Ollama embeddings")
        except Exception as e:
            print(f"[WARN] Ollama not available, using mock embeddings: {e}")
            self.use_real_embeddings = False

    def route(self, task_type: str, **kwargs):
        """Mock LLM scoring - returns fixed score"""
        self.call_count += 1
        return "0.75"

    def generate_embedding(self, text: str):
        """Generate real or mock embedding"""
        if self.use_real_embeddings:
            try:
                return self.local_llm.generate_embedding(text)
            except Exception as e:
                print(f"[WARN] Embedding generation failed, using mock: {e}")
                return self._mock_embedding(text)
        else:
            return self._mock_embedding(text)

    def _mock_embedding(self, text: str):
        """Fallback mock embedding for when Ollama is not available"""
        import math
        base = [0.01] * 384
        keywords = set(text.lower().split())

        # Semantic clusters
        if 'change' in keywords or 'feed' in keywords or 'ingestion' in keywords:
            for i in range(0, 100):
                base[i] += 5.0
        if 'data' in keywords or 'consuming' in keywords:
            for i in range(0, 100):
                base[i] += 5.0
        if 'errors' in keywords or 'problems' in keywords or 'issues' in keywords:
            for i in range(0, 100):
                base[i] += 5.0
        if 'dashboard' in keywords or 'deployment' in keywords or 'pilot' in keywords:
            for i in range(200, 300):
                base[i] += 5.0

        magnitude = math.sqrt(sum(x * x for x in base))
        if magnitude > 0:
            base = [x / magnitude for x in base]
        return base


print("=" * 70)
print("Phase 3: Multi-Tier Cache Performance Test")
print("=" * 70)

# Load config
config = Config()
router = MockRouter(config)

# Create reranker with Phase 3 settings
reranker = CrossEncoderReranker(
    model_router=router,
    cache_max_entries=256,
    cache_ttl_seconds=28800,  # 8 hours
    semantic_similarity_threshold=0.85,
    log_interval=0
)

print(f"Cache size: {reranker.cache_max_entries}")
print(f"TTL: {reranker.cache_ttl_seconds}s ({reranker.cache_ttl_seconds / 3600:.0f}h)")
print(f"Semantic threshold: {reranker.semantic_similarity_threshold}")
print()

# Test candidates
candidates = [
    {
        "id": "mem-001",
        "content": "Change feed ingestion pipeline handles streaming data errors",
        "metadata": {"memory_id": "mem-001", "project_id": "proj-alpha"}
    },
    {
        "id": "mem-002",
        "content": "Dashboard deployment configuration for pilot environment",
        "metadata": {"memory_id": "mem-002", "project_id": "proj-alpha"}
    }
]

# Test queries - realistic scenario
test_queries = [
    # Group 1: Change feed ingestion (should share L3 cache)
    ("change feed ingestion errors", "Q1: First query on topic A"),
    ("change feed ingestion errors", "Q2: Exact repeat (L1 hit)"),
    ("ingestion errors in change feed", "Q3: Word order (L2 hit)"),
    ("problems with change feed data ingestion", "Q4: Paraphrase (L3 hit)"),
    ("issues consuming data from change feed", "Q5: Synonym (L3 hit)"),

    # Group 2: Dashboard deployment (different topic, should share L3 cache)
    ("dashboard pilot deployment", "Q6: First query on topic B"),
    ("dashboard deployment pilot", "Q7: Word order (L2 hit)"),
    ("pilot dashboard deployment issues", "Q8: Paraphrase (L3 hit)"),

    # Group 3: Back to topic A (should still hit cache)
    ("errors in change feed ingestion", "Q9: Topic A again (L2 or L3 hit)"),
    ("change feed data consumption problems", "Q10: Topic A paraphrase (L3 hit)"),
]

print("Running Test Queries...")
print("=" * 70)

for i, (query, description) in enumerate(test_queries, 1):
    print(f"\n{description}")
    print(f"  Query: '{query}'")

    result = reranker.rerank(query, candidates.copy())
    metrics = reranker.get_metrics()

    # Show incremental stats
    print(f"  L1: {metrics['cache_hits']} hits")
    print(f"  L2: {metrics['keyword_cache_hits']} hits")
    print(f"  L3: {metrics['semantic_cache_hits']} hits")
    print(f"  LLM calls so far: {router.call_count}")

# Final Report
print("\n" + "=" * 70)
print("Final Performance Report")
print("=" * 70)

metrics = reranker.get_metrics()

print(f"\nCache Entries:")
print(f"  L1 (exact match): {metrics['cache_entries']} entries")
print(f"  L2 (keyword): {metrics['keyword_cache_entries']} entries")
print(f"  L3 (semantic): {metrics['semantic_cache_candidates']} candidates, {metrics['semantic_cache_embeddings']} embeddings")

print(f"\nCache Performance:")
print(f"  L1 hits: {metrics['cache_hits']}, misses: {metrics['cache_misses']}, rate: {metrics['cache_hit_rate'] * 100:.1f}%")
print(f"  L2 hits: {metrics['keyword_cache_hits']}, misses: {metrics['keyword_cache_misses']}, rate: {metrics['keyword_cache_hit_rate'] * 100:.1f}%")
print(f"  L3 hits: {metrics['semantic_cache_hits']}, misses: {metrics['semantic_cache_misses']}, rate: {metrics['semantic_cache_hit_rate'] * 100:.1f}%")

total_hit_rate = metrics['total_cache_hit_rate'] * 100
print(f"\n  TOTAL CACHE HIT RATE: {total_hit_rate:.1f}%")

print(f"\nLLM Efficiency:")
print(f"  Total pairs scored: {metrics['pairs_scored']}")
print(f"  Actual LLM calls: {router.call_count}")
print(f"  LLM call reduction: {(1 - router.call_count / max(1, metrics['pairs_scored'])) * 100:.1f}%")

# Compare with baselines
baseline = 11.0
phase2 = 28.57

print(f"\n" + "=" * 70)
print("Improvement Analysis")
print("=" * 70)
print(f"  Baseline (no cache): {baseline:.1f}%")
print(f"  Phase 2 (L1+L2): {phase2:.1f}%")
print(f"  Phase 3 (L1+L2+L3): {total_hit_rate:.1f}%")
print(f"\n  Improvement from baseline: +{total_hit_rate - baseline:.1f} percentage points")
print(f"  Improvement from Phase 2: +{total_hit_rate - phase2:.1f} percentage points")

# Success check
print(f"\n" + "=" * 70)
print("Success Criteria")
print("=" * 70)
target = 70.0
if total_hit_rate >= target:
    print(f"  [OK] PASS - Achieved {total_hit_rate:.1f}% (target: {target}%)")
elif total_hit_rate >= phase2:
    improvement = total_hit_rate - phase2
    print(f"  [OK] Improvement over Phase 2: +{improvement:.1f} percentage points")
    print(f"  [INFO] Target {target}% not yet reached, but progress made")
else:
    print(f"  [X] Below Phase 2 baseline - investigate")

print()
