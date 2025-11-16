# Changelog

All notable changes to Context Orchestrator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- PowerShell CLI recording wrapper now calls MCP `start_session → add_command → end_session` and feeds SessionLogCollector, enabling immediate `python -m src.cli session-history` results and live logs under `~/.context-orchestrator/logs`. README/Quick Start docs were updated to describe the workflow.

## [0.1.0] - 2025-11-14

### Added

#### Core Features
- **Automatic Memory Capture**: Transparently records CLI conversations (Claude, Codex)
- **Schema Classification**: Organizes memories into Incident, Snippet, Decision, Process schemas
- **Hybrid Search**: Vector (semantic) + BM25 (keyword) search with intelligent reranking
- **Local-First Privacy**: Embeddings and classification run locally using Ollama
- **Smart Model Routing**: Light tasks → local LLM, heavy tasks → cloud LLM
- **Memory Hierarchy**: Working → Short-term → Long-term memory patterns
- **Auto-Consolidation**: Nightly memory consolidation and forgetting

#### Search & Retrieval
- **Cross-Encoder Reranking**: LLM-based relevance scoring with LRU cache
- **Query Attribute Extraction**: Automatic topic/type/project detection
- **Project Management**: Organize memories by project/codebase
- **Search Bookmarks**: Save frequently used queries
- **Project Prefetching**: Warm cache when project is auto-resolved

#### Integrations
- **Obsidian Integration**: Auto-detect and ingest conversation notes from Obsidian vault
  - Monitors `.md` files for conversation patterns
  - Extracts Wikilinks for relationship tracking
  - Parses YAML frontmatter (tags, metadata)
- **Session Logging**: Preserves full terminal transcripts with auto-summarization
- **MCP Protocol**: Works with any MCP-compatible client (Claude CLI, Cursor, VS Code)

#### Management Tools
- **System Status**: Comprehensive health monitoring with `status` command
- **Diagnostics**: Automated troubleshooting with `doctor` command
- **Backup/Restore**: Export and import memories with `export`/`import` commands
- **Session History**: View and manage session logs and summaries

#### Testing & Quality Assurance
- **Edge Case Testing**: 48 comprehensive tests covering special characters, emoji, extreme inputs
- **Load Testing**: Memory leak detection, concurrent query validation, thread safety checks
- **Quality Metrics**: Precision/Recall/F1 analysis, false positive/negative detection
- **Query Pattern Coverage**: 50 diverse queries across 5 categories
- **Regression Testing**: Automated baseline comparison with `run_regression_ci`
- **Performance Profiling**: Benchmarking tool for latency, throughput, memory usage

#### CLI Commands
- `status` - Show comprehensive system status
- `doctor` - Run diagnostics and get remediation steps
- `consolidate` - Manual memory consolidation
- `list-recent` - List recent memories
- `export` - Export memories to JSON
- `import` - Import memories from JSON
- `session-history` - View session logs and summaries

#### Scripts
- `setup.py` - Setup wizard for initial configuration
- `performance_profiler.py` - Performance benchmarking tool
- `mcp_replay.py` - Scenario replay and metrics
- `run_regression_ci.py` - Regression testing wrapper
- `bench_qam.py` - Query attribute extraction benchmarking
- `train_rerank_weights.py` - Reranking weight training
- `load_scenarios.py` - Scenario data loader
- `load_test.py` - Load testing tool
- `concurrent_test.py` - Concurrent testing tool
- `quality_review.py` - Quality analysis tool

#### Configuration
- Flexible `config.yaml` with comprehensive settings
- Model routing configuration (local vs cloud LLM)
- Search parameter tuning (vector, BM25, cross-encoder)
- Memory management settings (forgetting, clustering, consolidation)
- Obsidian vault integration configuration
- Session logging configuration

### Performance

- **Search Latency**: 80-200ms (typical: ~80ms)
- **Ingestion Time**: <5 seconds per conversation
- **Memory Footprint**: 1GB resident, 3GB peak (during inference)
- **Disk Usage**: ~10MB/year (~100MB/10 years)
- **Consolidation**: Complete in <5 minutes for 10K memories
- **Cross-Encoder Cache Hit Rate**: ≥60% (in replay scenarios)
- **QAM Extraction**: <100ms (heuristics), <2s (LLM fallback)

### Test Results

- **Edge Case Tests**: 48/48 passing (100%)
- **Unit Tests**: ≥85% statement coverage
- **End-to-End Tests**: 15+ scenarios covering main workflows
- **Regression Tests**: Macro Precision ≥0.65, Macro NDCG ≥0.85
- **Load Tests**: Memory leak <5%, degradation <5%, error rate <1%
- **Concurrent Tests**: Success rate ≥99%, thread safety validated

### Documentation

- **README.md**: User-facing documentation with quick start guide
- **CLAUDE.md**: Developer guide with architecture details
- **CONTRIBUTING.md**: Contribution guidelines and development setup
- **LICENSE**: MIT License for wide adoption
- **CHANGELOG.md**: Version history (this file)
- **OSS_FILE_CHECKLIST.md**: OSS release file management guide

### Security & Privacy

- **Local-First Processing**: Embeddings and classification run locally
- **OS-Level Access Control**: File permissions protect user data
- **No Telemetry**: No external tracking or data collection
- **Export/Import**: Full control over data backups
- **Minimal Cloud Usage**: Only for complex tasks, user-configurable

## Release Notes

### v0.1.0 - Initial Public Release

Context Orchestrator v0.1.0 is a production-ready external brain system for developers. This initial release includes:

✅ **Complete Core Functionality**: Memory capture, classification, search, consolidation
✅ **Privacy-First Architecture**: Local LLM processing with optional cloud fallback
✅ **Universal Integration**: Works with any MCP-compatible client
✅ **Production-Ready Quality**: Comprehensive test suite (48 edge cases, 100% passing)
✅ **Performance Targets Met**: <200ms search, <5s ingestion, <5min consolidation
✅ **Developer Tools**: CLI commands, diagnostics, performance profiling

### What's Next?

#### v0.2.0 (Planned)
- **Project Initialization**: `/init` command for scanning existing codebase
- **Codebase Indexing**: Automatically index project files and structure
- **File-Level Associations**: Link memories to specific files/commits
- **Enhanced Obsidian Integration**: Bidirectional sync and advanced parsing

#### Future Considerations
- Web UI for memory exploration
- Team collaboration features
- Custom schema definitions
- Plugin system for extensibility

### Known Limitations

- **Database**: Uses local Chroma DB (not distributed, single user)
- **Scalability**: Optimized for personal use (10K-100K memories)
- **Windows Focus**: PowerShell wrapper tested primarily on Windows
- **MCP Protocol**: Requires MCP-compatible client (Claude CLI, Cursor, VS Code)

### Migration Notes

This is the initial release, no migration needed.

### Acknowledgments

Special thanks to:
- **Ollama** for local LLM runtime
- **Chroma** for vector database
- **Model Context Protocol (MCP)** for standardized integration
- **All contributors** who helped test and refine this release

---

[Unreleased]: https://github.com/myo-ojin/llm-brain/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/myo-ojin/llm-brain/releases/tag/v0.1.0
