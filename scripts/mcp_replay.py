#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Replay a list of MCP JSON-RPC requests and record the responses."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


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


def replay(requests, output_dir):
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

        for req in requests:
            params = req.get("params", {})
            if "project_name" in params:
                proj_name = params.pop("project_name")
                if proj_name in name_to_id:
                    params["project_id"] = name_to_id[proj_name]
                else:
                    print(f"Warning: project '{proj_name}' not found", file=sys.stderr)
            send_request(proc, req)
            resp, logs = read_response(proc, req.get("id"))
            results.append({"request": req, "response": resp, "logs": logs})
    finally:
        proc.stdin.close()
        try:
            remaining = proc.stdout.read()
            if remaining:
                print(remaining)
        except Exception:
            pass
        proc.terminate()

    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = Path(output_dir) / f"mcp_run-{ts}.jsonl"
    with out_path.open("w", encoding="utf-8") as fp:
        for entry in results:
            fp.write(json.dumps(entry) + "\n")
    print(f"Saved run log to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Replay MCP requests")
    parser.add_argument("--requests", required=True)
    parser.add_argument("--output", default="reports/mcp_runs")
    args = parser.parse_args()

    with open(args.requests, "r", encoding="utf-8") as fp:
        requests = json.load(fp)

    replay(requests, args.output)


if __name__ == "__main__":
    main()
