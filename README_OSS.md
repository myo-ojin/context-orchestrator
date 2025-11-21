# Context Orchestrator

> Your External Brain for Development Knowledge

**Context Orchestrator** is a privacy-first, AI-powered memory system that automatically captures, organizes, and recalls your development experiences across any LLM client.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-48%2F48%20passing-success)](tests/)

## Why Context Orchestrator?

As developers, we constantly learn, troubleshoot, and make decisions. But this knowledge gets lost in:
- Closed terminal sessions
- Forgotten conversations with AI assistants
- Scattered notes and documentation
- Limited LLM context windows

**Context Orchestrator solves this** by acting as your external brain:

✅ **Automatic Memory**: Records your CLI conversations transparently
✅ **Intelligent Organization**: Classifies experiences into searchable schemas
✅ **Privacy-First**: All processing happens locally on your machine
✅ **Universal Integration**: Works with Claude CLI, Cursor, VS Code, any MCP client
✅ **Smart Search**: Hybrid vector + keyword search finds exactly what you need
✅ **Production-Ready**: Comprehensive test suite (48 edge cases, 100% passing)

## Features

### 🧠 Automatic Memory Capture
- Transparently records CLI conversations (Claude, Codex)
- Extracts conversations from Obsidian vault notes
- No manual note-taking required

### 📊 Smart Organization
Classifies memories into domain-specific schemas:
- **Incident**: Bug reports, errors, troubleshooting steps
- **Snippet**: Code examples with usage context
- **Decision**: Architectural choices and trade-offs
- **Process**: Thought processes, learning, experimentation

### 🔍 Powerful Search
- **Hybrid Search**: Vector (semantic) + BM25 (keyword) search
- **Cross-Encoder Reranking**: LLM-based relevance scoring
- **Query Attributes**: Automatic topic/type/project extraction
- **Project Scoping**: Search within specific codebases
- **Search Bookmarks**: Save frequently used queries

### 🏠 Privacy-First Architecture
- **Local LLM Processing**: Embeddings and classification run locally (Ollama)
- **Smart Model Routing**: Light tasks → local, heavy tasks → cloud (your choice)
- **No Telemetry**: All data stays on your machine
- **Export/Import**: Full control over your data

### 💾 Memory Hierarchy
Mimics human memory patterns:
- **Working Memory**: Current task context (8 hours)
- **Short-Term Memory**: Recent experiences (days/weeks)
- **Long-Term Memory**: Important knowledge (permanent)
- **Auto-Consolidation**: Nightly memory optimization and cleanup

### 🔌 Universal Integration
Works with any MCP (Model Context Protocol) compatible client:
- Claude CLI
- Cursor IDE
- VS Code extensions
- Custom MCP clients

### 🧪 Production-Ready Quality
- **48 Edge Case Tests**: Special characters, emoji, extreme inputs (100% passing)
- **Load Testing**: Memory leak detection, concurrent query validation
- **Performance Targets**: <200ms search, <5s ingestion, <5min consolidation
- **Quality Metrics**: Precision ≥0.65, NDCG ≥0.85
- **Regression Testing**: Automated baseline comparison

## Quick Start

### Prerequisites

- **Python 3.11-3.12** (Python 3.11 recommended, 3.13+ not yet tested)
- **Ollama** (for local LLM processing)
- **PowerShell** (for Windows CLI integration) or **Bash** (for Unix/Linux/Mac)

### Installation

```bash
# Clone repository
git clone https://github.com/myo-ojin/llm-brain.git
cd llm-brain

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
.venv\Scripts\activate.bat
# Unix/Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python scripts/setup.py
```

**Note for Windows PowerShell users:**
If you get an execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**What the setup wizard does:**
- Checks Ollama installation and connectivity
- Verifies required models are downloaded
- Creates configuration file (`~/.context-orchestrator/config.yaml`)
- Creates data directory
- Tests basic functionality

### Download Required Models

Context Orchestrator uses Ollama for local LLM processing:

```bash
# Install Ollama from https://ollama.ai/

# Start Ollama (if not already running)
ollama serve  # Run in a separate terminal

# Download required models
ollama pull nomic-embed-text    # Embedding model (274MB, ~1 minute)
ollama pull qwen2.5:7b          # Local inference model (4.7GB, ~5-10 minutes)

# Verify installation
ollama list
```

**Expected output:**
```
NAME                       ID              SIZE      MODIFIED
nomic-embed-text:latest    0a109f422b47    274 MB    now
qwen2.5:7b                 845dbda0ea48    4.7 GB    now
```

### Configuration

The setup wizard creates `~/.context-orchestrator/config.yaml`:

```yaml
# Data storage
data_dir: ~/.context-orchestrator

# Ollama settings
ollama:
  url: http://localhost:11434
  embedding_model: nomic-embed-text
  inference_model: qwen2.5:7b

# CLI LLM for complex tasks (optional)
cli:
  command: claude  # or "codex", or leave empty for local-only

# Search parameters
search:
  candidate_count: 50
  result_count: 10
  cross_encoder_enabled: true
  cross_encoder_top_k: 3

# Memory management
working_memory:
  retention_hours: 8
  auto_consolidate: true

# Consolidation schedule (3:00 AM daily)
consolidation:
  schedule: "0 3 * * *"
  auto_enabled: true

# Obsidian integration (optional)
obsidian_vault_path: C:\Users\username\Documents\ObsidianVault
```

### Start the MCP Server

```bash
# Start Context Orchestrator as MCP server
python -m src.main

# Or use console entry point (if installed)
context-orchestrator
```

The server runs in stdio mode and communicates via JSON-RPC with MCP clients.

### CLI Commands

```bash
# System status
python -m src.cli status

# Health check and diagnostics
python -m src.cli doctor

# List recent memories
python -m src.cli list-recent --limit 20

# Manual memory consolidation
python -m src.cli consolidate

# Session history
python -m src.cli session-history
python -m src.cli session-history --session-id <id>

# Export/import memories
python -m src.cli export --output backup.json
python -m src.cli import --input backup.json
```

## How It Works

### 1. Capture
PowerShell/Bash wrapper intercepts CLI commands and sends conversations to Context Orchestrator via MCP protocol.

### 2. Process
- **Classify**: Local LLM classifies memories into schemas (Incident/Snippet/Decision/Process)
- **Chunk**: Content split into 512-token chunks for efficient processing
- **Embed**: Generate vector embeddings locally (nomic-embed-text)
- **Index**: Store in both Vector DB (semantic search) and BM25 (keyword search)

### 3. Search
When you query:
1. Generate query embedding locally
2. Parallel search: Vector DB + BM25 → top candidates
3. Extract query attributes (topic, type, project)
4. Rerank with cross-encoder LLM scoring
5. Return top results with references and metadata

### 4. Consolidate
Nightly automatic consolidation:
- Migrate working memory to short-term
- Cluster similar memories
- Forget old/unimportant memories
- Maintain memory hierarchy

## Performance

Context Orchestrator is optimized for personal use:

| Metric | Target | Typical |
|--------|--------|---------|
| Search Latency | ≤200ms | ~80ms |
| Ingestion Time | ≤5s/conversation | ~2-3s |
| Memory Footprint | ≤3GB peak | ~1GB resident |
| Disk Usage | ~10MB/year | Compressed |
| Consolidation | <5min/10K memories | ~2-3min |

Run benchmarks:
```bash
python scripts/performance_profiler.py
```

## Testing

Context Orchestrator includes comprehensive test coverage:

```bash
# Run all tests
pytest

# Run unit tests (48 edge cases)
pytest tests/unit/

# Run end-to-end tests
pytest tests/e2e/

# Run regression tests
python -m scripts.run_regression_ci

# Load testing
python -m scripts.load_test --num-queries 100
python -m scripts.concurrent_test --concurrency 5
```

**Test Coverage:**
- ✅ 48 edge case tests (special characters, emoji, extreme inputs)
- ✅ Load testing (memory leak detection)
- ✅ Concurrent testing (thread safety validation)
- ✅ Quality metrics (Precision/Recall/F1)
- ✅ Query pattern coverage (50 diverse queries)

## Architecture

```
┌─────────────────────────────────────────┐
│   MCP Clients (CLI/Cursor/VS Code)      │
└──────────────┬──────────────────────────┘
               │ stdio (JSON-RPC)
               ↓
┌─────────────────────────────────────────┐
│   Context Orchestrator (MCP Server)     │
│  ┌─────────────────────────────────┐   │
│  │ Services: Ingestion, Search,     │   │
│  │ Consolidation, Session Mgmt      │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ Model Router (Local ↔ Cloud)    │   │
│  └─────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   Storage Layer                         │
│  • Chroma DB (vector search)            │
│  • BM25 Index (keyword search)          │
│  • Session Logs                         │
└─────────────────────────────────────────┘
```

For detailed architecture and development guide, see [CLAUDE.md](CLAUDE.md).

## Use Cases

### 1. Bug Troubleshooting
"Remember that authentication error I fixed last month?"
→ Instantly retrieves the incident, root cause, and fix

### 2. Code Reuse
"Show me examples of retry logic in Python"
→ Finds code snippets you've used before with context

### 3. Decision Review
"Why did we choose PostgreSQL over MongoDB?"
→ Recalls architectural decisions with trade-offs

### 4. Learning Reinforcement
"What did I learn about async/await in Python?"
→ Surfaces your thought processes and experiments

### 5. Project Onboarding
"What are the main issues in the payment-service project?"
→ Project-scoped search for relevant memories

## Configuration

### Model Routing Strategy

Context Orchestrator intelligently routes tasks based on complexity:

| Task | Model | Rationale |
|------|-------|-----------|
| Embeddings | Local (nomic-embed-text) | Always needed, privacy-critical |
| Classification | Local (Qwen2.5) | Simple, privacy-critical |
| Short summaries | Local (Qwen2.5) | Sufficient quality |
| Long summaries | CLI (Claude/GPT) | High quality needed |
| Complex reasoning | CLI (Claude/GPT) | Advanced capabilities |

You can configure this in `config.yaml`:

```yaml
cli:
  command: claude  # or "codex", or empty for local-only

# Set to empty for 100% local processing:
cli:
  command: ""
```

### Obsidian Integration

If you use Obsidian for note-taking:

```yaml
obsidian_vault_path: C:\Users\username\Documents\ObsidianVault
```

Context Orchestrator will:
- Monitor `.md` files for conversation patterns
- Extract `**User:**` / `**Assistant:**` conversations
- Parse Wikilinks (`[[filename]]`) for relationships
- Parse YAML frontmatter (tags, metadata)

### Search Tuning

Adjust search behavior:

```yaml
search:
  vector_candidate_count: 100      # Vector search candidates
  bm25_candidate_count: 30         # BM25 search candidates
  result_count: 10                 # Final results returned
  cross_encoder_enabled: true      # Enable LLM reranking
  cross_encoder_top_k: 3           # How many to rerank with LLM
  cross_encoder_cache_size: 128    # Cache size for LLM scores
  cross_encoder_cache_ttl_seconds: 900  # Cache TTL
```

### Memory Management

Configure forgetting and consolidation:

```yaml
forgetting:
  age_threshold_days: 30           # Forget after 30 days
  importance_threshold: 0.3        # Keep if importance > 0.3
  compression_enabled: true        # Compress before forgetting

clustering:
  similarity_threshold: 0.9        # Cluster if similarity ≥ 0.9
  min_cluster_size: 2              # Minimum cluster size

consolidation:
  schedule: "0 3 * * *"            # Cron schedule (3:00 AM daily)
  auto_enabled: true               # Auto-consolidation enabled
```

## Troubleshooting

### Setup Wizard Fails

**Problem**: Setup wizard cannot connect to Ollama

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
# or on Windows:
Invoke-WebRequest http://localhost:11434/api/tags

# If not responding, start Ollama in a separate terminal
ollama serve

# Verify models are installed
ollama list
```

**Problem**: Port 11434 is already in use

Edit `config.yaml.template` before running setup:
```yaml
ollama:
  url: http://localhost:11435  # Use different port
```

### Python Version Issues

**Problem**: "Python 3.11+ required" error

```bash
# Check Python version
python --version

# Must be Python 3.11 or 3.12 (3.13+ not yet tested)
# Install Python 3.11:
# - Windows: https://www.python.org/downloads/
# - Ubuntu: sudo apt install python3.11
# - Mac: brew install python@3.11
```

### PowerShell Execution Policy Error (Windows)

**Problem**: "cannot be loaded because running scripts is disabled"

```powershell
# Solution 1: Change execution policy (recommended)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Solution 2: Bypass temporarily
powershell -ExecutionPolicy Bypass -File .venv\Scripts\Activate.ps1
```

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Verify models are installed
ollama list

# Test model directly
ollama run nomic-embed-text "test"
```

### Search Returns No Results

```bash
# Check if memories are indexed
python -m src.cli list-recent

# Verify database exists
ls ~/.context-orchestrator/chroma_db/
# Windows: dir %USERPROFILE%\.context-orchestrator\chroma_db

# Run diagnostics
python -m src.cli doctor

# Check logs
tail -f ~/.context-orchestrator/logs/context_orchestrator.log
# Windows: Get-Content -Wait ~/.context-orchestrator/logs/context_orchestrator.log -Tail 50
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

### PowerShell Wrapper Not Working (Windows)

```powershell
# Check if wrapper is loaded
Get-Command claude

# Reload profile
. $PROFILE

# Re-run setup
python scripts/setup.py --repair
```

### Import Errors or Missing Dependencies

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# If specific package fails, install individually
pip install chromadb tiktoken rank-bm25 pyyaml requests watchdog apscheduler

# Check installed packages
pip list
```

## Privacy & Security

### Data Protection
- **All data stored locally** in `~/.context-orchestrator/`
- **OS-level access control** (file permissions)
- **No telemetry or external tracking**
- **Export/import** for manual backups

### Privacy-Sensitive Processing
- **Embeddings**: Always local (nomic-embed-text)
- **Classification**: Always local (Qwen2.5)
- **Search**: Always local (no cloud API calls)
- **Summaries**: Local for short, cloud for long (configurable)

### Cloud LLM Usage (Optional)
- **Minimal context**: Only necessary content sent
- **User consent**: Setup wizard asks for preferences
- **Fallback**: Degrades to local LLM if cloud unavailable
- **No recording**: Internal calls skip memory capture

## Roadmap

### v0.1.0 (Current Release)
✅ Core memory capture and retrieval
✅ Hybrid search (vector + BM25)
✅ Cross-encoder reranking
✅ Query attribute extraction
✅ Project management
✅ Search bookmarks
✅ Comprehensive test suite

### v0.2.0 (Planned)
🔄 Project initialization (`/init` command)
🔄 Codebase scanning and indexing
🔄 File-level memory associations
🔄 Enhanced Obsidian integration

### Future Considerations
💡 Web UI for memory exploration
💡 Team collaboration features
💡 Custom schema definitions
💡 Plugin system for extensibility

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code style requirements
- Testing requirements
- Pull request process

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- **Ollama** for local LLM runtime
- **Chroma** for vector database
- **Model Context Protocol (MCP)** for standardized integration
- **All contributors** who make this project possible

## Support

- **Issues**: [GitHub Issues](https://github.com/myo-ojin/llm-brain/issues)
- **Documentation**: [CLAUDE.md](CLAUDE.md) (Developer Guide)
- **Discussions**: [GitHub Discussions](https://github.com/myo-ojin/llm-brain/discussions)

## Citation

If you use Context Orchestrator in your research or project, please cite:

```bibtex
@software{context_orchestrator,
  title = {Context Orchestrator: External Brain System for Developers},
  author = {Context Orchestrator Contributors},
  year = {2025},
  url = {https://github.com/myo-ojin/llm-brain}
}
```

---

**Built with ❤️ for developers who value privacy and knowledge continuity**
