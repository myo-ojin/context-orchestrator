# Scenario Harness

This folder contains synthetic conversations and queued MCP requests so that you can stress-test search quality without waiting for real usage.

## Files

- `scenario_data.json`: conversations grouped by high-level projects (AppBrain, BugFixer, etc.)
- `query_runs.json`: sample MCP requests that exercise discovery (global search, project search, etc.)
  - ファイルには英語に加えて日本語・スペイン語のクエリが含まれており、言語ルーティングのフォールバックや reranker キャッシュ挙動を検証できます。

## Quick Start

1. **Load the scenarios into your local data directory**

```powershell
python -m scripts.load_scenarios --file tests/scenarios/scenario_data.json
```

This will create projects (if supported) and ingest each conversation through the normal pipeline.

2. **Run replayed MCP queries and capture the results**

```powershell
python -m scripts.mcp_replay --requests tests/scenarios/query_runs.json --output reports/mcp_runs
```

The script spawns the MCP stdio server, sends each request (search, project search, etc.), and stores the responses under `reports/mcp_runs/<timestamp>.jsonl` for inspection.

To detect regressions automatically, point the script at the curated baseline under `reports/baselines/` and emit a zero-hit report for QAM辞書の補強:

```powershell
python -m scripts.mcp_replay `
  --requests tests/scenarios/query_runs.json `
  --output reports/mcp_runs `
  --baseline reports/baselines/mcp_run-20251109-143546.jsonl `
  --zero-hit-report reports/mcp_runs/zero_hits.json `
  --max-macro-precision-drop 0.02 `
  --max-macro-ndcg-drop 0.02
```

Use these commands whenever you tweak ranking weights or ingestion logic so you get deterministic before/after comparisons.

## Structured Summary Requirements

All scenarios must emit summaries with this template:

`
Topic: <value>
DocType: <value>
Project: <value or Unknown>
KeyActions:
- <imperative action 1>
- <imperative action 2>
`

- KeyActions lines **must** begin with - . Paragraphs or numbered lists will fail validation.
- python -m scripts.load_scenarios validates this structure and stops immediately if a conversation generates an invalid summary. The error message includes the memory ID and a snippet of the offending summary.
- Fix the scenario or prompt, then rerun scripts.load_scenarios until the loader finishes cleanly.

## QAM Latency Bench

When tuning Query Attribute Modeling (QAM), you can measure LLMフォールバックの遅延と抽出結果:

```powershell
python -m scripts.bench_qam --query-file tests/scenarios/query_runs.json --json-output reports/bench_qam.json
```

This loads the configured ModelRouter (Ollama など) and prints latency/topic/doc/project per query so you can validate性能 before rolling out changes.
