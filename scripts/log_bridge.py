#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log Bridge for Claude/Codex Sessions

Watches rollout-*.jsonl files and ingests them into Context Orchestrator
via SessionManager.

This script runs as a background daemon and monitors:
- ~/.codex/sessions/**/rollout-*.jsonl (Codex session logs)
- Future: ~/.claude/sessions/**/rollout-*.jsonl (if exists)

Requirements: Requirement 26 (Session Logging & CLI Integration)
"""

import json
import time
import hashlib
import os
import sys
import re
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config
from src.main import init_storage, init_models, init_processing, init_services
from src.utils.logger import setup_logger
from src.services.session_summary import SessionSummaryWorker

logger = setup_logger('log_bridge', 'INFO')


class LRUCache:
    """
    Simple LRU cache for deduplication with TTL

    Attributes:
        cache: Dictionary of hash -> timestamp
        capacity: Maximum number of entries
        ttl_seconds: Time-to-live for entries
    """

    def __init__(self, capacity: int = 5000, ttl_seconds: int = 3600):
        """
        Initialize LRU cache

        Args:
            capacity: Maximum cache size
            ttl_seconds: Time-to-live for entries (default: 1 hour)
        """
        self.cache: Dict[str, float] = {}
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()  # Thread-safe access to cache

    def contains(self, key: str) -> bool:
        """
        Check if key exists and is still valid

        Args:
            key: Hash key

        Returns:
            True if key exists and hasn't expired
        """
        with self._lock:
            if key in self.cache:
                ts = self.cache[key]
                if time.time() - ts < self.ttl_seconds:
                    return True
                else:
                    del self.cache[key]
            return False

    def add(self, key: str):
        """
        Add key to cache

        Args:
            key: Hash key
        """
        with self._lock:
            # Simple LRU: remove expired entries
            if len(self.cache) >= self.capacity:
                cutoff = time.time() - self.ttl_seconds
                self.cache = {k: v for k, v in self.cache.items() if v > cutoff}

            self.cache[key] = time.time()


# Global cache for deduplication
seen_messages = LRUCache()


class SessionTimeoutTracker:
    """
    Track session activity and detect idle sessions

    Monitors when sessions were last active and triggers end_session()
    when sessions have been idle for too long.

    Attributes:
        last_activity: Dictionary of session_id -> timestamp
        timeout_seconds: Idle timeout before ending session
        session_manager: SessionManager instance
    """

    def __init__(self, session_manager, timeout_seconds: int = 600):
        """
        Initialize session timeout tracker

        Args:
            session_manager: SessionManager instance
            timeout_seconds: Idle timeout in seconds (default: 10 minutes)
        """
        self.last_activity: Dict[str, float] = {}
        self.timeout_seconds = timeout_seconds
        self.session_manager = session_manager
        self._lock = threading.Lock()
        logger.info(f"Session timeout tracker initialized (timeout: {timeout_seconds}s)")

    def update_activity(self, session_id: str):
        """
        Update last activity timestamp for a session

        Args:
            session_id: Session ID
        """
        with self._lock:
            self.last_activity[session_id] = time.time()

    def check_and_end_idle_sessions(self):
        """
        Check for idle sessions and end them

        This method should be called periodically to check for sessions
        that haven't had activity for longer than timeout_seconds.
        """
        with self._lock:
            now = time.time()
            idle_sessions = []

            for session_id, last_ts in list(self.last_activity.items()):
                idle_time = now - last_ts
                if idle_time > self.timeout_seconds:
                    idle_sessions.append((session_id, idle_time))

            # Remove from tracking
            for session_id, _ in idle_sessions:
                del self.last_activity[session_id]

        # End sessions (may take time due to LLM calls)
        for session_id, idle_time in idle_sessions:
            try:
                logger.info(f"Ending idle session {session_id[:8]}... (idle for {idle_time:.1f}s)")
                memory_id = self.session_manager.end_session(session_id, create_obsidian_note=False)
                if memory_id:
                    logger.info(f"Session {session_id[:8]}... → Memory {memory_id[:8]}... (indexed)")
                else:
                    logger.warning(f"Session {session_id[:8]}... ended but no memory created")
            except Exception as e:
                logger.error(f"Error ending session {session_id[:8]}...: {e}", exc_info=True)


# Global session timeout tracker (initialized in main())
session_timeout_tracker: Optional[SessionTimeoutTracker] = None

# Global session summary worker (initialized in main())
session_summary_worker: Optional[SessionSummaryWorker] = None


def parse_rollout_event(line: str, file_path: str) -> Optional[Tuple[str, str, str, float]]:
    """
    Parse a rollout-*.jsonl event line

    Extracts user_message and agent_message events from Codex rollout logs.

    Args:
        line: JSON line from rollout file
        file_path: Full path to rollout file

    Returns:
        Tuple of (session_id, role, message_text, timestamp) or None if not a message event

    Example:
        >>> parse_rollout_event('{"type":"event_msg","payload":{"type":"user_message",...}}', "rollout-...-abc123.jsonl")
        ('abc123', 'user', 'hello', 1762599152.0)
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    # Only process event_msg events
    if obj.get("type") != "event_msg":
        return None

    payload = obj.get("payload", {})
    payload_type = payload.get("type")

    # Extract session_id from filename
    # Format: rollout-2025-11-08T19-51-59-019a6318-2a47-7692-889d-f99b4fc182e3.jsonl
    match = re.search(r'rollout-[^-]+-[^-]+-[^-]+-([^.]+)\.jsonl$', file_path)
    session_id = match.group(1) if match else None

    if not session_id:
        logger.warning(f"Could not extract session_id from filename: {file_path}")
        return None

    # Parse user_message
    if payload_type == "user_message":
        role = "user"
        text = payload.get("message", "")
    # Parse agent_message (assistant)
    elif payload_type == "agent_message":
        role = "assistant"
        text = payload.get("message", "")
    else:
        # Skip other event types (agent_reasoning, token_count, etc.)
        return None

    if not text.strip():
        return None

    # Parse timestamp (ISO 8601 format)
    ts_str = obj.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        ts = dt.timestamp()
    except:
        ts = time.time()

    return (session_id, role, text, ts)


def parse_claude_project_event(line: str, file_path: str) -> Optional[Tuple[str, str, str, float]]:
    """
    Parse a Claude project log event line

    Extracts user/assistant messages from Claude project logs.

    Args:
        line: JSON line from Claude project log
        file_path: Full path to project log file

    Returns:
        Tuple of (session_id, role, message_text, timestamp) or None if not a message event

    Example:
        >>> parse_claude_project_event('{"type":"user","message":{"content":"hi"},...}', "/.../abc123.jsonl")
        ('abc123', 'user', 'hi', 1762599152.0)
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    # Extract session_id from filename: {sessionId}.jsonl
    session_id = Path(file_path).stem

    if not session_id:
        logger.warning(f"Could not extract session_id from filename: {file_path}")
        return None

    # Parse user message
    if obj.get("type") == "user":
        role = "user"
        msg = obj.get("message", {})
        text = msg.get("content", "")
    # Parse assistant message
    elif "message" in obj and obj.get("message", {}).get("role") == "assistant":
        role = "assistant"
        content = obj.get("message", {}).get("content", [])
        # content is array of {"type": "text", "text": "..."}
        if isinstance(content, list):
            text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
        else:
            text = str(content)
    else:
        # Skip other event types (file-history-snapshot, etc.)
        return None

    if not text or not text.strip():
        return None

    # Parse timestamp (ISO 8601 format)
    ts_str = obj.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        ts = dt.timestamp()
    except:
        ts = time.time()

    return (session_id, role, text, ts)


def send_to_session_manager(session_manager, session_id: str, role: str, text: str):
    """
    Send message to SessionManager

    Args:
        session_manager: SessionManager instance
        session_id: Session ID (ULID format)
        role: 'user' or 'assistant'
        text: Message text
    """
    if not session_id or not text.strip():
        return

    # Check deduplication
    msg_hash = hashlib.sha1(f"{session_id}-{role}-{text}".encode()).hexdigest()
    if seen_messages.contains(msg_hash):
        logger.debug(f"Skipping duplicate message: {session_id[:8]}... {role}")
        return

    try:
        # Ensure session exists
        if session_id not in session_manager.sessions:
            logger.info(f"Starting new session: {session_id}")
            session_manager.start_session(session_id)

        # Add to session
        # Note: SessionManager.add_command expects (command, output)
        # We map user -> command, assistant -> output
        if role == "user":
            session_manager.add_command(
                session_id=session_id,
                command=text,
                output="",
                exit_code=0,
                metadata={"source": "log_bridge", "role": "user"}
            )
        else:  # assistant
            session_manager.add_command(
                session_id=session_id,
                command="",  # Empty command for assistant messages
                output=text,
                exit_code=0,
                metadata={"source": "log_bridge", "role": "assistant"}
            )

        seen_messages.add(msg_hash)
        logger.info(f"Ingested {role:9s} message to session {session_id[:8]}... ({len(text)} chars)")

        # Update session activity timestamp
        if session_timeout_tracker:
            session_timeout_tracker.update_activity(session_id)

    except Exception as e:
        logger.error(f"Error ingesting message: {e}", exc_info=True)


def tail_file(file_path: str, session_manager, parser_func):
    """
    Tail a single .jsonl file

    Monitors file for new lines and processes them.
    Handles file rotation (when file size decreases).

    Args:
        file_path: Path to .jsonl file
        session_manager: SessionManager instance
        parser_func: Function to parse each line (parse_rollout_event or parse_claude_project_event)
    """
    logger.info(f"Started monitoring: {file_path}")

    offset = 0
    last_size = 0

    while True:
        try:
            if not os.path.exists(file_path):
                logger.info(f"File deleted or moved: {file_path}")
                break

            size = os.path.getsize(file_path)
            if size < last_size:
                # File rotated or truncated
                logger.info(f"File rotation detected: {file_path}")
                offset = 0

            last_size = size

            # Open file with error handling for encoding issues
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(offset)

                # Read line by line to avoid splitting multibyte characters
                while True:
                    line = f.readline()
                    if not line:
                        # End of file reached
                        offset = f.tell()
                        break

                    line = line.strip()
                    if not line:
                        offset = f.tell()
                        continue

                    result = parser_func(line, file_path)
                    if result:
                        sid, role, text, ts = result
                        send_to_session_manager(session_manager, sid, role, text)

                    offset = f.tell()

        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error in {file_path}: {e}")
            # Skip to next check cycle
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}", exc_info=True)

        time.sleep(0.5)  # Poll every 500ms


def tail_rollout_file(file_path: str, session_manager):
    """Tail a Codex rollout-*.jsonl file"""
    tail_file(file_path, session_manager, parse_rollout_event)


def tail_claude_project_file(file_path: str, session_manager):
    """Tail a Claude project/*.jsonl file"""
    tail_file(file_path, session_manager, parse_claude_project_event)


def watch_rollout_directory(session_manager):
    """
    Watch for new rollout-*.jsonl files and start tailing them

    Scans ~/.codex/sessions/ directory for existing rollout files,
    then periodically checks for new files.

    Args:
        session_manager: SessionManager instance
    """
    sessions_dir = Path.home() / ".codex" / "sessions"
    active_files = set()

    if not sessions_dir.exists():
        logger.warning(f"Sessions directory does not exist: {sessions_dir}")
        logger.info("Creating sessions directory...")
        sessions_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Watching directory: {sessions_dir}")

    while True:
        try:
            # Scan for rollout-*.jsonl files
            current_files = set(sessions_dir.rglob("rollout-*.jsonl"))

            # Start monitoring new files
            new_files = current_files - active_files
            for f in new_files:
                logger.info(f"New rollout file detected: {f}")
                active_files.add(f)

                # Start tail thread
                t = threading.Thread(
                    target=tail_rollout_file,
                    args=(str(f), session_manager),
                    daemon=True,
                    name=f"tail-{f.name}"
                )
                t.start()

            # Remove deleted files from tracking
            deleted_files = active_files - current_files
            for f in deleted_files:
                logger.info(f"Rollout file removed: {f}")
                active_files.discard(f)

        except Exception as e:
            logger.error(f"Error scanning directory: {e}", exc_info=True)

        time.sleep(5)  # Scan for new files every 5 seconds


def get_claude_projects_dir():
    """
    Get Claude projects directory for current user

    Claude sanitizes the user's home directory path by replacing special characters.
    For example: C:\\Users\\ryomy -> C--Users-ryomy

    Returns:
        Path object for Claude projects directory
    """
    home = Path.home()
    # Sanitize home path: replace \ with - and : with -
    sanitized_home = str(home).replace('\\', '-').replace(':', '-')
    projects_dir = Path.home() / ".claude" / "projects" / sanitized_home

    # If directory doesn't exist, try to find any existing project directory
    if not projects_dir.exists():
        base_dir = Path.home() / ".claude" / "projects"
        if base_dir.exists():
            # List all subdirectories
            subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
            if subdirs:
                # Use the first one found
                projects_dir = subdirs[0]
                logger.info(f"Using existing Claude projects directory: {projects_dir}")

    return projects_dir


def watch_claude_projects(session_manager):
    """
    Watch for new Claude project .jsonl files and start tailing them

    Scans ~/.claude/projects/ directory for existing project log files,
    then periodically checks for new files.

    Args:
        session_manager: SessionManager instance
    """
    projects_dir = get_claude_projects_dir()
    active_files = set()

    if not projects_dir.exists():
        logger.warning(f"Claude projects directory does not exist: {projects_dir}")
        logger.info("Creating Claude projects directory...")
        projects_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Watching Claude projects directory: {projects_dir}")

    while True:
        try:
            # Scan for *.jsonl files (excluding metadata files)
            current_files = set(f for f in projects_dir.glob("*.jsonl")
                              if not f.name.startswith('.'))

            # Start monitoring new files
            new_files = current_files - active_files
            for f in new_files:
                logger.info(f"New Claude project file detected: {f}")
                active_files.add(f)

                # Start tail thread
                t = threading.Thread(
                    target=tail_claude_project_file,
                    args=(str(f), session_manager),
                    daemon=True,
                    name=f"tail-claude-{f.name}"
                )
                t.start()

            # Remove deleted files from tracking
            deleted_files = active_files - current_files
            for f in deleted_files:
                logger.info(f"Claude project file removed: {f}")
                active_files.discard(f)

        except Exception as e:
            logger.error(f"Error scanning Claude projects directory: {e}", exc_info=True)

        time.sleep(5)  # Scan for new files every 5 seconds


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Context Orchestrator Log Bridge")
    logger.info("=" * 60)
    logger.info("")

    # Load configuration
    config_path = Path.home() / ".context-orchestrator" / "config.yaml"
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.error("Please create config.yaml from config.yaml.template")
        return 1

    logger.info(f"Loading config: {config_path}")
    config = load_config(str(config_path))

    # Initialize Context Orchestrator services
    logger.info("Initializing Context Orchestrator...")

    try:
        vector_db, bm25_index = init_storage(config)
        model_router = init_models(config)
        classifier, chunker, indexer = init_processing(model_router, vector_db, bm25_index)

        (
            ingestion_service,
            search_service,
            consolidation_service,
            session_manager,
            obsidian_watcher,
            project_manager,
            bookmark_manager,
        ) = init_services(
            config=config,
            model_router=model_router,
            vector_db=vector_db,
            bm25_index=bm25_index,
            classifier=classifier,
            chunker=chunker,
            indexer=indexer,
        )

        logger.info("Context Orchestrator services initialized successfully")
        logger.info("")

    except Exception as e:
        logger.error(f"Failed to initialize Context Orchestrator: {e}", exc_info=True)
        return 1

    # Initialize session summary worker
    global session_summary_worker
    session_summary_worker = SessionSummaryWorker(
        model_router=model_router,
        vector_db=vector_db,
        summary_model=config.logging.summary_model,
        summary_max_tokens=config.router.mid_summary_max_tokens
    )
    logger.info("Initialized SessionSummaryWorker")

    # Pass session_summary_worker to session_manager
    session_manager.session_summary_worker = session_summary_worker

    # Initialize session timeout tracker
    global session_timeout_tracker
    session_timeout_tracker = SessionTimeoutTracker(
        session_manager=session_manager,
        timeout_seconds=600  # 10 minutes idle timeout
    )

    # Start watching both Codex and Claude sessions
    logger.info("Starting file watchers...")
    logger.info("  - Codex rollout files: ~/.codex/sessions/**/rollout-*.jsonl")
    claude_dir = get_claude_projects_dir()
    logger.info(f"  - Claude project files: {claude_dir}/*.jsonl")
    logger.info("  - Session timeout: 10 minutes (auto-index idle sessions)")
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    try:
        # Start Codex watcher in background thread
        codex_thread = threading.Thread(
            target=watch_rollout_directory,
            args=(session_manager,),
            daemon=True,
            name="codex-watcher"
        )
        codex_thread.start()
        logger.info("Started Codex watcher thread")

        # Start Claude watcher in background thread
        claude_thread = threading.Thread(
            target=watch_claude_projects,
            args=(session_manager,),
            daemon=True,
            name="claude-watcher"
        )
        claude_thread.start()
        logger.info("Started Claude watcher thread")

        # Start session timeout checker thread
        def check_idle_sessions_loop():
            """Periodically check for idle sessions and end them"""
            while True:
                time.sleep(60)  # Check every minute
                try:
                    session_timeout_tracker.check_and_end_idle_sessions()
                    # Process queued summary jobs
                    if session_summary_worker:
                        stats = session_summary_worker.run_once()
                        if stats['processed'] > 0 or stats['failed'] > 0:
                            logger.info(f"Summary worker stats: {stats}")
                except Exception as e:
                    logger.error(f"Error in session timeout checker: {e}", exc_info=True)

        timeout_thread = threading.Thread(
            target=check_idle_sessions_loop,
            daemon=True,
            name="session-timeout-checker"
        )
        timeout_thread.start()
        logger.info("Started session timeout checker thread")

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("")
        logger.info("Shutting down gracefully...")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
