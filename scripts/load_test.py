#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Load Test Script for Context Orchestrator
Phase 7c: Quality Assurance - Load Testing

Tests:
- 100 consecutive queries (memory leak detection)
- Memory profiling (RSS, peak usage)
- Performance degradation monitoring
- Cache effectiveness over time

Usage:
    python -m scripts.load_test [--num-queries 100] [--output report.json]
"""

import argparse
import json
import time
import tracemalloc
import psutil
import os
import sys
from datetime import datetime
from typing import List, Dict, Any


# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Settings
from src.services.search import SearchService
from src.services.ingestion import IngestionService
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index
from src.models.router import ModelRouter
from src.models.local_llm import LocalLLMClient
from src.processing.indexer import Indexer
from src.services.rerankers import CrossEncoderReranker
from src.services.project_memory_pool import ProjectMemoryPool
from src.utils.logger import setup_structured_logger


logger = setup_structured_logger(__name__, "INFO")


def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process()
    mem_info = process.memory_info()
    return {
        "rss_mb": mem_info.rss / (1024 * 1024),  # Resident Set Size
        "vms_mb": mem_info.vms / (1024 * 1024),  # Virtual Memory Size
    }


def initialize_services(config: Settings):
    """Initialize all required services"""
    logger.info("Initializing services...")

    # Storage layer
    vector_db = ChromaVectorDB(
        persist_directory=config.data_dir / "chroma_db",
        collection_name="memories"
    )

    bm25_index = BM25Index(
        persist_path=config.data_dir / "bm25_index.pkl"
    )

    # Model layer
    local_llm = LocalLLMClient(
        ollama_url=config.ollama_url,
        embedding_model=config.embedding_model,
        inference_model=config.inference_model
    )

    model_router = ModelRouter(
        local_llm=local_llm,
        cli_command=config.cli_command
    )

    # Processing layer
    indexer = Indexer(
        vector_db=vector_db,
        bm25_index=bm25_index,
        model_router=model_router
    )

    # Reranker
    reranker_config = {
        "enabled": config.cross_encoder_enabled,
        "top_k": config.cross_encoder_top_k,
        "cache_size": config.cross_encoder_cache_size,
        "cache_ttl_seconds": config.cross_encoder_cache_ttl_seconds,
        "max_parallel": config.cross_encoder_max_parallel,
        "fallback_max_wait_ms": config.cross_encoder_fallback_max_wait_ms,
    }

    cross_encoder_reranker = CrossEncoderReranker(
        model_router=model_router,
        config=reranker_config
    )

    # Project memory pool
    project_memory_pool = ProjectMemoryPool(
        vector_db=vector_db,
        model_router=model_router,
        config={
            "pool_size": config.project_pool_size,
            "pool_ttl_seconds": config.project_pool_ttl_seconds,
        }
    )

    # Search service
    search_service = SearchService(
        model_router=model_router,
        vector_db=vector_db,
        bm25_index=bm25_index,
        cross_encoder_reranker=cross_encoder_reranker,
        config={
            "vector_candidate_count": config.vector_candidate_count,
            "bm25_candidate_count": config.bm25_candidate_count,
            "search_result_count": config.search_result_count,
            "cross_encoder_enabled": config.cross_encoder_enabled,
            "cross_encoder_top_k": config.cross_encoder_top_k,
            "project_pool": project_memory_pool,
        }
    )

    logger.info("Services initialized successfully")
    return search_service, cross_encoder_reranker


def get_test_queries() -> List[str]:
    """Get a diverse set of test queries"""
    return [
        # Short queries
        "chunker",
        "timeline view",
        "BM25 errors",
        "reranking",
        "Ollama config",

        # Medium queries
        "session management and project memory pool",
        "cross-encoder cache optimization",
        "embedding quality testing framework",
        "query attribute modeling system",
        "memory consolidation strategy",

        # Long queries
        "detailed information about change feed ingestion pipeline error handling",
        "architecture decisions for cross-encoder reranking three-layer cache",
        "current approach for handling session management and project memory pool integration",

        # Multilingual
        "チャンカーの実装で発生したTypeError",
        "プロジェクトメモリプールの設計思想",
        "検索レイテンシの最適化戦略",
        "¿Cómo funciona el caché de tres niveles?",
        "Errores de ingestion en el change feed",

        # Technical
        "LRU cache TTL configuration cross-encoder",
        "QAM LLM routing langdetect fallback",
        "ChromaDB filter_metadata implementation",
        "Macro Precision NDCG baseline regression",

        # Natural language
        "How do I make the search faster?",
        "What was the solution for Japanese text?",
        "Tell me about recent improvements",
        "What steps to set up a new project?",

        # Edge cases
        "search with @mentions",
        "hashtag #test query",
        "price $100 query",
        "search 🔍 functionality",
        "bug 🐛 report",
    ]


def run_load_test(
    search_service: SearchService,
    reranker: CrossEncoderReranker,
    num_queries: int = 100
) -> Dict[str, Any]:
    """
    Run load test with consecutive queries

    Returns:
        Dict with test results and metrics
    """
    logger.info(f"Starting load test with {num_queries} queries...")

    # Get test queries
    base_queries = get_test_queries()

    # Start memory tracking
    tracemalloc.start()
    start_memory = get_memory_usage()

    # Metrics
    query_times = []
    memory_samples = []
    errors = []

    start_time = time.time()

    for i in range(num_queries):
        query_idx = i % len(base_queries)
        query = base_queries[query_idx]

        try:
            # Time individual query
            query_start = time.time()
            results = search_service.search(query, top_k=5)
            query_end = time.time()

            query_duration = (query_end - query_start) * 1000  # ms
            query_times.append(query_duration)

            # Sample memory every 10 queries
            if i % 10 == 0:
                current_mem = get_memory_usage()
                memory_samples.append({
                    "query_num": i,
                    "rss_mb": current_mem["rss_mb"],
                    "vms_mb": current_mem["vms_mb"],
                })

            if i % 20 == 0:
                logger.info(
                    f"Progress: {i}/{num_queries} queries, "
                    f"last query: {query_duration:.1f}ms, "
                    f"RSS: {current_mem['rss_mb']:.1f}MB"
                )

        except Exception as e:
            logger.error(f"Query {i} failed: {str(e)}")
            errors.append({
                "query_num": i,
                "query": query,
                "error": str(e)
            })

    end_time = time.time()

    # Get final memory and peak
    end_memory = get_memory_usage()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Get reranker metrics
    reranker_metrics = reranker.get_metrics()

    # Calculate statistics
    total_duration = (end_time - start_time)
    queries_per_second = num_queries / total_duration

    # Query time statistics
    query_times_sorted = sorted(query_times)
    p50_idx = int(len(query_times_sorted) * 0.50)
    p95_idx = int(len(query_times_sorted) * 0.95)
    p99_idx = int(len(query_times_sorted) * 0.99)

    # Memory growth
    memory_growth_mb = end_memory["rss_mb"] - start_memory["rss_mb"]
    memory_growth_percent = (memory_growth_mb / start_memory["rss_mb"]) * 100

    # Performance degradation (compare first 10% vs last 10%)
    first_10pct = query_times[:max(1, len(query_times) // 10)]
    last_10pct = query_times[-max(1, len(query_times) // 10):]
    avg_first = sum(first_10pct) / len(first_10pct)
    avg_last = sum(last_10pct) / len(last_10pct)
    degradation_percent = ((avg_last - avg_first) / avg_first) * 100 if avg_first > 0 else 0

    results = {
        "test_info": {
            "num_queries": num_queries,
            "total_duration_seconds": round(total_duration, 2),
            "queries_per_second": round(queries_per_second, 2),
            "timestamp": datetime.now().isoformat(),
        },
        "query_performance": {
            "mean_ms": round(sum(query_times) / len(query_times), 2) if query_times else 0,
            "p50_ms": round(query_times_sorted[p50_idx], 2) if query_times_sorted else 0,
            "p95_ms": round(query_times_sorted[p95_idx], 2) if query_times_sorted else 0,
            "p99_ms": round(query_times_sorted[p99_idx], 2) if query_times_sorted else 0,
            "min_ms": round(min(query_times), 2) if query_times else 0,
            "max_ms": round(max(query_times), 2) if query_times else 0,
        },
        "memory_usage": {
            "start_rss_mb": round(start_memory["rss_mb"], 2),
            "end_rss_mb": round(end_memory["rss_mb"], 2),
            "peak_mb": round(peak / (1024 * 1024), 2),
            "growth_mb": round(memory_growth_mb, 2),
            "growth_percent": round(memory_growth_percent, 2),
            "samples": memory_samples,
        },
        "performance_degradation": {
            "first_10pct_avg_ms": round(avg_first, 2),
            "last_10pct_avg_ms": round(avg_last, 2),
            "degradation_percent": round(degradation_percent, 2),
        },
        "reranker_metrics": reranker_metrics,
        "errors": {
            "count": len(errors),
            "details": errors[:10],  # First 10 errors
        },
        "pass_criteria": {
            "memory_leak": {
                "threshold_percent": 5.0,
                "actual_percent": round(memory_growth_percent, 2),
                "passed": memory_growth_percent < 5.0,
            },
            "performance_degradation": {
                "threshold_percent": 5.0,
                "actual_percent": round(degradation_percent, 2),
                "passed": degradation_percent < 5.0,
            },
            "error_rate": {
                "threshold_percent": 1.0,
                "actual_percent": round((len(errors) / num_queries) * 100, 2),
                "passed": (len(errors) / num_queries) * 100 < 1.0,
            },
        },
    }

    # Determine overall pass/fail
    all_passed = all(
        criteria["passed"]
        for criteria in results["pass_criteria"].values()
    )
    results["overall_passed"] = all_passed

    return results


def print_results(results: Dict[str, Any]):
    """Print test results to console"""
    print("\n" + "=" * 70)
    print("LOAD TEST RESULTS")
    print("=" * 70)

    # Test info
    info = results["test_info"]
    print(f"\nTest Configuration:")
    print(f"  Queries:        {info['num_queries']}")
    print(f"  Duration:       {info['total_duration_seconds']}s")
    print(f"  Throughput:     {info['queries_per_second']} queries/sec")

    # Query performance
    perf = results["query_performance"]
    print(f"\nQuery Performance:")
    print(f"  Mean:           {perf['mean_ms']}ms")
    print(f"  P50:            {perf['p50_ms']}ms")
    print(f"  P95:            {perf['p95_ms']}ms")
    print(f"  P99:            {perf['p99_ms']}ms")
    print(f"  Min:            {perf['min_ms']}ms")
    print(f"  Max:            {perf['max_ms']}ms")

    # Memory usage
    mem = results["memory_usage"]
    print(f"\nMemory Usage:")
    print(f"  Start RSS:      {mem['start_rss_mb']}MB")
    print(f"  End RSS:        {mem['end_rss_mb']}MB")
    print(f"  Peak:           {mem['peak_mb']}MB")
    print(f"  Growth:         {mem['growth_mb']}MB ({mem['growth_percent']}%)")

    # Performance degradation
    deg = results["performance_degradation"]
    print(f"\nPerformance Degradation:")
    print(f"  First 10%:      {deg['first_10pct_avg_ms']}ms avg")
    print(f"  Last 10%:       {deg['last_10pct_avg_ms']}ms avg")
    print(f"  Degradation:    {deg['degradation_percent']}%")

    # Reranker metrics
    rerank = results["reranker_metrics"]
    print(f"\nReranker Metrics:")
    print(f"  Pairs scored:   {rerank.get('pairs_scored', 0)}")
    print(f"  Cache hits:     {rerank.get('cache_hits', 0)}")
    print(f"  Cache misses:   {rerank.get('cache_misses', 0)}")
    print(f"  Hit rate:       {rerank.get('total_cache_hit_rate', 0):.1f}%")

    # Errors
    errors = results["errors"]
    print(f"\nErrors:")
    print(f"  Count:          {errors['count']}")

    # Pass/Fail criteria
    print(f"\nPass/Fail Criteria:")
    for name, criteria in results["pass_criteria"].items():
        status = "✓ PASS" if criteria["passed"] else "✗ FAIL"
        print(f"  {name:25s} {status}")
        print(f"    Threshold: {criteria['threshold_percent']}%, Actual: {criteria['actual_percent']}%")

    # Overall result
    print(f"\n{'=' * 70}")
    if results["overall_passed"]:
        print("OVERALL: ✓ PASSED")
    else:
        print("OVERALL: ✗ FAILED")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Run load test for Context Orchestrator")
    parser.add_argument(
        "--num-queries",
        type=int,
        default=100,
        help="Number of consecutive queries to run (default: 100)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/load_test_results.json",
        help="Output file for test results (default: reports/load_test_results.json)"
    )
    args = parser.parse_args()

    try:
        # Load configuration
        config = Settings()

        # Initialize services
        search_service, reranker = initialize_services(config)

        # Run load test
        results = run_load_test(
            search_service=search_service,
            reranker=reranker,
            num_queries=args.num_queries
        )

        # Print results
        print_results(results)

        # Save to file
        output_path = args.output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {output_path}")

        # Exit with appropriate code
        sys.exit(0 if results["overall_passed"] else 1)

    except Exception as e:
        logger.error(f"Load test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
