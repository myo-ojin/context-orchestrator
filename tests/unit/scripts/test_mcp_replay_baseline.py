#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import json

from scripts.mcp_replay import (
    detect_regression,
    load_metrics_from_run,
    extract_zero_hit_queries,
    write_zero_hit_report,
)


def test_detect_regression_flags_drop():
    baseline = {"macro_precision": 0.8, "macro_ndcg": 0.72}
    current = {"macro_precision": 0.74, "macro_ndcg": 0.7}

    regression, summary = detect_regression(baseline, current, 0.03, 0.05)
    assert regression is True
    assert summary["precision_drop"] == baseline["macro_precision"] - current["macro_precision"]


def test_detect_regression_passes_within_limits():
    baseline = {"macro_precision": 0.8, "macro_ndcg": 0.72}
    current = {"macro_precision": 0.78, "macro_ndcg": 0.71}

    regression, _ = detect_regression(baseline, current, 0.05, 0.05)
    assert regression is False


def test_load_metrics_from_run(tmp_path: Path):
    target = tmp_path / "run.jsonl"
    entries = [
        {"request": {"id": 1}},
        {"metrics": {"macro_precision": 0.7}},
        {"metrics": {"macro_precision": 0.75, "macro_ndcg": 0.69}},
    ]
    target.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    metrics = load_metrics_from_run(target)
    assert metrics["macro_precision"] == 0.75
    assert metrics["macro_ndcg"] == 0.69


def test_extract_zero_hit_queries():
    metrics = {"queries": [{"id": 1, "relevant_hits": 0}, {"id": 2, "relevant_hits": 2}]}
    results = [
        {"request": {"id": 1, "method": "search_memory", "params": {"query": "miss"}}, "relevance": {"topic": ["obsidian"]}},
        {"request": {"id": 2, "method": "search_memory", "params": {"query": "hit"}}},
    ]

    zero = extract_zero_hit_queries(results, metrics)
    assert len(zero) == 1
    assert zero[0]["query"] == "miss"


def test_write_zero_hit_report(tmp_path: Path):
    metrics = {"queries": [{"id": 3, "relevant_hits": 0}]}
    results = [
        {"request": {"id": 3, "method": "search_memory", "params": {"query": "another"}}, "relevance": {}}
    ]
    out = tmp_path / "zero.json"

    write_zero_hit_report(results, metrics, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["zero_hit_queries"]
    assert data["zero_hit_queries"][0]["query"] == "another"
