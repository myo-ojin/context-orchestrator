# Context Orchestrator Quick Start (v0.1.0)

> Spin up the privacy-first external brain in minutes, validate the toolchain, and run your first MCP session.

This guide assumes a clean workstation and mirrors the steps we use internally before tagging a release. Refer back here whenever you need to bootstrap a new machine or verify that everything still works after dependency upgrades.

## 1. Prerequisites

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python    | 3.11.x or 3.12.x | 3.13+ is not yet validated; use `pyenv`, `asdf`, or the official installers. |
| Git       | 2.40+   | Required to clone the repository and pull future updates. |
| Ollama    | 0.3.x   | Provides the local embedding (`nomic-embed-text`) and inference (`qwen2.5:7b`) models. |
| CLI Shell | PowerShell 7+ or Bash/zsh | All commands below show both PowerShell and POSIX variants when they differ. |

Optional but recommended:
- **GPU** with 竕･8GB VRAM (speeds up Qwen2.5 inference)
- **Claude CLI / Cursor / VS Code MCP** client for live testing

## 2. Clone and bootstrap the repo

```bash
git clone https://github.com/myo-ojin/llm-brain.git
cd llm-brain
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

> Tip: if you maintain both dev and release environments, consider a second environment `.venv311` pinned to the exact Python revision used in CI (3.11.9).

## 3. Run the setup wizard

```bash
python scripts/setup.py
```

The wizard performs:
1. Ollama reachability check (`http://localhost:11434`)
2. Model presence verification and optional download
3. Creation of `~/.context-orchestrator/config.yaml`
4. Data-directory bootstrap (`~/.context-orchestrator/{logs,chroma_db}`)
5. Optional PowerShell wrapper installation for CLI capture

If you need to run in headless CI, copy `config.yaml.template` to the desired location and populate the fields manually.

## 4. Ensure Ollama models are available

```bash
ollama serve                # run in a separate terminal
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
ollama list                 # should show both models
```

Expected list snippet:

```
NAME                       ID              SIZE      MODIFIED
nomic-embed-text:latest    0a109f422b47    274 MB    now
qwen2.5:7b                 845dbda0ea48    4.7 GB    now
```

## 5. Smoke-test the install

1. **Doctor + status**
   ```bash
   python -m src.cli status
   python -m src.cli doctor
   ```
2. **Edge-case regression (48 tests)**
   ```bash
   pytest tests/unit/services/test_search_edge_cases.py -q
   ```
3. **Hybrid retrieval replay**
   ```bash
   python -m scripts.run_regression_ci --baseline reports/baselines/mcp_run-20251109-143546.jsonl
   ```
4. **Optional**: run the load/concurrency harness
   ```bash
   python -m scripts.load_test --num-queries 100
   python -m scripts.concurrent_test --concurrency 5 --rounds 10
   ```

Investigate any failures before moving on窶牌0.1.0 release criteria require 100% pass on these gates.

## 6. Start the MCP server

```bash
python -m src.main
```

Key log lines indicate successful initialization:

```
Initialized Chroma DB 窶ｦ/chroma_db
Initialized BM25 Index 窶ｦ/bm25_index.pkl
Connected to Ollama: http://localhost:11434
MCP Protocol Handler initialized
Ready to accept requests on stdin
```

Attach your preferred MCP client (Claude Desktop/CLI, Cursor, VS Code, etc.) and configure it to point to the stdio bridge.

## 7. Import or capture your first memories

Choose any of the following flows:

- **Manual ingest**: run `python -m src.cli import --input path/to/conversations.json`
- **Scenario replay**: `python -m scripts.mcp_replay --requests tests/scenarios/diverse_queries.json`
- **PowerShell capture**: install the shell wrapper via `scripts/setup_cli_recording.ps1 -Install` and start a Claude/Codex session

Verify retrieval with:

```bash
python -m src.cli list-recent --limit 5
python -m src.cli search --query "deploy checklist"
```

## 8. Where things live

| Artifact | Location |
|----------|----------|
| Config file | `~/.context-orchestrator/config.yaml` |
| Data directory | `~/.context-orchestrator/` (logs, Chroma DB, BM25 index) |
| Reports | `reports/` (baselines in `reports/baselines/`) |
| MCP run logs | `reports/mcp_runs/*.jsonl` |
| Release docs | `CHANGELOG.md`, `OSS_RELEASE_SUMMARY.md`, `OSS_FILE_CHECKLIST.md` |

## 9. Next steps

- Read the main [README](../README.md) for feature deep-dives.
- Need Japanese docs? See [README_JA](../README_JA.md).
- Enable CLI session capture now: `powershell -ExecutionPolicy Bypass -File scripts/setup_cli_recording.ps1 -Install`. The wrapper fires `start_session → add_command → end_session` for every `claude`/`codex` command, writes logs to `~/.context-orchestrator/logs`, and lets `python -m src.cli session-history --limit 5` surface those transcripts instantly.

  The setup wizard already runs this installer automatically; rerun it whenever you reset your PowerShell profile.
- Planning an OSS drop? Follow [OSS_RELEASE_SUMMARY.md](../OSS_RELEASE_SUMMARY.md) and the new packaging checklist.
- Keep `QUICKSTART.md` up to date whenever setup or dependency steps change窶排elease tagging requires it.

Happy orchestrating! 噫

