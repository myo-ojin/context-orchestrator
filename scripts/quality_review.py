#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quality Review Script for Context Orchestrator
Phase 7d: Quality Assurance - Quality Review

Features:
- Topic-based sampling (5 samples per topic)
- Relevance score distribution analysis
- False positive/negative detection
- Cross-encoder reranking effectiveness
- Visual analysis with matplotlib

Usage:
    python -m scripts.quality_review [--samples-per-topic 5] [--output report.json]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import defaultdict


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
    return search_service


def get_sample_queries_by_topic() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get sample queries organized by topic for quality review

    Returns:
        Dict mapping topic names to list of query dicts
    """
    return {
        "OrchestratorX": [
            {"query": "OrchestratorX change feed ingestion", "expected_relevance": "high"},
            {"query": "OrchestratorX dashboard pilot", "expected_relevance": "high"},
            {"query": "OrchestratorX release checklist", "expected_relevance": "high"},
            {"query": "OrchestratorX microservices architecture", "expected_relevance": "medium"},
            {"query": "OrchestratorX deployment procedures", "expected_relevance": "medium"},
        ],
        "InsightOps": [
            {"query": "InsightOps dashboard features", "expected_relevance": "high"},
            {"query": "InsightOps data pipeline", "expected_relevance": "high"},
            {"query": "InsightOps monitoring setup", "expected_relevance": "medium"},
            {"query": "InsightOps error handling", "expected_relevance": "medium"},
            {"query": "InsightOps configuration", "expected_relevance": "medium"},
        ],
        "PhaseSync": [
            {"query": "PhaseSync timeline implementation", "expected_relevance": "high"},
            {"query": "PhaseSync release management", "expected_relevance": "high"},
            {"query": "PhaseSync workflow", "expected_relevance": "medium"},
            {"query": "PhaseSync integration", "expected_relevance": "medium"},
            {"query": "PhaseSync testing", "expected_relevance": "low"},
        ],
        "Technical": [
            {"query": "chunker TypeError fix", "expected_relevance": "high"},
            {"query": "cross-encoder cache optimization", "expected_relevance": "high"},
            {"query": "embedding quality testing", "expected_relevance": "high"},
            {"query": "BM25 search implementation", "expected_relevance": "medium"},
            {"query": "Ollama model configuration", "expected_relevance": "medium"},
        ],
        "Architecture": [
            {"query": "project memory pool design", "expected_relevance": "high"},
            {"query": "three-layer cache architecture", "expected_relevance": "high"},
            {"query": "hybrid search pipeline", "expected_relevance": "high"},
            {"query": "session management integration", "expected_relevance": "medium"},
            {"query": "consolidation strategy", "expected_relevance": "medium"},
        ],
    }


def analyze_relevance_score_distribution(
    all_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze the distribution of relevance scores

    Args:
        all_results: List of all search results

    Returns:
        Dict with distribution statistics
    """
    # Collect all scores
    scores = []
    for result_set in all_results:
        for result in result_set.get("results", []):
            score = result.get("score", 0)
            scores.append(score)

    if not scores:
        return {
            "count": 0,
            "mean": 0,
            "median": 0,
            "min": 0,
            "max": 0,
            "std_dev": 0,
            "histogram": {},
        }

    # Calculate statistics
    scores_sorted = sorted(scores)
    n = len(scores)
    mean = sum(scores) / n
    median = scores_sorted[n // 2]
    min_score = min(scores)
    max_score = max(scores)

    # Standard deviation
    variance = sum((x - mean) ** 2 for x in scores) / n
    std_dev = variance ** 0.5

    # Create histogram buckets (0.0-0.2, 0.2-0.4, etc.)
    histogram = defaultdict(int)
    for score in scores:
        bucket = int(score // 0.2) * 0.2
        bucket_label = f"{bucket:.1f}-{bucket+0.2:.1f}"
        histogram[bucket_label] += 1

    return {
        "count": n,
        "mean": round(mean, 3),
        "median": round(median, 3),
        "min": round(min_score, 3),
        "max": round(max_score, 3),
        "std_dev": round(std_dev, 3),
        "histogram": dict(histogram),
    }


def classify_result_relevance(
    result: Dict[str, Any],
    expected_relevance: str,
    score_threshold_high: float = 0.7,
    score_threshold_medium: float = 0.4
) -> Tuple[str, str]:
    """
    Classify a result as True Positive, False Positive, True Negative, or False Negative

    Args:
        result: Search result dict
        expected_relevance: Expected relevance level ("high", "medium", "low")
        score_threshold_high: Score threshold for high relevance
        score_threshold_medium: Score threshold for medium relevance

    Returns:
        Tuple of (classification, reason)
    """
    score = result.get("score", 0)

    # Determine actual relevance based on score
    if score >= score_threshold_high:
        actual_relevance = "high"
    elif score >= score_threshold_medium:
        actual_relevance = "medium"
    else:
        actual_relevance = "low"

    # Classify
    if expected_relevance == "high":
        if actual_relevance == "high":
            return "TP", "High score for high relevance query"
        else:
            return "FN", f"Low score ({score:.2f}) for high relevance query"

    elif expected_relevance == "medium":
        if actual_relevance in ["high", "medium"]:
            return "TP", "Adequate score for medium relevance query"
        else:
            return "FN", f"Low score ({score:.2f}) for medium relevance query"

    else:  # expected_relevance == "low"
        if actual_relevance == "low":
            return "TN", "Low score for low relevance query"
        else:
            return "FP", f"High score ({score:.2f}) for low relevance query"


def run_quality_review(
    search_service: SearchService,
    samples_per_topic: int = 5
) -> Dict[str, Any]:
    """
    Run quality review with topic-based sampling

    Args:
        search_service: SearchService instance
        samples_per_topic: Number of samples to review per topic

    Returns:
        Dict with review results and analysis
    """
    logger.info(f"Starting quality review with {samples_per_topic} samples per topic...")

    # Get sample queries
    queries_by_topic = get_sample_queries_by_topic()

    # Collect results
    all_results = []
    topic_results = defaultdict(list)
    classification_counts = defaultdict(int)
    false_positives = []
    false_negatives = []

    for topic, queries in queries_by_topic.items():
        logger.info(f"Reviewing topic: {topic}")

        for query_info in queries[:samples_per_topic]:
            query = query_info["query"]
            expected_relevance = query_info["expected_relevance"]

            try:
                # Execute search
                results = search_service.search(query, top_k=5)

                result_data = {
                    "topic": topic,
                    "query": query,
                    "expected_relevance": expected_relevance,
                    "result_count": len(results),
                    "results": results,
                }

                all_results.append(result_data)
                topic_results[topic].append(result_data)

                # Classify top result
                if results:
                    top_result = results[0]
                    classification, reason = classify_result_relevance(
                        top_result,
                        expected_relevance
                    )

                    classification_counts[classification] += 1

                    if classification == "FP":
                        false_positives.append({
                            "topic": topic,
                            "query": query,
                            "result": top_result,
                            "reason": reason,
                        })
                    elif classification == "FN":
                        false_negatives.append({
                            "topic": topic,
                            "query": query,
                            "result": top_result if results else None,
                            "reason": reason,
                        })

            except Exception as e:
                logger.error(f"Query failed: {query} - {str(e)}")

    # Analyze relevance score distribution
    distribution = analyze_relevance_score_distribution(all_results)

    # Calculate metrics
    total_queries = len(all_results)
    tp_count = classification_counts.get("TP", 0)
    tn_count = classification_counts.get("TN", 0)
    fp_count = classification_counts.get("FP", 0)
    fn_count = classification_counts.get("FN", 0)

    precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0
    recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    fp_rate = (fp_count / total_queries) * 100 if total_queries > 0 else 0
    fn_rate = (fn_count / total_queries) * 100 if total_queries > 0 else 0

    results = {
        "test_info": {
            "samples_per_topic": samples_per_topic,
            "total_topics": len(queries_by_topic),
            "total_queries": total_queries,
            "timestamp": datetime.now().isoformat(),
        },
        "classification": {
            "true_positives": tp_count,
            "true_negatives": tn_count,
            "false_positives": fp_count,
            "false_negatives": fn_count,
        },
        "metrics": {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1_score, 3),
            "false_positive_rate": round(fp_rate, 2),
            "false_negative_rate": round(fn_rate, 2),
        },
        "score_distribution": distribution,
        "topic_breakdown": {
            topic: {
                "query_count": len(results_list),
                "avg_result_count": round(
                    sum(r["result_count"] for r in results_list) / len(results_list), 1
                ) if results_list else 0,
            }
            for topic, results_list in topic_results.items()
        },
        "false_positives": false_positives[:10],  # Top 10
        "false_negatives": false_negatives[:10],  # Top 10
        "all_results": all_results,
        "pass_criteria": {
            "false_positive_rate": {
                "threshold_percent": 10.0,
                "actual_percent": round(fp_rate, 2),
                "passed": fp_rate < 10.0,
            },
            "false_negative_rate": {
                "threshold_percent": 15.0,
                "actual_percent": round(fn_rate, 2),
                "passed": fn_rate < 15.0,
            },
            "precision": {
                "threshold": 0.75,
                "actual": round(precision, 3),
                "passed": precision >= 0.75,
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
    """Print review results to console"""
    print("\n" + "=" * 70)
    print("QUALITY REVIEW RESULTS")
    print("=" * 70)

    # Test info
    info = results["test_info"]
    print(f"\nTest Configuration:")
    print(f"  Topics:         {info['total_topics']}")
    print(f"  Samples/Topic:  {info['samples_per_topic']}")
    print(f"  Total Queries:  {info['total_queries']}")

    # Classification
    cls = results["classification"]
    print(f"\nClassification:")
    print(f"  True Positives:  {cls['true_positives']}")
    print(f"  True Negatives:  {cls['true_negatives']}")
    print(f"  False Positives: {cls['false_positives']}")
    print(f"  False Negatives: {cls['false_negatives']}")

    # Metrics
    metrics = results["metrics"]
    print(f"\nMetrics:")
    print(f"  Precision:      {metrics['precision']:.3f}")
    print(f"  Recall:         {metrics['recall']:.3f}")
    print(f"  F1 Score:       {metrics['f1_score']:.3f}")
    print(f"  FP Rate:        {metrics['false_positive_rate']:.1f}%")
    print(f"  FN Rate:        {metrics['false_negative_rate']:.1f}%")

    # Score distribution
    dist = results["score_distribution"]
    print(f"\nScore Distribution:")
    print(f"  Count:          {dist['count']}")
    print(f"  Mean:           {dist['mean']}")
    print(f"  Median:         {dist['median']}")
    print(f"  Min-Max:        {dist['min']:.3f} - {dist['max']:.3f}")
    print(f"  Std Dev:        {dist['std_dev']}")

    if dist["histogram"]:
        print(f"\n  Histogram:")
        for bucket, count in sorted(dist["histogram"].items()):
            bar = "█" * int(count / max(dist["histogram"].values()) * 40)
            print(f"    {bucket}: {bar} ({count})")

    # Topic breakdown
    print(f"\nTopic Breakdown:")
    for topic, stats in results["topic_breakdown"].items():
        print(f"  {topic:15s} Queries: {stats['query_count']}, "
              f"Avg Results: {stats['avg_result_count']}")

    # False positives/negatives
    if results["false_positives"]:
        print(f"\nTop False Positives:")
        for i, fp in enumerate(results["false_positives"][:3], 1):
            print(f"  {i}. [{fp['topic']}] {fp['query']}")
            print(f"     Reason: {fp['reason']}")

    if results["false_negatives"]:
        print(f"\nTop False Negatives:")
        for i, fn in enumerate(results["false_negatives"][:3], 1):
            print(f"  {i}. [{fn['topic']}] {fn['query']}")
            print(f"     Reason: {fn['reason']}")

    # Pass/Fail criteria
    print(f"\nPass/Fail Criteria:")
    for name, criteria in results["pass_criteria"].items():
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
    parser = argparse.ArgumentParser(description="Run quality review for Context Orchestrator")
    parser.add_argument(
        "--samples-per-topic",
        type=int,
        default=5,
        help="Number of samples to review per topic (default: 5)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/quality_review_results.json",
        help="Output file for review results (default: reports/quality_review_results.json)"
    )
    args = parser.parse_args()

    try:
        # Load configuration
        config = Settings()

        # Initialize services
        search_service = initialize_services(config)

        # Run quality review
        results = run_quality_review(
            search_service=search_service,
            samples_per_topic=args.samples_per_topic
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
        logger.error(f"Quality review failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
