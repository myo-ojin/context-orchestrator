# Context Orchestrator
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.11--3.12-blue.svg)](https://www.python.org) [![Tests](https://img.shields.io/badge/tests-48%2F48%20passing-success)](tests/)

**Your personal AI memory layer** that captures everything you do with LLMs and terminal sessions, making it instantly searchable whenever you need it.

Context Orchestrator is a privacy-first MCP server that automatically records your CLI commands and LLM conversations (Claude, Codex, Cursor, VS Code), intelligently summarizes them with structured decision tracking, and makes your entire work history searchable through a powerful hybrid search engine—all running locally on your machine.

[TL;DR Quick Start (~60s)]
```bash
git clone https://github.com/myo-ojin/context-orchestrator.git
cd context-orchestrator
python -m venv .venv && .\.venv\Scripts\Activate.ps1  # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt && python scripts/setup.py
python -m src.main  # start the MCP server; PowerShell users can run scripts/setup_cli_recording.ps1 to auto-log sessions
```

[日本誁EREADME](README_JA.md) | [Quick Start](QUICKSTART.md) | [Setup Guide](SETUP_GUIDE.md)

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
  - **First run**: You'll be prompted to index existing session logs. This is a one-time operation to make your past sessions searchable. You can skip it—new sessions will be indexed automatically.
- log_bridge
  - If wrapper installed: auto-starts when you open PowerShell.
  - Otherwise:
```bash
python scripts/log_bridge.py
```

## Connect an MCP client
- **Claude Desktop/Web**: Settings → Model Context Protocol → Add server. Command: `python -m src.main` (or `C:\Users\ryomy\context-orchestrator\.venv\Scripts\python.exe -m src.main` if using venv). Working directory: project root (`context-orchestrator`).
- **mcp-shell (CLI)**: Run `mcp-shell "python -m src.main"` from the project root, then issue `search <query>` inside the shell.
- **VS Code / Cursor MCP extensions**: Add server with the same command and set the working directory to the repo root. After enabling, trigger search from the extension UI/command palette.

## Key Settings (config.yaml)
- `router.mid_summary_max_tokens` (default 800): token budget for hierarchical summaries.
- `search.include_session_summaries` (default true): include is_session_summary results.
- `logging.first_run_index_enabled` (default true): enable first-run indexing prompt on startup.
- `logging.first_run_index_max_file_mb` (default 100): maximum log file size to index (MB).
- `logging.first_run_index_allowed_extensions` (default ['.jsonl', '.log', '.txt']): file extensions to index.

## FAQ
Q. Ollama is not responding  
A. Start the service with `ollama serve`, then check models with `ollama list`. Pull missing models: `ollama pull nomic-embed-text` and `ollama pull qwen2.5:7b`.

Q. No session logs are showing up  
A. On PowerShell run `powershell -File scripts/setup_cli_recording.ps1` once. If you skip it, start `python scripts/log_bridge.py` manually before you begin working.

Q. Search feels slow  
A. Set `search.cross_encoder_enabled=false` to disable reranking, or lower `candidate_count` / `vector_candidate_count` in `config.yaml`.

Q. I want GPU acceleration
A. Ollama uses GPU when available. 8GB+ VRAM is recommended; verify with `nvidia-smi`.

Q. How do I skip or re-run first-run indexing?
A. To skip: answer 'N' at the prompt or disable via `logging.first_run_index_enabled=false` in config.yaml. To re-run: delete `~/.context-orchestrator/first_run_index_done` and restart. For non-interactive environments (CI/Docker), set `CO_FIRST_RUN_AUTO=1` to auto-approve.

## Troubleshooting
- Ollama not responding ↁE`ollama serve`
- No session logs ↁErerun `scripts/setup_cli_recording.ps1` or start `scripts/log_bridge.py`
- Summaries too short/long ↁEadjust `router.mid_summary_max_tokens`

## Optional: Obsidian
If configured, .md notes in your vault are ingested and searchable; otherwise ignore.

---

For detailed flows and smoke tests, see [Quick Start](QUICKSTART.md) and [Setup Guide](SETUP_GUIDE.md).
