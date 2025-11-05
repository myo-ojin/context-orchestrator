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
        print(f"Data Directory: {config.data_dir}")

        # Check Chroma DB
        chroma_path = Path(config.data_dir) / 'chroma_db'
        if chroma_path.exists():
            try:
                vector_db = ChromaVectorDB(
                    collection_name='context_orchestrator',
                    persist_directory=str(chroma_path)
                )
                count = vector_db.collection.count()
                print(f"Vector DB: {count} items")
            except Exception as e:
                print(f"Vector DB: Error ({e})")
        else:
            print("Vector DB: Not initialized")

        # Check session logs
        log_dir = Path(config.logging.session_log_dir)
        if log_dir.exists():
            log_files = list(log_dir.glob('*.log'))
            print(f"Session Logs: {len(log_files)} files")
        else:
            print("Session Logs: Not initialized")

        print()

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
        print("Running memory consolidation...")
        print("(This is not implemented yet - use MCP tool 'consolidate_memories')")
        print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
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
    """Export memories"""
    print("Export command not implemented yet")


def cmd_import(args):
    """Import memories"""
    print("Import command not implemented yet")


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
