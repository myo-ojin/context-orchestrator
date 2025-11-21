#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CI helper that runs scripts.mcp_replay against the canonical baseline and
fails if precision/NDCG regress or any zero-hit queries remain.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    print(" ".join(str(c) for c in cmd))
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def load_zero_hit_report(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("zero_hit_queries", [])


def check_embedding_quality(baseline_path: Path, quality_report_path: Path) -> bool:
    """Check if embedding quality meets baseline thresholds"""

    if not baseline_path.exists():
        print("[WARN] Baseline not found, skipping embedding quality check")
        return True

    if not quality_report_path.exists():
        print("[WARN] Embedding quality report not found, skipping check")
        return True

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    quality = json.loads(quality_report_path.read_text(encoding="utf-8"))

    thresholds = baseline.get("embedding_quality_thresholds", {})

    if not thresholds:
        print("[WARN] No embedding quality thresholds in baseline, skipping check")
        return True

    failures = []

    # Check each test case against thresholds
    for test_case in quality.get("test_cases", []):
        name = test_case.get("name")
        similarity = test_case.get("similarity")

        if name == "exact_match":
            threshold = thresholds.get("exact_match_min", 0.95)
            if similarity < threshold:
                failures.append(f"Exact match: {similarity:.3f} < {threshold:.3f}")

        elif name == "summary":
            threshold = thresholds.get("summary_min", 0.70)
            if similarity < threshold:
                failures.append(f"Summary: {similarity:.3f} < {threshold:.3f}")

        elif name == "full_content":
            threshold = thresholds.get("full_content_min", 0.50)
            if similarity < threshold:
                failures.append(f"Full content: {similarity:.3f} < {threshold:.3f}")

    if failures:
        print("[FAIL] Embedding quality regression detected:")
        for failure in failures:
            print(f"  - {failure}")
        return False

    print("[PASS] Embedding quality meets baseline thresholds")
    return True


def extract_run_metrics(path: Path) -> tuple[float | None, float | None]:
    """Parse the replay log for macro precision and cache hit rate (if available)."""

    macro_precision: float | None = None
    cache_hit_rate: float | None = None

    if not path.exists():
        return macro_precision, cache_hit_rate

    with open(path, "r", encoding="utf-8") as log_file:
        for line in log_file:
            line = line.strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            metrics_block = payload.get("metrics")
            if isinstance(metrics_block, dict):
                macro_precision = metrics_block.get("macro_precision", macro_precision)

            reranker_block = payload.get("reranker_metrics")
            if isinstance(reranker_block, dict):
                reranker_metrics = reranker_block.get("metrics", reranker_block)
                if isinstance(reranker_metrics, dict):
                    cache_hit_rate = reranker_metrics.get("cache_hit_rate", cache_hit_rate)

    return macro_precision, cache_hit_rate


def main():
    parser = argparse.ArgumentParser(description="Run MCP replay regression check")
    parser.add_argument(
        "--baseline",
        default="reports/baselines/mcp_run-20251109-143546.jsonl",
        help="Path to canonical baseline JSONL",
    )
    parser.add_argument(
        "--requests",
        default="tests/scenarios/query_runs.json",
        help="Replay request spec file",
    )
    parser.add_argument(
        "--output",
        default="reports/mcp_runs",
        help="Directory to store latest run log",
    )
    parser.add_argument(
        "--zero-hit-report",
        default="reports/mcp_runs/zero_hits.json",
        help="Where to write zero-hit queries",
    )
    parser.add_argument(
        "--max-macro-precision-drop",
        type=float,
        default=0.02,
        help="Allowed drop vs baseline",
    )
    parser.add_argument(
        "--max-macro-ndcg-drop",
        type=float,
        default=0.02,
        help="Allowed drop vs baseline",
    )
    # Phase 5: Alert thresholds for continuous verification
    parser.add_argument(
        "--min-precision-threshold",
        type=float,
        default=0.80,
        help="Fail if macro precision drops below this absolute value (Phase 5)",
    )
    parser.add_argument(
        "--min-cache-hit-rate",
        type=float,
        default=0.10,
        help="Fail if L3 cache hit rate drops below this value (Phase 5)",
    )
    parser.add_argument(
        "--rpc-timeout",
        type=int,
        default=45,
        help="Seconds to wait for each MCP response before failing",
    )
    parser.add_argument(
        "--precision-baseline",
        default="reports/precision_baseline.json",
        help="Precision baseline snapshot for embedding quality checks",
    )
    parser.add_argument(
        "--embedding-quality-report",
        default="reports/embedding_quality.json",
        help="Embedding quality test report",
    )
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "scripts.mcp_replay",
        "--requests",
        args.requests,
        "--output",
        args.output,
        "--baseline",
        args.baseline,
        "--zero-hit-report",
        args.zero_hit_report,
        "--max-macro-precision-drop",
        str(args.max_macro_precision_drop),
        "--max-macro-ndcg-drop",
        str(args.max_macro_ndcg_drop),
        "--rpc-timeout",
        str(args.rpc_timeout),
    ]
    run_command(cmd)

    # Phase 5: Check absolute threshold for macro precision
    latest_run_path = None
    output_dir = Path(args.output)
    if output_dir.exists():
        run_files = sorted(output_dir.glob("mcp_run-*.jsonl"), key=lambda p: p.name, reverse=True)
        if run_files:
            latest_run_path = run_files[0]

    if latest_run_path and latest_run_path.exists():
        macro_precision, cache_hit_rate = extract_run_metrics(latest_run_path)

        if macro_precision is not None:
            if macro_precision < args.min_precision_threshold:
                print(
                    f"[FAIL] Macro precision {macro_precision:.3f} < threshold {args.min_precision_threshold:.2f}"
                )
                raise SystemExit(1)
        else:
            print("[WARN] Could not locate macro precision in latest run log")

        if cache_hit_rate is not None:
            if cache_hit_rate < args.min_cache_hit_rate:
                print(f"[FAIL] Cache hit rate {cache_hit_rate:.2f} < threshold {args.min_cache_hit_rate:.2f}")
                raise SystemExit(1)
        else:
            print("[WARN] Could not locate cache hit rate in latest run log")

        if macro_precision is not None and cache_hit_rate is not None:
            print(f"[PASS] Absolute thresholds met: Precision={macro_precision:.3f}, Cache={cache_hit_rate:.2f}")

    # Check embedding quality against baseline thresholds
    embedding_ok = check_embedding_quality(
        Path(args.precision_baseline),
        Path(args.embedding_quality_report)
    )

    if not embedding_ok:
        raise SystemExit(1)

    zero_hits = load_zero_hit_report(Path(args.zero_hit_report))
    if zero_hits:
        print(
            f"[FAIL] Detected {len(zero_hits)} zero-hit queries. "
            "Please update QAM辞書 or metadata."
        )
        for item in zero_hits:
            print("-", item.get("query"), "params:", item.get("params"))
        raise SystemExit(1)

    print("[SUCCESS] All regression checks passed (MCP replay, embedding quality, zero-hit queries, absolute thresholds).")


if __name__ == "__main__":
    main()
