#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Session Manager

Manages working memory sessions for terminal/CLI interactions.
Tracks commands, outputs, and context within a session.

Requirements: Requirements 1, 4 (MVP - CLI Recording, Working Memory)
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
import logging
import uuid
import json
import threading

try:
    from typing import TYPE_CHECKING
except ImportError:  # pragma: no cover
    TYPE_CHECKING = False

if TYPE_CHECKING:  # pragma: no cover
    from src.services.search import SearchService

from src.models import ModelRouter
from src.services.ingestion import IngestionService
from src.services.project_manager import ProjectManager
from src.services.query_attributes import QueryAttributeExtractor, QueryAttributes
from src.services.project_memory_pool import ProjectMemoryPool
from src.services.session_log_collector import SessionLogCollector

logger = logging.getLogger(__name__)


@dataclass
class ProjectPrefetchSettings:
    """Runtime knobs for project-aware cache prefetch."""

    enabled: bool = False
    min_confidence: float = 0.8
    top_k: int = 5
    max_queries: int = 3
    queries: List[str] = field(default_factory=list)


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
        obsidian_vault_path: Optional[str] = None,
        query_attribute_extractor: Optional[QueryAttributeExtractor] = None,
        project_manager: Optional[ProjectManager] = None,
        search_service: Optional["SearchService"] = None,
        project_prefetch_settings: Optional[ProjectPrefetchSettings] = None,
        project_memory_pool: Optional[ProjectMemoryPool] = None,
        session_log_collector: Optional[SessionLogCollector] = None,
    ):
        """
        Initialize Session Manager

        Args:
            ingestion_service: IngestionService instance
            model_router: ModelRouter instance
            obsidian_vault_path: Optional path to Obsidian vault
            project_memory_pool: Optional ProjectMemoryPool for cache warming
        """
        self.ingestion_service = ingestion_service
        self.model_router = model_router
        self.obsidian_vault_path = obsidian_vault_path
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()  # Thread-safe access to sessions dict
        self.query_attribute_extractor = query_attribute_extractor or QueryAttributeExtractor(
            model_router=model_router,
            llm_enabled=False
        )
        self.project_manager = project_manager
        self.search_service = search_service
        self.project_prefetch_settings = project_prefetch_settings or ProjectPrefetchSettings()
        self.project_memory_pool = project_memory_pool
        self.session_log_collector = session_log_collector

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

        with self._lock:
            self.sessions[session_id] = {
                'id': session_id,
                'started_at': datetime.now(),
                'commands': [],
                'last_activity': datetime.now(),
                'project_hint': None,
                'project_hint_confidence': 0.0,
                'project_hint_source': None,
                'project_hint_history': [],
                'prefetched_projects': [],
            }

        self._start_session_log(session_id)

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
        with self._lock:
            if session_id not in self.sessions:
                logger.warning(f"Session not found: {session_id} (reopening)")
                # Temporarily release lock to call start_session
                pass  # start_session will be called outside lock

        if session_id not in self.sessions:
            self.start_session(session_id)

        command_entry = {
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'output': output,
            'exit_code': exit_code,
            'metadata': metadata or {}
        }

        with self._lock:
            self.sessions[session_id]['commands'].append(command_entry)
            self.sessions[session_id]['last_activity'] = datetime.now()

        self._maybe_update_project_from_metadata(session_id, command_entry['metadata'])
        self._maybe_update_project_from_text(session_id, f"{command}\n{output}")
        self._log_command_event(session_id, command_entry)

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
        with self._lock:
            if session_id not in self.sessions:
                logger.warning(f"Session not found: {session_id} (reopening)")
                # Will call start_session outside lock
                pass

        if session_id not in self.sessions:
            self.start_session(session_id)

        with self._lock:
            session = self.sessions[session_id].copy()  # Make a copy to work with outside lock

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
            self._inject_project_metadata(session, conversation)

            # Ingest as memory
            memory_id = self.ingestion_service.ingest_conversation(conversation)

            # Create Obsidian note if requested
            if create_obsidian_note and self.obsidian_vault_path:
                self._create_obsidian_note(session, summary, memory_id)

            # Remove from active sessions
            with self._lock:
                del self.sessions[session_id]

            logger.info(f"Ended session {session_id}, created memory {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return None
        finally:
            if session_id not in self.sessions:
                self._close_session_log(session_id)

    def _start_session_log(self, session_id: str) -> None:
        """Initialize SessionLogCollector for a session if configured."""
        if not self.session_log_collector:
            return

        try:
            self.session_log_collector.start_session(session_id)
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning(f"Failed to initialize session log for {session_id}: {exc}")

    def _log_command_event(self, session_id: str, command_entry: Dict[str, Any]) -> None:
        """Append a command event to SessionLogCollector."""
        if not self.session_log_collector:
            return

        try:
            metadata = dict(command_entry.get('metadata') or {})
            metadata.setdefault('exit_code', command_entry.get('exit_code', 0))
            metadata.setdefault('timestamp', command_entry.get('timestamp'))

            output = command_entry.get('output') or ''
            output_section = output if output.strip() else '<no output>'
            content_lines = [
                f"$ {command_entry.get('command', '').strip()}",
                "",
                "Output:",
                output_section
            ]

            self.session_log_collector.append_event(
                session_id,
                'command',
                '\n'.join(content_lines),
                metadata=metadata
            )
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning(f"Failed to append session log event for {session_id}: {exc}")

    def _close_session_log(self, session_id: str) -> None:
        """Close SessionLogCollector entry when session ends."""
        if not self.session_log_collector:
            return

        try:
            self.session_log_collector.close_session(session_id)
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning(f"Failed to close session log for {session_id}: {exc}")

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

    def get_project_hint(self, session_id: str) -> Tuple[Optional[str], float]:
        session = self.sessions.get(session_id)
        if not session:
            return None, 0.0
        return (
            session.get('project_hint'),
            session.get('project_hint_confidence', 0.0)
        )

    def get_project_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        if not session:
            return None

        project_hint = session.get('project_hint')
        if not project_hint:
            return None

        project_name, project_id = self._resolve_project_context(project_hint)
        return {
            'project_hint': project_hint,
            'project_name': project_name or project_hint,
            'project_id': project_id,
            'confidence': session.get('project_hint_confidence', 0.0),
            'source': session.get('project_hint_source')
        }

    # ------------------------------------------------------------------
    # Project hint helpers
    # ------------------------------------------------------------------

    def update_project_hint(
        self,
        session_id: str,
        project_name: Optional[str],
        confidence: float,
        source: str,
        force: bool = False
    ) -> bool:
        if session_id not in self.sessions or not project_name:
            return False

        session = self.sessions[session_id]
        normalized = self._normalize_project_name(project_name)
        if not normalized:
            return False

        current_conf = session.get('project_hint_confidence', 0.0)
        if not force and current_conf >= confidence:
            return False

        session['project_hint'] = normalized
        session['project_hint_confidence'] = confidence
        session['project_hint_source'] = source
        history = session.setdefault('project_hint_history', [])
        history.append({
            'timestamp': datetime.now().isoformat(),
            'value': normalized,
            'confidence': confidence,
            'source': source
        })
        logger.info(
            "Session %s project hint set to %s (source=%s, confidence=%.2f)",
            session_id,
            normalized,
            source,
            confidence
        )
        self._maybe_trigger_project_prefetch(session_id, normalized, confidence)
        return True

    def set_project_hint(
        self,
        session_id: str,
        project_identifier: Optional[str],
        confidence: float = 0.99,
        source: str = 'manual'
    ) -> bool:
        if not project_identifier:
            return False
        if session_id not in self.sessions:
            return False

        project_name, _ = self._resolve_project_context(project_identifier)
        target = project_name or project_identifier
        confidence = max(confidence, 0.0)
        if confidence == 0:
            confidence = 0.01
        return self.update_project_hint(
            session_id,
            target,
            confidence,
            source,
            force=True
        )

    def clear_project_hint(
        self,
        session_id: str,
        reason: str = 'manual_clear'
    ) -> bool:
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session['project_hint'] = None
        session['project_hint_confidence'] = 0.0
        session['project_hint_source'] = reason
        history = session.setdefault('project_hint_history', [])
        history.append({
            'timestamp': datetime.now().isoformat(),
            'value': None,
            'confidence': 0.0,
            'source': reason
        })
        session['prefetched_projects'] = []
        logger.info("Session %s project hint cleared (%s)", session_id, reason)
        return True

    def _maybe_update_project_from_metadata(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        if not metadata:
            return

        direct = metadata.get('project') or metadata.get('project_name') or metadata.get('project_hint')
        if direct:
            self.update_project_hint(session_id, direct, 0.95, 'metadata')
            return

        project_id = metadata.get('project_id')
        if project_id:
            self.update_project_hint(session_id, project_id, 0.9, 'metadata_id')
            return

        cwd = metadata.get('cwd') or metadata.get('path')
        if cwd:
            match = self._match_project_keyword(cwd)
            if match:
                self.update_project_hint(session_id, match, 0.6, 'cwd')

    def _maybe_update_project_from_text(
        self,
        session_id: str,
        text: str
    ) -> None:
        # DISABLED: QAM extraction causes timeout in mcp_replay due to LLM fallback
        #累積的なLLM呼び出しがOllamaを遅延させ、101回目のリクエストでタイムアウトが発生
        # metadata経由でのproject検知（_maybe_update_project_from_metadata）で十分カバーされている
        # See: タイムアウト調査 2025-11-11
        return

        # 以下のコードは保持（将来の再有効化に備える）
        # if not text or not self.query_attribute_extractor:
        #     return
        #
        # try:
        #     attributes: QueryAttributes = self.query_attribute_extractor.extract(text)
        # except Exception as exc:  # pragma: no cover - defensive
        #     logger.debug("Query attribute extraction failed: %s", exc)
        #     return
        #
        # if not attributes.project_name:
        #     return
        #
        # confidence = attributes.confidence.get('project_name', 0.0) if attributes.confidence else 0.0
        # if confidence <= 0:
        #     confidence = 0.45
        #
        # self.update_project_hint(session_id, attributes.project_name, confidence, 'query_attributes')

    @staticmethod
    def _normalize_project_name(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        val = value.strip()
        if not val:
            return None
        lowered = val.lower()
        for key, canonical in QueryAttributeExtractor.PROJECT_KEYWORDS.items():
            key_lower = key.lower()
            canonical_lower = canonical.lower()
            if key_lower in lowered or lowered == canonical_lower:
                return canonical
        return val

    def _match_project_keyword(self, text: str) -> Optional[str]:
        if not text:
            return None
        lowered = text.lower()
        for key, canonical in QueryAttributeExtractor.PROJECT_KEYWORDS.items():
            if key in lowered or canonical.lower() in lowered:
                return canonical
        return None

    # ------------------------------------------------------------------
    # Project prefetch integration
    # ------------------------------------------------------------------

    def _maybe_trigger_project_prefetch(
        self,
        session_id: str,
        project_hint: str,
        confidence: float
    ) -> None:
        settings = self.project_prefetch_settings
        if not settings or not settings.enabled:
            return
        if confidence < settings.min_confidence:
            return
        if not self.search_service:
            return

        session = self.sessions.get(session_id)
        if not session:
            return

        project_name, project_id = self._resolve_project_context(project_hint)
        if not project_id:
            return

        prefetched_projects: List[str] = session.setdefault('prefetched_projects', [])
        if project_id in prefetched_projects:
            return

        queries = self._collect_prefetch_queries(project_name or project_hint)
        if not queries:
            return

        try:
            stats = self.search_service.prefetch_project(
                project_id=project_id,
                project_name=project_name or project_hint,
                queries=queries,
                top_k=settings.top_k
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Project prefetch failed (session=%s, project=%s): %s",
                session_id,
                project_hint,
                exc
            )
            return

        # Note: prefetch_project now uses dual-strategy cache warming:
        # 1. ProjectMemoryPool.warm_cache() loads all project memories → L3 semantic cache (query-agnostic)
        # 2. Prefetch queries execute search → L1/L2 cache (query-specific)
        # See SearchService.prefetch_project() for implementation details.
        pool_stats = stats.get('pool_stats', {})

        prefetched_projects.append(project_id)
        history = session.setdefault('project_prefetch_history', [])
        history.append({
            'timestamp': datetime.now().isoformat(),
            'project_id': project_id,
            'project_name': project_name or project_hint,
            'queries': queries,
            'stats': stats,
            'pool_stats': pool_stats
        })

        logger.info(
            "Session %s prefetched project %s (queries=%d, cache_hits=+%s, pool_memories=%s)",
            session_id,
            project_id,
            len(queries),
            stats.get('reranker_delta', {}).get('cache_hits', '0'),
            pool_stats.get('memories_loaded', 0)
        )

    def _collect_prefetch_queries(self, project_label: Optional[str]) -> List[str]:
        settings = self.project_prefetch_settings
        if not settings:
            return []

        seeds: List[str] = []
        if project_label:
            seeds.append(project_label.strip())
        seeds.extend(settings.queries or [])

        deduped: List[str] = []
        for seed in seeds:
            normalized = (seed or "").strip()
            if not normalized or normalized in deduped:
                continue
            deduped.append(normalized)
            if settings.max_queries and len(deduped) >= settings.max_queries:
                break
        return deduped

    # ------------------------------------------------------------------
    # Project metadata propagation
    # ------------------------------------------------------------------

    def _inject_project_metadata(
        self,
        session: Dict[str, Any],
        conversation: Dict[str, Any]
    ) -> None:
        project_hint = session.get('project_hint')
        if not project_hint:
            return

        project_name, project_id = self._resolve_project_context(project_hint)
        metadata = conversation.setdefault('metadata', {})

        if project_name and not metadata.get('project'):
            metadata['project'] = project_name

        metadata['project_hint'] = project_name or project_hint
        metadata['project_hint_confidence'] = session.get('project_hint_confidence', 0.0)
        metadata['project_hint_source'] = session.get('project_hint_source')

        if project_id:
            metadata['project_id'] = project_id
            conversation['project_id'] = project_id

    def _resolve_project_context(
        self,
        project_hint: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        if not project_hint:
            return None, None

        normalized_name = self._normalize_project_name(project_hint) or project_hint
        resolved_id: Optional[str] = None

        if self.project_manager:
            # Try interpreting hint as project_id first
            project = self.project_manager.get_project(project_hint)
            if project:
                return project.name, project.id

            project = self.project_manager.get_project_by_name(project_hint)
            if project:
                return project.name, project.id

        if self._looks_like_uuid(project_hint):
            resolved_id = project_hint

        return normalized_name, resolved_id

    @staticmethod
    def _looks_like_uuid(value: Optional[str]) -> bool:
        if not value:
            return False
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, TypeError, AttributeError):
            return False
