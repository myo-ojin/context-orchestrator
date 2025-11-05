# Context Orchestrator (外部脳システム)

An external brain system that acts as an MCP (Model Context Protocol) server, enabling developers to capture, organize, and retrieve their work experiences across any LLM client.

## Features

- 🧠 **Automatic Memory Capture**: Transparently records CLI conversations (Claude, Codex)
- 📊 **Schema Classification**: Organizes memories into Incident, Snippet, Decision, Process
- 🔍 **Hybrid Search**: Vector (semantic) + BM25 (keyword) search with intelligent reranking
- 🏠 **Local-First Privacy**: Embeddings and classification run locally (Ollama)
- ⚡ **Smart Model Routing**: Light tasks → local LLM, heavy tasks → cloud LLM
- 💾 **Memory Hierarchy**: Working → Short-term → Long-term memory like human brain
- 🌙 **Auto Consolidation**: Nightly memory consolidation and forgetting

## Quick Start

### Prerequisites

- Python 3.11+
- Ollama (for local LLM)
- PowerShell (for Windows CLI integration)
- (Optional) chromadb `pip install chromadb` ? required if you want to run vector DB integration tests

### Installation

```bash
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python scripts/setup.py
```

### Download Required Models

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
```

## Usage

### Start MCP Server
```bash
# Start Context Orchestrator as MCP server
python -m src.main

# Or use console entry point (if installed)
context-orchestrator
```

### CLI Commands

```bash
# System status and health
python -m src.cli status      # Show comprehensive system status
python -m src.cli doctor      # Run diagnostics

# Memory management
python -m src.cli consolidate         # Manual memory consolidation
python -m src.cli list-recent --limit 20  # List recent memories
python -m src.cli export --output backup.json  # Export memories
python -m src.cli import --input backup.json   # Import memories

# Session history
python -m src.cli session-history  # List all sessions
python -m src.cli session-history --session-id <id>  # Show specific session
```

See [CLAUDE.md](CLAUDE.md) for detailed CLI documentation.

## Architecture

See [CLAUDE.md](CLAUDE.md) for detailed architecture and development guide.

## Documentation

- **Requirements**: `.kiro/specs/dev-knowledge-orchestrator/requirements.md`
- **Design**: `designtt.txt`
- **Tasks**: `.kiro/specs/dev-knowledge-orchestrator/tasks.md`
- **Developer Guide**: `CLAUDE.md`

## License

TBD

## Contributing

See [CLAUDE.md](CLAUDE.md) for coding guidelines and contribution process.
