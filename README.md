# Context Orchestrator

Privacy-first MCP server that captures and searches your CLI/LLM work across clients (Claude, Codex, Cursor, VS Code).

[日本語 README](README_JA.md) | [Quick Start](QUICKSTART.md) | [Setup Guide](SETUP_GUIDE.md)

---

## What you get
- Automatic CLI session capture (Codex/Claude logs), idle auto-close, hierarchical summaries (Decisions/Risks/NextSteps).
- Hybrid search (vector + BM25) with session summaries included by default.
- Optional Obsidian watcher to ingest .md notes.
- Local-first: embeddings + inference via Ollama (
omic-embed-text, qwen2.5:7b).

## Prerequisites
- Python 3.11/3.12, Git 2.40+, PowerShell 7+ or Bash/zsh
- [Ollama](https://ollama.ai/) running; models: 
omic-embed-text, qwen2.5:7b
- Optional: GPU ≥8GB VRAM for faster inference

## One-time Setup
1) Clone & create venv
`ash
git clone https://github.com/myo-ojin/context-orchestrator.git
cd context-orchestrator
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
`
2) Generate config & check Ollama
`ash
python scripts/setup.py
`
3) Pull required models (if not already pulled)
`ash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
`
4) Enable automatic session logging (recommended)
`powershell
powershell -File scripts/setup_cli_recording.ps1
# Installs PowerShell wrapper + auto-starts log_bridge via start_log_bridge.ps1
`
If you skip step 4, start log_bridge manually when needed (see Daily Use).

## Daily Use
- Start MCP server
`ash
python -m src.main
`
- log_bridge
  - If wrapper installed: auto-starts when you open PowerShell.
  - Otherwise:
`ash
python scripts/log_bridge.py
`

## Key Settings (config.yaml)
- outer.mid_summary_max_tokens (default 800): token budget for hierarchical summaries.
- search.include_session_summaries (default true): include is_session_summary results.

## Troubleshooting
- Ollama not responding → ollama serve
- No session logs → rerun scripts/setup_cli_recording.ps1 or start scripts/log_bridge.py
- Summaries too short/long → adjust outer.mid_summary_max_tokens

## Optional: Obsidian
If configured, .md notes in your vault are ingested and searchable; otherwise ignore.

---

For detailed flows and smoke tests, see [Quick Start](QUICKSTART.md) and [Setup Guide](SETUP_GUIDE.md).
