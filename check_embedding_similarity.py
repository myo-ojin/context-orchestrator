#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check embedding similarity between queries"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from test_semantic_cache import MockRouter
from src.utils.vector_utils import cosine_similarity

router = MockRouter()

queries = [
    "change feed ingestion errors",
    "problems with change feed data ingestion",
    "issues consuming data from change feed",
    "dashboard pilot deployment"
]

print("Embedding Similarity Analysis")
print("=" * 70)

embeddings = {}
for q in queries:
    embeddings[q] = router.generate_embedding(q)
    print(f"Generated embedding for: '{q}'")

print()
print("Similarity Matrix:")
print("=" * 70)

for i, q1 in enumerate(queries):
    for j, q2 in enumerate(queries):
        if j >= i:
            sim = cosine_similarity(embeddings[q1], embeddings[q2])
            print(f"\n'{q1}'")
            print(f"  vs '{q2}'")
            print(f"  Similarity: {sim:.4f} {'[ABOVE 0.85]' if sim >= 0.85 else '[BELOW 0.85]'}")
