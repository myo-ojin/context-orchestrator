#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test embedding quality for query vs memory similarity

This test validates that the embedding model (nomic-embed-text) correctly
produces high similarity scores for semantically similar content.

Requirements: Phase 1 - Baseline & Guardrails
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, 'src')

from src.models.local_llm import LocalLLMClient
from src.utils.vector_utils import cosine_similarity

def test_embedding_similarity(export_json=False, output_path=None):
    """Test query-memory similarity with different content lengths"""

    client = LocalLLMClient(
        ollama_url="http://localhost:11434",
        embedding_model="nomic-embed-text"
    )

    # Test cases: (query, memory_content, expected_similarity)
    test_cases = [
        {
            "name": "Exact match (short)",
            "query": "AppBrain release checklist",
            "memory": "AppBrain release checklist",
            "expected": ">0.95"
        },
        {
            "name": "Query vs detailed memory (full content)",
            "query": "AppBrain release checklist",
            "memory": """The AppBrain release checklist is as follows:
1. Environment verification
2. Test execution
3. Deployment approval
4. Rollback preparation
5. Monitoring setup
Complete all steps before proceeding with production deployment.""",
            "expected": "0.5-0.7"
        },
        {
            "name": "Query vs summary",
            "query": "AppBrain release checklist",
            "memory": "AppBrain release checklist includes environment checks, testing, and approval steps.",
            "expected": "0.7-0.85"
        },
        {
            "name": "Query vs title only",
            "query": "How to deploy AppBrain?",
            "memory": "AppBrain deployment guide",
            "expected": "0.6-0.8"
        },
        {
            "name": "Semantic match (different wording)",
            "query": "AppBrain deployment process",
            "memory": "AppBrain release procedure and checklist",
            "expected": "0.7-0.85"
        }
    ]

    print("=" * 80)
    print("EMBEDDING QUALITY TEST")
    print("=" * 80)
    print(f"Model: nomic-embed-text")
    print(f"Threshold: 0.85 (L3 cache)\n")

    for i, case in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {case['name']}")
        print("-" * 80)
        print(f"Query:  {case['query']}")
        print(f"Memory: {case['memory'][:100]}{'...' if len(case['memory']) > 100 else ''}")
        print(f"Expected similarity: {case['expected']}")

        try:
            query_emb = client.generate_embedding(case['query'])
            memory_emb = client.generate_embedding(case['memory'])

            similarity = cosine_similarity(query_emb, memory_emb)

            print(f"Actual similarity:   {similarity:.3f}")

            if similarity >= 0.85:
                status = "[PASS] would hit L3 cache"
            elif similarity >= 0.60:
                status = "[MARGINAL] close to useful range"
            else:
                status = "[FAIL] too low for L3 cache"

            print(f"Status: {status}")

        except Exception as e:
            print(f"[ERROR] {e}")

    print("\n" + "=" * 80)
    print("CONCLUSIONS")
    print("=" * 80)
    print("1. If 'Exact match' < 0.95: Model has issues")
    print("2. If 'Query vs summary' < 0.70: Model not capturing semantic meaning")
    print("3. If 'Query vs full content' < 0.50: Expected behavior (different granularity)")
    print("4. Recommendation: Use summaries/titles for L3 cache instead of full content")
    print("=" * 80)

if __name__ == "__main__":
    test_embedding_similarity()
