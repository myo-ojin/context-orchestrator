#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for ObsidianWatcher

Tests file watching functionality including:
- Watcher initialization
- File change detection
- Conversation ingestion
- Vault scanning
- Graceful shutdown
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from src.services.obsidian_watcher import ObsidianWatcher
from src.services.obsidian_parser import ObsidianParser


class TestObsidianWatcher:
    """Test suite for ObsidianWatcher"""

    @pytest.fixture
    def mock_ingestion_service(self):
        """Create mock ingestion service"""
        service = Mock()
        service.ingest_conversation = Mock(return_value="memory_id_123")
        return service

    @pytest.fixture
    def mock_parser(self):
        """Create mock parser"""
        parser = Mock(spec=ObsidianParser)
        parser.is_conversation_note = Mock(return_value=True)
        parser.parse_file = Mock(return_value={
            'conversations': [
                {'user': 'Test question', 'assistant': 'Test answer', 'index': 0}
            ],
            'wikilinks': ['TestLink'],
            'metadata': {'tags': ['test']},
            'file_path': '/test/file.md',
            'timestamp': '2025-01-15T10:00:00'
        })
        return parser

    @pytest.fixture
    def vault_path(self, tmp_path):
        """Create temporary vault directory"""
        vault = tmp_path / "test_vault"
        vault.mkdir()
        return vault

    def test_initialization_valid_vault(self, vault_path, mock_ingestion_service):
        """Test initialization with valid vault path"""
        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service
        )

        assert watcher.vault_path == str(vault_path)
        assert watcher.ingestion_service == mock_ingestion_service
        assert watcher.is_running is False

    def test_initialization_invalid_vault(self, mock_ingestion_service):
        """Test initialization with invalid vault path"""
        with pytest.raises(ValueError, match="Obsidian vault not found"):
            ObsidianWatcher(
                vault_path="/non/existent/path",
                ingestion_service=mock_ingestion_service
            )

    def test_initialization_file_not_directory(self, tmp_path, mock_ingestion_service):
        """Test initialization with file instead of directory"""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="not a directory"):
            ObsidianWatcher(
                vault_path=str(file_path),
                ingestion_service=mock_ingestion_service
            )

    def test_start_stop(self, vault_path, mock_ingestion_service):
        """Test starting and stopping watcher"""
        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service
        )

        # Start watcher
        watcher.start()
        assert watcher.is_running is True
        assert watcher.observer is not None

        # Stop watcher
        watcher.stop()
        assert watcher.is_running is False

    def test_start_already_running(self, vault_path, mock_ingestion_service):
        """Test starting watcher that is already running"""
        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service
        )

        watcher.start()

        with pytest.raises(RuntimeError, match="already running"):
            watcher.start()

        watcher.stop()

    def test_stop_not_running(self, vault_path, mock_ingestion_service):
        """Test stopping watcher that is not running"""
        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service
        )

        # Should not raise error
        watcher.stop()

    def test_scan_existing_notes(self, vault_path, mock_ingestion_service, mock_parser):
        """Test scanning existing notes in vault"""
        # Create test notes
        (vault_path / "note1.md").write_text(
            "**User:** Q1\n**Assistant:** A1",
            encoding='utf-8'
        )
        (vault_path / "note2.md").write_text(
            "**User:** Q2\n**Assistant:** A2",
            encoding='utf-8'
        )
        (vault_path / "no_conversation.md").write_text(
            "Regular note",
            encoding='utf-8'
        )

        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=mock_parser
        )

        # Scan vault
        watcher.scan_existing_notes()

        # Should call ingest_conversation for each conversation
        assert mock_ingestion_service.ingest_conversation.call_count >= 2

    def test_ingest_file(self, vault_path, mock_ingestion_service, mock_parser):
        """Test ingesting a single file"""
        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=mock_parser
        )

        test_file = vault_path / "test.md"
        test_file.write_text(
            "**User:** Test\n**Assistant:** Answer",
            encoding='utf-8'
        )

        # Manually trigger ingestion
        watcher._ingest_file(str(test_file))

        # Check ingestion was called
        mock_ingestion_service.ingest_conversation.assert_called_once()

        # Check conversation data structure
        call_args = mock_ingestion_service.ingest_conversation.call_args[0][0]
        assert call_args['user'] == 'Test question'
        assert call_args['assistant'] == 'Test answer'
        assert call_args['source'] == 'obsidian'
        assert str(test_file) in call_args['refs']

    def test_ingest_file_multiple_conversations(self, vault_path, mock_ingestion_service):
        """Test ingesting file with multiple conversations"""
        parser = Mock(spec=ObsidianParser)
        parser.is_conversation_note = Mock(return_value=True)
        parser.parse_file = Mock(return_value={
            'conversations': [
                {'user': 'Q1', 'assistant': 'A1', 'index': 0},
                {'user': 'Q2', 'assistant': 'A2', 'index': 1}
            ],
            'wikilinks': [],
            'metadata': {},
            'file_path': '/test/file.md',
            'timestamp': '2025-01-15T10:00:00'
        })

        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=parser
        )

        test_file = vault_path / "multi_conv.md"
        test_file.write_text("test", encoding='utf-8')

        # Manually trigger ingestion
        watcher._ingest_file(str(test_file))

        # Should ingest both conversations
        assert mock_ingestion_service.ingest_conversation.call_count == 2

    def test_ingest_file_no_conversations(self, vault_path, mock_ingestion_service):
        """Test ingesting file with no conversations"""
        parser = Mock(spec=ObsidianParser)
        parser.parse_file = Mock(return_value=None)

        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=parser
        )

        test_file = vault_path / "no_conv.md"
        test_file.write_text("Regular note", encoding='utf-8')

        # Manually trigger ingestion
        watcher._ingest_file(str(test_file))

        # Should not call ingestion
        mock_ingestion_service.ingest_conversation.assert_not_called()

    def test_ingest_file_error_handling(self, vault_path, mock_ingestion_service):
        """Test error handling during file ingestion"""
        parser = Mock(spec=ObsidianParser)
        parser.parse_file = Mock(side_effect=Exception("Parse error"))

        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=parser
        )

        test_file = vault_path / "error.md"
        test_file.write_text("test", encoding='utf-8')

        # Should not raise exception (error logged internally)
        watcher._ingest_file(str(test_file))

        # Should not call ingestion
        mock_ingestion_service.ingest_conversation.assert_not_called()

    def test_context_manager(self, vault_path, mock_ingestion_service):
        """Test context manager protocol"""
        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service
        )

        # Use as context manager
        with watcher as w:
            assert w.is_running is True

        # Should auto-stop after exit
        assert watcher.is_running is False

    def test_file_creation_triggers_ingestion(self, vault_path, mock_ingestion_service, mock_parser):
        """Test that creating a new file triggers ingestion"""
        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=mock_parser
        )

        watcher.start()

        try:
            # Create new file
            new_file = vault_path / "new_conversation.md"
            new_file.write_text(
                "**User:** New question\n**Assistant:** New answer",
                encoding='utf-8'
            )

            # Give watchdog time to detect change
            time.sleep(0.5)

            # Note: In real scenario, ingestion would be triggered
            # But in unit test, we can't easily test watchdog events
            # Integration tests should cover this

        finally:
            watcher.stop()

    def test_scan_subdirectories(self, vault_path, mock_ingestion_service, mock_parser):
        """Test scanning notes in subdirectories"""
        # Create subdirectory with note
        subdir = vault_path / "subfolder"
        subdir.mkdir()
        (subdir / "nested_note.md").write_text(
            "**User:** Nested question\n**Assistant:** Nested answer",
            encoding='utf-8'
        )

        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=mock_parser
        )

        # Scan vault
        watcher.scan_existing_notes()

        # Should find nested notes
        assert mock_ingestion_service.ingest_conversation.call_count >= 1

    def test_metadata_includes_wikilinks(self, vault_path, mock_ingestion_service):
        """Test that ingested data includes Wikilinks in metadata"""
        parser = Mock(spec=ObsidianParser)
        parser.is_conversation_note = Mock(return_value=True)
        parser.parse_file = Mock(return_value={
            'conversations': [
                {'user': 'Q', 'assistant': 'A', 'index': 0}
            ],
            'wikilinks': ['Link1', 'Link2'],
            'metadata': {'tags': ['test']},
            'file_path': '/test/file.md',
            'timestamp': '2025-01-15T10:00:00'
        })

        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=parser
        )

        test_file = vault_path / "test.md"
        test_file.write_text("test", encoding='utf-8')

        # Trigger ingestion
        watcher._ingest_file(str(test_file))

        # Check metadata includes Wikilinks
        call_args = mock_ingestion_service.ingest_conversation.call_args[0][0]
        assert 'wikilinks' in call_args['metadata']
        assert call_args['metadata']['wikilinks'] == ['Link1', 'Link2']

    def test_ignore_non_markdown_files(self, vault_path, mock_ingestion_service, mock_parser):
        """Test that non-Markdown files are ignored"""
        # Create non-markdown files
        (vault_path / "file.txt").write_text("text file")
        (vault_path / "file.json").write_text('{"key": "value"}')
        (vault_path / "file.pdf").write_bytes(b'PDF data')

        watcher = ObsidianWatcher(
            vault_path=str(vault_path),
            ingestion_service=mock_ingestion_service,
            parser=mock_parser
        )

        # Scan vault
        watcher.scan_existing_notes()

        # Should not call ingestion (no .md files)
        mock_ingestion_service.ingest_conversation.assert_not_called()
