#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Session Manager

Manages working memory sessions for terminal/CLI interactions.
Tracks commands, outputs, and context within a session.

Requirements: Requirements 1, 4 (MVP - CLI Recording, Working Memory)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging
import uuid
import json

from src.models import ModelRouter
from src.services.ingestion import IngestionService

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages working memory sessions

    A session represents a terminal window or work context.
    Commands and outputs are tracked within a session.

    Attributes:
        ingestion_service: IngestionService for storing memories
        model_router: ModelRouter for summarization
        obsidian_vault_path: Optional path to Obsidian vault
        sessions: Active sessions dict (session_id -> session_data)
    """

    def __init__(
        self,
        ingestion_service: IngestionService,
        model_router: ModelRouter,
        obsidian_vault_path: Optional[str] = None
    ):
        """
        Initialize Session Manager

        Args:
            ingestion_service: IngestionService instance
            model_router: ModelRouter instance
            obsidian_vault_path: Optional path to Obsidian vault
        """
        self.ingestion_service = ingestion_service
        self.model_router = model_router
        self.obsidian_vault_path = obsidian_vault_path
        self.sessions: Dict[str, Dict[str, Any]] = {}

        logger.info("Initialized SessionManager")

    def start_session(self, session_id: Optional[str] = None) -> str:
        """
        Start a new session

        Args:
            session_id: Optional session ID (generates UUID if not provided)

        Returns:
            Session ID

        Example:
            >>> manager = SessionManager(...)
            >>> session_id = manager.start_session()
            >>> print(session_id)
            'session-abc123...'
        """
        if session_id is None:
            session_id = f"session-{uuid.uuid4().hex[:12]}"

        self.sessions[session_id] = {
            'id': session_id,
            'started_at': datetime.now(),
            'commands': [],
            'last_activity': datetime.now()
        }

        logger.info(f"Started session: {session_id}")
        return session_id

    def add_command(
        self,
        session_id: str,
        command: str,
        output: str,
        exit_code: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a command and its output to a session

        Args:
            session_id: Session ID
            command: Command executed
            output: Command output
            exit_code: Exit code (0 = success)
            metadata: Optional metadata (e.g., cwd, env vars)

        Returns:
            True if successful

        Example:
            >>> manager.add_command(
            ...     session_id,
            ...     "python test.py",
            ...     "All tests passed",
            ...     exit_code=0
            ... )
        """
        if session_id not in self.sessions:
            logger.warning(f"Session not found: {session_id}")
            return False

        command_entry = {
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'output': output,
            'exit_code': exit_code,
            'metadata': metadata or {}
        }

        self.sessions[session_id]['commands'].append(command_entry)
        self.sessions[session_id]['last_activity'] = datetime.now()

        logger.debug(f"Added command to session {session_id}: {command[:50]}...")
        return True

    def end_session(
        self,
        session_id: str,
        create_obsidian_note: bool = False
    ) -> Optional[str]:
        """
        End a session and store as memory

        Args:
            session_id: Session ID
            create_obsidian_note: Whether to create Obsidian note

        Returns:
            Memory ID if successful, None otherwise

        Example:
            >>> memory_id = manager.end_session(session_id, create_obsidian_note=True)
        """
        if session_id not in self.sessions:
            logger.warning(f"Session not found: {session_id}")
            return None

        session = self.sessions[session_id]

        try:
            # Format session log
            session_log = self._format_session_log(session)

            # Generate summary
            summary = self._generate_summary(session)

            # Create conversation for ingestion
            conversation = {
                'user': f"Session {session_id} commands",
                'assistant': session_log,
                'timestamp': session['started_at'].isoformat(),
                'source': 'session',
                'refs': [f"session://{session_id}"],
                'metadata': {
                    'session_id': session_id,
                    'command_count': len(session['commands']),
                    'duration_seconds': (
                        datetime.now() - session['started_at']
                    ).total_seconds(),
                    'summary': summary
                }
            }

            # Ingest as memory
            memory_id = self.ingestion_service.ingest_conversation(conversation)

            # Create Obsidian note if requested
            if create_obsidian_note and self.obsidian_vault_path:
                self._create_obsidian_note(session, summary, memory_id)

            # Remove from active sessions
            del self.sessions[session_id]

            logger.info(f"Ended session {session_id}, created memory {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return None

    def _format_session_log(self, session: Dict[str, Any]) -> str:
        """
        Format session log as Markdown

        Args:
            session: Session data

        Returns:
            Formatted session log (Markdown)
        """
        lines = [
            f"# Session {session['id']}",
            f"",
            f"**Started**: {session['started_at'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Commands**: {len(session['commands'])}",
            f"",
            f"## Commands",
            f""
        ]

        for i, cmd in enumerate(session['commands'], 1):
            lines.extend([
                f"### Command {i}: `{cmd['command']}`",
                f"",
                f"**Time**: {cmd['timestamp']}",
                f"**Exit Code**: {cmd['exit_code']}",
                f"",
                f"**Output**:",
                f"```",
                cmd['output'][:1000],  # Limit output length
                f"```",
                f""
            ])

        return '\n'.join(lines)

    def _generate_summary(self, session: Dict[str, Any]) -> str:
        """
        Generate session summary

        Uses local LLM for short summaries.

        Args:
            session: Session data

        Returns:
            Session summary (1-2 sentences)
        """
        # Build summary prompt
        commands = [cmd['command'] for cmd in session['commands']]
        commands_text = '\n'.join(commands[:10])  # Limit to first 10 commands

        prompt = f"""Summarize this terminal session in 1-2 sentences.
Focus on what tasks were accomplished.

Session commands:
{commands_text}

Summary:"""

        try:
            summary = self.model_router.route(
                task_type='short_summary',
                prompt=prompt,
                max_tokens=100
            )
            return summary.strip()

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            # Fallback: use first command
            if session['commands']:
                return f"Session with {len(session['commands'])} commands: {session['commands'][0]['command']}"
            return "Empty session"

    def _create_obsidian_note(
        self,
        session: Dict[str, Any],
        summary: str,
        memory_id: str
    ) -> bool:
        """
        Create Obsidian note for session

        Args:
            session: Session data
            summary: Session summary
            memory_id: Associated memory ID

        Returns:
            True if successful
        """
        if not self.obsidian_vault_path:
            return False

        try:
            vault_path = Path(self.obsidian_vault_path)
            if not vault_path.exists():
                logger.warning(f"Obsidian vault not found: {vault_path}")
                return False

            # Create sessions directory
            sessions_dir = vault_path / "Sessions"
            sessions_dir.mkdir(exist_ok=True)

            # Generate filename
            date_str = session['started_at'].strftime('%Y-%m-%d')
            filename = f"{date_str}_{session['id']}.md"
            file_path = sessions_dir / filename

            # Build note content
            content = self._build_obsidian_note_content(session, summary, memory_id)

            # Write note
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Created Obsidian note: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create Obsidian note: {e}")
            return False

    def _build_obsidian_note_content(
        self,
        session: Dict[str, Any],
        summary: str,
        memory_id: str
    ) -> str:
        """
        Build Obsidian note content

        Args:
            session: Session data
            summary: Session summary
            memory_id: Memory ID

        Returns:
            Note content (Markdown)
        """
        lines = [
            "---",
            f"session_id: {session['id']}",
            f"memory_id: {memory_id}",
            f"date: {session['started_at'].strftime('%Y-%m-%d')}",
            f"tags: [session, terminal]",
            "---",
            "",
            f"# Session: {session['id']}",
            "",
            f"## Summary",
            f"{summary}",
            "",
            f"## Details",
            f"- **Started**: {session['started_at'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Commands**: {len(session['commands'])}",
            f"- **Memory**: [[{memory_id}]]",
            "",
            f"## Commands",
            ""
        ]

        for i, cmd in enumerate(session['commands'], 1):
            lines.extend([
                f"### {i}. `{cmd['command']}`",
                f"",
                f"**Exit Code**: {cmd['exit_code']}",
                f"",
                f"```",
                cmd['output'][:500],  # Limit output
                f"```",
                ""
            ])

        return '\n'.join(lines)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data

        Args:
            session_id: Session ID

        Returns:
            Session data or None
        """
        return self.sessions.get(session_id)

    def list_active_sessions(self) -> List[str]:
        """
        List active session IDs

        Returns:
            List of session IDs
        """
        return list(self.sessions.keys())

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics

        Returns:
            Dict with statistics
        """
        total_commands = sum(
            len(session['commands'])
            for session in self.sessions.values()
        )

        return {
            'active_sessions': len(self.sessions),
            'total_commands': total_commands
        }
