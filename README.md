# Context Orchestrator (外部脳システム)

An external brain system that acts as an MCP (Model Context Protocol) server, enabling developers to capture, organize, and retrieve their work experiences across any LLM client.

## Features

### Core Capabilities

- 🧠 **Automatic Memory Capture**: Transparently records CLI conversations (Claude, Codex)
- 📊 **Schema Classification**: Organizes memories into Incident, Snippet, Decision, Process
- 🔍 **Hybrid Search**: Vector (semantic) + BM25 (keyword) search with intelligent reranking
- 🏠 **Local-First Privacy**: Embeddings and classification run locally (Ollama)
- ⚡ **Smart Model Routing**: Light tasks → local LLM, heavy tasks → cloud LLM
- 💾 **Memory Hierarchy**: Working → Short-term → Long-term memory like human brain
- 🌙 **Auto Consolidation**: Nightly memory consolidation and forgetting

### Integrations

- 📓 **Obsidian Integration**: Auto-detect and ingest conversation notes from Obsidian vault
  - Monitors `.md` files for conversation patterns
  - Extracts Wikilinks for relationship tracking
  - Parses YAML frontmatter (tags, metadata)
- 📝 **Session Logging**: Preserves full terminal transcripts with auto-summarization
- 🔌 **MCP Protocol**: Works with any MCP-compatible client (Claude CLI, Cursor, VS Code)

### Management Tools

- 📊 **System Status**: Comprehensive health monitoring with `status` command
- 🩺 **Diagnostics**: Automated troubleshooting with `doctor` command
- 💾 **Backup/Restore**: Export and import memories with `export`/`import` commands
- 📋 **Session History**: View and manage session logs and summaries

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

## Configuration

Create `~/.context-orchestrator/config.yaml`:

```yaml
# Data storage
data_dir: ~/.context-orchestrator

# Obsidian integration (optional)
obsidian_vault_path: C:\Users\username\Documents\ObsidianVault

# Ollama settings
ollama:
  url: http://localhost:11434
  embedding_model: nomic-embed-text
  inference_model: qwen2.5:7b

# CLI LLM for complex tasks
cli:
  command: claude  # or "codex"

# Search parameters
search:
  candidate_count: 50
  result_count: 10
  timeout_seconds: 2

# Memory management
clustering:
  similarity_threshold: 0.9
  min_cluster_size: 2

forgetting:
  age_threshold_days: 30
  importance_threshold: 0.3
  compression_enabled: true

working_memory:
  retention_hours: 8
  auto_consolidate: true

# Consolidation schedule (cron format)
consolidation:
  schedule: "0 3 * * *"  # 3:00 AM daily
  auto_enabled: true

# Session logging
logging:
  session_log_dir: ~/.context-orchestrator/logs
  max_log_size_mb: 10
  summary_model: qwen2.5:7b
  level: INFO
```

## Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Verify models are installed
ollama list
```

### PowerShell Wrapper Not Working

```powershell
# Check if wrapper is loaded
Get-Command claude

# Reload profile
. $PROFILE

# Re-run setup
python scripts/setup.py --repair
```

### Search Returns No Results

```bash
# Check if memories are indexed
python -m src.cli list-recent

# Verify database exists
ls ~/.context-orchestrator/chroma_db/

# Check logs
python -m src.cli status

# Run diagnostics
python -m src.cli doctor
```

### High Memory Usage

```bash
# Check consolidation status
python -m src.cli status

# Run manual consolidation
python -m src.cli consolidate

# Export and prune old memories
python -m src.cli export --output backup_$(date +%Y%m%d).json
```

## How It Works

1. **Capture**: PowerShell wrapper intercepts CLI commands and sends conversations to the orchestrator
2. **Classify**: Local LLM classifies memories into schemas (Incident/Snippet/Decision/Process)
3. **Chunk**: Content is split into 512-token chunks for efficient processing
4. **Index**: Chunks are indexed in both Vector DB (semantic) and BM25 (keyword)
5. **Search**: Hybrid search retrieves relevant memories and reranks by importance
6. **Consolidate**: Nightly job migrates working memory, clusters similar memories, and forgets old data

## Architecture

See [CLAUDE.md](CLAUDE.md) for detailed architecture and development guide.

## Performance Targets

- **Search Latency**: 80-200ms (typical: ~80ms)
- **Ingestion Time**: <5 seconds per conversation
- **Memory Footprint**: 1GB resident, 3GB peak (during inference)
- **Disk Usage**: ~10MB/year (~100MB/10 years)
- **Consolidation**: Complete in <5 minutes for 10K memories

## Documentation

- **Requirements**: `.kiro/specs/dev-knowledge-orchestrator/requirements.md` - Full project requirements
- **Design**: `designtt.txt` - Detailed architecture and interfaces
- **Tasks**: `.kiro/specs/dev-knowledge-orchestrator/tasks.md` - Implementation roadmap
- **Developer Guide**: `CLAUDE.md` - Development and contribution guidelines
- **Integration Tests**: `INTEGRATION_TEST_RESULTS.md` - Test results and validation

## Project Status

- ✅ **Phase 1-10**: Core system (MCP server, storage, processing, services) - **COMPLETE**
- ✅ **Phase 11**: Obsidian Integration - **COMPLETE**
- ✅ **Phase 12**: CLI Interface - **COMPLETE**
- ✅ **Phase 13**: Testing and Documentation - **COMPLETE**
- ⏳ **Phase 14**: Integration & Optimization - PLANNED

**Current Status**: MVP Ready for Production Testing

## License

TBD

## Contributing

We welcome contributions! Please see:
- [CLAUDE.md](CLAUDE.md) for coding guidelines and development setup
- [CONTRIBUTING.md](CONTRIBUTING.md) for contribution process (coming soon)

### Development Setup

```bash
# Clone repository
git clone https://github.com/myo-ojin/llm-brain.git
cd llm-brain

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-cov black ruff mypy

# Run tests
pytest

# Format code
black .

# Lint
ruff .
```

## Support

- **Issues**: [GitHub Issues](https://github.com/myo-ojin/llm-brain/issues)
- **Documentation**: [CLAUDE.md](CLAUDE.md)
- **Test Results**: [INTEGRATION_TEST_RESULTS.md](INTEGRATION_TEST_RESULTS.md)
