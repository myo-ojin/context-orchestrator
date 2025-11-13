#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnostic script to inspect actual memory content in ChromaDB
"""

import sys
sys.path.insert(0, 'src')

from src.storage.vector_db import ChromaVectorDB
from pathlib import Path

def inspect_memory_content():
    """Check what content is stored in memories"""

    # Initialize vector DB
    data_dir = Path.home() / ".context-orchestrator"
    vector_db = ChromaVectorDB(
        persist_directory=str(data_dir / "chroma_db"),
        collection_name="memories"
    )

    print("=" * 80)
    print("MEMORY CONTENT INSPECTION")
    print("=" * 80)
    print(f"Total memories: {vector_db.count()}\n")

    # Get a few memory entries from the project
    memories = vector_db.list_by_metadata(
        filter_metadata={
            'project_id': 'project-appbrain',
            'is_memory_entry': True
        },
        include_documents=True,
        include_embeddings=False
    )

    if not memories:
        print("No project-appbrain memories found!")
        return

    print(f"Found {len(memories)} memories for project-appbrain\n")

    # Inspect first 5 memories
    for i, memory in enumerate(memories[:5], 1):
        print(f"[Memory {i}]")
        print(f"ID: {memory['id']}")

        metadata = memory.get('metadata', {})
        print(f"Schema: {metadata.get('schema_type', 'unknown')}")
        print(f"Created: {metadata.get('created_at', 'unknown')}")

        content = memory.get('content', '')
        print(f"Content length: {len(content)} chars")
        print(f"Content preview (first 200 chars):")
        print(content[:200])
        print(f"...")
        print()

        # Check if content is too short or generic
        if len(content) < 50:
            print("[WARNING] Content is very short! This may cause low similarity.")

        print("-" * 80)
        print()

if __name__ == "__main__":
    inspect_memory_content()
