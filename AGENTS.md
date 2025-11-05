# Repository Guidelines

## Project Structure & Module Organization
This repository currently ships the product specification in `.kiro/specs/dev-knowledge-orchestrator/`; treat those markdown files as canonical requirements. Implement runtime code in a top-level `src/` package once you scaffold the project. Recommended layout:
- `src/mcp_server.py` for the Model Context Protocol entry point.
- `src/services/` for ingestion, search, consolidation, and automation watchers.
- `src/processing/` for schema classification, chunking, and indexing utilities.
- `src/storage/` for vector and BM25 adapters.
- `tests/unit/`, `tests/integration/`, and `scripts/` for fixtures, end-to-end flows, and operational tooling.
Keep configuration (`config.yaml`) and dependency manifests (`requirements.txt`, `pyproject.toml` or `setup.py`) at the root, aligned with the tasks roadmap.

## Build, Test, and Development Commands
Target Python 3.11+. Typical setup:
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Run `pytest` for the whole suite or `pytest tests/unit/processing/test_chunker.py` for focused checks. Once health tooling exists, execute `python -m scripts.doctor`. During feature work, use `python -m src.cli status` (or equivalent entry point) to verify MCP wiring before pushing.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation, explicit type hints, and descriptive snake_case for functions and modules; use PascalCase for classes. Document public APIs with Google-style docstrings and reference requirement IDs (e.g., `Req-03`) where relevant. Enforce formatting with `black .`, lint with `ruff .`, and run `mypy src` before opening a PR.

## Testing Guidelines
Adopt pytest with `tests/unit` mirroring the `src` tree and `tests/integration` covering ingestion -> search -> recall flows. Name files `test_<component>.py` and functions `test_<behavior>_<expectation>`. Maintain >=85% statement coverage (`pytest --cov=src`) and store deterministic conversation fixtures under `tests/fixtures/`.

## Commit & Pull Request Guidelines
Use Conventional Commits (`feat: ingest pipeline`, `fix: bm25 config`). Reference the relevant requirement numbers or design sections in the body and note updates to `.kiro/specs`. Pull requests should include a purpose summary, key changes, verification steps (command output or screenshots), and links to tracking issues.

## Documentation & Knowledge Base
Keep the spec set in `.kiro/specs/dev-knowledge-orchestrator/` synchronized with implementation decisions. Update README onboarding steps whenever dependencies or commands change, and refresh this guide when new agent workflows or automation scripts are added.
