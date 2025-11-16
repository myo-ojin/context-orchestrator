#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for SessionManager

Tests session management functionality including:
- Session lifecycle (start, add commands, end)
- Session log formatting
- Summary generation
- Obsidian note creation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from src.services.session_manager import SessionManager, ProjectPrefetchSettings
from src.services.query_attributes import QueryAttributes


class TestSessionManager:
    """Test suite for SessionManager"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for SessionManager"""
        ingestion_service = Mock()
        model_router = Mock()

        return {
            'ingestion_service': ingestion_service,
            'model_router': model_router
        }

    @pytest.fixture
    def manager(self, mock_dependencies):
        """Create SessionManager instance with mocks"""
        return SessionManager(
            ingestion_service=mock_dependencies['ingestion_service'],
            model_router=mock_dependencies['model_router'],
            obsidian_vault_path=None
        )

    @pytest.fixture
    def manager_with_vault(self, mock_dependencies, tmp_path):
        """Create SessionManager with Obsidian vault"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        return SessionManager(
            ingestion_service=mock_dependencies['ingestion_service'],
            model_router=mock_dependencies['model_router'],
            obsidian_vault_path=str(vault_path)
        )

    @pytest.fixture
    def manager_with_project_manager(self, mock_dependencies):
        """Create SessionManager with a mock ProjectManager"""
        project_manager = Mock()
        manager = SessionManager(
            ingestion_service=mock_dependencies['ingestion_service'],
            model_router=mock_dependencies['model_router'],
            obsidian_vault_path=None,
            project_manager=project_manager
        )
        return manager, project_manager

    @pytest.fixture
    def log_collector(self):
        collector = Mock()
        collector.log_dir = Path("/tmp")
        return collector

    def test_init(self, manager, mock_dependencies):
        """Test manager initialization"""
        assert manager.ingestion_service == mock_dependencies['ingestion_service']
        assert manager.model_router == mock_dependencies['model_router']
        assert manager.obsidian_vault_path is None
        assert manager.sessions == {}

    def test_start_session(self, manager):
        """Test starting a new session"""
        session_id = manager.start_session()

        assert session_id is not None
        assert session_id.startswith('session-')
        assert session_id in manager.sessions
        assert 'started_at' in manager.sessions[session_id]
        assert 'commands' in manager.sessions[session_id]
        assert manager.sessions[session_id]['project_hint'] is None
        assert manager.sessions[session_id]['project_hint_confidence'] == 0.0

    def test_start_session_with_custom_id(self, manager):
        """Test starting session with custom ID"""
        custom_id = "my-custom-session"
        session_id = manager.start_session(custom_id)

        assert session_id == custom_id
        assert custom_id in manager.sessions

    def test_start_session_notifies_log_collector(self, mock_dependencies, log_collector):
        manager = SessionManager(
            ingestion_service=mock_dependencies['ingestion_service'],
            model_router=mock_dependencies['model_router'],
            session_log_collector=log_collector
        )

        session_id = manager.start_session("session-log-test")

        log_collector.start_session.assert_called_once_with("session-log-test")
        assert session_id == "session-log-test"

    def test_add_command(self, manager):
        """Test adding command to session"""
        session_id = manager.start_session()

        result = manager.add_command(
            session_id,
            "python test.py",
            "All tests passed",
            exit_code=0
        )

        assert result is True
        assert len(manager.sessions[session_id]['commands']) == 1

        command = manager.sessions[session_id]['commands'][0]
        assert command['command'] == "python test.py"
        assert command['output'] == "All tests passed"
        assert command['exit_code'] == 0

    def test_add_command_appends_log_event(self, mock_dependencies, log_collector):
        manager = SessionManager(
            ingestion_service=mock_dependencies['ingestion_service'],
            model_router=mock_dependencies['model_router'],
            session_log_collector=log_collector
        )

        session_id = manager.start_session("session-log")
        manager.add_command(
            session_id,
            "echo test",
            "test",
            exit_code=0,
            metadata={'cwd': '/tmp'}
        )

        log_collector.append_event.assert_called_once()
        args, kwargs = log_collector.append_event.call_args
        assert args[0] == "session-log"
        assert args[1] == "command"

    def test_add_command_updates_project_from_metadata(self, manager):
        session_id = manager.start_session()
        manager.add_command(
            session_id,
            "deploy",
            "ok",
            metadata={'project': 'OrchestratorX'}
        )
        hint, confidence = manager.get_project_hint(session_id)
        assert hint == "OrchestratorX"
        assert confidence >= 0.9

    def test_add_command_does_not_update_project_from_text_when_disabled(self, manager):
        session_id = manager.start_session()
        fake_attrs = QueryAttributes(project_name="BugFixer")
        fake_attrs.confidence = {'project_name': 0.5}
        manager.query_attribute_extractor = Mock()
        manager.query_attribute_extractor.extract.return_value = fake_attrs

        manager.add_command(session_id, "git status", "output")

        hint, confidence = manager.get_project_hint(session_id)
        assert hint is None
        assert confidence == 0.0

    def test_project_prefetch_runs_once_until_cleared(self, mock_dependencies):
        search_service = Mock()
        project_manager = Mock()
        project_manager.get_project.return_value = None
        project_manager.get_project_by_name.return_value = SimpleNamespace(
            name="OrchestratorX",
            id="proj-appbrain"
        )

        manager = SessionManager(
            ingestion_service=mock_dependencies['ingestion_service'],
            model_router=mock_dependencies['model_router'],
            project_manager=project_manager,
            search_service=search_service,
            project_prefetch_settings=ProjectPrefetchSettings(
                enabled=True,
                min_confidence=0.8,
                top_k=3,
                max_queries=2,
                queries=["launch checklist"]
            )
        )

        session_id = manager.start_session()
        manager.update_project_hint(session_id, "OrchestratorX", 0.9, "metadata")
        search_service.prefetch_project.assert_called_once()

        # Updating with same project should not trigger until cleared.
        manager.update_project_hint(session_id, "OrchestratorX", 0.95, "metadata")
        assert search_service.prefetch_project.call_count == 1

        # Clearing resets guard so new prefetch can run.
        manager.clear_project_hint(session_id)
        manager.update_project_hint(session_id, "OrchestratorX", 0.9, "metadata")
        assert search_service.prefetch_project.call_count == 2

    def test_update_project_hint_prefers_higher_confidence(self, manager):
        session_id = manager.start_session()
        manager.update_project_hint(session_id, "BugFixer", 0.4, "test")
        manager.update_project_hint(session_id, "OrchestratorX", 0.9, "metadata")

        hint, confidence = manager.get_project_hint(session_id)
        assert hint == "OrchestratorX"
        assert confidence == 0.9

        # Lower confidence should not overwrite
        manager.update_project_hint(session_id, "BugFixer", 0.5, "later")
        hint, confidence = manager.get_project_hint(session_id)
        assert hint == "OrchestratorX"

    def test_add_command_to_nonexistent_session(self, manager):
        """Test adding command to nonexistent session"""
        result = manager.add_command(
            "nonexistent-session",
            "test command",
            "output"
        )

        assert result is False

    def test_add_command_with_metadata(self, manager):
        """Test adding command with metadata"""
        session_id = manager.start_session()

        metadata = {'cwd': '/home/user', 'env': {'PATH': '/usr/bin'}}

        manager.add_command(
            session_id,
            "ls",
            "file1.txt file2.txt",
            metadata=metadata
        )

        command = manager.sessions[session_id]['commands'][0]
        assert command['metadata'] == metadata

    def test_end_session(self, manager, mock_dependencies):
        """Test ending a session"""
        session_id = manager.start_session()
        manager.add_command(session_id, "echo hello", "hello", exit_code=0)

        # Mock ingestion service
        mock_dependencies['ingestion_service'].ingest_conversation.return_value = "mem-123"

        # Mock summary generation
        mock_dependencies['model_router'].route.return_value = "Test session summary"

        memory_id = manager.end_session(session_id)

        assert memory_id == "mem-123"
        assert session_id not in manager.sessions

        # Verify ingestion was called
        mock_dependencies['ingestion_service'].ingest_conversation.assert_called_once()

    def test_end_session_closes_log(self, mock_dependencies, log_collector):
        manager = SessionManager(
            ingestion_service=mock_dependencies['ingestion_service'],
            model_router=mock_dependencies['model_router'],
            session_log_collector=log_collector
        )
        mock_dependencies['ingestion_service'].ingest_conversation.return_value = "mem-closed"
        mock_dependencies['model_router'].route.return_value = "summary"

        session_id = manager.start_session("session-close")
        manager.add_command(session_id, "echo ok", "ok", exit_code=0)

        manager.end_session(session_id)

        log_collector.close_session.assert_called_once_with("session-close")

    def test_end_session_nonexistent(self, manager):
        """Test ending nonexistent session"""
        memory_id = manager.end_session("nonexistent-session")

        assert memory_id is None

    def test_format_session_log(self, manager):
        """Test session log formatting"""
        session_id = manager.start_session()
        manager.add_command(session_id, "echo test", "test", exit_code=0)
        manager.add_command(session_id, "ls", "file1 file2", exit_code=0)

        session = manager.sessions[session_id]
        log = manager._format_session_log(session)

        assert f"# Session {session_id}" in log
        assert "echo test" in log
        assert "ls" in log
        assert "Exit Code" in log  # Changed from "Exit Code: 0" to "Exit Code" (format is "**Exit Code**: 0")

    def test_generate_summary(self, manager, mock_dependencies):
        """Test summary generation"""
        session_id = manager.start_session()
        manager.add_command(session_id, "python test.py", "OK", exit_code=0)

        mock_dependencies['model_router'].route.return_value = "Ran Python tests successfully"

        session = manager.sessions[session_id]
        summary = manager._generate_summary(session)

        assert summary == "Ran Python tests successfully"
        mock_dependencies['model_router'].route.assert_called_once()

    def test_generate_summary_failure(self, manager, mock_dependencies):
        """Test summary generation with LLM failure"""
        session_id = manager.start_session()
        manager.add_command(session_id, "test command", "output", exit_code=0)

        # Make LLM fail
        mock_dependencies['model_router'].route.side_effect = Exception("LLM error")

        session = manager.sessions[session_id]
        summary = manager._generate_summary(session)

        # Should fallback to first command
        assert "test command" in summary

    def test_create_obsidian_note(self, manager_with_vault, mock_dependencies):
        """Test Obsidian note creation"""
        session_id = manager_with_vault.start_session()
        manager_with_vault.add_command(session_id, "test", "output", exit_code=0)

        session = manager_with_vault.sessions[session_id]
        summary = "Test summary"
        memory_id = "mem-123"

        result = manager_with_vault._create_obsidian_note(session, summary, memory_id)

        assert result is True

        # Verify file was created
        vault_path = Path(manager_with_vault.obsidian_vault_path)
        sessions_dir = vault_path / "Sessions"

        assert sessions_dir.exists()
        assert len(list(sessions_dir.glob("*.md"))) > 0

    def test_create_obsidian_note_no_vault(self, manager):
        """Test Obsidian note creation without vault path"""
        session_id = manager.start_session()
        session = manager.sessions[session_id]

        result = manager._create_obsidian_note(session, "summary", "mem-123")

        assert result is False

    def test_build_obsidian_note_content(self, manager):
        """Test Obsidian note content generation"""
        session_id = manager.start_session()
        manager.add_command(session_id, "echo test", "test", exit_code=0)

        session = manager.sessions[session_id]
        content = manager._build_obsidian_note_content(
            session,
            "Test summary",
            "mem-123"
        )

        assert f"session_id: {session_id}" in content
        assert "memory_id: mem-123" in content
        assert "Test summary" in content
        assert "echo test" in content

    def test_get_session(self, manager):
        """Test getting session data"""
        session_id = manager.start_session()

        session = manager.get_session(session_id)

        assert session is not None
        assert session['id'] == session_id

    def test_get_nonexistent_session(self, manager):
        """Test getting nonexistent session"""
        session = manager.get_session("nonexistent")

        assert session is None

    def test_list_active_sessions(self, manager):
        """Test listing active sessions"""
        session1 = manager.start_session()
        session2 = manager.start_session()

        sessions = manager.list_active_sessions()

        assert len(sessions) == 2
        assert session1 in sessions
        assert session2 in sessions

    def test_get_session_stats(self, manager):
        """Test getting session statistics"""
        session1 = manager.start_session()
        session2 = manager.start_session()

        manager.add_command(session1, "cmd1", "out1")
        manager.add_command(session1, "cmd2", "out2")
        manager.add_command(session2, "cmd3", "out3")

        stats = manager.get_session_stats()

        assert stats['active_sessions'] == 2
        assert stats['total_commands'] == 3

    def test_get_project_context_none_without_hint(self, manager):
        session_id = manager.start_session()
        assert manager.get_project_context(session_id) is None

    def test_get_project_context_with_resolved_project(self, manager_with_project_manager):
        manager, project_manager = manager_with_project_manager
        session_id = manager.start_session()
        fake_project = SimpleNamespace(id="proj-abc", name="OrchestratorX")
        project_manager.get_project.return_value = fake_project
        manager.update_project_hint(session_id, fake_project.id, 0.8, "metadata")

        context = manager.get_project_context(session_id)

        assert context['project_id'] == fake_project.id
        assert context['project_name'] == fake_project.name
        assert context['confidence'] == 0.8

    def test_set_project_hint_overrides_existing(self, manager):
        session_id = manager.start_session()
        manager.update_project_hint(session_id, "OrchestratorX", 0.9, "metadata")

        manager.set_project_hint(session_id, "BugFixer", confidence=0.5)

        hint, confidence = manager.get_project_hint(session_id)
        assert hint == "BugFixer"
        assert confidence == 0.5

    def test_clear_project_hint(self, manager):
        session_id = manager.start_session()
        manager.update_project_hint(session_id, "OrchestratorX", 0.9, "metadata")

        cleared = manager.clear_project_hint(session_id)

        assert cleared is True
        hint, confidence = manager.get_project_hint(session_id)
        assert hint is None
        assert confidence == 0.0

    def test_end_session_injects_project_metadata(self, mock_dependencies, manager_with_project_manager):
        """Session end should propagate project metadata to ingestion payload."""
        manager, project_manager = manager_with_project_manager
        session_id = manager.start_session()
        manager.add_command(
            session_id,
            "deploy --project appbrain",
            "ok",
            metadata={'project': 'OrchestratorX'}
        )

        fake_project = MagicMock()
        fake_project.id = "proj-123"
        fake_project.name = "OrchestratorX"
        project_manager.get_project.return_value = None
        project_manager.get_project_by_name.return_value = fake_project

        mock_dependencies['model_router'].route.return_value = "Session summary"
        mock_dependencies['ingestion_service'].ingest_conversation.return_value = "mem-xyz"

        memory_id = manager.end_session(session_id)

        assert memory_id == "mem-xyz"
        project_manager.get_project.assert_called_once_with("OrchestratorX")
        project_manager.get_project_by_name.assert_called_once_with("OrchestratorX")

        args, _ = mock_dependencies['ingestion_service'].ingest_conversation.call_args
        payload = args[0]
        assert payload['project_id'] == fake_project.id
        metadata = payload['metadata']
        assert metadata['project'] == "OrchestratorX"
        assert metadata['project_id'] == fake_project.id
        assert metadata['project_hint'] == "OrchestratorX"
        assert metadata['project_hint_confidence'] >= 0.9
        assert metadata['project_hint_source'] in ("metadata", "metadata_id")

    def test_multiple_commands_in_session(self, manager):
        """Test adding multiple commands to a session"""
        session_id = manager.start_session()

        for i in range(10):
            manager.add_command(
                session_id,
                f"command {i}",
                f"output {i}",
                exit_code=0
            )

        assert len(manager.sessions[session_id]['commands']) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
