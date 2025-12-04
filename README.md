# Context Orchestrator

**Your personal AI memory layer** that captures everything you do with LLMs and terminal sessions, making it instantly searchable whenever you need it.

Context Orchestrator is a privacy-first MCP server that automatically records your CLI commands and LLM conversations (Claude, Codex, Cursor, VS Code), intelligently summarizes them with structured decision tracking, and makes your entire work history searchable through a powerful hybrid search engine—all running locally on your machine.

[日本語 README](README_JA.md) | [Quick Start](QUICKSTART.md) | [Setup Guide](SETUP_GUIDE.md)

---

## What you get

**🔍 Never lose context again**
- **Automatic session capture**: Your terminal commands and LLM conversations are captured in real-time without manual effort
- **Smart idle detection**: Sessions auto-close after 10 minutes of inactivity and get indexed automatically
- **Hierarchical summaries**: Long sessions (>3500 chars) are intelligently chunked and summarized with structured Decision/Rationale/Risks/NextSteps schema

**⚡ Powerful search at your fingertips**
- **Hybrid search engine**: Combines vector embeddings and BM25 keyword matching for the most relevant results
- **Session summaries included**: All your past work contexts are searchable by default—find that decision you made 3 weeks ago in seconds
- **Cross-encoder reranking**: LLM-powered reranking ensures the best results bubble to the top

**🏠 Privacy-first, runs locally**
- **100% local inference**: Embeddings and summarization powered by Ollama (nomic-embed-text + qwen2.5:7b)
- **No cloud dependencies**: Your data never leaves your machine unless you explicitly configure cloud LLM fallback
- **Optional Obsidian integration**: Automatically ingest and search your .md notes alongside session logs

## Prerequisites
- Python 3.11/3.12, Git 2.40+, PowerShell 7+ or Bash/zsh
- [Ollama](https://ollama.ai/) running; models: nomic-embed-text, qwen2.5:7b
- Optional: GPU ≥8GB VRAM for faster inference

## One-time Setup
1) Clone & create venv
```bash
git clone https://github.com/myo-ojin/context-orchestrator.git
cd context-orchestrator
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```
2) Generate config & check Ollama
```bash
python scripts/setup.py
```
3) Pull required models (if not already pulled)
```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
```
4) Enable automatic session logging (recommended)
```powershell
powershell -File scripts/setup_cli_recording.ps1
# Installs PowerShell wrapper + auto-starts log_bridge via start_log_bridge.ps1
```
If you skip step 4, start log_bridge manually when needed (see Daily Use).

## Daily Use
- Start MCP server
```bash
python -m src.main
```
- log_bridge
  - If wrapper installed: auto-starts when you open PowerShell.
  - Otherwise:
```bash
python scripts/log_bridge.py
```

## Key Settings (config.yaml)
- `router.mid_summary_max_tokens` (default 800): token budget for hierarchical summaries.
- `search.include_session_summaries` (default true): include is_session_summary results.

## Troubleshooting
- Ollama not responding → `ollama serve`
- No session logs → rerun `scripts/setup_cli_recording.ps1` or start `scripts/log_bridge.py`
- Summaries too short/long → adjust `router.mid_summary_max_tokens`

## Optional: Obsidian
If configured, .md notes in your vault are ingested and searchable; otherwise ignore.

---

For detailed flows and smoke tests, see [Quick Start](QUICKSTART.md) and [Setup Guide](SETUP_GUIDE.md).
