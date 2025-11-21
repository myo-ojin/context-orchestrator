#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Codex Session Ingestor

Scans Codex session logs and ingests them into Context Orchestrator.
Implements differential processing to avoid duplicate ingestion.

Phase 2 Implementation for Issue #2025-11-15-01
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import argparse
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config
from src.utils.logger import setup_logger, get_logger

# Import MCP client
try:
    from scripts.mcp_client import MCPClient
except ImportError:
    # Fallback if running from different location
    sys.path.insert(0, str(Path(__file__).parent))
    from mcp_client import MCPClient

logger = get_logger(__name__)


class CodexSessionIngestor:
    """
    Ingests Codex session logs into Context Orchestrator.

    Features:
    - Scans %USERPROFILE%/.codex/sessions/**/rollout-*.jsonl
    - Filters by session_meta.cwd (current repository only)
    - Differential processing using SQLite (session_id, line_number)
    - Sends to Context Orchestrator via MCP RPC
    """

    def __init__(
        self,
        config,
        current_cwd: str,
        state_db_path: Optional[str] = None,
        orchestrator_path: Optional[str] = None
    ):
        """
        Initialize Codex session ingestor.

        Args:
            config: Configuration object
            current_cwd: Current working directory to filter sessions
            state_db_path: Path to SQLite state database (default: data_dir/codex_ingest_state.db)
            orchestrator_path: Path to Context Orchestrator main.py (default: src/main.py)
        """
        self.config = config
        self.current_cwd = Path(current_cwd).resolve()

        # Codex session directory
        self.codex_home = Path(os.environ.get('USERPROFILE', '~')).expanduser() / '.codex'
        self.sessions_dir = self.codex_home / 'sessions'

        # State database
        if state_db_path:
            self.state_db_path = Path(state_db_path)
        else:
            self.state_db_path = Path(config.data_dir) / 'codex_ingest_state.db'

        # MCP orchestrator path
        if orchestrator_path:
            self.orchestrator_path = orchestrator_path
        else:
            # Default to src/main.py in current project
            self.orchestrator_path = str(Path(__file__).parent.parent / 'src' / 'main.py')

        self._init_state_db()

        logger.info(f"Initialized CodexSessionIngestor: cwd={self.current_cwd}, sessions_dir={self.sessions_dir}")

    def _init_state_db(self):
        """Initialize SQLite state database for tracking processed logs."""
        self.state_db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_logs (
                session_id TEXT,
                line_number INTEGER,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, line_number)
            )
        """)

        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id
            ON processed_logs(session_id)
        """)

        conn.commit()
        conn.close()

        logger.debug(f"State database initialized: {self.state_db_path}")

    def is_processed(self, session_id: str, line_number: int) -> bool:
        """
        Check if a log line has been processed.

        Args:
            session_id: Codex session ID
            line_number: Line number in JSONL file

        Returns:
            True if already processed
        """
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM processed_logs WHERE session_id = ? AND line_number = ?",
            (session_id, line_number)
        )

        result = cursor.fetchone() is not None
        conn.close()

        return result

    def mark_processed(self, session_id: str, line_number: int):
        """
        Mark a log line as processed.

        Args:
            session_id: Codex session ID
            line_number: Line number in JSONL file
        """
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO processed_logs (session_id, line_number) VALUES (?, ?)",
            (session_id, line_number)
        )

        conn.commit()
        conn.close()

    def scan_sessions(self) -> List[Path]:
        """
        Scan Codex sessions directory for rollout JSONL files.

        Returns:
            List of session file paths matching current repository
        """
        if not self.sessions_dir.exists():
            logger.warning(f"Codex sessions directory not found: {self.sessions_dir}")
            return []

        # Find all rollout-*.jsonl files
        all_session_files = list(self.sessions_dir.glob('**/rollout-*.jsonl'))

        logger.info(f"Found {len(all_session_files)} Codex session files")

        # Filter by cwd
        matched_files = []
        for file_path in all_session_files:
            try:
                session_meta = self._extract_session_meta(file_path)
                if session_meta:
                    session_cwd = Path(session_meta.get('cwd', '')).resolve()

                    if session_cwd == self.current_cwd:
                        matched_files.append(file_path)
                        logger.debug(f"Matched session: {file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")

        logger.info(f"Matched {len(matched_files)} sessions for cwd={self.current_cwd}")

        return matched_files

    def _extract_session_meta(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Extract session_meta from first line of JSONL file.

        Args:
            file_path: Path to rollout-*.jsonl file

        Returns:
            session_meta payload or None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                record = json.loads(first_line)

                if record.get('type') == 'session_meta':
                    return record.get('payload', {})
        except Exception as e:
            logger.debug(f"Failed to extract session_meta from {file_path}: {e}")

        return None

    def parse_session_file(self, file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse a Codex session JSONL file and extract conversation events.

        Args:
            file_path: Path to rollout-*.jsonl file

        Returns:
            (session_id, list of events)
            Events have format: {
                'line_number': int,
                'timestamp': str,
                'role': 'user' | 'assistant',
                'content': str,
                'metadata': dict
            }
        """
        events = []
        session_id = None

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, start=1):
                try:
                    record = json.loads(line)
                    record_type = record.get('type')

                    # Extract session_id from session_meta
                    if record_type == 'session_meta':
                        payload = record.get('payload', {})
                        session_id = payload.get('id')
                        logger.debug(f"Found session_id: {session_id}")
                        continue

                    # Extract response_item (user/assistant messages)
                    if record_type == 'response_item':
                        timestamp = record.get('timestamp')
                        payload = record.get('payload', {})
                        role = payload.get('role')
                        content_blocks = payload.get('content') or []

                        # Combine content blocks
                        content_parts = []
                        for block in content_blocks:
                            block_type = block.get('type')
                            if block_type == 'output_text':
                                content_parts.append(block.get('text', ''))
                            elif block_type == 'tool_use':
                                tool_name = block.get('name', 'unknown_tool')
                                content_parts.append(f"[Tool: {tool_name}]")

                        content = '\n'.join(content_parts)

                        if role in ('user', 'assistant') and content.strip():
                            events.append({
                                'line_number': line_number,
                                'timestamp': timestamp,
                                'role': role,
                                'content': content,
                                'metadata': {
                                    'source': 'codex_rollout',
                                    'file_path': str(file_path),
                                    'cli_version': record.get('cli_version', 'unknown')
                                }
                            })

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON at {file_path}:{line_number}: {e}")
                except Exception as e:
                    logger.warning(f"Error parsing {file_path}:{line_number}: {e}")

        if not session_id:
            logger.error(f"No session_id found in {file_path}")

        return session_id, events

    def send_to_orchestrator(
        self,
        session_id: str,
        events: List[Dict[str, Any]],
        use_mcp: bool = True
    ) -> int:
        """
        Send conversation events to Context Orchestrator via stdio MCP.

        Args:
            session_id: Codex session ID
            events: List of conversation events
            use_mcp: If True, use MCP client; if False, just log (dry-run)

        Returns:
            Number of events successfully sent
        """
        # Filter out already processed events
        new_events = []
        for event in events:
            line_number = event['line_number']
            if self.is_processed(session_id, line_number):
                logger.debug(f"Skipping already processed: {session_id}:{line_number}")
            else:
                new_events.append(event)

        if not new_events:
            logger.info(f"No new events to send for session {session_id}")
            return 0

        # If dry-run mode, just log (do NOT mark as processed)
        if not use_mcp:
            for event in new_events:
                logger.info(f"Would send to orchestrator: {session_id}:{event['line_number']} ({event['role']})")
            return 0  # Dry-run does not actually send events

        # Use MCP client to send events
        sent_count = 0

        try:
            with MCPClient(self.orchestrator_path) as client:
                # Start MCP session (map Codex session to Context Orchestrator session)
                orchestrator_session_id = client.start_session(metadata={
                    'client': 'codex_ingestor',
                    'codex_session_id': session_id,
                    'cwd': str(self.current_cwd)
                })

                logger.info(f"Started MCP session: {orchestrator_session_id} (Codex session: {session_id})")

                # Send each event as add_command
                for event in new_events:
                    try:
                        success = client.add_command(
                            session_id=orchestrator_session_id,
                            command=f"[{event['role']}] {event['content'][:100]}...",
                            output=event['content'],
                            exit_code=0,
                            metadata={
                                **event['metadata'],
                                'codex_session_id': session_id,
                                'codex_line_number': event['line_number'],
                                'timestamp': event['timestamp'],
                                'role': event['role']
                            }
                        )

                        if success:
                            self.mark_processed(session_id, event['line_number'])
                            sent_count += 1
                            logger.debug(f"Sent event: {session_id}:{event['line_number']}")
                        else:
                            logger.warning(f"Failed to send event: {session_id}:{event['line_number']}")

                    except Exception as e:
                        logger.error(f"Error sending event {session_id}:{event['line_number']}: {e}")

                # End MCP session
                memory_id = client.end_session(orchestrator_session_id)
                logger.info(f"Ended MCP session: {orchestrator_session_id}, memory_id={memory_id}")

        except Exception as e:
            logger.error(f"MCP client error for session {session_id}: {e}")
            # Don't mark as processed if MCP communication failed
            return sent_count

        return sent_count

    def ingest_all(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Ingest all Codex sessions for current repository.

        Args:
            dry_run: If True, don't send to orchestrator (just parse)

        Returns:
            Statistics: {
                'sessions_found': int,
                'sessions_matched': int,
                'events_parsed': int,
                'events_sent': int
            }
        """
        stats = {
            'sessions_found': 0,
            'sessions_matched': 0,
            'events_parsed': 0,
            'events_sent': 0
        }

        # Scan sessions
        session_files = self.scan_sessions()
        stats['sessions_found'] = len(session_files)
        stats['sessions_matched'] = len(session_files)

        # Process each session
        for file_path in session_files:
            try:
                session_id, events = self.parse_session_file(file_path)

                if not session_id:
                    logger.warning(f"Skipping file with no session_id: {file_path}")
                    continue

                stats['events_parsed'] += len(events)

                # Send to orchestrator (use_mcp=True unless dry_run)
                sent_count = self.send_to_orchestrator(session_id, events, use_mcp=not dry_run)
                stats['events_sent'] += sent_count

                if dry_run:
                    logger.info(f"Dry run: would send {len(events)} events from {session_id}")

            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")

        return stats


def main():
    """CLI entry point for Codex session ingestor."""
    parser = argparse.ArgumentParser(description='Ingest Codex session logs into Context Orchestrator')
    parser.add_argument('--config', help='Config file path')
    parser.add_argument('--cwd', help='Working directory to filter sessions (default: current dir)')
    parser.add_argument('--orchestrator-path', help='Path to Context Orchestrator main.py')
    parser.add_argument('--dry-run', action='store_true', help='Parse but don\'t send to orchestrator')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logger('codex_ingestor', log_level)

    # Load config
    config = load_config(args.config)

    # Determine cwd
    current_cwd = args.cwd if args.cwd else os.getcwd()

    # Run ingestor
    ingestor = CodexSessionIngestor(
        config,
        current_cwd,
        orchestrator_path=args.orchestrator_path
    )
    stats = ingestor.ingest_all(dry_run=args.dry_run)

    # Print results
    print("=" * 60)
    print("Codex Session Ingestion Results")
    print("=" * 60)
    print(f"Sessions found:   {stats['sessions_found']}")
    print(f"Sessions matched: {stats['sessions_matched']}")
    print(f"Events parsed:    {stats['events_parsed']}")
    print(f"Events sent:      {stats['events_sent']}")
    print("=" * 60)

    if args.dry_run:
        print("\n(Dry run - no data sent to Context Orchestrator)")


if __name__ == '__main__':
    main()
