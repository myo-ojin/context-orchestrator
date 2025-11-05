#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CLI Interface

Command-line interface for Context Orchestrator management.

Requirements: Requirement 13, 26 (CLI Interface, Session Logging)
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Optional
import argparse

from src.config import load_config
from src.utils.logger import setup_logger, get_logger
from src.storage.vector_db import ChromaVectorDB
from src.services.session_log_collector import SessionLogCollector
from src.services.session_summary import SessionSummaryWorker
from src.models.router import ModelRouter
from src.models.local_llm import LocalLLMClient
from src.models.cli_llm import CLILLMClient

logger = get_logger(__name__)


def cmd_status(args):
    """Show system status"""
    try:
        config = load_config(args.config)

        print("=" * 60)
        print("Context Orchestrator Status")
        print("=" * 60)
        print()

        # Data directory
        print(f"📁 Data Directory: {config.data_dir}")
        data_dir_exists = Path(config.data_dir).exists()
        print(f"   Status: {'✓ Exists' if data_dir_exists else '✗ Not found'}")
        print()

        # Check Ollama connection
        print("🤖 Ollama:")
        try:
            local_llm = LocalLLMClient(
                ollama_url=config.ollama.url,
                embedding_model=config.ollama.embedding_model,
                inference_model=config.ollama.inference_model
            )
            print(f"   URL: {config.ollama.url}")
            print(f"   Status: ✓ Connected")

            # Check models
            print(f"   Embedding Model: {config.ollama.embedding_model}")
            print(f"   Inference Model: {config.ollama.inference_model}")
        except Exception as e:
            print(f"   URL: {config.ollama.url}")
            print(f"   Status: ✗ Failed ({str(e)[:50]}...)")
        print()

        # Check Chroma DB
        print("💾 Vector Database:")
        chroma_path = Path(config.data_dir) / 'chroma_db'
        if chroma_path.exists():
            try:
                vector_db = ChromaVectorDB(
                    collection_name='context_orchestrator',
                    persist_directory=str(chroma_path)
                )
                count = vector_db.collection.count()
                print(f"   Path: {chroma_path}")
                print(f"   Status: ✓ Initialized")
                print(f"   Memories: {count} items")
            except Exception as e:
                print(f"   Path: {chroma_path}")
                print(f"   Status: ✗ Error ({e})")
        else:
            print(f"   Path: {chroma_path}")
            print(f"   Status: ✗ Not initialized")
        print()

        # Check BM25 Index
        print("🔍 BM25 Index:")
        bm25_path = Path(config.data_dir) / 'bm25_index.pkl'
        if bm25_path.exists():
            size_kb = bm25_path.stat().st_size / 1024
            print(f"   Path: {bm25_path}")
            print(f"   Status: ✓ Exists ({size_kb:.1f} KB)")
        else:
            print(f"   Path: {bm25_path}")
            print(f"   Status: ✗ Not initialized")
        print()

        # Check session logs
        print("📝 Session Logs:")
        log_dir = Path(config.logging.session_log_dir)
        if log_dir.exists():
            log_files = list(log_dir.glob('*.log'))
            total_size = sum(f.stat().st_size for f in log_files) / 1024 / 1024  # MB
            print(f"   Directory: {log_dir}")
            print(f"   Status: ✓ Initialized")
            print(f"   Files: {len(log_files)} sessions ({total_size:.2f} MB)")
        else:
            print(f"   Directory: {log_dir}")
            print(f"   Status: ✗ Not initialized")
        print()

        # Check Obsidian integration
        print("📓 Obsidian Integration:")
        if config.obsidian_vault_path:
            vault_path = Path(config.obsidian_vault_path)
            if vault_path.exists():
                md_files = list(vault_path.rglob('*.md'))
                print(f"   Vault: {vault_path}")
                print(f"   Status: ✓ Connected")
                print(f"   Notes: {len(md_files)} markdown files")
            else:
                print(f"   Vault: {vault_path}")
                print(f"   Status: ✗ Not found")
        else:
            print(f"   Status: Not configured")
        print()

        # Check consolidation
        print("🌙 Consolidation:")
        last_consolidation_file = Path(config.data_dir) / 'last_consolidation'
        if last_consolidation_file.exists():
            try:
                import datetime
                last_time_str = last_consolidation_file.read_text(encoding='utf-8').strip()
                last_time = datetime.datetime.fromisoformat(last_time_str)
                time_since = datetime.datetime.now() - last_time
                hours_since = time_since.total_seconds() / 3600

                print(f"   Last run: {last_time.strftime('%Y-%m-%d %H:%M:%S')} ({hours_since:.1f}h ago)")
                print(f"   Schedule: {config.consolidation.schedule}")
                print(f"   Status: {'✓ Up to date' if hours_since < 24 else '⚠ Overdue'}")
            except Exception as e:
                print(f"   Status: ✗ Error reading timestamp")
        else:
            print(f"   Status: Never run")
            print(f"   Schedule: {config.consolidation.schedule}")
        print()

        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_doctor(args):
    """Run health check"""
    try:
        # Run doctor script
        doctor_script = Path(__file__).parent.parent / 'scripts' / 'doctor.py'

        result = subprocess.run(
            [sys.executable, str(doctor_script)],
            capture_output=False
        )

        sys.exit(result.returncode)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_consolidate(args):
    """Run memory consolidation"""
    try:
        from src.storage.bm25_index import BM25Index
        from src.processing.indexer import Indexer
        from src.services.consolidation import ConsolidationService

        config = load_config(args.config)

        print("=" * 60)
        print("Memory Consolidation")
        print("=" * 60)
        print()

        # Initialize storage
        chroma_path = Path(config.data_dir) / 'chroma_db'
        bm25_path = Path(config.data_dir) / 'bm25_index.pkl'

        if not chroma_path.exists():
            print("Error: Vector database not initialized")
            print("Run the system at least once to initialize storage.")
            sys.exit(1)

        print("Initializing storage...")
        vector_db = ChromaVectorDB(
            collection_name='context_orchestrator',
            persist_directory=str(chroma_path)
        )

        bm25_index = BM25Index(persist_path=str(bm25_path))

        # Initialize model router
        print("Initializing models...")
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

        # Initialize indexer
        indexer = Indexer(
            vector_db=vector_db,
            bm25_index=bm25_index,
            model_router=model_router
        )

        # Initialize consolidation service
        print("Initializing consolidation service...")
        consolidation_service = ConsolidationService(
            vector_db=vector_db,
            indexer=indexer,
            model_router=model_router,
            similarity_threshold=config.clustering.similarity_threshold,
            min_cluster_size=config.clustering.min_cluster_size,
            age_threshold_days=config.forgetting.age_threshold_days,
            importance_threshold=config.forgetting.importance_threshold,
            working_memory_retention_hours=config.working_memory.retention_hours
        )

        print()
        print("Running consolidation...")
        stats = consolidation_service.consolidate()

        print()
        print("=" * 60)
        print("Consolidation Results")
        print("=" * 60)
        print()
        print(f"Migrated Working Memories: {stats.get('migrated_working', 0)}")
        print(f"Clusters Created: {stats.get('clusters_created', 0)}")
        print(f"Memories Compressed: {stats.get('compressed', 0)}")
        print(f"Memories Deleted: {stats.get('deleted', 0)}")
        print()

        # Update last consolidation timestamp
        last_consolidation_file = Path(config.data_dir) / 'last_consolidation'
        from datetime import datetime
        last_consolidation_file.write_text(datetime.now().isoformat(), encoding='utf-8')

        print("✓ Consolidation completed successfully")
        print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_list_recent(args):
    """List recent memories"""
    try:
        config = load_config(args.config)

        chroma_path = Path(config.data_dir) / 'chroma_db'

        if not chroma_path.exists():
            print("No memories found (database not initialized)")
            return

        vector_db = ChromaVectorDB(
            collection_name='context_orchestrator',
            persist_directory=str(chroma_path)
        )

        # Get recent memories
        results = vector_db.list_by_metadata(
            {'is_memory_entry': True},
            include_documents=True
        )

        # Sort by timestamp (newest first)
        results_sorted = sorted(
            results,
            key=lambda x: x.get('metadata', {}).get('timestamp', ''),
            reverse=True
        )

        # Limit
        results_limited = results_sorted[:args.limit]

        print("=" * 60)
        print(f"Recent Memories (showing {len(results_limited)} of {len(results_sorted)})")
        print("=" * 60)
        print()

        for item in results_limited:
            memory_id = item.get('id', 'unknown')
            metadata = item.get('metadata', {})
            content = item.get('content', '')

            schema_type = metadata.get('schema_type', 'Unknown')
            timestamp = metadata.get('timestamp', 'Unknown')

            print(f"ID: {memory_id}")
            print(f"Type: {schema_type}")
            print(f"Time: {timestamp}")
            print(f"Summary: {content[:100]}...")
            print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_session_history(args):
    """Show session history"""
    try:
        config = load_config(args.config)

        log_dir = Path(config.logging.session_log_dir)

        if not log_dir.exists():
            print("No session logs found")
            return

        # If session_id provided
        if args.session_id:
            session_id = args.session_id

            # Get log file
            log_file = log_dir / f"{session_id}.log"

            if not log_file.exists():
                print(f"Session not found: {session_id}")
                sys.exit(1)

            # Show summary only
            if args.summary_only:
                chroma_path = Path(config.data_dir) / 'chroma_db'

                if chroma_path.exists():
                    vector_db = ChromaVectorDB(
                        collection_name='context_orchestrator',
                        persist_directory=str(chroma_path)
                    )

                    result = vector_db.get(f"{session_id}-summary")

                    if result:
                        print("=" * 60)
                        print(f"Session Summary: {session_id}")
                        print("=" * 60)
                        print()
                        print(result.get('content', 'No summary'))
                        print()
                    else:
                        print(f"No summary found for session: {session_id}")
                else:
                    print("Database not initialized")

            # Open in editor
            elif args.open:
                if os.name == 'nt':  # Windows
                    os.startfile(log_file)
                elif os.name == 'posix':  # Unix/Linux/Mac
                    editor = os.environ.get('EDITOR', 'nano')
                    subprocess.run([editor, str(log_file)])

            # Show raw log
            else:
                print("=" * 60)
                print(f"Session Log: {session_id}")
                print("=" * 60)
                print()

                content = log_file.read_text(encoding='utf-8')
                print(content)

        # List all sessions
        else:
            log_files = sorted(log_dir.glob('*.log'), key=lambda p: p.stat().st_mtime, reverse=True)

            print("=" * 60)
            print(f"Session Logs ({len(log_files)} sessions)")
            print("=" * 60)
            print()

            for log_file in log_files[:args.limit]:
                session_id = log_file.stem
                size_kb = log_file.stat().st_size / 1024
                mtime = log_file.stat().st_mtime

                import datetime
                mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

                print(f"{session_id:<30} {size_kb:>8.1f} KB  {mtime_str}")

            print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_export(args):
    """Export memories to JSON file"""
    try:
        config = load_config(args.config)

        print("=" * 60)
        print("Export Memories")
        print("=" * 60)
        print()

        # Check if database exists
        chroma_path = Path(config.data_dir) / 'chroma_db'

        if not chroma_path.exists():
            print("Error: Vector database not initialized")
            print("No memories to export.")
            sys.exit(1)

        print("Loading memories from database...")
        vector_db = ChromaVectorDB(
            collection_name='context_orchestrator',
            persist_directory=str(chroma_path)
        )

        # Get all memories
        all_results = vector_db.collection.get(
            include=['documents', 'metadatas', 'embeddings']
        )

        if not all_results or not all_results['ids']:
            print("No memories found to export.")
            return

        # Build export data
        export_data = {
            'version': '1.0',
            'exported_at': json.dumps(Path(config.data_dir).as_posix()),
            'total_memories': len(all_results['ids']),
            'memories': []
        }

        for i, memory_id in enumerate(all_results['ids']):
            memory_data = {
                'id': memory_id,
                'content': all_results['documents'][i] if all_results['documents'] else None,
                'metadata': all_results['metadatas'][i] if all_results['metadatas'] else {},
                'embedding': all_results['embeddings'][i] if all_results['embeddings'] else None
            }
            export_data['memories'].append(memory_data)

        # Write to file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        size_mb = output_path.stat().st_size / 1024 / 1024

        print(f"✓ Exported {len(all_results['ids'])} memories")
        print(f"✓ Output file: {output_path}")
        print(f"✓ File size: {size_mb:.2f} MB")
        print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_import(args):
    """Import memories from JSON file"""
    try:
        from src.storage.bm25_index import BM25Index

        config = load_config(args.config)

        print("=" * 60)
        print("Import Memories")
        print("=" * 60)
        print()

        # Check input file
        input_path = Path(args.input)

        if not input_path.exists():
            print(f"Error: Input file not found: {input_path}")
            sys.exit(1)

        # Load import data
        print("Loading import file...")
        with open(input_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)

        if 'memories' not in import_data:
            print("Error: Invalid import file format (missing 'memories' key)")
            sys.exit(1)

        memories = import_data['memories']

        print(f"Found {len(memories)} memories in import file")
        print()

        # Initialize storage
        chroma_path = Path(config.data_dir) / 'chroma_db'
        bm25_path = Path(config.data_dir) / 'bm25_index.pkl'

        chroma_path.parent.mkdir(parents=True, exist_ok=True)

        print("Initializing storage...")
        vector_db = ChromaVectorDB(
            collection_name='context_orchestrator',
            persist_directory=str(chroma_path)
        )

        bm25_index = BM25Index(persist_path=str(bm25_path))

        # Import memories
        print("Importing memories...")
        imported_count = 0
        skipped_count = 0

        for memory in memories:
            memory_id = memory.get('id')
            content = memory.get('content')
            metadata = memory.get('metadata', {})
            embedding = memory.get('embedding')

            if not memory_id or not content:
                skipped_count += 1
                continue

            try:
                # Check if memory already exists
                existing = vector_db.get(memory_id)

                if existing and not args.force:
                    skipped_count += 1
                    continue

                # Add to vector DB
                vector_db.add(
                    ids=[memory_id],
                    documents=[content],
                    metadatas=[metadata],
                    embeddings=[embedding] if embedding else None
                )

                # Add to BM25 index
                bm25_index.add_document(
                    doc_id=memory_id,
                    text=content
                )

                imported_count += 1

            except Exception as e:
                logger.error(f"Failed to import memory {memory_id}: {e}")
                skipped_count += 1

        # Save BM25 index
        bm25_index._save()

        print()
        print("=" * 60)
        print("Import Results")
        print("=" * 60)
        print()
        print(f"✓ Imported: {imported_count} memories")
        print(f"⊘ Skipped: {skipped_count} memories")
        print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Context Orchestrator CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        help='Path to config file'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # status command
    parser_status = subparsers.add_parser('status', help='Show system status')
    parser_status.set_defaults(func=cmd_status)

    # doctor command
    parser_doctor = subparsers.add_parser('doctor', help='Run health check')
    parser_doctor.set_defaults(func=cmd_doctor)

    # consolidate command
    parser_consolidate = subparsers.add_parser('consolidate', help='Run memory consolidation')
    parser_consolidate.set_defaults(func=cmd_consolidate)

    # list-recent command
    parser_list = subparsers.add_parser('list-recent', help='List recent memories')
    parser_list.add_argument('--limit', type=int, default=20, help='Number of memories to show')
    parser_list.set_defaults(func=cmd_list_recent)

    # session-history command
    parser_session = subparsers.add_parser('session-history', help='Show session history')
    parser_session.add_argument('--session-id', help='Session ID to show')
    parser_session.add_argument('--open', action='store_true', help='Open log in editor')
    parser_session.add_argument('--summary-only', action='store_true', help='Show summary only')
    parser_session.add_argument('--limit', type=int, default=20, help='Number of sessions to list')
    parser_session.set_defaults(func=cmd_session_history)

    # export command
    parser_export = subparsers.add_parser('export', help='Export memories')
    parser_export.add_argument('--output', required=True, help='Output file path')
    parser_export.set_defaults(func=cmd_export)

    # import command
    parser_import = subparsers.add_parser('import', help='Import memories')
    parser_import.add_argument('--input', required=True, help='Input file path')
    parser_import.add_argument('--force', action='store_true', help='Overwrite existing memories')
    parser_import.set_defaults(func=cmd_import)

    # Parse args
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run command
    args.func(args)


if __name__ == '__main__':
    main()
