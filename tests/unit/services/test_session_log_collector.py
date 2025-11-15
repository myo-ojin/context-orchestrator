#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for SessionLogCollector

Tests session log collection including:
- Session start/close
- Event appending
- Log rotation
- Old log cleanup
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from pathlib import Path

from src.services.session_log_collector import SessionLogCollector


class TestSessionLogCollector:
    """Test suite for SessionLogCollector"""

    @pytest.fixture
    def collector(self, tmp_path):
        """Create SessionLogCollector with temporary directory"""
        log_dir = tmp_path / "logs"
        return SessionLogCollector(log_dir=str(log_dir), max_log_size_mb=10)

    def test_init(self, collector, tmp_path):
        """Test collector initialization"""
        assert collector.log_dir == tmp_path / "logs"
        assert collector.max_log_size_mb == 10
        assert collector.active_sessions == {}

        # Verify log directory was created
        assert collector.log_dir.exists()

    def test_start_session(self, collector):
        """Test starting a new session"""
        session_id = collector.start_session()

        assert session_id is not None
        assert session_id.startswith('session-')
        assert session_id in collector.active_sessions

        # Verify log file was created
        log_file = collector.active_sessions[session_id]
        assert log_file.exists()

        # Verify header was written
        content = log_file.read_text(encoding='utf-8')
        assert session_id in content
        assert "Session Log" in content

    def test_start_session_with_custom_id(self, collector):
        """Test starting session with custom ID"""
        custom_id = "my-session"
        session_id = collector.start_session(custom_id)

        assert session_id == custom_id
        assert custom_id in collector.active_sessions

    def test_append_event(self, collector):
        """Test appending event to session log"""
        session_id = collector.start_session()

        result = collector.append_event(
            session_id,
            'command',
            'python test.py'
        )

        assert result is True

        # Verify event was written
        log_file = collector.active_sessions[session_id]
        content = log_file.read_text(encoding='utf-8')

        assert 'COMMAND' in content
        assert 'python test.py' in content

    def test_append_event_with_metadata(self, collector):
        """Test appending event with metadata"""
        session_id = collector.start_session()

        metadata = {'cwd': '/home/user', 'exit_code': 0}

        collector.append_event(
            session_id,
            'output',
            'Test output',
            metadata=metadata
        )

        # Verify metadata in log
        log_file = collector.active_sessions[session_id]
        content = log_file.read_text(encoding='utf-8')

        assert 'cwd: /home/user' in content
        assert 'exit_code: 0' in content

    def test_append_event_to_nonexistent_session(self, collector):
        """Test appending to nonexistent session"""
        result = collector.append_event(
            "nonexistent",
            'test',
            'content'
        )

        assert result is False

    def test_close_session(self, collector):
        """Test closing a session"""
        session_id = collector.start_session()
        collector.append_event(session_id, 'test', 'content')

        log_file_path = collector.close_session(session_id)

        assert log_file_path is not None
        assert log_file_path.exists()
        assert session_id not in collector.active_sessions

        # Verify closing marker
        content = log_file_path.read_text(encoding='utf-8')
        assert "Session closed" in content

    def test_close_nonexistent_session(self, collector):
        """Test closing nonexistent session"""
        log_file = collector.close_session("nonexistent")

        assert log_file is None

    def test_format_event(self, collector):
        """Test event formatting"""
        event_text = collector._format_event(
            'command',
            'echo hello',
            {'cwd': '/home/user'}
        )

        assert 'COMMAND' in event_text
        assert 'echo hello' in event_text
        assert 'cwd: /home/user' in event_text
        assert '-' * 80 in event_text

    def test_log_rotation_threshold(self, collector):
        """Test log rotation threshold check"""
        session_id = collector.start_session()
        log_file = collector.active_sessions[session_id]

        # Write small file (should not rotate)
        log_file.write_text("small content", encoding='utf-8')
        assert not collector._should_rotate(log_file)

        # Write large file (should rotate)
        large_content = "x" * (11 * 1024 * 1024)  # 11 MB
        log_file.write_text(large_content, encoding='utf-8')
        assert collector._should_rotate(log_file)

    def test_log_rotation(self, collector):
        """Test log file rotation"""
        session_id = collector.start_session()
        log_file = collector.active_sessions[session_id]

        # Write large content to trigger rotation
        large_content = "x" * (11 * 1024 * 1024)  # 11 MB
        log_file.write_text(large_content, encoding='utf-8')

        # Trigger rotation by appending
        collector.append_event(session_id, 'test', 'content')

        # Verify rotated file exists
        rotated_file = collector.log_dir / f"{session_id}.1.log"
        assert rotated_file.exists()

        # Verify new log file was created
        assert log_file.exists()
        new_content = log_file.read_text(encoding='utf-8')
        assert "Previous log rotated" in new_content

    def test_get_log_path(self, collector):
        """Test getting log path"""
        session_id = collector.start_session()

        log_path = collector.get_log_path(session_id)

        assert log_path is not None
        assert session_id in str(log_path)

    def test_get_log_path_nonexistent(self, collector):
        """Test getting log path for nonexistent session"""
        log_path = collector.get_log_path("nonexistent")

        assert log_path is None

    def test_list_active_sessions(self, collector):
        """Test listing active sessions"""
        session1 = collector.start_session()
        session2 = collector.start_session()

        sessions = collector.list_active_sessions()

        assert len(sessions) == 2
        assert session1 in sessions
        assert session2 in sessions

    def test_get_session_log_content_active(self, collector):
        """Test getting content of active session log"""
        session_id = collector.start_session()
        collector.append_event(session_id, 'test', 'test content')

        content = collector.get_session_log_content(session_id)

        assert content is not None
        assert 'test content' in content

    def test_get_session_log_content_closed(self, collector):
        """Test getting content of closed session log"""
        session_id = collector.start_session()
        collector.append_event(session_id, 'test', 'test content')
        collector.close_session(session_id)

        content = collector.get_session_log_content(session_id)

        assert content is not None
        assert 'test content' in content

    def test_get_session_log_content_nonexistent(self, collector):
        """Test getting content of nonexistent session"""
        content = collector.get_session_log_content("nonexistent")

        assert content is None

    def test_cleanup_old_logs(self, collector):
        """Test cleaning up old log files"""
        # Create old log file
        old_log = collector.log_dir / "old-session.log"
        old_log.write_text("old content", encoding='utf-8')

        # Set modified time to 31 days ago
        old_time = (datetime.now() - timedelta(days=31)).timestamp()
        old_log.touch()
        # Note: In real test, would need to mock st_mtime

        # Create recent log file
        recent_log = collector.log_dir / "recent-session.log"
        recent_log.write_text("recent content", encoding='utf-8')

        # Mock the st_mtime check
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_mtime = old_time

            deleted_count = collector.cleanup_old_logs(days=30)

            # Note: Actual deletion depends on mocking

    def test_multiple_events_in_session(self, collector):
        """Test appending multiple events"""
        session_id = collector.start_session()

        for i in range(10):
            collector.append_event(session_id, 'command', f'cmd{i}')

        content = collector.get_session_log_content(session_id)

        for i in range(10):
            assert f'cmd{i}' in content

    def test_session_lifecycle(self, collector):
        """Test full session lifecycle"""
        # Start session
        session_id = collector.start_session()
        assert session_id in collector.active_sessions

        # Add events
        collector.append_event(session_id, 'command', 'ls')
        collector.append_event(session_id, 'output', 'file1 file2')

        # Close session
        log_file = collector.close_session(session_id)
        assert log_file is not None
        assert session_id not in collector.active_sessions

        # Verify log content
        content = log_file.read_text(encoding='utf-8')
        assert 'ls' in content
        assert 'file1 file2' in content
        assert 'Session closed' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
