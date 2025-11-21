#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test embedding quality for CI integration

This test validates embedding model quality and exports results in JSON format
for automated regression detection.

Requirements: Phase 1 - Baseline & Guardrails
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.local_llm import LocalLLMClient
from src.utils.vector_utils import cosine_similarity

def test_embedding_quality():
    """Test query-memory similarity with different content lengths"""

    client = LocalLLMClient(
        ollama_url="http://localhost:11434",
        embedding_model="nomic-embed-text"
    )

    # Test cases with expected thresholds
    test_cases = [
        {
            "name": "exact_match",
            "query": "OrchestratorX release checklist",
            "memory": "OrchestratorX release checklist",
            "expected_min": 0.95
        },
        {
            "name": "full_content",
            "query": "OrchestratorX release checklist",
            "memory": """The OrchestratorX release checklist is as follows:
1. Environment verification
2. Test execution
3. Deployment approval
4. Rollback preparation
5. Monitoring setup
Complete all steps before proceeding with production deployment.""",
            "expected_min": 0.50
        },
        {
            "name": "summary",
            "query": "OrchestratorX release checklist",
            "memory": "OrchestratorX release checklist includes environment checks, testing, and approval steps.",
            "expected_min": 0.70
        }
    ]

    results = {
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "model": "nomic-embed-text",
        "test_cases": [],
        "all_passed": True
    }

    print("=" * 80)
    print("EMBEDDING QUALITY TEST (CI)")
    print("=" * 80)
    print(f"Model: nomic-embed-text")
    print(f"Timestamp: {results['timestamp']}\n")

    for i, case in enumerate(test_cases, 1):
        print(f"[Test {i}] {case['name']}")
        print("-" * 80)
        print(f"Query:  {case['query']}")
        print(f"Memory: {case['memory'][:100]}{'...' if len(case['memory']) > 100 else ''}")
        print(f"Expected minimum similarity: {case['expected_min']:.2f}")

        try:
            query_emb = client.generate_embedding(case['query'])
            memory_emb = client.generate_embedding(case['memory'])
            similarity = cosine_similarity(query_emb, memory_emb)

            passed = similarity >= case['expected_min']
            status = "[PASS]" if passed else "[FAIL]"

            print(f"Actual similarity:   {similarity:.3f}")
            print(f"Status: {status}")

            test_result = {
                "name": case['name'],
                "similarity": round(similarity, 3),
                "expected_min": case['expected_min'],
                "passed": passed
            }

            results["test_cases"].append(test_result)

            if not passed:
                results["all_passed"] = False

        except Exception as e:
            print(f"[ERROR] {e}")
            results["test_cases"].append({
                "name": case['name'],
                "error": str(e),
                "passed": False
            })
            results["all_passed"] = False

        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed_count = sum(1 for tc in results["test_cases"] if tc.get("passed"))
    total_count = len(results["test_cases"])
    print(f"Passed: {passed_count}/{total_count}")
    print(f"Overall: {'[PASS]' if results['all_passed'] else '[FAIL]'}")
    print("=" * 80)

    return results

def main():
    parser = argparse.ArgumentParser(description='Test embedding quality')
    parser.add_argument('--export-json', action='store_true',
                        help='Export results to JSON file')
    parser.add_argument('--output', type=str,
                        default='reports/embedding_quality.json',
                        help='Output JSON file path')
    args = parser.parse_args()

    results = test_embedding_quality()

    if args.export_json:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] Results exported to: {output_path}")

    # Exit with non-zero code if any test failed
    sys.exit(0 if results['all_passed'] else 1)

if __name__ == "__main__":
    main()
