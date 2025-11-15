#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Benchmark Query Attribute Modeling (QAM) latency and outputs.

This script loads the configured ModelRouter (typically Ollama) and
executes QueryAttributeExtractor against a list of queries, recording
Latency + extracted attributes. Use this to verify that the heuristic-first
→ LLM fallback pipeline performs within acceptable bounds.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Iterable, List

from src.config import load_config
from src.main import init_models
from src.services.query_attributes import QueryAttributeExtractor


def load_queries_from_file(path: Path) -> List[str]:
    data = json.loads(path.read_text(encoding='utf-8'))
    queries = []
    for entry in data:
        req = entry.get("request", entry)
        params = req.get("params") or {}
        query = params.get("query")
        if query:
            queries.append(query)
    return queries


def iter_queries(args) -> Iterable[str]:
    if args.queries:
        for q in args.queries:
            yield q
        return

    if args.query_file:
        yield from load_queries_from_file(Path(args.query_file))
        return

    # Default fallback: a handful of representative prompts
    defaults = [
        "timeline view orchestrator",
        "change feed ingestion errors",
        "hybrid search rerank plan",
        "retention policy long term memories",
        "obsidian vault edits triage",
        "TypeError chunker fix",
    ]
    for q in defaults:
        yield q


def main():
    parser = argparse.ArgumentParser(description="Benchmark QAM latency/output")
    parser.add_argument("--config", help="Path to config.yaml", default=None)
    parser.add_argument(
        "--query-file",
        help="JSON file (e.g., tests/scenarios/query_runs.json) to pull queries from",
    )
    parser.add_argument(
        "--queries",
        nargs="*",
        help="Directly specify one or more queries (overrides --query-file)",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path to write detailed results as JSON",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    model_router = init_models(config)
    extractor = QueryAttributeExtractor(
        model_router=model_router,
        min_llm_confidence=config.search.query_attribute_min_confidence,
        llm_enabled=config.search.query_attribute_llm_enabled,
    )

    rows = []
    print(f"{'Latency(ms)':>12} | {'Query':<60} | topic / doc_type / project / severity")
    print("-" * 120)
    for query in iter_queries(args):
        start = time.perf_counter()
        attributes = extractor.extract(query)
        duration = (time.perf_counter() - start) * 1000
        rows.append(
            {
                "query": query,
                "latency_ms": duration,
                "topic": attributes.topic,
                "doc_type": attributes.doc_type,
                "project_name": attributes.project_name,
                "severity": attributes.severity,
                "confidence": attributes.confidence,
            }
        )
        print(
            f"{duration:12.0f} | {query[:60]:<60} | "
            f"{attributes.topic or '-'} / "
            f"{attributes.doc_type or '-'} / "
            f"{attributes.project_name or '-'} / "
            f"{attributes.severity or '-'}"
        )

    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
