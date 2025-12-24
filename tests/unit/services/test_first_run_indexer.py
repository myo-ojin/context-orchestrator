#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for First-Run Indexer

Tests first-run indexing including:
- Flag check and creation
- File scanning with size limits
- Checkpoint and resume functionality
- Skip when flag exists
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
from datetime import datetime

from src.services.first_run_indexer import (
    check_first_run_flag,
    mark_first_run_complete,
    should_run_first_run_indexing,
    scan_log_directory,
    IndexingCheckpoint,
    filter_unprocessed_files,
    run_first_run_indexing
)


class TestFirstRunFlag:
    """Test suite for first-run flag operations"""

    def test_check_first_run_flag_not_exists(self, tmp_path):
        """Test flag check when file doesn't exist"""
        assert check_first_run_flag(str(tmp_path)) is False

    def test_check_first_run_flag_exists(self, tmp_path):
        """Test flag check when file exists"""
        flag_file = tmp_path / 'first_run_index_done'
        flag_file.write_text(datetime.now().isoformat())

        assert check_first_run_flag(str(tmp_path)) is True

    def test_mark_first_run_complete(self, tmp_path):
        """Test marking first-run as complete"""
        mark_first_run_complete(str(tmp_path))

        flag_file = tmp_path / 'first_run_index_done'
        assert flag_file.exists()

        # Verify content is valid ISO timestamp
        content = flag_file.read_text(encoding='utf-8')
        datetime.fromisoformat(content)  # Should not raise


class TestShouldRunFirstRunIndexing:
    """Test suite for should_run_first_run_indexing"""

    def test_disabled_in_config(self, tmp_path):
        """Test when feature is disabled"""
        result = should_run_first_run_indexing(str(tmp_path), enabled=False)
        assert result is False

    def test_already_completed(self, tmp_path):
        """Test when first-run already completed"""
        mark_first_run_complete(str(tmp_path))
        result = should_run_first_run_indexing(str(tmp_path), enabled=True)
        assert result is False

    def test_non_interactive_without_auto(self, tmp_path, monkeypatch):
        """Non-interactive stdin without CO_FIRST_RUN_AUTO should skip but not set flag"""
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        monkeypatch.delenv("CO_FIRST_RUN_AUTO", raising=False)

        result = should_run_first_run_indexing(str(tmp_path), enabled=True)
        assert result is False
        # Flag should NOT be created automatically
        assert check_first_run_flag(str(tmp_path)) is False

    def test_non_interactive_with_auto(self, tmp_path, monkeypatch):
        """Non-interactive stdin with CO_FIRST_RUN_AUTO=1 should run"""
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        monkeypatch.setenv("CO_FIRST_RUN_AUTO", "1")

        result = should_run_first_run_indexing(str(tmp_path), enabled=True)
        assert result is True


class TestScanLogDirectory:
    """Test suite for scan_log_directory"""

    @pytest.fixture
    def log_dir(self, tmp_path):
        """Create temporary log directory with test files"""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        return log_dir

    def test_scan_empty_directory(self, log_dir):
        """Test scanning empty directory"""
        candidates, total_bytes = scan_log_directory(
            str(log_dir),
            max_file_size_mb=100,
            allowed_extensions=['.log', '.jsonl']
        )

        assert len(candidates) == 0
        assert total_bytes == 0

    def test_scan_with_valid_files(self, log_dir):
        """Test scanning directory with valid log files"""
        # Create test files
        (log_dir / "session1.log").write_text("Test log 1", encoding='utf-8')
        (log_dir / "session2.log").write_text("Test log 2", encoding='utf-8')
        (log_dir / "session3.jsonl").write_text("Test log 3", encoding='utf-8')

        candidates, total_bytes = scan_log_directory(
            str(log_dir),
            max_file_size_mb=100,
            allowed_extensions=['.log', '.jsonl']
        )

        assert len(candidates) == 3
        assert total_bytes > 0

    def test_scan_filters_by_extension(self, log_dir):
        """Test that files are filtered by extension"""
        # Create test files with different extensions
        (log_dir / "session1.log").write_text("Test log", encoding='utf-8')
        (log_dir / "session2.txt").write_text("Test text", encoding='utf-8')
        (log_dir / "session3.json").write_text("Test json", encoding='utf-8')

        candidates, total_bytes = scan_log_directory(
            str(log_dir),
            max_file_size_mb=100,
            allowed_extensions=['.log']
        )

        assert len(candidates) == 1
        assert candidates[0].suffix == '.log'

    def test_scan_filters_by_size(self, log_dir):
        """Test that large files are filtered out"""
        # Create small file
        (log_dir / "small.log").write_text("Small", encoding='utf-8')

        # Create large file (2MB)
        large_content = "x" * (2 * 1024 * 1024)
        (log_dir / "large.log").write_text(large_content, encoding='utf-8')

        # Scan with 1MB limit
        candidates, total_bytes = scan_log_directory(
            str(log_dir),
            max_file_size_mb=1,
            allowed_extensions=['.log']
        )

        # Only small file should be included
        assert len(candidates) == 1
        assert candidates[0].name == "small.log"

    def test_scan_ignores_hidden_files(self, log_dir):
        """Test that hidden files are ignored"""
        (log_dir / "visible.log").write_text("Visible", encoding='utf-8')
        (log_dir / ".hidden.log").write_text("Hidden", encoding='utf-8')

        candidates, total_bytes = scan_log_directory(
            str(log_dir),
            max_file_size_mb=100,
            allowed_extensions=['.log']
        )

        assert len(candidates) == 1
        assert candidates[0].name == "visible.log"

    def test_scan_ignores_temp_files(self, log_dir):
        """Test that temp files are ignored"""
        (log_dir / "session.log").write_text("Normal", encoding='utf-8')
        (log_dir / "session.tmp").write_text("Temp", encoding='utf-8')

        candidates, total_bytes = scan_log_directory(
            str(log_dir),
            max_file_size_mb=100,
            allowed_extensions=['.log', '.tmp']
        )

        # .tmp should be ignored despite being in allowed_extensions
        assert len(candidates) == 1
        assert candidates[0].suffix == '.log'


class TestIndexingCheckpoint:
    """Test suite for IndexingCheckpoint"""

    @pytest.fixture
    def checkpoint(self, tmp_path):
        """Create checkpoint instance"""
        return IndexingCheckpoint(str(tmp_path))

    def test_init_no_existing_checkpoint(self, checkpoint, tmp_path):
        """Test initialization with no existing checkpoint"""
        assert checkpoint.processed == {}
        checkpoint_file = tmp_path / 'first_run_index_checkpoint.json'
        assert not checkpoint_file.exists()

    def test_save_and_load_checkpoint(self, tmp_path):
        """Test saving and loading checkpoint"""
        # Create and save checkpoint
        checkpoint1 = IndexingCheckpoint(str(tmp_path))
        test_file = tmp_path / "test.log"
        test_file.write_text("test", encoding='utf-8')

        checkpoint1.mark_processed(test_file)
        checkpoint1.save()

        # Load in new instance
        checkpoint2 = IndexingCheckpoint(str(tmp_path))

        assert str(test_file) in checkpoint2.processed
        assert checkpoint2.is_processed(test_file) is True

    def test_is_processed_unchanged_file(self, checkpoint, tmp_path):
        """Test is_processed for unchanged file"""
        test_file = tmp_path / "test.log"
        test_file.write_text("test", encoding='utf-8')

        # Mark as processed
        checkpoint.mark_processed(test_file)

        # Should return True for unchanged file
        assert checkpoint.is_processed(test_file) is True

    def test_is_processed_changed_file(self, checkpoint, tmp_path):
        """Test is_processed for changed file"""
        test_file = tmp_path / "test.log"
        test_file.write_text("original", encoding='utf-8')

        # Mark as processed
        checkpoint.mark_processed(test_file)

        # Modify file
        test_file.write_text("modified content", encoding='utf-8')

        # Should return False for changed file
        assert checkpoint.is_processed(test_file) is False

    def test_clear_checkpoint(self, checkpoint, tmp_path):
        """Test clearing checkpoint"""
        test_file = tmp_path / "test.log"
        test_file.write_text("test", encoding='utf-8')

        checkpoint.mark_processed(test_file)
        checkpoint.save()

        checkpoint.clear()

        assert checkpoint.processed == {}
        checkpoint_file = tmp_path / 'first_run_index_checkpoint.json'
        assert not checkpoint_file.exists()


class TestFilterUnprocessedFiles:
    """Test suite for filter_unprocessed_files"""

    def test_filter_all_unprocessed(self, tmp_path):
        """Test filtering when all files are unprocessed"""
        checkpoint = IndexingCheckpoint(str(tmp_path))

        files = [
            tmp_path / "file1.log",
            tmp_path / "file2.log",
        ]
        for f in files:
            f.write_text("test", encoding='utf-8')

        unprocessed = filter_unprocessed_files(files, checkpoint)

        assert len(unprocessed) == 2

    def test_filter_some_processed(self, tmp_path):
        """Test filtering when some files are processed"""
        checkpoint = IndexingCheckpoint(str(tmp_path))

        file1 = tmp_path / "file1.log"
        file2 = tmp_path / "file2.log"
        file1.write_text("test", encoding='utf-8')
        file2.write_text("test", encoding='utf-8')

        # Mark file1 as processed
        checkpoint.mark_processed(file1)

        files = [file1, file2]
        unprocessed = filter_unprocessed_files(files, checkpoint)

        assert len(unprocessed) == 1
        assert unprocessed[0] == file2


class TestRunFirstRunIndexing:
    """Test suite for run_first_run_indexing"""

    @pytest.fixture
    def mock_ingestion_service(self):
        """Create mock ingestion service"""
        mock = MagicMock()
        mock.ingest_conversation.return_value = "mem-test123"
        return mock

    @pytest.fixture
    def log_dir_with_files(self, tmp_path):
        """Create log directory with test files"""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        # Create test log files
        (log_dir / "session1.log").write_text("Session log 1", encoding='utf-8')
        (log_dir / "session2.log").write_text("Session log 2", encoding='utf-8')

        return log_dir

    def test_run_no_files(self, tmp_path, mock_ingestion_service):
        """Test running when no log files exist"""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        result = run_first_run_indexing(
            data_dir=str(tmp_path),
            session_log_dir=str(log_dir),
            ingestion_service=mock_ingestion_service,
            auto_approve=True
        )

        assert result is True
        assert check_first_run_flag(str(tmp_path)) is True

    def test_run_with_files_auto_approve(self, tmp_path, log_dir_with_files, mock_ingestion_service):
        """Test running with files and auto-approve"""
        result = run_first_run_indexing(
            data_dir=str(tmp_path),
            session_log_dir=str(log_dir_with_files),
            ingestion_service=mock_ingestion_service,
            auto_approve=True
        )

        assert result is True
        assert check_first_run_flag(str(tmp_path)) is True

        # Verify ingestion was called
        assert mock_ingestion_service.ingest_conversation.call_count == 2

    def test_resume_after_partial_completion(self, tmp_path, log_dir_with_files, mock_ingestion_service):
        """Test resuming after partial completion"""
        # Create checkpoint with one file processed
        checkpoint = IndexingCheckpoint(str(tmp_path))
        file1 = log_dir_with_files / "session1.log"
        checkpoint.mark_processed(file1)
        checkpoint.save()

        result = run_first_run_indexing(
            data_dir=str(tmp_path),
            session_log_dir=str(log_dir_with_files),
            ingestion_service=mock_ingestion_service,
            auto_approve=True
        )

        assert result is True

        # Only one file should be ingested (the unprocessed one)
        assert mock_ingestion_service.ingest_conversation.call_count == 1
