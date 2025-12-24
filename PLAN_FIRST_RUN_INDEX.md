# Plan: First-Run Log Indexing & Autostart Flow

## Goals
- On first run, optionally index all existing session logs into vector/BM25 stores, then never prompt again unless user triggers a manual reindex.
- Keep day‑to‑day startup simple (fits into upcoming `context-orchestrator start` flow).
- Provide safe defaults: size limits, ignore patterns, resumable progress, clear user prompt.

## Non-Goals
- Full project/repo crawling (handled separately).
- UI/UX changes on MCP client side.

## Tasks (ordered)
1) Add first-run flag check (e.g., `data_dir/first_run_index_done`) early in `src/main.py` startup path.
2) Implement prompt + dry run: count candidate log files, total bytes, estimated time; abort cleanly if user declines.
3) Build log indexer helper (walk `session_log_dir`, apply ignore list and size cap, hash/mtime tracking for resume).
4) Pipe parsed logs through existing `IngestionService/Indexer`; batch commits to avoid OOM and show progress.
5) Write flag on success; on partial failure, record checkpoint file so next start resumes remaining files.
6) Add config knobs (max file MB, allowed extensions, prompt timeout/auto-yes) with sensible defaults.
7) Tests: temp log dir, mixed sizes, resume after forced interrupt, skip when flag exists.
8) Docs: README/QUICKSTART one-liner about first-run indexing; note manual `co reindex` (future) hook.
9) Docs (MCP接続手順): README に「代表的な MCP クライアントへの登録方法」を追加（Claude Desktop/Web, mcp-shell, VS Code/Cursor）。venv 利用時の python パス指定例と CWD 設定を明記。

## Open Questions (resolved)
- Non-interactive stdin (CI/mcp-shell): default to **skip**; allow opt-in auto-run via env `CO_FIRST_RUN_AUTO=1`.
- Progress tracking: default to **mtime + size** for speed; optional hash check behind flag `--verify-hash` (or config) if needed.
- Progress UI: emit INFO logs to stdout every ~5s like `indexing 12/120 files (24 MB)...`; clear start/complete/abort messages.
