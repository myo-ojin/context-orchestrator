#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Replay a list of MCP JSON-RPC requests and record the responses."""

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


def start_mcp_server():
    cmd = [sys.executable, "-m", "scripts.mcp_stdio"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return proc


def wait_for_server_ready(proc, timeout: int = 30) -> None:
    start = time.time()
    while time.time() - start < timeout:
        line = proc.stdout.readline()
        if not line:
            break
        if "MCP Protocol Handler started" in line:
            return
    raise RuntimeError("MCP server did not signal readiness")


def send_request(proc, request):
    payload = json.dumps(request)
    proc.stdin.write(payload + "\n")
    proc.stdin.flush()


def read_response(proc, target_id, timeout=15):
    deadline = time.time() + timeout
    buffer = []
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        buffer.append(line.rstrip())
        stripped = line.strip()
        if stripped.startswith("{"):
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if obj.get("id") == target_id:
                return obj, buffer
    raise RuntimeError(f"Timed out waiting for response id {target_id}")


def load_request_specs(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)

    specs = []
    for entry in raw:
        if "request" in entry:
            specs.append(entry)
        else:
            specs.append({"request": entry})
    return specs


def fetch_reranker_metrics(proc, rpc_timeout: int):
    req = {
        "jsonrpc": "2.0",
        "id": 888888,
        "method": "get_reranker_metrics",
        "params": {},
    }
    try:
        send_request(proc, req)
        resp, logs = read_response(proc, req["id"], timeout=rpc_timeout)
        return resp.get("result"), {
            "request": req,
            "response": resp,
            "logs": logs,
        }
    except Exception as exc:
        print(f"Warning: failed to fetch reranker metrics ({exc})", file=sys.stderr)
        return None, None


def replay(request_specs, output_dir, rpc_timeout=15):
    proc = start_mcp_server()
    try:
        wait_for_server_ready(proc, timeout=rpc_timeout)
    except Exception as exc:
        proc.terminate()
        raise RuntimeError(f"MCP server failed to start: {exc}") from exc
    results = []
    reranker_metrics = None
    session_id = None
    try:
        # Start session for project prefetch support
        try:
            send_request(proc, {"jsonrpc": "2.0", "id": 99998, "method": "start_session", "params": {}})
            session_resp, session_logs = read_response(proc, 99998, timeout=rpc_timeout)
            if "result" in session_resp:
                session_id = session_resp["result"].get("session_id")
                print(f"Started session: {session_id}", file=sys.stderr)
            results.append({"request": {"method": "start_session"}, "response": session_resp})
        except Exception as exc:
            print(f"Warning: start_session failed ({exc})", file=sys.stderr)

        # Prefetch projects for name -> id mapping
        name_to_id = {}
        try:
            send_request(proc, {"jsonrpc": "2.0", "id": 99999, "method": "list_projects", "params": {}})
            list_resp, log_lines = read_response(proc, 99999, timeout=rpc_timeout)
            if "result" in list_resp:
                for proj in list_resp["result"].get("projects", []):
                    name_to_id[proj.get("name")] = proj.get("project_id")
            results.append({"request": {"method": "list_projects"}, "response": list_resp})
        except Exception as exc:
            print(f"Warning: list_projects prefetch failed ({exc})", file=sys.stderr)

        for spec in request_specs:
            req = spec.get("request", {})
            params = req.get("params", {})
            method = req.get("method")

            # Handle project_name -> project_id conversion
            if "project_name" in params:
                proj_name = params.pop("project_name")
                if proj_name in name_to_id:
                    project_id = name_to_id[proj_name]
                    params["project_id"] = project_id

                    # Update project hint if session exists
                    if session_id and method == "search_in_project":
                        try:
                            send_request(proc, {
                                "jsonrpc": "2.0",
                                "id": 99997,
                                "method": "update_project_hint",
                                "params": {
                                    "session_id": session_id,
                                    "project_hint": proj_name,
                                    "confidence": 0.9,
                                    "source": "replay_script"
                                }
                            })
                            hint_resp, hint_logs = read_response(proc, 99997, timeout=rpc_timeout)
                            print(f"Updated project hint: {proj_name} (confidence=0.9)", file=sys.stderr)
                        except Exception as exc:
                            print(f"Warning: update_project_hint failed ({exc})", file=sys.stderr)
                else:
                    print(f"Warning: project '{proj_name}' not found", file=sys.stderr)

            # Add session_id to search requests
            if session_id and method in ("search_memory", "search_in_project"):
                params["session_id"] = session_id

            send_request(proc, req)
            resp, logs = read_response(proc, req.get("id"), timeout=rpc_timeout)
            results.append({
                "request": req,
                "response": resp,
                "logs": logs,
                "relevance": spec.get("relevance")
            })
        reranker_metrics, metrics_entry = fetch_reranker_metrics(proc, rpc_timeout)
        if metrics_entry:
            results.append(metrics_entry)
    finally:
        proc.stdin.close()
        try:
            remaining = proc.stdout.read()
            if remaining:
                print(remaining)
        except Exception:
            pass
        proc.terminate()

    metrics = evaluate_metrics(results)
    if metrics:
        results.append({"metrics": metrics})
    if reranker_metrics is not None:
        results.append({"reranker_metrics": reranker_metrics})

    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = Path(output_dir) / f"mcp_run-{ts}.jsonl"
    with out_path.open("w", encoding="utf-8") as fp:
        for entry in results:
            fp.write(json.dumps(entry) + "\n")
    print(f"Saved run log to {out_path}")
    if metrics:
        print_metrics_summary(metrics)
    print_reranker_metrics(reranker_metrics)
    return out_path, metrics, results, reranker_metrics


def print_metrics_summary(metrics: dict) -> None:
    print("\nReplay Metrics Summary")
    print("=" * 26)
    for q in metrics.get("queries", []):
        print(
            f"Req {q['id']}: "
            f"P@{q['k']}={q['precision_at_k']:.2f}, "
            f"NDCG@{q['k']}={q['ndcg_at_k']:.2f}, "
            f"relevant={q['relevant_hits']}"
        )
    print("-" * 26)
    print(
        f"Macro Precision: {metrics.get('macro_precision', 0.0):.3f}, "
        f"Macro NDCG: {metrics.get('macro_ndcg', 0.0):.3f}"
    )


def print_reranker_metrics(snapshot: Optional[dict]) -> None:
    if snapshot is None:
        return

    print("\nReranker Metrics")
    print("=" * 20)
    if not snapshot.get("enabled"):
        print("Cross-encoder reranker disabled or unavailable.")
        return

    metrics = snapshot.get("metrics", {})
    print(f"Cache hit rate:       {metrics.get('cache_hit_rate', 0.0):.2f}")
    print(
        f"Cache size / entries: {metrics.get('cache_size', 0)} / {metrics.get('cache_entries', 0)}"
    )
    print(f"Pairs scored:         {metrics.get('pairs_scored', 0)}")
    prefetch_requests = metrics.get("prefetch_requests", 0)
    if prefetch_requests:
        print(
            f"Prefetch requests:    {prefetch_requests} "
            f"(hits {metrics.get('prefetch_cache_hits', 0)}, "
            f"misses {metrics.get('prefetch_cache_misses', 0)})"
        )
    print(
        f"LLM calls/failures:   {metrics.get('llm_calls', 0)} / {metrics.get('llm_failures', 0)}"
    )
    print(f"Avg LLM latency (ms): {metrics.get('avg_llm_latency_ms', 0.0):.1f}")
    print(f"Max LLM latency (ms): {metrics.get('max_llm_latency_ms', 0.0):.1f}")


FEATURE_EXPORT_COLUMNS = [
    "request_id",
    "method",
    "rank",
    "is_relevant",
    "score",
    "memory_id",
    "memory_strength",
    "recency",
    "refs_reliability",
    "bm25_score",
    "vector_similarity",
    "metadata_bonus",
]


def export_rerank_features(results: list[dict], export_path: Path) -> None:
    """
    Export reranker feature rows to a CSV file for offline weight training.
    """
    rows: list[dict] = []
    for entry in results:
        req = entry.get("request", {})
        relevance = entry.get("relevance")
        if not relevance or req.get("method") == "list_projects":
            continue

        resp = entry.get("response", {}) or {}
        top_results = resp.get("result", {}).get("results", [])
        if not top_results:
            continue

        for rank, item in enumerate(top_results, start=1):
            metadata = item.get("metadata", {}) or {}
            components = item.get("components", {}) or {}
            rows.append({
                "request_id": req.get("id"),
                "method": req.get("method"),
                "rank": rank,
                "is_relevant": 1 if is_relevant(metadata, relevance) else 0,
                "score": item.get("score", 0.0),
                "memory_id": metadata.get("memory_id") or item.get("id"),
                "memory_strength": components.get("memory_strength", 0.0),
                "recency": components.get("recency", 0.0),
                "refs_reliability": components.get("refs_reliability", 0.0),
                "bm25_score": components.get("bm25", components.get("bm25_score", 0.0)),
                "vector_similarity": components.get("vector", components.get("vector_similarity", 0.0)),
                "metadata_bonus": components.get("metadata", components.get("metadata_bonus", 0.0)),
            })

    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=FEATURE_EXPORT_COLUMNS)
        writer.writeheader()
        if rows:
            writer.writerows(rows)

    print(f"Exported {len(rows)} rerank feature rows to {export_path}")


def evaluate_metrics(results: list[dict]) -> Optional[dict]:
    query_metrics = []
    precisions: list[float] = []
    ndcgs: list[float] = []

    for entry in results:
        req = entry.get("request", {})
        relevance = entry.get("relevance")
        if not relevance or req.get("method") == "list_projects":
            continue

        resp = entry.get("response", {})
        top_results = resp.get("result", {}).get("results", [])
        params = req.get("params", {})
        k = params.get("top_k", len(top_results)) or len(top_results)

        precision, ndcg, hits = compute_metrics(top_results, relevance, k)
        query_metrics.append({
            "id": req.get("id"),
            "method": req.get("method"),
            "k": k,
            "precision_at_k": precision,
            "ndcg_at_k": ndcg,
            "relevant_hits": hits
        })
        precisions.append(precision)
        ndcgs.append(ndcg)

    if not query_metrics:
        return None

    return {
        "queries": query_metrics,
        "macro_precision": sum(precisions) / len(precisions) if precisions else 0.0,
        "macro_ndcg": sum(ndcgs) / len(ndcgs) if ndcgs else 0.0
    }


def compute_metrics(top_results: list[dict], relevance: dict, k: int) -> tuple[float, float, int]:
    if k <= 0:
        return 0.0, 0.0, 0

    limit = min(k, len(top_results))
    flags = []
    for idx in range(limit):
        metadata = top_results[idx].get("metadata", {})
        flags.append(1 if is_relevant(metadata, relevance) else 0)

    hits = sum(flags)
    precision = hits / limit if limit else 0.0

    dcg = sum(flag / math.log2(i + 2) for i, flag in enumerate(flags))
    ideal_hits = min(determine_ideal_hits(relevance), k)
    if ideal_hits <= 0:
        ndcg = 0.0
    else:
        idcg = sum(1 / math.log2(i + 2) for i in range(ideal_hits))
        ndcg = (dcg / idcg) if idcg else 0.0

    return precision, ndcg, hits


def determine_ideal_hits(relevance: dict) -> int:
    if not relevance:
        return 0
    if isinstance(relevance.get("ideal_hits"), int):
        return max(relevance["ideal_hits"], 0)

    total = 0
    for key, values in relevance.items():
        if key == "ideal_hits":
            continue
        if isinstance(values, list):
            total += len(values)
        else:
            total += 1
    return max(total, 1)


def is_relevant(metadata: dict, relevance: dict) -> bool:
    if not relevance:
        return False

    for key, values in relevance.items():
        if key == "ideal_hits":
            continue
        criterion_values = values if isinstance(values, list) else [values]
        criterion_values = [str(v).lower() for v in criterion_values]

        meta_value = metadata.get(key)
        if meta_value is None:
            continue

        if isinstance(meta_value, list):
            meta_values = [str(v).lower() for v in meta_value]
        else:
            meta_values = [str(meta_value).lower()]

        if any(val in meta_values for val in criterion_values):
            return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Replay MCP requests")
    parser.add_argument("--requests", required=True)
    parser.add_argument("--output", default="reports/mcp_runs")
    parser.add_argument("--baseline", help="Existing JSONL run to compare against", default=None)
    parser.add_argument(
        "--max-macro-precision-drop",
        type=float,
        default=0.02,
        help="Fail if macro precision drops more than this value"
    )
    parser.add_argument(
        "--max-macro-ndcg-drop",
        type=float,
        default=0.02,
        help="Fail if macro NDCG drops more than this value"
    )
    parser.add_argument(
        "--zero-hit-report",
        help="Write queries with zero relevant hits to this JSON file"
    )
    parser.add_argument(
        "--export-features",
        help="Write reranker feature rows to this CSV file"
    )
    parser.add_argument(
        "--rpc-timeout",
        type=int,
        default=25,
        help="Seconds to wait for each MCP response before failing"
    )
    args = parser.parse_args()

    specs = load_request_specs(Path(args.requests))
    out_path, metrics, results, reranker_metrics = replay(
        specs,
        args.output,
        rpc_timeout=args.rpc_timeout
    )

    if args.export_features:
        export_rerank_features(results, Path(args.export_features))

    exit_code = 0
    if args.baseline and metrics:
        baseline_metrics = load_metrics_from_run(Path(args.baseline))
        if baseline_metrics:
            regression, summary = detect_regression(
                baseline_metrics,
                metrics,
                args.max_macro_precision_drop,
                args.max_macro_ndcg_drop
            )
            print("\nBaseline comparison")
            print("=" * 26)
            print(
                f"Precision: baseline={summary['baseline_precision']:.3f} "
                f"current={summary['current_precision']:.3f} "
                f"Δ={summary['precision_drop']:.3f}"
            )
            print(
                f"NDCG:     baseline={summary['baseline_ndcg']:.3f} "
                f"current={summary['current_ndcg']:.3f} "
                f"Δ={summary['ndcg_drop']:.3f}"
            )
            if regression:
                print("Result: regression detected (exceeds allowed drop)")
                exit_code = 1
            else:
                print("Result: within allowed tolerances")
        else:
            print(f"Warning: baseline metrics not found in {args.baseline}", file=sys.stderr)

    if not metrics:
        print("Warning: no metrics computed; skipping regression checks", file=sys.stderr)
    elif args.zero_hit_report:
        write_zero_hit_report(
            results,
            metrics,
            Path(args.zero_hit_report)
        )

    sys.exit(exit_code)


def load_metrics_from_run(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    last_metrics = None
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "metrics" in entry:
                last_metrics = entry["metrics"]
    return last_metrics


def detect_regression(
    baseline: dict,
    current: dict,
    max_precision_drop: float,
    max_ndcg_drop: float
) -> Tuple[bool, dict]:
    baseline_precision = baseline.get("macro_precision", 0.0)
    baseline_ndcg = baseline.get("macro_ndcg", 0.0)
    current_precision = current.get("macro_precision", 0.0)
    current_ndcg = current.get("macro_ndcg", 0.0)

    precision_drop = baseline_precision - current_precision
    ndcg_drop = baseline_ndcg - current_ndcg

    regression = (
        precision_drop > max_precision_drop or
        ndcg_drop > max_ndcg_drop
    )

    summary = {
        "baseline_precision": baseline_precision,
        "baseline_ndcg": baseline_ndcg,
        "current_precision": current_precision,
        "current_ndcg": current_ndcg,
        "precision_drop": precision_drop,
        "ndcg_drop": ndcg_drop
    }
    return regression, summary


def extract_zero_hit_queries(results: list[dict], metrics: dict) -> list[dict]:
    zero_ids = {
        q.get("id")
        for q in metrics.get("queries", [])
        if q.get("relevant_hits", 0) == 0
    }
    if not zero_ids:
        return []

    zero_queries = []
    for entry in results:
        req = entry.get("request", {})
        req_id = req.get("id")
        if req_id not in zero_ids:
            continue
        params = req.get("params", {})
        zero_queries.append({
            "id": req_id,
            "method": req.get("method"),
            "query": params.get("query"),
            "params": params,
            "relevance": entry.get("relevance")
        })
    return zero_queries


def write_zero_hit_report(
    results: list[dict],
    metrics: dict,
    path: Path
) -> None:
    zero_hits = extract_zero_hit_queries(results, metrics)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "zero_hit_queries": zero_hits,
        "generated_at": datetime.now().isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if zero_hits:
        print(f"Zero-hit report written to {path} ({len(zero_hits)} queries)")
    else:
        print(f"Zero-hit report written to {path} (no zero-hit queries)")


if __name__ == "__main__":
    main()
