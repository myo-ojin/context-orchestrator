#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Expand AppBrain scenarios for testing ProjectMemoryPool effectiveness.

Adds 30 AppBrain conversations and 15 AppBrain queries to measure:
- Memory ID filtering effect (100→30 candidate reduction)
- L3 semantic cache warm-up effect
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

def expand_scenarios():
    """Add AppBrain-focused conversations and queries."""

    # Paths
    scenario_file = Path('tests/scenarios/scenario_data.json')
    query_file = Path('tests/scenarios/query_runs.json')

    # Load existing data
    with open(scenario_file, 'r', encoding='utf-8') as f:
        scenario_data = json.load(f)

    with open(query_file, 'r', encoding='utf-8') as f:
        query_data = json.load(f)

    # Base timestamp
    base_time = datetime(2025, 11, 1, 10, 0, 0)

    # 30 new AppBrain conversations
    new_conversations = [
        # Architecture & Design (5)
        {
            'user': 'How should we structure the vector indexing pipeline for AppBrain?',
            'assistant': 'Use a two-stage approach: first embed documents with nomic-embed-text, then index in Chroma DB with metadata filters. Keep batch size at 100 docs for optimal throughput.',
            'project': 'AppBrain',
            'source': 'scenario_architecture',
            'refs': ['AppBrain-VectorPipeline'],
            'metadata': {'topic': 'vector_indexing', 'doc_type': 'design'},
            'timestamp': (base_time + timedelta(hours=1)).isoformat()
        },
        {
            'user': 'What chunking strategy should we use for long documents in AppBrain?',
            'assistant': 'Split by markdown headings first, then by paragraphs if chunks exceed 512 tokens. Never split code blocks. Use tiktoken for accurate token counting.',
            'project': 'AppBrain',
            'source': 'scenario_architecture',
            'refs': ['AppBrain-ChunkStrategy'],
            'metadata': {'topic': 'chunking', 'doc_type': 'design'},
            'timestamp': (base_time + timedelta(hours=2)).isoformat()
        },
        {
            'user': 'How do we handle concurrent writes to vector database in AppBrain?',
            'assistant': 'Chroma DB handles concurrency internally. For high-throughput scenarios, queue writes in batches and use background workers with exponential backoff on conflicts.',
            'project': 'AppBrain',
            'source': 'scenario_architecture',
            'refs': ['AppBrain-Concurrency'],
            'metadata': {'topic': 'concurrency', 'doc_type': 'design'},
            'timestamp': (base_time + timedelta(hours=3)).isoformat()
        },
        {
            'user': 'What caching strategy for embeddings in AppBrain?',
            'assistant': 'Implement 3-layer cache: L1 exact matches (LRU, 128 entries), L2 keyword matches (top 3), L3 semantic similarity (cosine >0.85). TTL 8 hours.',
            'project': 'AppBrain',
            'source': 'scenario_architecture',
            'refs': ['AppBrain-CacheDesign'],
            'metadata': {'topic': 'caching', 'doc_type': 'design'},
            'timestamp': (base_time + timedelta(hours=4)).isoformat()
        },
        {
            'user': 'How to implement project-scoped search in AppBrain?',
            'assistant': 'Add project_id to metadata filters. When project confirmed (confidence >0.75), pre-load memory pool and filter candidates before reranking. Expected 70% reduction.',
            'project': 'AppBrain',
            'source': 'scenario_architecture',
            'refs': ['AppBrain-ProjectScope'],
            'metadata': {'topic': 'project_search', 'doc_type': 'design'},
            'timestamp': (base_time + timedelta(hours=5)).isoformat()
        },
        # Implementation & Code (10)
        {
            'user': 'Show me the code for generating embeddings in AppBrain.',
            'assistant': 'Use ModelRouter.generate_embedding(text). Returns List[float] with 768 dimensions from nomic-embed-text. Cache results in memory pool for reuse.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-EmbeddingCode'],
            'metadata': {'topic': 'embedding_generation', 'doc_type': 'snippet'},
            'timestamp': (base_time + timedelta(hours=6)).isoformat()
        },
        {
            'user': 'How do we filter candidates by memory IDs in AppBrain?',
            'assistant': 'Use list comprehension: pool_candidates = [c for c in all_candidates if get_memory_id(c) in memory_ids]. Reduces 100 to ~30 candidates.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-FilterCode'],
            'metadata': {'topic': 'candidate_filtering', 'doc_type': 'snippet'},
            'timestamp': (base_time + timedelta(hours=7)).isoformat()
        },
        {
            'user': 'What is the cross-encoder reranking flow in AppBrain?',
            'assistant': 'Check L1/L2/L3 caches first. If miss, call LLM to score (query, candidate) pair. Store in all 3 caches. Use 3-parallel execution for throughput.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-RerankFlow'],
            'metadata': {'topic': 'reranking', 'doc_type': 'process'},
            'timestamp': (base_time + timedelta(hours=8)).isoformat()
        },
        {
            'user': 'How to warm the semantic cache in AppBrain?',
            'assistant': 'Call ProjectMemoryPool.warm_cache(reranker, project_id). Loads all project memories, generates embeddings, and populates L3 cache. Query-agnostic optimization.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-WarmCache'],
            'metadata': {'topic': 'cache_warming', 'doc_type': 'snippet'},
            'timestamp': (base_time + timedelta(hours=9)).isoformat()
        },
        {
            'user': 'Show the graduated degradation workflow implementation in AppBrain.',
            'assistant': 'Step 1: search_within_pool(). Step 2: is_result_sufficient() check. Step 3: If insufficient, fallback to full search. Logs "Pool filtering: X→Y candidates".',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-WorkflowA'],
            'metadata': {'topic': 'graduated_degradation', 'doc_type': 'process'},
            'timestamp': (base_time + timedelta(hours=10)).isoformat()
        },
        {
            'user': 'How do we calculate result sufficiency in AppBrain?',
            'assistant': 'Check: len(results) >= top_k AND min_score >= 0.3. Returns True if both conditions met, False otherwise.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-Sufficiency'],
            'metadata': {'topic': 'result_sufficiency', 'doc_type': 'snippet'},
            'timestamp': (base_time + timedelta(hours=11)).isoformat()
        },
        {
            'user': 'What is the memory pool loading logic in AppBrain?',
            'assistant': 'Fetch memories by project_id with is_memory_entry=True filter. Sort by created_at desc. Limit to max_memories_per_project (default 100). Generate embeddings for each.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-PoolLoading'],
            'metadata': {'topic': 'memory_pool_loading', 'doc_type': 'process'},
            'timestamp': (base_time + timedelta(hours=12)).isoformat()
        },
        {
            'user': 'How do we extract memory IDs from candidates in AppBrain?',
            'assistant': 'Check metadata.memory_id for chunks, or use candidate ID if is_memory_entry=True. Return empty string if neither found.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-MemoryIDExtraction'],
            'metadata': {'topic': 'memory_id_extraction', 'doc_type': 'snippet'},
            'timestamp': (base_time + timedelta(hours=13)).isoformat()
        },
        {
            'user': 'Show the prefetch_project implementation in AppBrain.',
            'assistant': 'Dual strategy: (1) ProjectMemoryPool.warm_cache() for L3, (2) Execute prefetch queries for L1/L2. Logs pool_stats with memories_loaded and cache_entries_added.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-Prefetch'],
            'metadata': {'topic': 'prefetch_project', 'doc_type': 'process'},
            'timestamp': (base_time + timedelta(hours=14)).isoformat()
        },
        {
            'user': 'What parallel execution strategy does AppBrain use?',
            'assistant': 'Use ThreadPoolExecutor with max_workers=2 for vector+BM25 search, max_workers=3 for cross-encoder reranking. Reduces latency from 118s to 40s per query.',
            'project': 'AppBrain',
            'source': 'scenario_code',
            'refs': ['AppBrain-Parallel'],
            'metadata': {'topic': 'parallel_execution', 'doc_type': 'design'},
            'timestamp': (base_time + timedelta(hours=15)).isoformat()
        },
        # Operations & Monitoring (5)
        {
            'user': 'How do we monitor cache hit rates in AppBrain?',
            'assistant': 'Call get_reranker_metrics() MCP tool. Returns L1/L2/L3 hit rates, LLM call count, avg latency. Target: total hit rate >60%.',
            'project': 'AppBrain',
            'source': 'scenario_ops',
            'refs': ['AppBrain-CacheMetrics'],
            'metadata': {'topic': 'monitoring', 'doc_type': 'runbook'},
            'timestamp': (base_time + timedelta(hours=16)).isoformat()
        },
        {
            'user': 'What performance targets for AppBrain search?',
            'assistant': 'Search latency ≤200ms (typical 80ms without reranking). LLM calls ≤20 per query. Cache hit rate ≥60%. Precision ≥84%. Zero-hit queries = 0.',
            'project': 'AppBrain',
            'source': 'scenario_ops',
            'refs': ['AppBrain-PerformanceTargets'],
            'metadata': {'topic': 'performance_targets', 'doc_type': 'specification'},
            'timestamp': (base_time + timedelta(hours=17)).isoformat()
        },
        {
            'user': 'How to debug memory pool filtering in AppBrain?',
            'assistant': 'Check logs for "Pool filtering: X→Y candidates". If Y=0, verify project_id metadata. If Y=X, memory pool not loaded. Expected ratio ~30%.',
            'project': 'AppBrain',
            'source': 'scenario_ops',
            'refs': ['AppBrain-DebugPool'],
            'metadata': {'topic': 'debugging', 'doc_type': 'runbook'},
            'timestamp': (base_time + timedelta(hours=18)).isoformat()
        },
        {
            'user': 'What triggers project memory pool loading in AppBrain?',
            'assistant': 'SessionManager.set_project_hint() with confidence >0.75 triggers prefetch_project(). This loads pool and warms L3 cache automatically.',
            'project': 'AppBrain',
            'source': 'scenario_ops',
            'refs': ['AppBrain-PoolTrigger'],
            'metadata': {'topic': 'pool_loading_trigger', 'doc_type': 'process'},
            'timestamp': (base_time + timedelta(hours=19)).isoformat()
        },
        {
            'user': 'How to measure memory pool effectiveness in AppBrain?',
            'assistant': 'Compare LLM calls before/after pool integration. Track candidate reduction ratio (expect 70%). Monitor L3 cache hit rate (target >40%).',
            'project': 'AppBrain',
            'source': 'scenario_ops',
            'refs': ['AppBrain-PoolEffectiveness'],
            'metadata': {'topic': 'effectiveness_measurement', 'doc_type': 'analysis'},
            'timestamp': (base_time + timedelta(hours=20)).isoformat()
        },
        # Configuration & Tuning (5)
        {
            'user': 'What are key config parameters for AppBrain memory pool?',
            'assistant': 'max_memories_per_project: 100, pool_ttl_seconds: 28800 (8h), project_prefetch_min_confidence: 0.75, semantic_similarity_threshold: 0.85.',
            'project': 'AppBrain',
            'source': 'scenario_config',
            'refs': ['AppBrain-PoolConfig'],
            'metadata': {'topic': 'configuration', 'doc_type': 'specification'},
            'timestamp': (base_time + timedelta(hours=21)).isoformat()
        },
        {
            'user': 'How to tune semantic similarity threshold in AppBrain?',
            'assistant': 'Default 0.85 is conservative. Lower to 0.70-0.75 for higher hit rate (trade precision). Measure via get_reranker_metrics() after changes.',
            'project': 'AppBrain',
            'source': 'scenario_config',
            'refs': ['AppBrain-ThresholdTuning'],
            'metadata': {'topic': 'threshold_tuning', 'doc_type': 'guidance'},
            'timestamp': (base_time + timedelta(hours=22)).isoformat()
        },
        {
            'user': 'What cache sizes should we use in AppBrain?',
            'assistant': 'L1/L2: 128 entries each (OrderedDict with LRU eviction). L3: unlimited (Dict per candidate_id). TTL: 28800s (8 hours) for all layers.',
            'project': 'AppBrain',
            'source': 'scenario_config',
            'refs': ['AppBrain-CacheSizes'],
            'metadata': {'topic': 'cache_sizing', 'doc_type': 'specification'},
            'timestamp': (base_time + timedelta(hours=23)).isoformat()
        },
        {
            'user': 'How many parallel reranking workers for AppBrain?',
            'assistant': 'cross_encoder_max_parallel: 3 (default). Increase to 5-10 if CPU allows. Monitor queue_wait_ms via metrics. Use fallback_mode: heuristic if wait >500ms.',
            'project': 'AppBrain',
            'source': 'scenario_config',
            'refs': ['AppBrain-ParallelTuning'],
            'metadata': {'topic': 'parallel_tuning', 'doc_type': 'guidance'},
            'timestamp': (base_time + timedelta(hours=24)).isoformat()
        },
        {
            'user': 'What prefetch queries should we use for AppBrain?',
            'assistant': 'Use actual user query patterns. Default: "project status", "open issues", "risk summary". Update based on query_runs.json analysis. Max 3 queries.',
            'project': 'AppBrain',
            'source': 'scenario_config',
            'refs': ['AppBrain-PrefetchQueries'],
            'metadata': {'topic': 'prefetch_queries', 'doc_type': 'guidance'},
            'timestamp': (base_time + timedelta(hours=25)).isoformat()
        },
        # Testing & Validation (5)
        {
            'user': 'How to test memory pool functionality in AppBrain?',
            'assistant': 'Unit tests: test_load_project, test_warm_cache, test_get_memory_ids. Integration: check pool_stats in prefetch_project response. Verify >0 memories_loaded.',
            'project': 'AppBrain',
            'source': 'scenario_testing',
            'refs': ['AppBrain-PoolTesting'],
            'metadata': {'topic': 'testing', 'doc_type': 'guidance'},
            'timestamp': (base_time + timedelta(hours=26)).isoformat()
        },
        {
            'user': 'What regression tests validate AppBrain memory pool?',
            'assistant': 'Run mcp_replay with AppBrain-heavy scenarios. Verify: Precision ≥84%, LLM calls reduction, cache hit rate increase. Check zero_hits.json for regressions.',
            'project': 'AppBrain',
            'source': 'scenario_testing',
            'refs': ['AppBrain-RegressionTests'],
            'metadata': {'topic': 'regression_testing', 'doc_type': 'process'},
            'timestamp': (base_time + timedelta(hours=27)).isoformat()
        },
        {
            'user': 'How to validate cache warming in AppBrain?',
            'assistant': 'Check logs for "[Prefetch] Warmed L3 cache" with >0 memories_loaded. Query same project immediately after—L3 hit rate should spike.',
            'project': 'AppBrain',
            'source': 'scenario_testing',
            'refs': ['AppBrain-CacheValidation'],
            'metadata': {'topic': 'cache_validation', 'doc_type': 'process'},
            'timestamp': (base_time + timedelta(hours=28)).isoformat()
        },
        {
            'user': 'What are success criteria for AppBrain memory pool?',
            'assistant': 'LLM calls ≤20 per query (vs 44 baseline). Candidate reduction 100→30 (70%). L3 cache hit rate >40%. Precision maintained ≥84%.',
            'project': 'AppBrain',
            'source': 'scenario_testing',
            'refs': ['AppBrain-SuccessCriteria'],
            'metadata': {'topic': 'success_criteria', 'doc_type': 'specification'},
            'timestamp': (base_time + timedelta(hours=29)).isoformat()
        },
        {
            'user': 'How to measure graduated degradation effectiveness in AppBrain?',
            'assistant': 'Parse logs for "Pool filtering" and "Sufficient results from pool". Calculate pool-only success rate. Target: >70% queries satisfied by pool alone.',
            'project': 'AppBrain',
            'source': 'scenario_testing',
            'refs': ['AppBrain-WorkflowAMetrics'],
            'metadata': {'topic': 'workflow_metrics', 'doc_type': 'analysis'},
            'timestamp': (base_time + timedelta(hours=30)).isoformat()
        },
    ]

    # Add to scenario data
    scenario_data['conversations'].extend(new_conversations)

    # Write back
    with open(scenario_file, 'w', encoding='utf-8') as f:
        json.dump(scenario_data, f, indent=2, ensure_ascii=False)

    print(f'[OK] Added {len(new_conversations)} AppBrain conversations to scenario_data.json')
    print(f'   Total conversations: {len(scenario_data["conversations"])}')

    # Now add 15 AppBrain queries
    new_queries = [
        {
            'query': 'How does vector indexing work in AppBrain?',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'vector_indexing',
                'expected_results': 3
            }
        },
        {
            'query': 'What is the chunking strategy for AppBrain documents?',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'chunking',
                'expected_results': 3
            }
        },
        {
            'query': 'Explain AppBrain caching layers',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'caching',
                'expected_results': 3
            }
        },
        {
            'query': 'How to filter candidates in AppBrain memory pool?',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'candidate_filtering',
                'expected_results': 3
            }
        },
        {
            'query': 'Show me graduated degradation workflow in AppBrain',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'graduated_degradation',
                'expected_results': 3
            }
        },
        {
            'query': 'How does prefetch_project work in AppBrain?',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'prefetch_project',
                'expected_results': 3
            }
        },
        {
            'query': 'What are AppBrain performance targets?',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'performance_targets',
                'expected_results': 3
            }
        },
        {
            'query': 'How to debug memory pool filtering in AppBrain?',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'debugging',
                'expected_results': 3
            }
        },
        {
            'query': 'AppBrain cache warming process',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'cache_warming',
                'expected_results': 3
            }
        },
        {
            'query': 'Tune semantic similarity threshold in AppBrain',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'threshold_tuning',
                'expected_results': 3
            }
        },
        {
            'query': 'AppBrain memory pool configuration parameters',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'configuration',
                'expected_results': 3
            }
        },
        {
            'query': 'How to test AppBrain memory pool?',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'testing',
                'expected_results': 3
            }
        },
        {
            'query': 'AppBrain regression testing procedure',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'regression_testing',
                'expected_results': 3
            }
        },
        {
            'query': 'What are success criteria for AppBrain pool?',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'success_criteria',
                'expected_results': 3
            }
        },
        {
            'query': 'Measure memory pool effectiveness in AppBrain',
            'expected_memory_ids': [],
            'metadata': {
                'project': 'AppBrain',
                'topic': 'effectiveness_measurement',
                'expected_results': 3
            }
        },
    ]

    query_data.extend(new_queries)

    # Write back
    with open(query_file, 'w', encoding='utf-8') as f:
        json.dump(query_data, f, indent=2, ensure_ascii=False)

    print(f'[OK] Added {len(new_queries)} AppBrain queries to query_runs.json')
    print(f'   Total queries: {len(query_data)}')

    print('\n[Summary]:')
    print(f'   - AppBrain conversations: 8 → {8 + len(new_conversations)} (+{len(new_conversations)})')
    print(f'   - AppBrain queries: 0 → {len(new_queries)} (+{len(new_queries)})')
    print(f'   - Expected pool size: ~{len(new_conversations) + 8} memories')
    print(f'   - Expected filtering: 100 candidates → ~30 candidates (70% reduction)')

if __name__ == '__main__':
    expand_scenarios()
