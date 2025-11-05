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

```bash
# Start Context Orchestrator (MCP server)
python -m src.main

# Check system status
python -m src.cli status

# Run diagnostics
python -m src.cli doctor

# Manual consolidation
python -m src.cli consolidate
```

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
