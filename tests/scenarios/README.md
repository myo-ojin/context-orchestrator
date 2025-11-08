# Scenario Harness

This folder contains synthetic conversations and queued MCP requests so that you can stress-test search quality without waiting for real usage.

## Files

- `scenario_data.json`: conversations grouped by high-level projects (AppBrain, BugFixer, etc.)
- `query_runs.json`: sample MCP requests that exercise discovery (global search, project search, etc.)

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

Use these commands whenever you tweak ranking weights or ingestion logic—you get deterministic scenarios to compare before/after changes.
