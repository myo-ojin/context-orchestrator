# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Context Orchestrator** is an external brain system (外部脳システム) that acts as an MCP (Model Context Protocol) server, enabling developers to capture, organize, and retrieve their work experiences across any LLM client (Claude CLI, Codex CLI, Cursor, VS Code extensions, etc.).

### Core Philosophy
- Automatically records conversations and experiences
- Structures memories using domain-specific schemas (Incident, Snippet, Decision, Process)
- Provides hybrid search (vector + BM25) for intelligent recall
- Uses local LLMs for privacy-sensitive tasks, cloud LLMs for complex reasoning
- Implements human brain-like memory hierarchy (working → short-term → long-term)

## Important: Project Specification Directory

**ALWAYS reference the `.kiro` directory for project specifications:**
- Location: `.kiro` (in project root directory)
- This directory contains the canonical project requirements, design documents, and implementation roadmap
- Before making significant changes, consult:
  - `.kiro/specs/dev-knowledge-orchestrator/requirements.md` - Full requirements specification
  - `.kiro/specs/dev-knowledge-orchestrator/design.md` - Detailed architecture and component interfaces
  - `.kiro/specs/dev-knowledge-orchestrator/tasks.md` - Implementation task breakdown

**Key principle:** The `.kiro` directory is the source of truth for project specifications. Always check these documents when:
- Planning new features
- Understanding design rationale
- Clarifying requirements
- Breaking down implementation tasks

## Development Setup

### Prerequisites
- **Python 3.11+** (required)
- **Ollama** (local LLM runtime)
- **PowerShell** (for Windows CLI integration)

### Initial Setup
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python scripts/setup.py
```

### Required Models
Download these Ollama models:
```bash
ollama pull nomic-embed-text  # Embedding generation
ollama pull qwen2.5:7b        # Local inference
```

## Architecture

### High-Level System Design

```
┌─────────────────────────────────────────┐
│   MCP Clients (CLI/Cursor/VS Code)      │
└──────────────┬──────────────────────────┘
               │ stdio (JSON-RPC)
               ↓
┌─────────────────────────────────────────┐
│   Context Orchestrator (MCP Server)     │
│  ┌─────────────────────────────────┐   │
│  │ MCP Protocol Handler            │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ Core Services                    │   │
│  │  • IngestionService              │   │
│  │  • SearchService                 │   │
│  │  • ConsolidationService          │   │
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

### Directory Structure

```
src/
├── main.py                    # Entry point
├── config.py                  # Configuration management
├── mcp/
│   └── protocol_handler.py    # MCP JSON-RPC handler
├── services/
│   ├── ingestion.py           # Conversation ingestion pipeline
│   ├── search.py              # Hybrid search (vector + BM25)
│   ├── consolidation.py       # Memory consolidation & forgetting
│   ├── session_manager.py     # Working memory sessions
│   ├── session_log_collector.py    # Session logging
│   ├── session_summary.py     # Session summarization worker
│   ├── obsidian_watcher.py    # File system monitoring
│   ├── obsidian_parser.py     # Conversation extraction
│   ├── query_attributes.py    # Query attribute extraction (QAM)
│   ├── rerankers.py           # Cross-encoder reranking
│   ├── project_manager.py     # Project CRUD operations
│   └── bookmark_manager.py    # Search bookmark management
├── models/
│   ├── router.py              # Task → Model routing
│   ├── local_llm.py           # Ollama client
│   └── cli_llm.py             # Cloud LLM via CLI
├── processing/
│   ├── classifier.py          # Schema classification
│   ├── chunker.py             # Text chunking (512 tokens)
│   └── indexer.py             # Vector + BM25 indexing
├── storage/
│   ├── vector_db.py           # Chroma DB wrapper
│   ├── bm25_index.py          # BM25 search adapter
│   ├── project_storage.py     # Project persistence
│   └── bookmark_storage.py    # Bookmark persistence
└── utils/
    ├── logger.py              # Logging setup
    ├── errors.py              # Custom exceptions
    └── error_handler.py       # Error handling framework

scripts/
├── setup.py                   # Setup wizard
├── performance_profiler.py    # Performance benchmarking
├── doctor.py                  # System diagnostics
├── mcp_replay.py              # Scenario replay and metrics
├── run_regression_ci.py       # Regression testing wrapper
├── bench_qam.py               # QAM latency benchmarking
├── train_rerank_weights.py    # Reranking weight training
└── load_scenarios.py          # Scenario data loader
```

## Core Concepts

### Memory Schemas
Conversations are classified into four schemas:
- **Incident**: Bug reports, errors, troubleshooting (不具合・原因・再現手順・修正PR)
- **Snippet**: Code examples with usage context (コード片・使用理由・適用コンテキスト)
- **Decision**: Architectural choices, trade-offs (選択肢・判断根拠・トレードオフ)
- **Process**: Thought processes, learning, experimentation (思考プロセス・試行錯誤)

### Memory Processing Pipeline

**Ingestion Flow:**
1. Receive conversation (User + Assistant + metadata)
2. Classify schema via `SchemaClassifier` (local LLM)
3. Chunk content via `Chunker` (512 tokens max, tiktoken)
4. Generate embeddings via `LocalLLMClient` (nomic-embed-text)
5. Index in both Chroma DB and BM25 via `Indexer`
6. Record refs (source URLs, file paths, commit IDs)

**Search Flow:**
1. Generate query embedding (local LLM)
2. Parallel search: vector (Chroma) + keyword (BM25) → top candidates
3. Rerank via rule-based scoring (memory strength, recency, refs, similarity)
4. Return top results with refs and related memories

### Model Routing Strategy

The `ModelRouter` intelligently selects models based on task complexity:

| Task | Model | Rationale |
|------|-------|-----------|
| Embedding generation | Local (nomic-embed-text) | Always needed, privacy-critical |
| Schema classification | Local (Qwen2.5-3B) | Simple, privacy-critical |
| Short summaries (<100 tokens) | Local (Qwen2.5-3B) | Sufficient quality |
| Long summaries (>500 tokens) | CLI (Claude/GPT) | High quality needed |
| Investigation requests | CLI (Claude/GPT) | Complex reasoning |
| Memory consolidation | CLI (Claude/GPT) | Complex reasoning |

**CLI Invocation Prevention:**
- Sets `CONTEXT_ORCHESTRATOR_INTERNAL=1` env var
- PowerShell wrapper detects this flag and skips recording
- Prevents infinite loops when orchestrator calls Claude/Codex

### Memory Hierarchy

**Working Memory** (数時間保持):
- Current task context, retains for ~8 hours
- Auto-migrates to short-term on completion

**Short-term Memory** (数日〜数週間):
- Recent experiences
- Subject to consolidation nightly at 3:00 AM

**Long-term Memory** (永続的):
- Important knowledge
- High importance score (based on refs, recency, access frequency)

### Consolidation Process

Runs automatically at 3:00 AM (configurable):
1. **Migrate working memory** to short-term (completed sessions)
2. **Cluster similar memories** (cosine similarity ≥ 0.9)
3. **Select representative memory** (most detailed or recent)
4. **Forget old memories** (>30 days, low importance <0.3)
5. **Log statistics** (clusters created, memories compressed/deleted)

## Core Components

For detailed component documentation, see:
- **[docs/COMPONENTS.md](docs/COMPONENTS.md)** - Session Logging, Obsidian Integration, Codex Session Ingestion, Query Attribute Modeling, Cross-Encoder Reranking, Project Management, Search Bookmarks

**Quick overview:**
- **Session Logging**: Preserves full terminal transcripts and auto-summarizes
- **Obsidian Integration**: Auto-ingests conversation notes from Obsidian vault
- **Codex Session Ingestion**: Captures Codex CLI sessions automatically
- **Query Attribute Modeling (QAM)**: Extracts structured metadata from queries
- **Cross-Encoder Reranking**: LLM-based relevance scoring with caching
- **Project Management**: Organize memories by project/codebase
- **Search Bookmarks**: Save frequently used search queries

## CLI Commands

### System Management
```bash
# Start MCP server
python -m src.main

# Show system status
python -m src.cli status

# Run diagnostics
python -m src.cli doctor

# Manual consolidation
python -m src.cli consolidate
```

### Memory Management
```bash
# List recent memories
python -m src.cli list-recent --limit 20

# Export memories (backup)
python -m src.cli export --output backup.json

# Import memories (restore)
python -m src.cli import --input backup.json
```

### Session History
```bash
# List all sessions
python -m src.cli session-history

# Show specific session
python -m src.cli session-history --session-id <id>

# List Codex sessions
python -m src.cli session-history --backend codex
```

### Testing & Performance
```bash
# Run tests
pytest
pytest tests/unit/
pytest tests/e2e/

# Performance profiling
python scripts/performance_profiler.py

# Regression testing
python -m scripts.run_regression_ci
```

For complete testing documentation, see **[docs/TESTING.md](docs/TESTING.md)**

## Configuration

Configuration is loaded from `~/.context-orchestrator/config.yaml`. Key settings:

```yaml
# Paths
data_dir: ~/.context-orchestrator
obsidian_vault_path: /path/to/vault  # Optional

# Ollama settings
ollama_url: http://localhost:11434
embedding_model: nomic-embed-text
inference_model: qwen2.5:7b

# Search parameters
search_candidate_count: 50
search_result_count: 10

# Query Attribute Modeling
query_attribute_min_confidence: 0.4
query_attribute_llm_enabled: true

# Cross-Encoder Reranking
cross_encoder_enabled: true
cross_encoder_top_k: 3
cross_encoder_cache_size: 128

# Memory management
similarity_threshold: 0.9
age_threshold_days: 30
importance_threshold: 0.3
```

See configuration file for complete options and defaults.

## Important Design Decisions

### Why stdio (not HTTP)?
- **Simplicity**: No server management, auth, or port conflicts
- **Security**: Process isolation prevents external access
- **Compatibility**: Standard MCP transport mode
- **Multi-client**: Each client spawns isolated process, shares DB

### Why local LLM for most tasks?
- **Privacy**: Embeddings and classification stay local
- **Cost**: Zero API costs for high-frequency operations
- **Speed**: Local inference faster for small tasks (50-100ms)
- **Reliability**: No network dependency for core functions

### Why CLI-based cloud LLM?
- **Zero infrastructure**: Reuses existing `claude`/`codex` CLI
- **Cost-efficient**: Leverages user's existing subscription
- **Quality**: Complex reasoning benefits from Sonnet/GPT-4
- **Flexible**: Easy to switch providers (change `cli_command` config)

### Why Chroma DB?
- **Zero setup**: SQLite-based, no database server
- **Persistent**: File-based storage
- **Performance**: Sufficient for personal use (10K-100K memories)
- **Portability**: Single directory backup

## Development Guides

For detailed development guides, see:
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Common development tasks (adding schemas, modifying ranking, tuning reranker, etc.)
- **[docs/TESTING.md](docs/TESTING.md)** - Testing strategy and regression testing
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Solutions to common issues

**Quick reference:**
- Adding new memory schema → Update `SchemaClassifier`, add tests
- Modifying search ranking → Edit `SearchService._rerank()`, adjust weights
- Adding MCP tool → Define schema in `MCPProtocolHandler`, implement handler
- Changing consolidation → Modify `ConsolidationService`, update config

## Performance Targets

- **Search latency**: 80-200ms (typical: ~80ms)
- **Cross-encoder latency**: ~2.2s per uncached pair
- **Cross-encoder cache hit rate**: ≥60%
- **Ingestion time**: <5 seconds per conversation
- **QAM extraction**: <100ms (heuristics), <2s (LLM fallback)
- **Memory footprint**: 1GB resident, 3GB peak
- **Consolidation**: <5 minutes for 10K memories
- **Regression metrics**: Macro Precision ≥0.65, Macro NDCG ≥0.85

## Security & Privacy

### Data Protection
- All data stored locally in `~/.context-orchestrator/`
- OS-level access control (file permissions)
- No telemetry or external tracking
- Export/import for manual backups

### Privacy-Sensitive Processing
- **Embeddings**: Always local (nomic-embed-text)
- **Classification**: Always local (Qwen2.5)
- **Search**: Always local (no cloud API calls)
- **Summaries**: Local for short, cloud for long (user controls via config)

### Cloud LLM Usage
- **Minimal context**: Only necessary content sent
- **User consent**: Setup wizard asks for API keys
- **Fallback**: Degrades to local LLM if cloud unavailable
- **No recording**: Internal calls use `CONTEXT_ORCHESTRATOR_INTERNAL=1`

## References

### Specification Documents
- **Requirements**: `.kiro/specs/dev-knowledge-orchestrator/requirements.md`
  - MVP: Requirements 1-13 (Core system)
  - Phase 2: Requirements 21-26 (Obsidian, CLI, Session logging)
  - Phase 15: Query attributes, Cross-encoder reranking, Project management, Search bookmarks
- **Design**: `designtt.txt` - Detailed architecture and interfaces
- **Tasks**: `.kiro/specs/dev-knowledge-orchestrator/tasks.md` - Implementation roadmap
- **Issues**: `.kiro/specs/dev-knowledge-orchestrator/issues.md` - Issue log and resolution history

### External Resources
- **MCP Protocol**: Model Context Protocol specification
- **Ollama**: https://ollama.ai/
- **Chroma DB**: https://www.trychroma.com/
- **tiktoken**: https://github.com/openai/tiktoken

## Contributing Guidelines

### File Encoding Requirements

**CRITICAL: Always save Japanese text files with UTF-8 encoding**

When working with files containing Japanese text (日本語):
- **Encoding**: UTF-8 with BOM or UTF-8 (no BOM preferred)
- **Line endings**: LF (Unix-style) preferred, CRLF (Windows) acceptable
- **Never use**: Shift-JIS, EUC-JP, or other legacy encodings

**Files that commonly contain Japanese:**
- Configuration files (`config.yaml`)
- Documentation files (`.md`, `.txt`)
- Obsidian vault notes (`.md`)
- Session logs (`logs/*.log`)
- Python source comments (inline documentation)
- Requirements and design documents (`.kiro/specs/**/*.md`)

**How to ensure UTF-8 encoding:**

In VS Code:
```
1. Open file
2. Click encoding in status bar (bottom right)
3. Select "Save with Encoding"
4. Choose "UTF-8"
```

In Python code:
```python
# Always specify UTF-8 when reading/writing files
with open('file.txt', 'r', encoding='utf-8') as f:
    content = f.read()

with open('file.txt', 'w', encoding='utf-8') as f:
    f.write('日本語テキスト')
```

**Why this matters:**
- Japanese characters will be corrupted if saved with wrong encoding
- Ollama local LLM expects UTF-8 for Japanese text processing
- MCP protocol transmits data in UTF-8
- Session logs and summaries contain Japanese conversations
- Obsidian vault notes are typically UTF-8

### Code Style
- **PEP 8** with 4-space indentation
- **Type hints** for all function signatures
- **Docstrings** (Google style) for public APIs
- **Reference requirement IDs** in comments (e.g., `# Req-03`)
- **File encoding**: UTF-8 for all source files (especially those with Japanese comments)

### Formatting & Linting
```bash
black .      # Format code
ruff .       # Lint
mypy src     # Type check
```

### Commit Messages
Use Conventional Commits format:
- `feat: add session summary worker`
- `fix: handle BM25 index corruption`
- `refactor: extract reranking logic`
- `docs: update CLAUDE.md with session logging`
- `test: add unit tests for chunker`

Reference requirement numbers in commit body when applicable.
