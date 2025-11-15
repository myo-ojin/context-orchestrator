#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QAM Dictionary Coverage Measurement
Analyzes query coverage by current dictionary and identifies gaps
"""

import json
import sys
from pathlib import Path
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from services.query_attributes import QueryAttributeExtractor

def analyze_coverage():
    """Measure dictionary coverage and identify gaps"""

    # Load query runs
    query_runs_path = Path(__file__).parent.parent / 'tests' / 'scenarios' / 'query_runs.json'
    with open(query_runs_path, 'r', encoding='utf-8') as f:
        query_runs = json.load(f)

    # Initialize extractor without LLM
    extractor = QueryAttributeExtractor(llm_enabled=False)

    # Collect statistics
    covered_queries = []
    uncovered_queries = []
    partial_queries = []

    topic_coverage = Counter()
    project_coverage = Counter()
    doctype_coverage = Counter()

    all_topics = set()
    all_projects = set()
    all_doctypes = set()

    print("=" * 70)
    print("QAM Dictionary Coverage Analysis")
    print("=" * 70)
    print()

    # Analyze each query
    for item in query_runs:
        request = item.get('request', {})
        params = request.get('params', {})
        query = params.get('query', '')

        if not query:
            continue

        # Extract attributes
        attrs = extractor.extract(query)

        # Get expected attributes from relevance
        relevance = item.get('relevance', {})
        expected_topics = set(relevance.get('topic', []))

        # Record all expected attributes
        all_topics.update(expected_topics)

        # Check coverage
        has_topic = bool(attrs.topic)
        has_project = bool(attrs.project_name)
        has_doctype = bool(attrs.doc_type)

        coverage_level = sum([has_topic, has_project, has_doctype])

        if coverage_level == 0:
            uncovered_queries.append({
                'query': query,
                'expected_topics': list(expected_topics),
                'extracted': None
            })
        elif coverage_level >= 2:
            covered_queries.append({
                'query': query,
                'expected_topics': list(expected_topics),
                'extracted': {
                    'topic': attrs.topic,
                    'project': attrs.project_name,
                    'doctype': attrs.doc_type
                }
            })
            if has_topic:
                topic_coverage[attrs.topic] += 1
            if has_project:
                project_coverage[attrs.project_name] += 1
            if has_doctype:
                doctype_coverage[attrs.doc_type] += 1
        else:
            partial_queries.append({
                'query': query,
                'expected_topics': list(expected_topics),
                'extracted': {
                    'topic': attrs.topic,
                    'project': attrs.project_name,
                    'doctype': attrs.doc_type
                }
            })

    total = len(query_runs)
    covered_count = len(covered_queries)
    partial_count = len(partial_queries)
    uncovered_count = len(uncovered_queries)

    coverage_rate = (covered_count / total * 100) if total > 0 else 0
    partial_rate = (partial_count / total * 100) if total > 0 else 0
    uncovered_rate = (uncovered_count / total * 100) if total > 0 else 0

    # Print results
    print(f"Total queries analyzed: {total}")
    print()
    print(f"Fully covered (>=2 attributes): {covered_count} ({coverage_rate:.1f}%)")
    print(f"Partially covered (1 attribute): {partial_count} ({partial_rate:.1f}%)")
    print(f"Not covered (0 attributes): {uncovered_count} ({uncovered_rate:.1f}%)")
    print()

    print("=" * 70)
    print("Coverage by Attribute Type")
    print("=" * 70)
    print()
    print(f"Topic coverage: {len(topic_coverage)} unique topics detected")
    for topic, count in topic_coverage.most_common(10):
        print(f"  {topic}: {count} queries")
    print()

    print(f"Project coverage: {len(project_coverage)} unique projects detected")
    for project, count in project_coverage.most_common(10):
        print(f"  {project}: {count} queries")
    print()

    print(f"DocType coverage: {len(doctype_coverage)} unique doctypes detected")
    for doctype, count in doctype_coverage.most_common(10):
        print(f"  {doctype}: {count} queries")
    print()

    print("=" * 70)
    print("Uncovered Queries (Need Dictionary Expansion)")
    print("=" * 70)
    print()
    for i, item in enumerate(uncovered_queries[:10], 1):
        print(f"{i}. Query: \"{item['query']}\"")
        print(f"   Expected topics: {', '.join(item['expected_topics'])}")
        print()

    if len(uncovered_queries) > 10:
        print(f"... and {len(uncovered_queries) - 10} more uncovered queries")
        print()

    print("=" * 70)
    print("Partially Covered Queries (Could Improve)")
    print("=" * 70)
    print()
    for i, item in enumerate(partial_queries[:5], 1):
        extracted = item['extracted']
        print(f"{i}. Query: \"{item['query']}\"")
        print(f"   Expected topics: {', '.join(item['expected_topics'])}")
        print(f"   Extracted: topic={extracted['topic']}, project={extracted['project']}, doctype={extracted['doctype']}")
        print()

    # Gap analysis
    print("=" * 70)
    print("Gap Analysis")
    print("=" * 70)
    print()

    # Extract all unique queries from uncovered + partial
    missing_keywords = []
    for item in uncovered_queries + partial_queries:
        query = item['query'].lower()
        expected = item['expected_topics']

        # Extract important words (>3 chars, not common words)
        words = set(w for w in query.split() if len(w) > 3 and w not in {'view', 'need', 'show', 'find'})
        missing_keywords.extend(words)

    keyword_freq = Counter(missing_keywords)

    print("Most common keywords in uncovered/partial queries:")
    for keyword, count in keyword_freq.most_common(20):
        print(f"  {keyword}: {count} times")
    print()

    # Recommendations
    print("=" * 70)
    print("Recommendations for 90% Coverage")
    print("=" * 70)
    print()
    print(f"Current coverage: {coverage_rate:.1f}%")
    print(f"Target: 90%")
    print(f"Gap: {90 - coverage_rate:.1f} percentage points")
    print()

    needed_queries = int((90 - coverage_rate) / 100 * total)
    print(f"Need to cover approximately {needed_queries} more queries")
    print()

    print("Priority vocabulary to add:")
    print("1. Release/Deployment: deployment, rollout, canary, blue-green")
    print("2. Incident/Monitoring: alert, monitoring, sla, downtime, outage")
    print("3. Audit/Compliance: audit, compliance, security, vulnerability")
    print("4. Development: refactor, migration, tech-debt, prototype")
    print("5. Operations: backup, disaster-recovery, failover, scaling")
    print()

    return {
        'total': total,
        'covered': covered_count,
        'partial': partial_count,
        'uncovered': uncovered_count,
        'coverage_rate': coverage_rate,
        'recommendations': keyword_freq.most_common(20)
    }

if __name__ == '__main__':
    analyze_coverage()
