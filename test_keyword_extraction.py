#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check what keywords are actually extracted"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.keyword_extractor import extract_keywords, build_keyword_signature

queries = [
    "change feed ingestion errors",
    "ingestion errors in change feed",
    "dashboard pilot deployment",
    "timeline view orchestrator",
    "TypeError chunker fix",
]

print("Query Keyword Analysis")
print("=" * 70)

for query in queries:
    keywords = extract_keywords(query, top_n=3)
    signature = build_keyword_signature(keywords)
    print(f"\nQuery: '{query}'")
    print(f"  Keywords: {keywords}")
    print(f"  Signature: {signature}")

# Check if similar queries produce same signature
print("\n" + "=" * 70)
print("Similarity Check:")
print("=" * 70)

q1 = "change feed ingestion errors"
q2 = "ingestion errors in change feed"
q3 = "errors in change feed ingestion"

k1 = extract_keywords(q1, top_n=3)
k2 = extract_keywords(q2, top_n=3)
k3 = extract_keywords(q3, top_n=3)

s1 = build_keyword_signature(k1)
s2 = build_keyword_signature(k2)
s3 = build_keyword_signature(k3)

print(f"\n1. '{q1}'")
print(f"   Keywords: {k1}")
print(f"   Signature: {s1}")

print(f"\n2. '{q2}'")
print(f"   Keywords: {k2}")
print(f"   Signature: {s2}")
print(f"   Match: {'YES' if s1 == s2 else 'NO'}")

print(f"\n3. '{q3}'")
print(f"   Keywords: {k3}")
print(f"   Signature: {s3}")
print(f"   Match with 1: {'YES' if s1 == s3 else 'NO'}")
print(f"   Match with 2: {'YES' if s2 == s3 else 'NO'}")
