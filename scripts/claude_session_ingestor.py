#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Claude Session Ingestor

Scans Claude session logs and ingests them into Context Orchestrator.
Implements differential processing to avoid duplicate ingestion.

Implementation for Issue #2025-11-15-01
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


class ClaudeSessionIngestor:
    """
    Ingests Claude session logs into Context Orchestrator.

    Features:
    - Scans %USERPROFILE%/.claude/projects/**/[sessionId].jsonl
    - Filters by cwd (current repository only)
    - Differential processing using SQLite (session_id, line_number)
    - Sends to Context Orchestrator via MCP RPC
    """

    def __init__(self, config: Dict[str, Any], repository_cwd: str):
        """
        Initialize Claude session ingestor.

        Args:
            config: Context Orchestrator configuration
            repository_cwd: Current repository working directory (for filtering)
        """
        self.config = config
        self.repository_cwd = Path(repository_cwd).resolve()
        self.claude_dir = Path(os.environ.get('USERPROFILE', '~')).expanduser() / '.claude'
        self.projects_dir = self.claude_dir / 'projects'

        # State DB path (tracks processed events)
        self.state_db_path = self.claude_dir / 'context_orchestrator_state.db'
        self._init_state_db()

        logger.info(f"Claude session ingestor initialized")
        logger.info(f"Repository CWD: {self.repository_cwd}")
        logger.info(f"Projects directory: {self.projects_dir}")

    def _init_state_db(self):
        """Initialize SQLite database for tracking processed events."""
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()

        # Create table for tracking processed events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                session_id TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_uuid TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                PRIMARY KEY (session_id, line_number)
            )
        """)

        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_uuid
            ON processed_events(session_id, event_uuid)
        """)

        conn.commit()
        conn.close()

    def is_processed(self, session_id: str, line_number: int) -> bool:
        """
        Check if an event has already been processed.

        Args:
            session_id: Session ID
            line_number: Line number in JSONL file

        Returns:
            True if already processed, False otherwise
        """
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM processed_events WHERE session_id = ? AND line_number = ?",
            (session_id, line_number)
        )
        result = cursor.fetchone()
        conn.close()

        return result is not None

    def mark_processed(self, session_id: str, line_number: int, event_type: str, event_uuid: str):
        """
        Mark an event as processed.

        Args:
            session_id: Session ID
            line_number: Line number in JSONL file
            event_type: Event type (user/assistant/tool_use/tool_result)
            event_uuid: Event UUID
        """
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO processed_events
            (session_id, line_number, event_type, event_uuid, processed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, line_number, event_type, event_uuid, datetime.now().isoformat())
        )

        conn.commit()
        conn.close()

    def extract_session_meta(self, session_file: Path) -> Optional[Dict[str, Any]]:
        """
        Extract session metadata (cwd, session_id) from first event.

        Args:
            session_file: Path to session JSONL file

        Returns:
            Session metadata dict, or None if file is invalid
        """
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                # Read first few lines to find session metadata
                for _ in range(10):  # Check first 10 lines
                    line = f.readline()
                    if not line:
                        break

                    event = json.loads(line)

                    # Extract metadata from events with cwd/sessionId
                    if 'cwd' in event and 'sessionId' in event:
                        return {
                            'session_id': event['sessionId'],
                            'cwd': event.get('cwd', ''),
                            'git_branch': event.get('gitBranch', ''),
                            'version': event.get('version', ''),
                        }

            return None

        except Exception as e:
            logger.error(f"Failed to extract metadata from {session_file}: {e}")
            return None

    def parse_session_file(self, session_file: Path) -> List[Dict[str, Any]]:
        """
        Parse Claude session JSONL file and extract events.

        Args:
            session_file: Path to session JSONL file

        Returns:
            List of parsed events with context
        """
        events = []

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    if not line.strip():
                        continue

                    event = json.loads(line)
                    event_type = event.get('type', '')

                    # Extract session metadata
                    session_id = event.get('sessionId', '')
                    if not session_id:
                        continue  # Skip events without sessionId

                    # Skip if already processed
                    if self.is_processed(session_id, line_num):
                        continue

                    # Filter by event type
                    if event_type == 'user':
                        # Check if user message contains tool_result
                        message = event.get('message', {})
                        content = message.get('content', [])

                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'tool_result':
                                    # Extract tool_result as separate event
                                    events.append({
                                        'session_id': session_id,
                                        'line_number': line_num,
                                        'type': 'tool_result',
                                        'uuid': event.get('uuid', ''),
                                        'parent_uuid': event.get('parentUuid'),
                                        'timestamp': event.get('timestamp', ''),
                                        'cwd': event.get('cwd', ''),
                                        'git_branch': event.get('gitBranch', ''),
                                        'message': message,
                                        'tool_use_id': item.get('tool_use_id', ''),
                                        'tool_result': item.get('content', ''),
                                        'tool_name': 'tool',  # Will be inferred from tool_use_id
                                    })
                        else:
                            # Regular user message (string content)
                            events.append({
                                'session_id': session_id,
                                'line_number': line_num,
                                'type': event_type,
                                'uuid': event.get('uuid', ''),
                                'parent_uuid': event.get('parentUuid'),
                                'timestamp': event.get('timestamp', ''),
                                'cwd': event.get('cwd', ''),
                                'git_branch': event.get('gitBranch', ''),
                                'message': message,
                            })

                    elif event_type == 'assistant':
                        # Check if assistant message contains tool_use or text
                        message = event.get('message', {})
                        content = message.get('content', [])

                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    if item.get('type') == 'tool_use':
                                        # Extract tool_use as separate event
                                        events.append({
                                            'session_id': session_id,
                                            'line_number': line_num,
                                            'type': 'tool_use',
                                            'uuid': event.get('uuid', ''),
                                            'parent_uuid': event.get('parentUuid'),
                                            'timestamp': event.get('timestamp', ''),
                                            'cwd': event.get('cwd', ''),
                                            'git_branch': event.get('gitBranch', ''),
                                            'message': message,
                                            'tool_use_id': item.get('id', ''),
                                            'tool_name': item.get('name', 'unknown'),
                                            'tool_input': item.get('input', {}),
                                        })
                                    elif item.get('type') == 'text':
                                        # Regular assistant text message
                                        events.append({
                                            'session_id': session_id,
                                            'line_number': line_num,
                                            'type': event_type,
                                            'uuid': event.get('uuid', ''),
                                            'parent_uuid': event.get('parentUuid'),
                                            'timestamp': event.get('timestamp', ''),
                                            'cwd': event.get('cwd', ''),
                                            'git_branch': event.get('gitBranch', ''),
                                            'message': message,
                                        })
                        else:
                            # Fallback for non-list content
                            events.append({
                                'session_id': session_id,
                                'line_number': line_num,
                                'type': event_type,
                                'uuid': event.get('uuid', ''),
                                'parent_uuid': event.get('parentUuid'),
                                'timestamp': event.get('timestamp', ''),
                                'cwd': event.get('cwd', ''),
                                'git_branch': event.get('gitBranch', ''),
                                'message': message,
                            })

                    # Note: file-history-snapshot and other types are ignored

        except Exception as e:
            logger.error(f"Failed to parse {session_file}: {e}")

        return events

    def scan_sessions(self) -> List[Tuple[Path, Dict[str, Any]]]:
        """
        Scan Claude projects directory for session files matching current repository.

        Returns:
            List of (session_file_path, session_meta) tuples
        """
        matching_sessions = []

        if not self.projects_dir.exists():
            logger.warning(f"Projects directory not found: {self.projects_dir}")
            return []

        # Scan all project directories
        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            # Find all .jsonl files (session logs)
            for session_file in project_dir.glob('*.jsonl'):
                # Skip agent-*.jsonl files (those are agent-specific)
                if session_file.name.startswith('agent-'):
                    continue

                # Extract session metadata
                meta = self.extract_session_meta(session_file)
                if not meta:
                    continue

                # Filter by cwd
                session_cwd = Path(meta.get('cwd', ''))
                if session_cwd.resolve() != self.repository_cwd:
                    continue

                matching_sessions.append((session_file, meta))

        logger.info(f"Found {len(matching_sessions)} matching Claude sessions")
        return matching_sessions

    def send_to_orchestrator(
        self,
        session_meta: Dict[str, Any],
        events: List[Dict[str, Any]],
        use_mcp: bool = True
    ) -> int:
        """
        Send session events to Context Orchestrator.

        Args:
            session_meta: Session metadata
            events: List of events to send
            use_mcp: If True, send via MCP; if False, just log (dry-run)

        Returns:
            Number of events sent
        """
        if not events:
            return 0

        # If dry-run mode, just log (do NOT mark as processed)
        if not use_mcp:
            for event in events:
                logger.info(
                    f"[DRY-RUN] Would send event: "
                    f"session={event['session_id']}, "
                    f"type={event['type']}, "
                    f"uuid={event['uuid']}"
                )
            return 0  # Dry-run does not actually send events

        # Use MCP client to send events
        sent_count = 0

        try:
            # Get path to Context Orchestrator
            orchestrator_path = Path(__file__).parent.parent / 'src' / 'main.py'

            with MCPClient(str(orchestrator_path)) as client:
                # Start MCP session (map Claude session to Context Orchestrator session)
                claude_session_id = session_meta['session_id']
                orchestrator_session_id = client.start_session(metadata={
                    'client': 'claude_ingestor',
                    'claude_session_id': claude_session_id,
                    'cwd': str(self.repository_cwd),
                    'git_branch': session_meta.get('git_branch', ''),
                    'claude_version': session_meta.get('version', ''),
                })

                logger.info(
                    f"Started MCP session: {orchestrator_session_id} "
                    f"(Claude session: {claude_session_id})"
                )

                # Send each event as add_command
                for event in events:
                    try:
                        # Format message based on event type
                        if event['type'] == 'user':
                            message_content = event['message'].get('content', '')
                            command_summary = f"[user] {message_content[:100]}"
                        elif event['type'] == 'assistant':
                            # Extract text content from assistant message
                            content = event['message'].get('content', [])
                            if isinstance(content, list):
                                text_parts = [c.get('text', '') for c in content if c.get('type') == 'text']
                                message_content = '\n'.join(text_parts)
                            else:
                                message_content = str(content)
                            command_summary = f"[assistant] {message_content[:100]}"
                        elif event['type'] == 'tool_use':
                            tool_name = event.get('tool_name', 'unknown')
                            tool_input = json.dumps(event.get('tool_input', {}), ensure_ascii=False)
                            message_content = f"Tool: {tool_name}\nInput: {tool_input}"
                            command_summary = f"[tool_use] {tool_name}"
                        elif event['type'] == 'tool_result':
                            tool_name = event.get('tool_name', 'unknown')
                            tool_result = event.get('tool_result', '')
                            message_content = f"Tool: {tool_name}\nResult: {tool_result}"
                            command_summary = f"[tool_result] {tool_name}"
                        else:
                            message_content = json.dumps(event['message'], ensure_ascii=False)
                            command_summary = f"[{event['type']}] ..."

                        # Send command event
                        success = client.add_command(
                            session_id=orchestrator_session_id,
                            command=command_summary,
                            output=message_content,
                            exit_code=0,
                            metadata={
                                'role': event['message'].get('role', event['type']),
                                'uuid': event['uuid'],
                                'parent_uuid': event.get('parent_uuid'),
                                'timestamp': event['timestamp'],
                                'claude_session_id': claude_session_id,
                                'claude_line_number': event['line_number'],
                            }
                        )

                        if success:
                            # Mark as processed
                            self.mark_processed(
                                claude_session_id,
                                event['line_number'],
                                event['type'],
                                event['uuid']
                            )
                            sent_count += 1
                            logger.debug(f"Sent event: {claude_session_id}:{event['line_number']}")
                        else:
                            logger.warning(f"Failed to send event: {claude_session_id}:{event['line_number']}")

                    except Exception as e:
                        logger.error(f"Error sending event {claude_session_id}:{event['line_number']}: {e}")

                # End MCP session
                memory_id = client.end_session(orchestrator_session_id)
                logger.info(
                    f"Ended MCP session: {orchestrator_session_id}, "
                    f"memory_id={memory_id}"
                )

        except Exception as e:
            logger.error(f"MCP client error for session {claude_session_id}: {e}")
            # Don't mark as processed if MCP communication failed
            return sent_count

        return sent_count

    def ingest_all(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Scan and ingest all Claude sessions.

        Args:
            dry_run: If True, don't actually send to MCP (just log)

        Returns:
            Statistics dict with counts
        """
        stats = {
            'sessions_matched': 0,
            'events_parsed': 0,
            'events_sent': 0,
        }

        # Scan for matching sessions
        matching_sessions = self.scan_sessions()
        stats['sessions_matched'] = len(matching_sessions)

        # Process each session
        for session_file, session_meta in matching_sessions:
            logger.info(f"Processing session: {session_file.name}")

            # Parse events
            events = self.parse_session_file(session_file)
            stats['events_parsed'] += len(events)

            # Send to orchestrator
            sent_count = self.send_to_orchestrator(session_meta, events, use_mcp=not dry_run)
            stats['events_sent'] += sent_count

            logger.info(
                f"Session {session_meta['session_id']}: "
                f"{len(events)} events parsed, {sent_count} sent"
            )

        return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest Claude session logs into Context Orchestrator"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Don't actually send to MCP, just log what would be done"
    )
    parser.add_argument(
        '--cwd',
        type=str,
        default=os.getcwd(),
        help="Repository working directory to filter sessions (default: current directory)"
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logger(level=log_level)

    # Load config
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return 1

    # Initialize ingestor
    ingestor = ClaudeSessionIngestor(config, args.cwd)

    # Ingest sessions
    start_time = datetime.now()
    stats = ingestor.ingest_all(dry_run=args.dry_run)
    elapsed = (datetime.now() - start_time).total_seconds()

    # Print summary
    print("\n" + "=" * 60)
    print("Claude Session Ingestion Summary")
    print("=" * 60)
    print(f"Sessions matched: {stats['sessions_matched']}")
    print(f"Events parsed: {stats['events_parsed']}")
    print(f"Events sent: {stats['events_sent']}")
    print(f"Elapsed time: {elapsed:.3f}s")
    if args.dry_run:
        print("\n[DRY-RUN MODE] No events were actually sent to MCP")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
