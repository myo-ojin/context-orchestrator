# Implementation Plan - Context Orchestrator

This document lists the implementation tasks for the Context Orchestrator (external brain system). Tasks are ordered to allow incremental delivery and are phrased so Claude Code / Sonnet 4.5 can execute them directly.

## Task Legend
- `[ ]`: task not yet started
- `[x]`: task completed
- `*`: optional task (nice-to-have, not core MVP)

---

## Phase 1: Project Scaffolding and Core Layout

### 1. Repository Bootstrap
- [x] 1.1 Create the project directory structure
  - Add `src/`, `tests/`, `scripts/`, `requirements.txt`, `setup.py`, and `README.md`
  - _Requirements: Requirement 13_
- [x] 1.2 Prepare dependency manifest
  - Populate `requirements.txt` with `chromadb`, `tiktoken`, `rank-bm25`, `pyyaml`, `requests`, `watchdog`, `python-dateutil`, `apscheduler`
  - _Requirements: Requirement 13_
- [x] 1.3 Provide configuration template
  - Author `config.yaml` template (fields: `data_dir`, `ollama_url`, `embedding_model`, `inference_model`, `cli_command`, etc.)
  - _Requirements: Requirement 13_

---

## Phase 2: Storage Layer

### 2. Vector and Keyword Retrieval
- [x] 2.1 Implement Chroma vector DB adapter (`src/storage/vector_db.py` > `ChromaVectorDB` with `add`, `search`, `get`, `delete`)
  - _Requirements: Requirement 12_
- [x] 2.2 Implement BM25 index adapter (`src/storage/bm25_index.py` > `BM25Index` with `add_document`, `search`, `_rebuild_index`, `_save`, `_load`)
  - _Requirements: Requirement 12_
- [x] 2.3 Define domain data models (`src/models/__init__.py` > `Memory`, `Chunk` dataclasses)
  - _Requirements: Requirements 2, 3_

---

## Phase 3: Local LLM Client Layer

### 3. Ollama Integration and Model Routing
- [x] 3.1 Implement `LocalLLMClient` (`src/models/local_llm.py`) with `generate_embedding`, `generate`
  - _Requirements: Requirement 10_
- [x] 3.2 Implement `CLILLMClient` (`src/models/cli_llm.py`) with `generate`, `_call_cli_background`; respect `CONTEXT_ORCHESTRATOR_INTERNAL=1`
  - _Requirements: Requirement 10_
- [x] 3.3 Implement `ModelRouter` (`src/models/router.py`) with `route`, `_is_lightweight_task` to pick local vs CLI-based models
  - _Requirements: Requirement 10_

---

## Phase 4: Memory Processing Pipeline

### 4. Classification, Chunking, Indexing
- [x] 4.1 Implement `SchemaClassifier` (`src/processing/classifier.py`) for Incident/Snippet/Decision/Process classification
  - _Requirements: Requirement 2_
- [x] 4.2 Implement `Chunker` (`src/processing/chunker.py`) that respects headings, paragraphs, code blocks, and 512-token limit via `tiktoken`
  - Ensure chunk metadata stores `memory_id` and `chunk_index` for downstream indexing/deletion workflows
  - _Requirements: Requirement 3_
- [x] 4.3 Implement `Indexer` (`src/processing/indexer.py`) to push chunks into vector DB and BM25 index
  - _Requirements: Requirement 3_

---

## Phase 5: Core Services

### 5. Ingestion, Search, Consolidation
- [x] 5.1 Implement `IngestionService` (`src/services/ingestion.py`) with `ingest_conversation`, `_classify_schema`, `_chunk_content`, `_index_chunks`
  - _Requirements: Requirements 1, 2, 3_
- [x] 5.2 Implement `SearchService` (`src/services/search.py`) with hybrid retrieval (`_generate_query_embedding`, `_vector_search`, `_bm25_search`, `_merge_results`, `_rerank`)
  - _Requirements: Requirement 8_
- [x] 5.3 Implement `ConsolidationService` (`src/services/consolidation.py`) with `_migrate_working_memory`, `_cluster_similar_memories`, `_select_representative_memory`, `_forget_old_memories`
  - _Requirements: Requirement 6_
- [x] 5.4 Unit tests for all three services (`tests/unit/services/test_*.py`)
  - Completed: test_ingestion.py, test_search.py, test_consolidation.py

---

## Phase 6: Session Management (Working Memory)

### 6. PowerShell Session Capture
- [x] 6.1 Implement `SessionManager` (`src/services/session_manager.py`) handling `add_command`, `end_session`, `_format_session_log`, `_create_obsidian_note`, `_save_to_vault`
  - _Requirements: Requirements 1, 4_
- [x] 6.2 Generate Obsidian notes from sessions and send content through local LLM summarization before writing to the vault
  - _Requirements: Requirements 1.5, 9_
- [x] 6.3 Implement `SessionLogCollector` (`src/services/session_log_collector.py`) for session transcript logging with rotation
  - _Requirements: Requirement 26_
- [x] 6.4 Implement `SessionSummaryWorker` (`src/services/session_summary.py`) for async summarization with retry logic
  - _Requirements: Requirement 26_
- [x] 6.5 Unit tests for session management (`tests/unit/services/test_session_*.py`)
  - Completed: test_session_manager.py, test_session_log_collector.py, test_session_summary.py

---

## Phase 7: MCP Protocol Handler

### 7. stdio JSON-RPC Bridge
- [x] 7.1 Implement `MCPProtocolHandler` (`src/mcp/protocol_handler.py`) with `start`, `handle_request`, `_route_to_service`
  - _Requirements: Requirement 11_
- [x] 7.2 Expose MCP tools (`ingest_conversation`, `search_memory`, `get_memory`, `list_recent_memories`, `consolidate_memories`)
  - _Requirements: Requirement 11_
- [x] 7.3 Unit tests for MCP protocol handler (`tests/unit/mcp/test_protocol_handler.py`)
  - Completed: 32 test cases covering JSON-RPC handling, all 8 tools (5 main + 3 session), error handling

---

## Phase 8: Entry Point & Configuration

### 8. Main Program and Utilities
- [x] 8.1 Implement config loader (`src/config.py` > `load_config` returning typed Config)
  - _Requirements: Requirement 13_
  - Completed: Typed Config dataclasses, YAML loading, path expansion, default values
- [x] 8.2 Implement logging utilities (`src/utils/logger.py` > `setup_logger`)
  - _Requirements: Requirement 13_
  - Completed: Console and file logging, configurable levels, consistent formatting
- [x] 8.3 Implement custom errors (`src/utils/errors.py` with `OllamaConnectionError`, `ModelNotFoundError`, `CLICallError`, `DatabaseError`)
  - _Requirements: Requirement 13_
  - Completed: 11 custom exception classes with user-friendly messages
- [x] 8.4 Implement main entry point (`src/main.py` > `main` to load config, init storage/services, start MCP handler)
  - _Requirements: Requirements 11, 13_
  - Completed: Full initialization pipeline, graceful error handling, MCP handler startup

---

## Phase 9: PowerShell Wrapper and Setup Scripts

### 9. CLI Recording & Setup
- [x] 9.1 Build the PowerShell wrapper script
  - Create `scripts/setup_cli_recording.ps1` and enable automatic profile insertion via `$PROFILE`
  - Implement session ID issuance, background submission, and the `CONTEXT_ORCHESTRATOR_INTERNAL` guard
  - _Requirements: Requirement 1, 26_
  - Completed: Install/Uninstall support, claude/codex wrapper functions, background job submission
- [x] 9.2 Implement the setup wizard
  - Create `scripts/setup.py` and guide users through Ollama check → model download → Vault configuration → PowerShell wrapper configuration
  - Auto-verify/download recommended models (`nomic-embed-text`, `qwen2.5:7b`)
  - _Requirements: Requirement 13_
  - Completed: Interactive wizard with Ollama check, model installation, path configuration, CLI setup
- [x] 9.3 Implement the troubleshooting tool
  - Create `scripts/doctor.py` with health checks for Ollama, model presence, PowerShell wrapper, and database connectivity
  - On failure, print remediation steps to stdout
  - _Requirements: Requirement 13_
  - Completed: 5 health checks (Ollama, models, data dir, Chroma DB, config) with remediation steps
- [x] 9.4 Implement the Session Log Collector
  - _Requirements: Requirement 26_
  - **Already completed in Phase 6** - `src/services/session_log_collector.py`
- [x] 9.5 Implement the Session Summary Worker
  - _Requirements: Requirement 26_
  - **Already completed in Phase 6** - `src/services/session_summary.py`
- [x] 9.6 Add the session history CLI command
  - Extend `src/cli.py` with a `session-history` command to return raw logs and summaries by session_id
  - Add options such as `--open` (launch raw log in default editor) and `--summary-only`
  - _Requirements: Requirement 26_
  - Completed: Full CLI with status, doctor, consolidate, list-recent, session-history, export, import commands

---

## Phase 10: Overnight Consolidation Scheduler

### 10. Automated Consolidation
- [x] 10.1 Integrate APScheduler (`src/main.py`) to run `consolidation_service.consolidate()` nightly at 03:00
  - _Requirements: Requirement 6_
  - Completed: Scheduler initialized with cron trigger, graceful shutdown implemented
- [x] 10.2 Implement startup consolidation check (`check_and_run_consolidation`) to catch missed runs (>24h)
  - _Requirements: Requirement 6_
  - Completed: Checks last_consolidation timestamp, runs if >24h passed, handles first run

---

## Phase 11: Obsidian Integration

### 11. File Watcher and Parser
- [x] 11.1 Implement `ObsidianWatcher` (`src/services/obsidian_watcher.py`) using `watchdog` to detect `.md` changes
  - _Requirements: Requirement 1.5_
  - Completed: File system monitoring with watchdog, debouncing, graceful shutdown
- [x] 11.2 Implement `ObsidianParser` (`src/services/obsidian_parser.py`) to parse conversation notes (`**User:**` / `**Assistant:**`, Wikilinks)
  - _Requirements: Requirements 1.5, 9_
  - Completed: Conversation extraction, Wikilink parsing, YAML frontmatter support
- [x] 11.3 Integrate ObsidianWatcher with main.py startup
  - Completed: Auto-start when obsidian_vault_path is configured
- [x] 11.4 Add unit tests for ObsidianWatcher and ObsidianParser
  - Completed: Comprehensive test suites with 20+ test cases each

---

## Phase 12: CLI Interface

### 12. Command Implementation
- [x] 12.1 Implement CLI commands in `src/cli.py` (`status`, `doctor`, `consolidate`, `list-recent`, `export`, `import`)
  - _Requirements: Requirement 13_
  - Completed: All 7 commands fully implemented with comprehensive functionality
  - status: Enhanced with Ollama, Vector DB, BM25, Obsidian, and consolidation checks
  - doctor: Delegates to scripts/doctor.py
  - consolidate: Full consolidation service integration with statistics
  - list-recent: Lists recent memories with metadata
  - session-history: Complete session log management with summary support
  - export: JSON export with embeddings and metadata
  - import: JSON import with --force option for overwriting
- [x] 12.2 Provide packaging entry point (`setup.py` / console script for `context-orchestrator`)
  - _Requirements: Requirement 13_
  - Completed: setup.py with console_scripts entry point configured

---

## Phase 13: Testing and Documentation

### 13. Tests and README
- [ ]* 13.1 Author unit tests (`tests/unit/`) for Chunker, SchemaClassifier, Reranker
  - _Requirements: Testing Strategy_
- [ ]* 13.2 Author integration tests (`tests/integration/`) covering ingestion→indexing and search→reranking
  - _Requirements: Testing Strategy_
- [x] 13.3 Write `README.md` (installation, setup, usage, troubleshooting)
  - _Requirements: Requirement 13_

---

## Phase 14: Integration & Optimization

### 14. System Hardening
- [ ] 14.1 End-to-end validation (record → search → retrieve loop)
  - _Requirements: All Requirements_
- [ ] 14.2 Performance tuning (target search latency ≤200ms; profile and optimize bottlenecks)
  - _Requirements: Requirement 8_
- [ ] 14.3 Improve error handling (consistent messaging and structured logging across services)
  - _Requirements: Requirement 13_

---

## Delivery Priorities
- **MVP (highest)**: Phases 1–8 for MCP-ready core, Phase 9 PowerShell wrapper, Phase 13.3 README
- **Next**: Phase 10 scheduler, Phase 11 Obsidian integration, Phase 12 CLI polish
- **Optional**: Phase 13 unit/integration tests once core features pass smoke tests; Phase 14 performance tuning as capacity allows

---

## Notes
1. Execute phases sequentially and validate functionality after each milestone.
2. Keep implementation testable—add quick verification scripts whenever feasible.
3. Document high-friction areas with inline comments and update specs/README continuously.
4. Ensure external dependencies (Ollama, Chroma DB, filesystem watchers) have clear failure handling.
5. Favor configuration-driven values over hard-coding (mirror fields from `config.yaml`).
