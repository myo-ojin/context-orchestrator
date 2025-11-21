#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Refresh Memory Embeddings - Backfill Script

Re-generates enriched summaries and embeddings for existing memory entries.
This is part of Phase 2: Memory Representation Refresh.

Usage:
    python scripts/refresh_memory_embeddings.py [--dry-run] [--limit N]

Requirements: Phase 2 - Memory Representation Refresh
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.ingestion import IngestionService
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index
from src.models.router import ModelRouter
from src.models.local_llm import LocalLLMClient
from src.models.cli_llm import CLILLMClient
from src.processing.indexer import Indexer
from src.processing.chunker import Chunker
from src.processing.classifier import SchemaClassifier
from src.config import load_config

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def refresh_embeddings(dry_run: bool = False, limit: int = None) -> dict:
    """
    Refresh enriched summaries and embeddings for existing memory entries

    Args:
        dry_run: If True, only show what would be done without actually updating
        limit: Maximum number of entries to refresh (None = all)

    Returns:
        Statistics dictionary
    """
    print("=" * 70)
    print("Memory Embeddings Refresh - Phase 2")
    print("=" * 70)
    print()

    # Load configuration
    config = load_config()

    # Initialize components
    local_llm = LocalLLMClient(
        ollama_url=config.ollama.url,
        embedding_model=config.ollama.embedding_model,
        inference_model=config.ollama.inference_model
    )

    cli_llm = CLILLMClient(
        cli_command=config.cli.command
    )

    model_router = ModelRouter(
        local_llm_client=local_llm,
        cli_llm_client=cli_llm
    )

    chroma_dir = Path(config.data_dir).expanduser() / "chroma_db"
    vector_db = ChromaVectorDB(persist_directory=str(chroma_dir))

    bm25_path = Path(config.data_dir).expanduser() / "bm25_index.pkl"
    bm25_index = BM25Index(persist_path=str(bm25_path))

    chunker = Chunker()  # Use default max_tokens
    classifier = SchemaClassifier(model_router=model_router)

    indexer = Indexer(
        vector_db=vector_db,
        bm25_index=bm25_index,
        model_router=model_router
    )

    ingestion_service = IngestionService(
        model_router=model_router,
        chunker=chunker,
        indexer=indexer,
        classifier=classifier,
        vector_db=vector_db
    )

    # Statistics
    stats = {
        'total_entries': 0,
        'refreshed': 0,
        'skipped': 0,
        'errors': 0,
        'start_time': datetime.utcnow()
    }

    try:
        # Query all memory metadata entries
        print("Fetching existing memory entries...")

        # Get all documents with is_memory_entry=True
        results = vector_db.collection.get(
            where={"is_memory_entry": True},
            include=['metadatas', 'documents', 'embeddings']
        )

        if not results['ids']:
            print("[WARN] No memory entries found in database")
            return stats

        stats['total_entries'] = len(results['ids'])
        print(f"Found {stats['total_entries']} memory entries")
        print()

        # Apply limit if specified
        entries_to_process = stats['total_entries']
        if limit:
            entries_to_process = min(limit, stats['total_entries'])
            print(f"[INFO] Limiting to {entries_to_process} entries (--limit {limit})")
            print()

        # Process each memory entry
        for i in range(entries_to_process):
            entry_id = results['ids'][i]
            metadata = results['metadatas'][i]
            document = results['documents'][i]

            memory_id = metadata.get('memory_id')

            print(f"[{i+1}/{entries_to_process}] Processing {memory_id}...")

            try:
                # Get the full memory object (includes content from chunks)
                memory = ingestion_service.get_memory(memory_id)

                if not memory:
                    print(f"  [SKIP] Memory not found: {memory_id}")
                    stats['skipped'] += 1
                    continue

                # Build enriched summary
                enriched_summary = ingestion_service._build_enriched_summary(memory)

                print(f"  Original: {document[:80]}...")
                print(f"  Enriched: {enriched_summary[:80]}...")

                if dry_run:
                    print(f"  [DRY-RUN] Would update embedding for {memory_id}")
                    stats['refreshed'] += 1
                else:
                    # Generate new embedding for enriched summary
                    new_embedding = model_router.generate_embedding(enriched_summary)

                    # Update the entry in vector DB
                    metadata['enriched_summary'] = enriched_summary

                    vector_db.collection.update(
                        ids=[entry_id],
                        embeddings=[new_embedding],
                        metadatas=[metadata],
                        documents=[enriched_summary]
                    )

                    print(f"  [SUCCESS] Updated {memory_id}")
                    stats['refreshed'] += 1

            except Exception as e:
                print(f"  [ERROR] Failed to process {memory_id}: {e}")
                stats['errors'] += 1
                logger.error(f"Error processing {memory_id}", exc_info=True)

            print()

    except Exception as e:
        print(f"[ERROR] Failed to refresh embeddings: {e}")
        logger.error("Refresh failed", exc_info=True)
        stats['errors'] += 1

    finally:
        stats['end_time'] = datetime.utcnow()
        stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()

    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total entries: {stats['total_entries']}")
    print(f"Refreshed: {stats['refreshed']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print(f"Duration: {stats['duration_seconds']:.2f} seconds")

    if dry_run:
        print()
        print("[DRY-RUN] No changes were made. Run without --dry-run to apply updates.")

    print("=" * 70)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Refresh enriched summaries and embeddings for existing memories'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of entries to process (for testing)'
    )
    args = parser.parse_args()

    stats = refresh_embeddings(dry_run=args.dry_run, limit=args.limit)

    # Exit with error code if there were errors
    if stats['errors'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
