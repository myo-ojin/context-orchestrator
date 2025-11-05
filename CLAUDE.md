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
- Location: `c:\Users\81906\Documents\app\brainsystem\.kiro`
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
The system uses these Ollama models:
- `nomic-embed-text` - Embedding generation (137M, Q4_K_M quantized)
- `qwen2.5:7b` - Local inference for classification, summarization (3B, Q4_K_M quantized)

Download via:
```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
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
│   └── obsidian_parser.py     # Conversation extraction
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
│   └── bm25_index.py          # BM25 search adapter
└── utils/
    ├── logger.py              # Logging setup
    └── errors.py              # Custom exceptions
```

## Core Components

### 1. Memory Schemas
Conversations are classified into four schemas:
- **Incident**: Bug reports, errors, troubleshooting (不具合・原因・再現手順・修正PR)
- **Snippet**: Code examples with usage context (コード片・使用理由・適用コンテキスト)
- **Decision**: Architectural choices, trade-offs (選択肢・判断根拠・トレードオフ)
- **Process**: Thought processes, learning, experimentation (思考プロセス・試行錯誤)

### 2. Memory Processing Pipeline

**Ingestion Flow:**
1. Receive conversation (User + Assistant + metadata)
2. Classify schema via `SchemaClassifier` (local LLM)
3. Chunk content via `Chunker` (512 tokens max, tiktoken)
4. Generate embeddings via `LocalLLMClient` (nomic-embed-text)
5. Index in both Chroma DB and BM25 via `Indexer`
6. Record refs (source URLs, file paths, commit IDs)

**Search Flow:**
1. Generate query embedding (local LLM)
2. Parallel search: vector (Chroma) + keyword (BM25) → top 50 candidates
3. Rerank via rule-based scoring (memory strength, recency, refs, similarity)
4. Return top 10 results with refs and related memories

### 3. Model Routing Strategy

The `ModelRouter` intelligently selects models based on task complexity:

| Task | Model | Rationale | Cost |
|------|-------|-----------|------|
| Embedding generation | Local (nomic-embed-text) | Always needed, privacy-critical | Free |
| Schema classification | Local (Qwen2.5-3B) | Simple, privacy-critical | Free |
| Short summaries (<100 tokens) | Local (Qwen2.5-3B) | Sufficient quality | Free |
| Long summaries (>500 tokens) | CLI (Claude/GPT) | High quality needed | User's existing plan |
| Investigation requests | CLI (Claude/GPT) | Complex reasoning | User's existing plan |
| Memory consolidation | CLI (Claude/GPT) | Complex reasoning | User's existing plan |

**CLI Invocation Prevention:**
- Sets `CONTEXT_ORCHESTRATOR_INTERNAL=1` env var
- PowerShell wrapper detects this flag and skips recording
- Prevents infinite loops when orchestrator calls Claude/Codex

### 4. Memory Hierarchy

**Working Memory** (数時間保持):
- Current task context
- Retains for ~8 hours
- Auto-migrates to short-term on completion

**Short-term Memory** (数日〜数週間):
- Recent experiences
- Subject to consolidation nightly at 3:00 AM

**Long-term Memory** (永続的):
- Important knowledge
- High importance score (based on refs, recency, access frequency)

### 5. Consolidation Process

Runs automatically at 3:00 AM (configurable):
1. **Migrate working memory** to short-term (completed sessions)
2. **Cluster similar memories** (cosine similarity ≥ 0.9)
3. **Select representative memory** (most detailed or recent)
4. **Forget old memories** (>30 days, low importance <0.3)
5. **Log statistics** (clusters created, memories compressed/deleted)

### 6. Session Logging (Requirement 26)

**Purpose**: Preserve full terminal transcripts and auto-summarize when sessions close, preventing context loss from token limits or resets.

**Components:**
- `SessionLogCollector`: Issues unique session_id, streams to `logs/<session_id>.log`, rotates at 10MB
- `SessionSummaryWorker`: Queues closed logs, summarizes via local LLM, stores with metadata (session_id, start/end time, model), retries failures up to 3 times
- `session-history` CLI: Retrieves raw logs and summaries by session_id

**Flow:**
1. PowerShell wrapper or MCP client sends events to `SessionLogCollector`
2. Events append to live log file (UTF-8 text)
3. On session close, `SessionSummaryWorker` runs async summarization job
4. Summary + metadata saved to session repository
5. Failed jobs auto-retry with exponential backoff

### 7. Obsidian Integration (Requirements 1.5, 9)

**Purpose**: Automatically detect and ingest conversation notes from Obsidian vault, enabling seamless integration with existing knowledge base.

**Components:**
- `ObsidianWatcher`: File system watcher that monitors `.md` files in the vault
- `ObsidianParser`: Parses conversation format (`**User:**` / `**Assistant:**`) and Wikilinks

**Flow:**
1. `ObsidianWatcher` monitors vault directory using watchdog library
2. When `.md` file is created/modified, check if it contains conversations
3. `ObsidianParser` extracts:
   - User/Assistant conversation turns
   - Wikilinks (`[[filename]]`) for relationship tracking
   - YAML frontmatter (tags, date, metadata)
4. Each conversation is ingested through `IngestionService`
5. Metadata includes file path, Wikilinks, and conversation index

**Features:**
- **Auto-detection**: Automatically finds conversation notes as they're created
- **Debouncing**: Prevents duplicate processing of rapid file changes (2s interval)
- **Graceful handling**: Errors in parsing don't crash the watcher
- **Vault scanning**: Optional one-time import of existing notes via `scan_existing_notes()`
- **Recursive monitoring**: Detects changes in subdirectories
- **Context manager support**: Properly manages lifecycle with `with` statement

**Configuration:**
```yaml
# config.yaml
obsidian_vault_path: C:\Users\username\Documents\ObsidianVault
```

When `obsidian_vault_path` is set, ObsidianWatcher starts automatically on system startup.

## Development Commands

### Running the System
```bash
# Start Context Orchestrator as MCP server (stdio mode)
python -m src.main

# Or use console entry point (if installed with pip install -e .)
context-orchestrator
```

### CLI Commands

**System Status:**
```bash
# Show comprehensive system status
python -m src.cli status
# or: context-orchestrator status

# Displays:
# - Data directory status
# - Ollama connection and models
# - Vector DB (Chroma) statistics
# - BM25 index status
# - Session logs statistics
# - Obsidian integration status
# - Last consolidation time
```

**Health Check:**
```bash
# Run diagnostics and get remediation steps
python -m src.cli doctor
# or: context-orchestrator doctor

# Checks:
# - Ollama service status
# - Required models (nomic-embed-text, qwen2.5:7b)
# - Data directory permissions
# - Database integrity
# - Configuration validity
```

**Memory Consolidation:**
```bash
# Manually run memory consolidation
python -m src.cli consolidate
# or: context-orchestrator consolidate

# Performs:
# - Working memory → Short-term migration
# - Clustering similar memories
# - Forgetting old/unimportant memories
# - Reports statistics (migrated, clustered, deleted)
```

**Memory Management:**
```bash
# List recent memories
python -m src.cli list-recent --limit 20
# or: context-orchestrator list-recent --limit 20

# Export memories to JSON (backup)
python -m src.cli export --output backup.json
# or: context-orchestrator export --output backup.json

# Import memories from JSON (restore)
python -m src.cli import --input backup.json
python -m src.cli import --input backup.json --force  # Overwrite existing
# or: context-orchestrator import --input backup.json
```

**Session History:**
```bash
# List all sessions
python -m src.cli session-history
# or: context-orchestrator session-history

# Show specific session log
python -m src.cli session-history --session-id <session_id>

# Show only summary
python -m src.cli session-history --session-id <session_id> --summary-only

# Open log in editor
python -m src.cli session-history --session-id <session_id> --open
```

### Testing Commands
```bash
# Run full test suite
pytest

# Run unit tests only
pytest tests/unit/

# Run end-to-end tests
pytest tests/e2e/

# Run specific test file
pytest tests/e2e/test_full_workflow.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run with verbose output
pytest -v
```

### Performance Profiling
```bash
# Run all performance benchmarks
python scripts/performance_profiler.py

# Custom number of runs
python scripts/performance_profiler.py --runs 200

# Save report to custom location
python scripts/performance_profiler.py --output ./performance_report.json

# Benchmarks include:
# - Search latency (P50/P95/P99, target ≤200ms)
# - Ingestion throughput (target <5s/conversation)
# - Consolidation time (target <5min for 10K memories)
# - Memory footprint (target ≤1GB resident, ≤3GB peak)
```

## Configuration

Configuration is loaded from `~/.context-orchestrator/config.yaml`:

```yaml
# Paths
data_dir: ~/.context-orchestrator
obsidian_vault_path: C:\Users\...\ObsidianVault  # Optional

# Ollama settings
ollama_url: http://localhost:11434
embedding_model: nomic-embed-text
inference_model: qwen2.5:7b

# CLI LLM (for heavy tasks)
cli_command: claude  # or "codex"

# Search parameters
search_candidate_count: 50
search_result_count: 10
search_timeout_seconds: 2

# Clustering
similarity_threshold: 0.9
min_cluster_size: 2

# Forgetting
age_threshold_days: 30
importance_threshold: 0.3
compression_enabled: true

# Working memory
working_memory_retention_hours: 8
auto_consolidate: true

# Consolidation schedule (cron format)
consolidation_schedule: "0 3 * * *"  # 3:00 AM daily

# Session logging
logging:
  session_log_dir: ~/.context-orchestrator/logs
  max_log_size_mb: 10
  summary_model: qwen2.5:7b
```

## Key Implementation Patterns

### 1. Chunking Strategy
- **Primary split**: Markdown headings (`#`, `##`, `###`)
- **Overflow split**: Paragraphs (`\n\n`) if >512 tokens
- **Preserve**: Code blocks (` ```...``` `) never split
- **Conversations**: 1 turn (User + Assistant) = 1 chunk

### 2. Reranking Score Calculation
```python
score = (
    memory.strength * 0.3 +           # Memory strength
    recency_score * 0.2 +             # Recency
    len(memory.refs) * 0.1 +          # Refs reliability
    memory.bm25_score * 0.2 +         # Keyword match
    memory.vector_similarity * 0.2    # Vector similarity
)
```

### 3. Error Handling (Enhanced in Phase 14)
- **Graceful degradation**: Continue operating on partial failures
- **Detailed logging**: All errors logged with context
- **User-friendly messages**: Technical details hidden from users
- **Fallback chains**: Cloud LLM fails → local LLM fallback

**Error Handling Framework:**
```python
from src.utils.error_handler import ErrorHandler, ErrorContext, with_error_handling

# Using ErrorContext for structured error handling
try:
    result = risky_operation()
except Exception as e:
    context = ErrorContext(
        operation='search',
        context={'query': query},
        user_message='Failed to search memories',
        suggestions=['Check database connection', 'Verify Ollama is running']
    )
    ErrorHandler.handle_error(e, context, reraise=False)

# Using decorator for automatic error handling
@with_error_handling("ingest_conversation", "Failed to ingest conversation")
def ingest(conversation):
    # Implementation
    pass
```

**Structured Logging:**
```python
from src.utils.logger import setup_structured_logger, get_logger_with_context, log_operation

# JSON-formatted logging
logger = setup_structured_logger('my_service', 'INFO')
logger.info('Processing item', extra={'context': {'item_id': '123'}})
# Output: {"timestamp": "2025-01-15T10:00:00", "level": "INFO", "message": "Processing item", "context": {"item_id": "123"}}

# Logger with automatic context injection
logger = get_logger_with_context(__name__, {'service': 'ingestion'})

# Operation timing context manager
with log_operation(logger, 'search'):
    results = search_memory(query)
# Logs: Operation 'search' started
# Logs: Operation 'search' completed in 123.45ms
```

### 4. PowerShell CLI Recording
The system uses a PowerShell wrapper function that:
1. Intercepts `claude` and `codex` commands
2. Captures stdout/stderr via `Tee-Object`
3. Sends to Context Orchestrator in background job (non-blocking)
4. Preserves exit codes and error messages
5. Checks `$env:CONTEXT_ORCHESTRATOR_INTERNAL` to prevent recursive recording

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

## Testing Strategy (Updated Phase 14)

### Unit Tests (`tests/unit/`)
Focus on individual components:
- `Chunker`: Token counting, heading splits, code block preservation
- `SchemaClassifier`: Schema detection accuracy
- `Reranker`: Score calculation logic
- `BM25Index`: Keyword search correctness
- **Coverage**: 20+ unit test files with mocked dependencies

### Integration Tests
Documented in `INTEGRATION_TEST_RESULTS.md`:
- 7/10 components tested (70% coverage)
- 100% pass rate for tested components
- CLI commands (status, doctor, list-recent, export, import)
- ObsidianParser (conversation extraction, wikilinks, frontmatter)
- Error handling validation

### End-to-End Tests (`tests/e2e/`) - Phase 14
Comprehensive full-workflow validation in `tests/e2e/test_full_workflow.py`:

**TestEndToEndWorkflow:**
- Basic ingestion and retrieval loop
- Multiple conversation retrieval with ranking
- Consolidation workflow (cluster detection)
- Search with special characters
- Long content chunking validation
- Japanese text handling
- Code block preservation
- Search result ranking validation

**TestErrorHandling:**
- Missing required fields
- Empty content handling
- Empty query handling

**TestPerformance:**
- Search latency measurement (target ≤200ms)
- Batch ingestion throughput (target <5s/conversation)

### Performance Profiling (`scripts/performance_profiler.py`)
Automated benchmarking tool that measures:
- **Search Latency**: P50/P95/P99 with 100+ runs
- **Ingestion Throughput**: Conversations per second
- **Consolidation Time**: Extrapolated to 10K memories
- **Memory Footprint**: Peak and resident memory tracking
- **JSON Reports**: Pass/fail for each target with detailed metrics

Run with: `python scripts/performance_profiler.py [--runs N] [--output PATH]`

### Target Metrics
- **Coverage**: ≥85% statement coverage (unit tests)
- **E2E Coverage**: 15+ test scenarios covering main workflows
- **Search latency**: ≤200ms (typical ~80ms)
- **Ingestion speed**: ≤5 seconds per conversation
- **Memory usage**: ~1GB resident, ~3GB peak
- **All performance targets**: Validated via profiler

## Common Development Tasks

### Adding a new memory schema
1. Update `SchemaClassifier._build_classification_prompt()`
2. Add schema type to `Memory` dataclass in `src/models/__init__.py`
3. Update classification logic to handle new schema fields
4. Add test cases in `tests/unit/processing/test_classifier.py`

### Modifying search ranking
1. Edit `SearchService._rerank()` in `src/services/search.py`
2. Adjust weight coefficients in score calculation
3. Add unit tests for new scoring logic
4. Run integration tests to validate overall search quality

### Adding a new MCP tool
1. Define tool schema in `MCPProtocolHandler`
2. Implement handler method in `_route_to_service()`
3. Connect to appropriate service (ingestion/search/consolidation)
4. Update documentation in README and AGENTS.md

### Changing consolidation behavior
1. Modify `ConsolidationService` methods in `src/services/consolidation.py`
2. Update configuration parameters in `config.yaml`
3. Test with `python -m src.cli consolidate`
4. Verify via `python -m src.cli status --verbose`

## Troubleshooting

### Ollama not responding
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Verify models are installed
ollama list
```

### PowerShell wrapper not working
```powershell
# Check if wrapper is loaded
Get-Command claude

# Reload profile
. $PROFILE

# Re-run setup
python scripts/setup.py --repair
```

### Search returns no results
1. Check if memories are indexed: `python -m src.cli list-recent`
2. Verify Chroma DB exists: `ls ~/.context-orchestrator/chroma_db/`
3. Check logs: `python -m src.cli logs --tail 50`
4. Rebuild index: `python -m src.cli reindex`

### High memory usage
1. Check consolidation schedule: `python -m src.cli status --verbose`
2. Run manual consolidation: `python -m src.cli consolidate`
3. Adjust forgetting thresholds in `config.yaml`
4. Export and prune old memories: `python -m src.cli export --before 2024-01-01`

## Performance Targets

- **Search latency**: 80-200ms (typical: ~80ms)
- **Ingestion time**: <5 seconds per conversation
- **Memory footprint**: 1GB resident, 3GB peak (during inference)
- **Disk usage**: ~10MB/year (73MB/10 years)
- **Consolidation**: Complete in <5 minutes for 10K memories

## Security & Privacy

### Data Protection
- **All data stored locally** in `~/.context-orchestrator/`
- **OS-level access control** (file permissions)
- **No telemetry or external tracking**
- **Export/import** for manual backups

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
- **Requirements**: `.kiro/specs/dev-knowledge-orchestrator/requirements.md` - Full requirements (MVP: Req 1-13, Phase 2: Req 21-26)
- **Design**: `designtt.txt` - Detailed architecture and interfaces
- **Tasks**: `.kiro/specs/dev-knowledge-orchestrator/tasks.md` - Implementation roadmap

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

In PowerShell scripts:
```powershell
# Use UTF-8 encoding for output
[System.IO.File]::WriteAllText($path, $content, [System.Text.Encoding]::UTF8)

# Or specify encoding in Out-File
$content | Out-File -FilePath $path -Encoding utf8
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
# Format code
black .

# Lint
ruff .

# Type check
mypy src
```

### Commit Messages
Use Conventional Commits format:
- `feat: add session summary worker`
- `fix: handle BM25 index corruption`
- `refactor: extract reranking logic`
- `docs: update CLAUDE.md with session logging`
- `test: add unit tests for chunker`

Reference requirement numbers in commit body when applicable.
