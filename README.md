# Context Orchestrator

> Privacy-first MCP server that acts as your external brain across Claude CLI, Cursor, VS Code, and any other Model Context Protocol client.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11-3.12](https://img.shields.io/badge/python-3.11--3.12-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-48%2F48%20passing-success)](tests/)
[![Release](https://img.shields.io/badge/version-v0.1.0-6f42c1.svg)](CHANGELOG.md)

[日本語ドキュメント](README_JA.md) | [OSS README](README_OSS.md) | [Quick Start](QUICKSTART.md) | [Setup Guide](SETUP_GUIDE.md) | [Setup Verification](SETUP_VERIFICATION.md)

An external brain system that acts as an MCP (Model Context Protocol) server, enabling developers to capture, organize, and retrieve their work experiences across any LLM client.

## Documentation Map

- [Quick Start](QUICKSTART.md): five-minute setup, smoke tests, and first MCP run.
- [Setup Guide](SETUP_GUIDE.md): detailed environment preparation notes (PowerShell + Bash).
- [Setup Verification](SETUP_VERIFICATION.md): checklist we run before tagging releases.
- [README_JA](README_JA.md): full Japanese translation of the OSS README.
- [README_OSS](README_OSS.md): public-facing README that ships with release archives.
- [OSS Release Summary](OSS_RELEASE_SUMMARY.md) / [OSS File Checklist](OSS_FILE_CHECKLIST.md): packaging and distribution steps.

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

### Testing & Quality Assurance

- 🧪 **Edge Case Testing**: 48 comprehensive tests covering special characters, emoji, extreme inputs
- 📈 **Load Testing**: Memory leak detection, concurrent query validation, thread safety checks
- 📊 **Quality Metrics**: Precision/Recall/F1 analysis, false positive/negative detection
- 🎯 **Query Pattern Coverage**: 50 diverse queries across 5 categories for comprehensive validation

## Quick Start

Need the full walkthrough (clone → setup wizard → smoke tests)? Follow the dedicated [Quick Start guide](QUICKSTART.md). The condensed steps are below.

### Prerequisites

- Python **3.11.x or 3.12.x** (v3.11.9 is what we ship/verify in CI)
- [Ollama](https://ollama.ai/) 0.3+ (for local embeddings + inference)
- PowerShell 7+ (Windows) or Bash/zsh (macOS/Linux)
- Git 2.40+ and curl (for cloning and health checks)
- Optional: GPU with ≥8GB VRAM for faster Qwen2.5 inference

### Installation

```bash
# Clone & enter repository
git clone https://github.com/myo-ojin/context-orchestrator.git
cd context-orchestrator

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

### Smoke Test (recommended)

```bash
# Verify services
python -m src.cli status
python -m src.cli doctor

# Edge-case regression
pytest tests/unit/services/test_search_edge_cases.py -q

# Hybrid replay against the latest baseline
python -m scripts.run_regression_ci --baseline reports/baselines/mcp_run-20251109-143546.jsonl
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

> 💡 **Tip:** Run `powershell -ExecutionPolicy Bypass -File scripts/setup_cli_recording.ps1 -Install` once so every PowerShell session is captured automatically. After that, `python -m src.cli session-history` will always have fresh memories to show.

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

# Performance profiling
python scripts/performance_profiler.py  # Run performance benchmarks
```

See [CLAUDE.md](CLAUDE.md) for detailed CLI documentation.

### Testing & Quality Assurance

Context Orchestrator includes comprehensive test suites to ensure reliability and performance:

```bash
# Unit tests (including edge cases)
pytest tests/unit/services/test_search_edge_cases.py  # 48 edge case tests (100% pass)

# Regression testing
python -m scripts.run_regression_ci  # Compare against baseline metrics

# Load testing
python -m scripts.load_test --num-queries 100  # Consecutive query load test
python -m scripts.concurrent_test --concurrency 5 --rounds 10  # Parallel query test

# Quality review
python -m scripts.quality_review --samples-per-topic 5  # Topic-based quality analysis

# Query pattern testing
python -m scripts.mcp_replay --requests tests/scenarios/diverse_queries.json  # 50 diverse queries
```

**Test Coverage:**
- **Edge Cases** (48 tests): Zero-hit queries, special characters (20 types), emoji (9 types), whitespace (6 types), extreme length queries, project ID filtering
- **Load Tests**: 100 consecutive queries with memory leak detection, concurrent execution with thread safety validation
- **Quality Metrics**: Precision/Recall/F1, false positive/negative rates, score distribution analysis
- **Query Patterns**: 50 diverse queries across 5 categories (long/short, multilingual, technical/natural, domain-specific, vague/specific)

### Structured Summaries & Scenario Loader

Every ingested conversation must produce a structured summary with the following exact layout:

```
Topic: <short topic name>
DocType: <incident|decision|checklist|guide|...>
Project: <project name or Unknown>
KeyActions:
- <Imperative Action 1>
- <Action 2>
```

- `KeyActions` は必ず `- ` で始まる箇条書きにする。段落や番号付きリストは検証に失敗する。
- `scripts.load_scenarios` は取り込み時にこの形式をチェックし、違反があるとメモ ID と生成サマリの抜粋を表示して中断する。
- エラーが出た場合は該当会話かテンプレートを修正し、`python -m scripts.load_scenarios --file tests/scenarios/scenario_data.json` を再実行する。

CI の `python -m scripts.run_regression_ci` も同じ検証を行うため、テンプレートを更新した際は README とシナリオ README を同期させてからテストを流してください。

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
  cross_encoder_enabled: true
  cross_encoder_top_k: 3
  cross_encoder_cache_size: 128
  cross_encoder_cache_ttl_seconds: 900
  vector_candidate_count: 100
  bm25_candidate_count: 30
  query_attribute_min_confidence: 0.4
  query_attribute_llm_enabled: true

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

# Language routing (local LLM handles these language codes; others fall back to cloud)
languages:
  supported_local:
    - en
    - ja
    - es
  fallback_strategy: cloud
```

`languages.supported_local` に含まれない言語が検知されると、`fallback_strategy` に従ってクラウド LLM へルーティングされます。短期的に特定言語を強制したい場合は MCP サーバーを起動するシェルで環境変数 `CONTEXT_ORCHESTRATOR_LANG_OVERRIDE` を設定してください。

```powershell
$env:CONTEXT_ORCHESTRATOR_LANG_OVERRIDE = "fr"
python -m src.main  # 以降の要約はフランス語扱いで routing
```

### Cross-Encoder Reranker Cache

- `search.cross_encoder_cache_size` / `search.cross_encoder_cache_ttl_seconds` で LRU キャッシュの容量と保持期間（秒）を制御できます。
- `python -m scripts.mcp_replay` を実行すると、キャッシュヒット率や LLM レイテンシが “Reranker Metrics” として表示され、`reports/mcp_runs/*.jsonl` にも保存されます。
- MCP 経由で `{"jsonrpc":"2.0","id":1,"method":"get_reranker_metrics","params":{}}` を呼び出すと、現在のキャッシュ統計をオンデマンドで取得できます。
- `--export-features <path>` を付けてリプレイすると、各検索結果の rerank 特徴量が CSV に出力され、後述の重み学習スクリプトに渡せます。

### Rerank Weight Training

1. `python -m scripts.mcp_replay --requests tests/scenarios/query_runs.json --export-features reports/features.csv`
2. `python -m scripts.train_rerank_weights --features reports/features.csv --config config.yaml`
3. `python -m scripts.run_regression_ci` を再実行して Precision/NDCG を確認し、必要に応じて `reranking_weights` や `search.cross_encoder_cache_*` を調整してください。

クラウド側へのフォールバックが発生すると `Language routing fallback (lang=...)` ログにレイテンシ（ミリ秒）と成否が出力されます。`python -m scripts.run_regression_ci` や平常運用中に `logs/context_orchestrator.log` を tail しておけば、遅延や失敗回数を継続的にモニタリングできます。


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

### Performance Profiling

Run performance benchmarks to validate system performance:

```bash
# Run all benchmarks
python scripts/performance_profiler.py

# Custom run count
python scripts/performance_profiler.py --runs 200

# Save report to custom location
python scripts/performance_profiler.py --output ./perf_report.json
```

The profiler measures:
- **Search Latency**: P50/P95/P99 latencies with target ≤200ms
- **Ingestion Throughput**: Conversations per second, target <5s/conversation
- **Consolidation Time**: Extrapolated time for 10K memories, target <5 minutes
- **Memory Footprint**: Peak and resident memory usage

Reports are saved as JSON with pass/fail indicators for each target.

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
- ✅ **Phase 14**: Integration & Optimization - **COMPLETE**
  - End-to-end validation tests
  - Performance profiling tool
  - Enhanced error handling and structured logging

**Current Status**: Production Ready

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

### Regression Replay Check

Run this guard whenever retrieval, QAM, or memory code changes:

```bash
python -m scripts.run_regression_ci
```

This helper wraps `scripts.mcp_replay` against the canonical baseline (`reports/baselines/mcp_run-20251109-143546.jsonl`), saves the latest log under `reports/mcp_runs/`, and fails if either condition is met:

- Macro Precision or Macro NDCG drops by more than 0.02 versus the baseline.
- `reports/mcp_runs/zero_hits.json` records any zero-hit queries (indicates missing dictionary/metadata entries).

Override `--baseline`, `--requests`, or `--output` when adding new scenarios, and commit refreshed baselines once metrics improve. For CI, activate `.venv311` then add a step such as `python -m scripts.run_regression_ci`; no extra services are required because the script launches the MCP server via `scripts.mcp_stdio`.

## Support

- **Issues**: [GitHub Issues](https://github.com/myo-ojin/llm-brain/issues)
- **Documentation**: [CLAUDE.md](CLAUDE.md)
- **Test Results**: [INTEGRATION_TEST_RESULTS.md](INTEGRATION_TEST_RESULTS.md)
