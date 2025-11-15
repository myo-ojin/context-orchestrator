#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Session Log Collector

Collects and persists terminal transcripts to prevent context loss.
Issues unique session_id, streams to logs/<session_id>.log, rotates at 10MB.

Requirements: Requirement 26 (Phase 2 - Session Logging & Summaries)
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging
import uuid

logger = logging.getLogger(__name__)


class SessionLogCollector:
    """
    Collects session logs and writes to files

    Each terminal session gets a unique ID and its own log file.
    Logs are rotated when they exceed max_log_size_mb.

    Attributes:
        log_dir: Directory for session logs
        max_log_size_mb: Maximum log file size in MB
        active_sessions: Dict of active session IDs -> log file paths
    """

    def __init__(
        self,
        log_dir: str = "~/.context-orchestrator/logs",
        max_log_size_mb: int = 10
    ):
        """
        Initialize Session Log Collector

        Args:
            log_dir: Directory for session logs
            max_log_size_mb: Maximum log file size in MB (default: 10)
        """
        self.log_dir = Path(log_dir).expanduser()
        self.max_log_size_mb = max_log_size_mb
        self.active_sessions: Dict[str, Path] = {}

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized SessionLogCollector (log_dir={self.log_dir}, "
                   f"max_size={max_log_size_mb}MB)")

    def start_session(self, session_id: Optional[str] = None) -> str:
        """
        Start a new session and create log file

        Args:
            session_id: Optional session ID (generates UUID if not provided)

        Returns:
            Session ID

        Example:
            >>> collector = SessionLogCollector()
            >>> session_id = collector.start_session()
            >>> print(session_id)
            'session-abc123...'
        """
        if session_id is None:
            session_id = f"session-{uuid.uuid4().hex[:12]}"

        # Create log file path
        log_file = self.log_dir / f"{session_id}.log"

        # Create initial log entry
        self._write_log_header(log_file, session_id)

        # Track active session
        self.active_sessions[session_id] = log_file

        logger.info(f"Started session log: {session_id} -> {log_file}")
        return session_id

    def append_event(
        self,
        session_id: str,
        event_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Append an event to session log

        Args:
            session_id: Session ID
            event_type: Event type ('command', 'output', 'error', etc.)
            content: Event content
            metadata: Optional metadata

        Returns:
            True if successful

        Example:
            >>> collector.append_event(
            ...     session_id,
            ...     'command',
            ...     'python test.py'
            ... )
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return False

        log_file = self.active_sessions[session_id]

        try:
            # Check if rotation is needed
            if self._should_rotate(log_file):
                self._rotate_log(session_id, log_file)

            # Format event
            event_text = self._format_event(event_type, content, metadata)

            # Append to log file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(event_text)
                f.write('\n')

            logger.debug(f"Appended {event_type} to session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to append event to {session_id}: {e}")
            return False

    def close_session(self, session_id: str) -> Optional[Path]:
        """
        Close a session and return log file path

        Args:
            session_id: Session ID

        Returns:
            Path to log file, or None if session not found

        Example:
            >>> log_file = collector.close_session(session_id)
            >>> print(log_file)
            PosixPath('/home/user/.context-orchestrator/logs/session-abc123.log')
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return None

        log_file = self.active_sessions[session_id]

        try:
            # Write closing marker
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Session closed: {datetime.now().isoformat()}\n")
                f.write(f"{'='*80}\n")

            # Remove from active sessions
            del self.active_sessions[session_id]

            logger.info(f"Closed session log: {session_id}")
            return log_file

        except Exception as e:
            logger.error(f"Failed to close session {session_id}: {e}")
            return None

    def _write_log_header(self, log_file: Path, session_id: str) -> None:
        """
        Write log file header

        Args:
            log_file: Log file path
            session_id: Session ID
        """
        header = f"""{'='*80}
Session Log: {session_id}
Started: {datetime.now().isoformat()}
{'='*80}

"""
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(header)

    def _format_event(
        self,
        event_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format event for log file

        Args:
            event_type: Event type
            content: Event content
            metadata: Optional metadata

        Returns:
            Formatted event text
        """
        timestamp = datetime.now().isoformat()

        lines = [
            f"[{timestamp}] {event_type.upper()}"
        ]

        if metadata:
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")

        lines.append(f"{'-'*80}")
        lines.append(content)
        lines.append(f"{'-'*80}")

        return '\n'.join(lines)

    def _should_rotate(self, log_file: Path) -> bool:
        """
        Check if log file should be rotated

        Args:
            log_file: Log file path

        Returns:
            True if file size exceeds max_log_size_mb
        """
        if not log_file.exists():
            return False

        size_mb = log_file.stat().st_size / (1024 * 1024)
        return size_mb >= self.max_log_size_mb

    def _rotate_log(self, session_id: str, current_log: Path) -> None:
        """
        Rotate log file when it exceeds max size

        Creates a new log file with incremented suffix.

        Args:
            session_id: Session ID
            current_log: Current log file path
        """
        try:
            # Find next available rotation number
            rotation_num = 1
            while True:
                rotated_log = self.log_dir / f"{session_id}.{rotation_num}.log"
                if not rotated_log.exists():
                    break
                rotation_num += 1

            # Rename current log
            current_log.rename(rotated_log)

            # Create new log file
            self._write_log_header(current_log, session_id)

            # Write rotation notice
            with open(current_log, 'a', encoding='utf-8') as f:
                f.write(f"[Note: Previous log rotated to {rotated_log.name}]\n\n")

            logger.info(f"Rotated log for session {session_id}: {rotated_log.name}")

        except Exception as e:
            logger.error(f"Failed to rotate log for {session_id}: {e}")

    def get_log_path(self, session_id: str) -> Optional[Path]:
        """
        Get log file path for a session

        Args:
            session_id: Session ID

        Returns:
            Path to log file, or None if not found
        """
        return self.active_sessions.get(session_id)

    def list_active_sessions(self) -> list[str]:
        """
        List active session IDs

        Returns:
            List of session IDs
        """
        return list(self.active_sessions.keys())

    def get_session_log_content(self, session_id: str) -> Optional[str]:
        """
        Get content of session log

        Args:
            session_id: Session ID

        Returns:
            Log content or None if not found
        """
        log_file = self.active_sessions.get(session_id)
        if not log_file or not log_file.exists():
            # Try to find closed session log
            log_file = self.log_dir / f"{session_id}.log"
            if not log_file.exists():
                return None

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read log for {session_id}: {e}")
            return None

    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        Clean up log files older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of files deleted
        """
        try:
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
            deleted_count = 0

            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old log: {log_file.name}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old log files")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0
