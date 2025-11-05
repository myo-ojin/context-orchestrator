#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for SessionSummaryWorker

Tests session summary generation including:
- Job queuing
- Summary generation
- Job processing
- Retry logic with exponential backoff
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path

from src.services.session_summary import SessionSummaryWorker


class TestSessionSummaryWorker:
    """Test suite for SessionSummaryWorker"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for SessionSummaryWorker"""
        model_router = Mock()
        vector_db = Mock()

        return {
            'model_router': model_router,
            'vector_db': vector_db
        }

    @pytest.fixture
    def worker(self, mock_dependencies):
        """Create SessionSummaryWorker instance with mocks"""
        return SessionSummaryWorker(
            model_router=mock_dependencies['model_router'],
            vector_db=mock_dependencies['vector_db'],
            summary_model="qwen2.5:7b"
        )

    @pytest.fixture
    def sample_log_file(self, tmp_path):
        """Create sample log file"""
        log_file = tmp_path / "session-123.log"
        log_content = """Session Log: session-123
Started: 2025-01-15T10:00:00

[2025-01-15T10:00:00] COMMAND
python test.py
--------------------------------------------------------------------------------
All tests passed
--------------------------------------------------------------------------------

[2025-01-15T10:01:00] COMMAND
git status
--------------------------------------------------------------------------------
On branch main
nothing to commit
--------------------------------------------------------------------------------
"""
        log_file.write_text(log_content, encoding='utf-8')
        return log_file

    def test_init(self, worker, mock_dependencies):
        """Test worker initialization"""
        assert worker.model_router == mock_dependencies['model_router']
        assert worker.vector_db == mock_dependencies['vector_db']
        assert worker.summary_model == "qwen2.5:7b"
        assert worker.job_queue == []
        assert worker.failed_jobs == []

    def test_queue_log(self, worker, sample_log_file):
        """Test queuing a log for summarization"""
        result = worker.queue_log(
            "session-123",
            sample_log_file,
            metadata={'start_time': '2025-01-15T10:00:00'}
        )

        assert result is True
        assert len(worker.job_queue) == 1

        job = worker.job_queue[0]
        assert job['session_id'] == "session-123"
        assert job['log_path'] == str(sample_log_file)
        assert job['metadata']['start_time'] == '2025-01-15T10:00:00'

    def test_queue_log_nonexistent_file(self, worker):
        """Test queuing nonexistent log file"""
        result = worker.queue_log(
            "session-123",
            Path("/nonexistent/file.log")
        )

        assert result is False
        assert len(worker.job_queue) == 0

    def test_read_log_file(self, worker, sample_log_file):
        """Test reading log file"""
        content = worker._read_log_file(sample_log_file)

        assert content is not None
        assert "python test.py" in content
        assert "git status" in content

    def test_read_log_file_error(self, worker):
        """Test reading nonexistent log file"""
        content = worker._read_log_file(Path("/nonexistent/file.log"))

        assert content is None

    def test_summarize_log(self, worker, mock_dependencies):
        """Test log summarization"""
        log_content = "python test.py\nAll tests passed\ngit status\nOn branch main"

        mock_dependencies['model_router'].route.return_value = "Ran Python tests and checked git status"

        summary = worker._summarize_log(log_content)

        assert summary == "Ran Python tests and checked git status"
        mock_dependencies['model_router'].route.assert_called_once()

    def test_summarize_log_truncation(self, worker, mock_dependencies):
        """Test log truncation for very long logs"""
        # Create very long log content
        log_content = "x" * 10000

        mock_dependencies['model_router'].route.return_value = "Summary"

        summary = worker._summarize_log(log_content)

        # Verify truncation occurred (content passed to LLM should be shorter)
        call_args = mock_dependencies['model_router'].route.call_args
        prompt = call_args[1]['prompt']

        assert len(prompt) < len(log_content)
        assert "truncated" in prompt

    def test_store_summary(self, worker, mock_dependencies):
        """Test storing summary"""
        mock_dependencies['model_router'].generate_embedding.return_value = [0.1] * 768

        worker._store_summary(
            "session-123",
            "Test summary",
            {'start_time': '2025-01-15T10:00:00'}
        )

        # Verify embedding was generated
        mock_dependencies['model_router'].generate_embedding.assert_called_once_with("Test summary")

        # Verify vector_db.add was called
        mock_dependencies['vector_db'].add.assert_called_once()

        # Verify the ID and metadata
        call_args = mock_dependencies['vector_db'].add.call_args
        assert call_args[1]['id'] == 'session-123-summary'
        assert call_args[1]['document'] == 'Test summary'
        assert call_args[1]['metadata']['session_id'] == 'session-123'

    def test_process_job_success(self, worker, mock_dependencies, sample_log_file):
        """Test successful job processing"""
        job = {
            'session_id': 'session-123',
            'log_path': str(sample_log_file),
            'metadata': {},
            'retry_count': 0
        }

        mock_dependencies['model_router'].route.return_value = "Test summary"
        mock_dependencies['model_router'].generate_embedding.return_value = [0.1] * 768

        result = worker._process_job(job)

        assert result is True

        # Verify all steps were called
        mock_dependencies['model_router'].route.assert_called_once()
        mock_dependencies['model_router'].generate_embedding.assert_called_once()
        mock_dependencies['vector_db'].add.assert_called_once()

    def test_process_job_failure(self, worker, mock_dependencies):
        """Test job processing failure"""
        job = {
            'session_id': 'session-123',
            'log_path': '/nonexistent/file.log',
            'metadata': {},
            'retry_count': 0
        }

        result = worker._process_job(job)

        assert result is False

    def test_run_once(self, worker, mock_dependencies, sample_log_file):
        """Test processing one batch of jobs"""
        # Queue multiple jobs
        worker.queue_log("session-1", sample_log_file)
        worker.queue_log("session-2", sample_log_file)

        mock_dependencies['model_router'].route.return_value = "Summary"
        mock_dependencies['model_router'].generate_embedding.return_value = [0.1] * 768

        stats = worker.run_once()

        assert stats['processed'] == 2
        assert stats['failed'] == 0
        assert len(worker.job_queue) == 0

    def test_handle_failed_job(self, worker):
        """Test handling failed job"""
        job = {
            'session_id': 'session-123',
            'retry_count': 0
        }

        worker._handle_failed_job(job)

        # Verify job was added to failed_jobs
        assert len(worker.failed_jobs) == 1
        assert worker.failed_jobs[0]['retry_count'] == 1
        assert 'last_failure' in worker.failed_jobs[0]

    def test_handle_failed_job_max_retries(self, worker):
        """Test handling job that exceeded max retries"""
        job = {
            'session_id': 'session-123',
            'retry_count': 3  # Already at max
        }

        worker._handle_failed_job(job)

        # Should not be added to retry queue
        assert len(worker.failed_jobs) == 0

    def test_retry_failed_jobs(self, worker, mock_dependencies, sample_log_file):
        """Test retrying failed jobs"""
        # Create failed job with old timestamp
        failed_job = {
            'session_id': 'session-123',
            'log_path': str(sample_log_file),
            'metadata': {},
            'retry_count': 1,
            'last_failure': (datetime.now() - timedelta(seconds=10)).isoformat()
        }

        worker.failed_jobs.append(failed_job)

        mock_dependencies['model_router'].route.return_value = "Summary"
        mock_dependencies['model_router'].generate_embedding.return_value = [0.1] * 768

        retried_count = worker._retry_failed_jobs()

        assert retried_count == 1
        assert len(worker.failed_jobs) == 0

    def test_retry_failed_jobs_not_ready(self, worker):
        """Test that jobs are not retried if backoff time hasn't passed"""
        # Create failed job with recent timestamp
        failed_job = {
            'session_id': 'session-123',
            'log_path': '/some/path.log',
            'metadata': {},
            'retry_count': 1,
            'last_failure': datetime.now().isoformat()
        }

        worker.failed_jobs.append(failed_job)

        retried_count = worker._retry_failed_jobs()

        # Should not retry yet
        assert retried_count == 0
        assert len(worker.failed_jobs) == 1

    def test_get_queue_stats(self, worker, sample_log_file):
        """Test getting queue statistics"""
        # Add to queue
        worker.queue_log("session-1", sample_log_file)
        worker.queue_log("session-2", sample_log_file)

        # Add failed job
        worker.failed_jobs.append({
            'retry_count': 2
        })

        stats = worker.get_queue_stats()

        assert stats['pending'] == 2
        assert stats['failed'] == 1
        assert stats['total_failed_retries'] == 2

    def test_clear_queue(self, worker, sample_log_file):
        """Test clearing job queue"""
        worker.queue_log("session-1", sample_log_file)
        worker.queue_log("session-2", sample_log_file)
        worker.failed_jobs.append({'session_id': 'failed-1'})

        count = worker.clear_queue()

        assert count == 3
        assert len(worker.job_queue) == 0
        assert len(worker.failed_jobs) == 0

    def test_get_session_summary(self, worker, mock_dependencies):
        """Test getting session summary"""
        mock_dependencies['vector_db'].get.return_value = {
            'content': 'Test summary for session'
        }

        summary = worker.get_session_summary('session-123')

        assert summary == 'Test summary for session'
        mock_dependencies['vector_db'].get.assert_called_once_with('session-123-summary')

    def test_get_session_summary_not_found(self, worker, mock_dependencies):
        """Test getting nonexistent session summary"""
        mock_dependencies['vector_db'].get.return_value = None

        summary = worker.get_session_summary('session-123')

        assert summary is None

    def test_exponential_backoff(self, worker):
        """Test exponential backoff calculation"""
        # Retry count 1: 2^1 = 2 seconds
        # Retry count 2: 2^2 = 4 seconds
        # Retry count 3: 2^3 = 8 seconds

        failed_job = {
            'session_id': 'session-123',
            'log_path': '/some/path.log',
            'metadata': {},
            'retry_count': 2,  # 4 seconds backoff
            'last_failure': (datetime.now() - timedelta(seconds=3)).isoformat()
        }

        worker.failed_jobs.append(failed_job)

        # Not enough time passed (3 < 4)
        retried = worker._retry_failed_jobs()
        assert retried == 0

        # Update to 5 seconds ago
        failed_job['last_failure'] = (datetime.now() - timedelta(seconds=5)).isoformat()

        # Mock successful processing
        with patch.object(worker, '_process_job', return_value=True):
            retried = worker._retry_failed_jobs()
            assert retried == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
