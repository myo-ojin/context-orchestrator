#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance Profiler for Context Orchestrator

Profiles and benchmarks critical system operations:
- Search latency
- Ingestion throughput
- Memory footprint
- Consolidation time

Requirements: Requirement 8 (Phase 14.2)

Usage:
    python scripts/performance_profiler.py [--config CONFIG_PATH] [--runs N] [--output REPORT_PATH]
"""

import argparse
import time
import sys
import json
import psutil
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config
from src.services.ingestion import IngestionService
from src.services.search import SearchService
from src.services.consolidation import ConsolidationService
from src.processing.classifier import SchemaClassifier
from src.processing.chunker import Chunker
from src.processing.indexer import Indexer
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index
from src.models.local_llm import LocalLLMClient


class PerformanceProfiler:
    """Performance profiling and benchmarking tool"""

    def __init__(self, config_path: str = None):
        """Initialize profiler with configuration"""
        self.config = load_config(config_path)
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self._get_system_info(),
            'benchmarks': {}
        }
        self.temp_dir = None

    def _get_system_info(self) -> Dict[str, Any]:
        """Collect system information"""
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'python_version': sys.version.split()[0],
            'platform': sys.platform
        }

    def _setup_test_environment(self):
        """Set up temporary test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix='context_orchestrator_perf_')

        # Initialize storage with temp directory
        vector_db = ChromaVectorDB(
            persist_directory=str(Path(self.temp_dir) / "chroma_db")
        )

        bm25_index = BM25Index(
            index_path=str(Path(self.temp_dir) / "bm25_index.pkl")
        )

        # Initialize LLM client
        llm_client = LocalLLMClient(
            base_url=self.config.ollama.url,
            embedding_model=self.config.ollama.embedding_model,
            inference_model=self.config.ollama.inference_model
        )

        # Initialize processing components
        classifier = SchemaClassifier(llm_client=llm_client)
        chunker = Chunker()
        indexer = Indexer(vector_db=vector_db, bm25_index=bm25_index)

        # Initialize services
        ingestion_service = IngestionService(
            classifier=classifier,
            chunker=chunker,
            indexer=indexer,
            llm_client=llm_client
        )

        search_service = SearchService(
            vector_db=vector_db,
            bm25_index=bm25_index,
            llm_client=llm_client,
            candidate_count=self.config.search.candidate_count,
            result_count=self.config.search.result_count
        )

        consolidation_service = ConsolidationService(
            vector_db=vector_db,
            bm25_index=bm25_index,
            llm_client=llm_client,
            similarity_threshold=self.config.clustering.similarity_threshold
        )

        return {
            'ingestion': ingestion_service,
            'search': search_service,
            'consolidation': consolidation_service,
            'vector_db': vector_db,
            'bm25_index': bm25_index
        }

    def _cleanup_test_environment(self):
        """Clean up temporary test environment"""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage in MB"""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return {
            'rss_mb': round(mem_info.rss / (1024**2), 2),
            'vms_mb': round(mem_info.vms / (1024**2), 2)
        }

    def benchmark_search_latency(self, services: Dict, runs: int = 100) -> Dict[str, Any]:
        """
        Benchmark search latency

        Target: ≤200ms (Requirement 8)
        """
        print(f"\n[*] Benchmarking search latency ({runs} runs)...")

        ingestion = services['ingestion']
        search = services['search']

        # Ingest test data
        print("  - Ingesting test data...")
        test_queries = []
        for i in range(50):
            conversation = {
                'user': f'How do I implement {["sorting", "searching", "hashing", "graph traversal", "dynamic programming"][i % 5]} in Python?',
                'assistant': f'Here is how to implement {["sorting", "searching", "hashing", "graph traversal", "dynamic programming"][i % 5]}:\n\n```python\ndef example_{i}():\n    # Implementation here\n    pass\n```\n\nThis algorithm has O(n log n) time complexity.' * 5,
                'source': 'test_benchmark',
                'refs': [f'https://example.com/ref{i}']
            }
            ingestion.ingest_conversation(conversation)

            if i % 5 == 0:
                test_queries.append(conversation['user'])

        print(f"  - Ingested {50} conversations")
        print(f"  - Running {runs} search queries...")

        # Measure search latency
        latencies = []
        mem_before = self._get_memory_usage()

        for i in range(runs):
            query = test_queries[i % len(test_queries)]

            start_time = time.perf_counter()
            results = search.search(query, limit=10)
            end_time = time.perf_counter()

            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            if (i + 1) % 20 == 0:
                print(f"  - Completed {i + 1}/{runs} queries (avg: {sum(latencies[-20:]) / 20:.2f}ms)")

        mem_after = self._get_memory_usage()

        # Calculate statistics
        latencies.sort()
        avg_latency = sum(latencies) / len(latencies)
        p50_latency = latencies[len(latencies) // 2]
        p95_latency = latencies[int(len(latencies) * 0.95)]
        p99_latency = latencies[int(len(latencies) * 0.99)]
        min_latency = latencies[0]
        max_latency = latencies[-1]

        result = {
            'runs': runs,
            'avg_latency_ms': round(avg_latency, 2),
            'p50_latency_ms': round(p50_latency, 2),
            'p95_latency_ms': round(p95_latency, 2),
            'p99_latency_ms': round(p99_latency, 2),
            'min_latency_ms': round(min_latency, 2),
            'max_latency_ms': round(max_latency, 2),
            'target_latency_ms': 200,
            'meets_target': p95_latency <= 200,
            'memory_delta_mb': round(mem_after['rss_mb'] - mem_before['rss_mb'], 2)
        }

        print(f"\n  ✓ Search Latency Results:")
        print(f"    - Average: {result['avg_latency_ms']}ms")
        print(f"    - P50: {result['p50_latency_ms']}ms")
        print(f"    - P95: {result['p95_latency_ms']}ms")
        print(f"    - P99: {result['p99_latency_ms']}ms")
        print(f"    - Target (≤200ms): {'✓ PASS' if result['meets_target'] else '✗ FAIL'}")

        return result

    def benchmark_ingestion_throughput(self, services: Dict, count: int = 50) -> Dict[str, Any]:
        """
        Benchmark ingestion throughput

        Target: <5 seconds per conversation (Requirement 1)
        """
        print(f"\n[*] Benchmarking ingestion throughput ({count} conversations)...")

        ingestion = services['ingestion']

        conversations = [
            {
                'user': f'Question {i}: Explain topic {i % 10}',
                'assistant': f'Answer {i}: This is a detailed explanation about topic {i % 10}. ' * 50,
                'source': 'test_benchmark',
                'refs': [f'https://example.com/doc{i}']
            }
            for i in range(count)
        ]

        mem_before = self._get_memory_usage()
        start_time = time.perf_counter()

        for i, conv in enumerate(conversations):
            ingestion.ingest_conversation(conv)

            if (i + 1) % 10 == 0:
                elapsed = time.perf_counter() - start_time
                rate = (i + 1) / elapsed
                print(f"  - Ingested {i + 1}/{count} conversations ({rate:.2f} conv/sec)")

        end_time = time.perf_counter()
        mem_after = self._get_memory_usage()

        total_time = end_time - start_time
        avg_time_per_conv = total_time / count
        throughput = count / total_time

        result = {
            'count': count,
            'total_time_sec': round(total_time, 2),
            'avg_time_per_conversation_sec': round(avg_time_per_conv, 2),
            'throughput_conv_per_sec': round(throughput, 2),
            'target_time_sec': 5,
            'meets_target': avg_time_per_conv < 5,
            'memory_delta_mb': round(mem_after['rss_mb'] - mem_before['rss_mb'], 2)
        }

        print(f"\n  ✓ Ingestion Throughput Results:")
        print(f"    - Total time: {result['total_time_sec']}s")
        print(f"    - Average per conversation: {result['avg_time_per_conversation_sec']}s")
        print(f"    - Throughput: {result['throughput_conv_per_sec']} conv/sec")
        print(f"    - Target (<5s/conv): {'✓ PASS' if result['meets_target'] else '✗ FAIL'}")

        return result

    def benchmark_consolidation_time(self, services: Dict) -> Dict[str, Any]:
        """
        Benchmark consolidation time

        Target: <5 minutes for 10K memories (from requirements)
        """
        print(f"\n[*] Benchmarking consolidation time...")

        ingestion = services['ingestion']
        consolidation = services['consolidation']

        # Ingest test data (scaled down for reasonable test time)
        test_size = 100
        print(f"  - Ingesting {test_size} conversations...")

        for i in range(test_size):
            conversation = {
                'user': f'Question about topic {i % 20}',
                'assistant': f'Detailed answer about topic {i % 20}. ' * 20,
                'source': 'test_benchmark',
                'refs': []
            }
            ingestion.ingest_conversation(conversation)

        print("  - Running consolidation...")
        mem_before = self._get_memory_usage()
        start_time = time.perf_counter()

        stats = consolidation.consolidate()

        end_time = time.perf_counter()
        mem_after = self._get_memory_usage()

        total_time = end_time - start_time

        # Extrapolate to 10K memories
        extrapolated_time_10k = (total_time / test_size) * 10000

        result = {
            'test_size': test_size,
            'total_time_sec': round(total_time, 2),
            'extrapolated_time_10k_sec': round(extrapolated_time_10k, 2),
            'extrapolated_time_10k_min': round(extrapolated_time_10k / 60, 2),
            'target_time_min': 5,
            'meets_target': extrapolated_time_10k / 60 < 5,
            'stats': stats,
            'memory_delta_mb': round(mem_after['rss_mb'] - mem_before['rss_mb'], 2)
        }

        print(f"\n  ✓ Consolidation Results:")
        print(f"    - Time for {test_size} memories: {result['total_time_sec']}s")
        print(f"    - Extrapolated time for 10K: {result['extrapolated_time_10k_min']:.2f} min")
        print(f"    - Target (<5 min for 10K): {'✓ PASS' if result['meets_target'] else '✗ FAIL'}")
        print(f"    - Migrated: {stats.get('migrated', 0)}")
        print(f"    - Clustered: {stats.get('clustered', 0)}")
        print(f"    - Forgotten: {stats.get('forgotten', 0)}")

        return result

    def benchmark_memory_footprint(self, services: Dict) -> Dict[str, Any]:
        """
        Benchmark memory footprint

        Target: ~1GB resident, ~3GB peak (from requirements)
        """
        print(f"\n[*] Benchmarking memory footprint...")

        ingestion = services['ingestion']
        search = services['search']

        mem_initial = self._get_memory_usage()
        mem_peak = mem_initial.copy()

        # Simulate workload
        print("  - Running workload simulation...")

        for i in range(100):
            # Ingest
            conversation = {
                'user': f'Memory test question {i}',
                'assistant': f'Memory test answer {i}. ' * 100,
                'source': 'test_benchmark',
                'refs': []
            }
            ingestion.ingest_conversation(conversation)

            # Search
            if i % 10 == 0:
                search.search(f"memory test {i}", limit=10)

            # Track peak memory
            mem_current = self._get_memory_usage()
            if mem_current['rss_mb'] > mem_peak['rss_mb']:
                mem_peak = mem_current.copy()

            if (i + 1) % 20 == 0:
                print(f"  - Completed {i + 1}/100 operations (current: {mem_current['rss_mb']}MB)")

        mem_final = self._get_memory_usage()

        result = {
            'initial_rss_mb': mem_initial['rss_mb'],
            'peak_rss_mb': mem_peak['rss_mb'],
            'final_rss_mb': mem_final['rss_mb'],
            'target_resident_mb': 1024,
            'target_peak_mb': 3072,
            'meets_resident_target': mem_final['rss_mb'] <= 1024,
            'meets_peak_target': mem_peak['rss_mb'] <= 3072
        }

        print(f"\n  ✓ Memory Footprint Results:")
        print(f"    - Initial: {result['initial_rss_mb']}MB")
        print(f"    - Peak: {result['peak_rss_mb']}MB")
        print(f"    - Final: {result['final_rss_mb']}MB")
        print(f"    - Resident target (≤1GB): {'✓ PASS' if result['meets_resident_target'] else '✗ FAIL'}")
        print(f"    - Peak target (≤3GB): {'✓ PASS' if result['meets_peak_target'] else '✗ FAIL'}")

        return result

    def run_all_benchmarks(self, runs: int = 100) -> Dict[str, Any]:
        """Run all performance benchmarks"""
        print("=" * 60)
        print("Context Orchestrator - Performance Profiler")
        print("=" * 60)

        try:
            # Set up test environment
            print("\n[*] Setting up test environment...")
            services = self._setup_test_environment()
            print("  ✓ Test environment ready")

            # Run benchmarks
            self.results['benchmarks']['search_latency'] = self.benchmark_search_latency(services, runs)
            self.results['benchmarks']['ingestion_throughput'] = self.benchmark_ingestion_throughput(services, 50)
            self.results['benchmarks']['consolidation_time'] = self.benchmark_consolidation_time(services)
            self.results['benchmarks']['memory_footprint'] = self.benchmark_memory_footprint(services)

            # Overall assessment
            print("\n" + "=" * 60)
            print("Overall Performance Assessment")
            print("=" * 60)

            all_targets_met = all([
                self.results['benchmarks']['search_latency']['meets_target'],
                self.results['benchmarks']['ingestion_throughput']['meets_target'],
                self.results['benchmarks']['consolidation_time']['meets_target'],
                self.results['benchmarks']['memory_footprint']['meets_resident_target'],
                self.results['benchmarks']['memory_footprint']['meets_peak_target']
            ])

            if all_targets_met:
                print("\n✓ ALL PERFORMANCE TARGETS MET")
            else:
                print("\n⚠ SOME PERFORMANCE TARGETS NOT MET")

            return self.results

        finally:
            # Clean up
            print("\n[*] Cleaning up test environment...")
            self._cleanup_test_environment()
            print("  ✓ Cleanup complete")

    def save_report(self, output_path: str):
        """Save performance report to file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[*] Performance report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Performance Profiler for Context Orchestrator')
    parser.add_argument('--config', type=str, default=None, help='Path to config file')
    parser.add_argument('--runs', type=int, default=100, help='Number of search runs for benchmarking')
    parser.add_argument('--output', type=str, default=None, help='Path to save performance report (JSON)')

    args = parser.parse_args()

    try:
        profiler = PerformanceProfiler(config_path=args.config)
        results = profiler.run_all_benchmarks(runs=args.runs)

        if args.output:
            profiler.save_report(args.output)
        else:
            # Save to default location
            default_output = Path.home() / '.context-orchestrator' / 'performance_report.json'
            default_output.parent.mkdir(parents=True, exist_ok=True)
            profiler.save_report(str(default_output))

    except KeyboardInterrupt:
        print("\n\n[*] Benchmarking interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during benchmarking: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
