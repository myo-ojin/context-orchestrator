# Context Orchestrator

Privacy-first MCP server that captures and searches your CLI/LLM work across clients (Claude, Codex, Cursor, VS Code).

[日本語 README](README_JA.md) | [Quick Start](QUICKSTART.md) | [Setup Guide](SETUP_GUIDE.md)

---

## Quick Path (TL;DR)
1) One-time
`
python scripts/setup.py                 # generate config, check Ollama
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
powershell -File scripts/setup_cli_recording.ps1   # optional but recommended: auto session logging + log_bridge autostart
`
2) Daily
`
python -m src.main          # start MCP server
# if you didn't install the wrapper:
python scripts/log_bridge.py # manual log bridge
`

## What’s Included
- Automatic CLI session capture (Codex/Claude logs) with idle auto-close
- Hierarchical session summaries (Decision/Risks/NextSteps, default 800 tokens via outer.mid_summary_max_tokens)
- Hybrid search (vector + BM25) with session summaries included by default
- Optional Obsidian watcher to ingest .md notes

## Prerequisites
- Python 3.11/3.12, Git 2.40+, PowerShell 7+ or Bash/zsh
- [Ollama](https://ollama.ai/) running; models: 
omic-embed-text, qwen2.5:7b
- Optional: GPU ≥8GB VRAM for faster inference

## One-Time Setup
`
git clone https://github.com/myo-ojin/context-orchestrator.git
cd context-orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # or source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup.py
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
powershell -File scripts/setup_cli_recording.ps1  # enables auto session logging & log_bridge autostart
`

## Run
`
python -m src.main          # MCP server
# log_bridge: auto if wrapper installed, otherwise run:
python scripts/log_bridge.py
`

## Key Settings
- outer.mid_summary_max_tokens (default 800): summary token budget for hierarchical summaries
- search.include_session_summaries (default true): include is_session_summary results

## Troubleshooting
- Ollama not responding → ollama serve
- No session logs → rerun scripts/setup_cli_recording.ps1 or start scripts/log_bridge.py
- Summaries too short/long → adjust outer.mid_summary_max_tokens in config.yaml

## Optional: Obsidian
If configured, .md notes in your vault are ingested and searchable; otherwise ignore.

---

For detailed flows and smoke tests, see [Quick Start](QUICKSTART.md) and [Setup Guide](SETUP_GUIDE.md).
