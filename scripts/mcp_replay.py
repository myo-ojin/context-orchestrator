#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Replay a list of MCP JSON-RPC requests and record the responses."""

import argparse
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


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
    )
    return proc


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


def replay(request_specs, output_dir):
    proc = start_mcp_server()
    results = []
    try:
        # Prefetch projects for name -> id mapping
        send_request(proc, {"jsonrpc": "2.0", "id": 99999, "method": "list_projects", "params": {}})
        list_resp, log_lines = read_response(proc, 99999)
        name_to_id = {}
        if "result" in list_resp:
            for proj in list_resp["result"].get("projects", []):
                name_to_id[proj.get("name")] = proj.get("project_id")
        results.append({"request": {"method": "list_projects"}, "response": list_resp})

        for spec in request_specs:
            req = spec.get("request", {})
            params = req.get("params", {})
            if "project_name" in params:
                proj_name = params.pop("project_name")
                if proj_name in name_to_id:
                    params["project_id"] = name_to_id[proj_name]
                else:
                    print(f"Warning: project '{proj_name}' not found", file=sys.stderr)
            send_request(proc, req)
            resp, logs = read_response(proc, req.get("id"))
            results.append({
                "request": req,
                "response": resp,
                "logs": logs,
                "relevance": spec.get("relevance")
            })
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

    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = Path(output_dir) / f"mcp_run-{ts}.jsonl"
    with out_path.open("w", encoding="utf-8") as fp:
        for entry in results:
            fp.write(json.dumps(entry) + "\n")
    print(f"Saved run log to {out_path}")
    if metrics:
        print_metrics_summary(metrics)


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
    args = parser.parse_args()

    specs = load_request_specs(Path(args.requests))
    replay(specs, args.output)


if __name__ == "__main__":
    main()
