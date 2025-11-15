#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Concurrent Test Script for Context Orchestrator
Phase 7c: Quality Assurance - Concurrent Load Testing

Tests:
- Parallel query execution (5-10 concurrent queries)
- Thread safety verification
- Cache contention detection
- Resource usage under concurrent load

Usage:
    python -m scripts.concurrent_test [--concurrency 5] [--output report.json]
"""

import argparse
import json
import time
import asyncio
import concurrent.futures
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import threading
import tracemalloc


# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Settings
from src.services.search import SearchService
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index
from src.models.router import ModelRouter
from src.models.local_llm import LocalLLMClient
from src.processing.indexer import Indexer
from src.services.rerankers import CrossEncoderReranker
from src.services.project_memory_pool import ProjectMemoryPool
from src.utils.logger import setup_structured_logger


logger = setup_structured_logger(__name__, "INFO")


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
    """Get diverse test queries for concurrent testing"""
    return [
        "chunker TypeError fix",
        "timeline view orchestrator",
        "BM25 search errors",
        "cross-encoder cache optimization",
        "session management integration",
        "プロジェクトメモリプールの設計",
        "検索レイテンシの最適化",
        "¿Cómo funciona el caché?",
        "LRU cache TTL configuration",
        "embedding quality testing",
    ]


def execute_query(
    search_service: SearchService,
    query: str,
    thread_id: int,
    results_lock: threading.Lock,
    results_list: List[Dict[str, Any]]
):
    """
    Execute a single query in a thread

    Args:
        search_service: SearchService instance
        query: Query string
        thread_id: Thread identifier
        results_lock: Lock for thread-safe results access
        results_list: Shared list to store results
    """
    try:
        start_time = time.time()

        # Execute search
        search_results = search_service.search(query, top_k=5)

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # Thread-safe result storage
        with results_lock:
            results_list.append({
                "thread_id": thread_id,
                "query": query,
                "duration_ms": round(duration_ms, 2),
                "result_count": len(search_results),
                "success": True,
                "error": None,
            })

        logger.info(
            f"Thread {thread_id}: Query completed in {duration_ms:.1f}ms, "
            f"{len(search_results)} results"
        )

    except Exception as e:
        logger.error(f"Thread {thread_id}: Query failed - {str(e)}")

        with results_lock:
            results_list.append({
                "thread_id": thread_id,
                "query": query,
                "duration_ms": None,
                "result_count": 0,
                "success": False,
                "error": str(e),
            })


def run_concurrent_test(
    search_service: SearchService,
    reranker: CrossEncoderReranker,
    concurrency: int = 5,
    num_rounds: int = 10
) -> Dict[str, Any]:
    """
    Run concurrent query test

    Args:
        search_service: SearchService instance
        reranker: CrossEncoderReranker instance
        concurrency: Number of concurrent queries
        num_rounds: Number of rounds to run

    Returns:
        Dict with test results and metrics
    """
    logger.info(
        f"Starting concurrent test: {concurrency} concurrent queries, "
        f"{num_rounds} rounds"
    )

    # Get test queries
    base_queries = get_test_queries()

    # Track results
    all_results = []
    results_lock = threading.Lock()

    # Start memory tracking
    tracemalloc.start()

    start_time = time.time()

    # Run multiple rounds
    for round_num in range(num_rounds):
        logger.info(f"Starting round {round_num + 1}/{num_rounds}")

        round_start = time.time()

        # Create thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Submit concurrent queries
            futures = []
            for i in range(concurrency):
                query_idx = (round_num * concurrency + i) % len(base_queries)
                query = base_queries[query_idx]

                future = executor.submit(
                    execute_query,
                    search_service,
                    query,
                    round_num * concurrency + i,
                    results_lock,
                    all_results
                )
                futures.append(future)

            # Wait for all queries to complete
            concurrent.futures.wait(futures)

        round_end = time.time()
        round_duration = round_end - round_start

        logger.info(f"Round {round_num + 1} completed in {round_duration:.2f}s")

    end_time = time.time()

    # Get memory stats
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Get reranker metrics
    reranker_metrics = reranker.get_metrics()

    # Calculate statistics
    total_duration = end_time - start_time
    total_queries = concurrency * num_rounds

    # Success/failure counts
    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]

    # Duration statistics (only successful queries)
    durations = [r["duration_ms"] for r in successful]
    if durations:
        durations_sorted = sorted(durations)
        p50_idx = int(len(durations_sorted) * 0.50)
        p95_idx = int(len(durations_sorted) * 0.95)
        p99_idx = int(len(durations_sorted) * 0.99)

        duration_stats = {
            "mean_ms": round(sum(durations) / len(durations), 2),
            "p50_ms": round(durations_sorted[p50_idx], 2),
            "p95_ms": round(durations_sorted[p95_idx], 2),
            "p99_ms": round(durations_sorted[p99_idx], 2),
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2),
        }
    else:
        duration_stats = {}

    # Thread safety check (detect race conditions)
    # If there are unexpected failures, it may indicate thread safety issues
    thread_safety_passed = len(failed) == 0

    # Cache contention (check if concurrent access affects cache performance)
    expected_cache_hit_rate = 20  # Baseline from Phase 3g
    actual_cache_hit_rate = reranker_metrics.get("total_cache_hit_rate", 0)
    cache_contention_detected = actual_cache_hit_rate < (expected_cache_hit_rate * 0.8)

    results = {
        "test_info": {
            "concurrency": concurrency,
            "num_rounds": num_rounds,
            "total_queries": total_queries,
            "total_duration_seconds": round(total_duration, 2),
            "queries_per_second": round(total_queries / total_duration, 2),
            "timestamp": datetime.now().isoformat(),
        },
        "query_results": {
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": round((len(successful) / total_queries) * 100, 2),
        },
        "query_performance": duration_stats,
        "memory_usage": {
            "peak_mb": round(peak / (1024 * 1024), 2),
            "current_mb": round(current / (1024 * 1024), 2),
        },
        "reranker_metrics": reranker_metrics,
        "thread_safety": {
            "passed": thread_safety_passed,
            "failed_queries": len(failed),
        },
        "cache_contention": {
            "expected_hit_rate": expected_cache_hit_rate,
            "actual_hit_rate": actual_cache_hit_rate,
            "contention_detected": cache_contention_detected,
        },
        "detailed_results": all_results,
        "pass_criteria": {
            "success_rate": {
                "threshold_percent": 99.0,
                "actual_percent": round((len(successful) / total_queries) * 100, 2),
                "passed": (len(successful) / total_queries) * 100 >= 99.0,
            },
            "thread_safety": {
                "passed": thread_safety_passed,
            },
            "cache_performance": {
                "threshold_hit_rate": expected_cache_hit_rate * 0.8,
                "actual_hit_rate": actual_cache_hit_rate,
                "passed": not cache_contention_detected,
            },
        },
    }

    # Determine overall pass/fail
    all_passed = all(
        criteria.get("passed", True)
        for criteria in results["pass_criteria"].values()
    )
    results["overall_passed"] = all_passed

    return results


def print_results(results: Dict[str, Any]):
    """Print test results to console"""
    print("\n" + "=" * 70)
    print("CONCURRENT TEST RESULTS")
    print("=" * 70)

    # Test info
    info = results["test_info"]
    print(f"\nTest Configuration:")
    print(f"  Concurrency:    {info['concurrency']}")
    print(f"  Rounds:         {info['num_rounds']}")
    print(f"  Total Queries:  {info['total_queries']}")
    print(f"  Duration:       {info['total_duration_seconds']}s")
    print(f"  Throughput:     {info['queries_per_second']} queries/sec")

    # Query results
    qr = results["query_results"]
    print(f"\nQuery Results:")
    print(f"  Successful:     {qr['successful']}")
    print(f"  Failed:         {qr['failed']}")
    print(f"  Success Rate:   {qr['success_rate']}%")

    # Query performance
    if results["query_performance"]:
        perf = results["query_performance"]
        print(f"\nQuery Performance:")
        print(f"  Mean:           {perf['mean_ms']}ms")
        print(f"  P50:            {perf['p50_ms']}ms")
        print(f"  P95:            {perf['p95_ms']}ms")
        print(f"  P99:            {perf['p99_ms']}ms")

    # Memory usage
    mem = results["memory_usage"]
    print(f"\nMemory Usage:")
    print(f"  Peak:           {mem['peak_mb']}MB")
    print(f"  Current:        {mem['current_mb']}MB")

    # Thread safety
    ts = results["thread_safety"]
    print(f"\nThread Safety:")
    print(f"  Status:         {'✓ PASS' if ts['passed'] else '✗ FAIL'}")
    print(f"  Failed Queries: {ts['failed_queries']}")

    # Cache contention
    cc = results["cache_contention"]
    print(f"\nCache Contention:")
    print(f"  Expected Hit:   {cc['expected_hit_rate']}%")
    print(f"  Actual Hit:     {cc['actual_hit_rate']:.1f}%")
    print(f"  Contention:     {'✗ Detected' if cc['contention_detected'] else '✓ None'}")

    # Reranker metrics
    rerank = results["reranker_metrics"]
    print(f"\nReranker Metrics:")
    print(f"  Pairs scored:   {rerank.get('pairs_scored', 0)}")
    print(f"  Cache hits:     {rerank.get('cache_hits', 0)}")
    print(f"  Hit rate:       {rerank.get('total_cache_hit_rate', 0):.1f}%")

    # Pass/Fail criteria
    print(f"\nPass/Fail Criteria:")
    for name, criteria in results["pass_criteria"].items():
        if "passed" in criteria:
            status = "✓ PASS" if criteria["passed"] else "✗ FAIL"
            print(f"  {name:25s} {status}")

    # Overall result
    print(f"\n{'=' * 70}")
    if results["overall_passed"]:
        print("OVERALL: ✓ PASSED")
    else:
        print("OVERALL: ✗ FAILED")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Run concurrent test for Context Orchestrator")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent queries (default: 5)"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=10,
        help="Number of rounds to run (default: 10)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/concurrent_test_results.json",
        help="Output file for test results (default: reports/concurrent_test_results.json)"
    )
    args = parser.parse_args()

    try:
        # Load configuration
        config = Settings()

        # Initialize services
        search_service, reranker = initialize_services(config)

        # Run concurrent test
        results = run_concurrent_test(
            search_service=search_service,
            reranker=reranker,
            concurrency=args.concurrency,
            num_rounds=args.rounds
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
        logger.error(f"Concurrent test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
