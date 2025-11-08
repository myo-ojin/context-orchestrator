#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Utility helpers to retag memories into a different hierarchy tier."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from src.config import load_config
from src.storage.vector_db import ChromaVectorDB
from src.utils.logger import setup_root_logger


def _normalize_id(raw_id: str) -> str:
    """Ensure we point at the metadata record stored in Chroma."""
    return raw_id if raw_id.endswith("-metadata") else f"{raw_id}-metadata"


def _update_memory_type(vector_db: ChromaVectorDB, entry_id: str, target_type: str) -> bool:
    """Fetch the metadata entry, mutate the tier, and persist."""
    record = vector_db.get(entry_id)
    if record is None:
        print(f"[!] Memory not found: {entry_id}")
        return False

    metadata = dict(record.get("metadata") or {})
    metadata["memory_type"] = target_type
    metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
    vector_db.update_metadata(entry_id, metadata)
    print(f"[+] Updated {entry_id} -> {target_type}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manually set the memory_type field for specific memories."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--memory-type",
        required=True,
        choices=["working", "short_term", "long_term"],
        help="Target tier to apply.",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        required=True,
        help="Memory IDs (with or without the -metadata suffix).",
    )
    args = parser.parse_args()

    setup_root_logger("INFO")
    config = load_config(args.config)
    vector_db = ChromaVectorDB(
        collection_name="context_orchestrator",
        persist_directory=str(Path(config.data_dir) / "chroma_db"),
    )

    all_ok = True
    for raw_id in args.ids:
        entry_id = _normalize_id(raw_id)
        ok = _update_memory_type(vector_db, entry_id, args.memory_type)
        all_ok = all_ok and ok

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
