#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Obsidian Watcher

File system watcher for Obsidian vault.
Monitors .md file changes and ingests conversations automatically.

Requirements: Requirement 1.5 (Obsidian Integration)
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Set
from threading import Thread, Lock

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from src.services.obsidian_parser import ObsidianParser

logger = logging.getLogger(__name__)


class ObsidianFileHandler(FileSystemEventHandler):
    """
    File system event handler for Obsidian vault

    Detects .md file changes and triggers conversation ingestion.

    Attributes:
        parser: ObsidianParser instance
        ingestion_callback: Callback function for ingestion
        processed_files: Set of recently processed files (debouncing)
        lock: Thread lock for processed_files
    """

    def __init__(self, parser: ObsidianParser, ingestion_callback):
        """
        Initialize file handler

        Args:
            parser: ObsidianParser instance
            ingestion_callback: Callback function (file_path) -> None
        """
        super().__init__()
        self.parser = parser
        self.ingestion_callback = ingestion_callback
        self.processed_files: Set[str] = set()
        self.lock = Lock()

        # Debouncing interval (seconds)
        self.debounce_interval = 2.0

        # Start cleanup thread
        self._start_cleanup_thread()

    def on_modified(self, event):
        """Handle file modification events"""
        if isinstance(event, FileModifiedEvent) and not event.is_directory:
            self._process_file(event.src_path)

    def on_created(self, event):
        """Handle file creation events"""
        if isinstance(event, FileCreatedEvent) and not event.is_directory:
            self._process_file(event.src_path)

    def _process_file(self, file_path: str):
        """
        Process a file change event

        Args:
            file_path: Path to the changed file
        """
        # Only process .md files
        if not file_path.endswith('.md'):
            return

        # Debouncing: Skip if recently processed
        with self.lock:
            if file_path in self.processed_files:
                logger.debug(f"Skipping recently processed file: {file_path}")
                return

            # Mark as processed
            self.processed_files.add(file_path)

        # Check if file contains conversations
        try:
            if not self.parser.is_conversation_note(file_path):
                logger.debug(f"File has no conversations: {file_path}")
                return

            logger.info(f"Detected conversation note: {file_path}")

            # Trigger ingestion
            self.ingestion_callback(file_path)

        except Exception as e:
            logger.error(f"Failed to process file: {file_path} - {e}")

    def _start_cleanup_thread(self):
        """Start background thread to clean up processed_files set"""
        def cleanup():
            while True:
                time.sleep(self.debounce_interval)

                with self.lock:
                    self.processed_files.clear()

        thread = Thread(target=cleanup, daemon=True)
        thread.start()


class ObsidianWatcher:
    """
    Obsidian vault watcher

    Monitors an Obsidian vault for .md file changes and automatically
    ingests conversations through the ingestion service.

    Attributes:
        vault_path: Path to Obsidian vault
        parser: ObsidianParser instance
        observer: watchdog Observer instance
        ingestion_service: IngestionService instance
        is_running: Whether the watcher is active
    """

    def __init__(
        self,
        vault_path: str,
        ingestion_service,  # IngestionService (avoid circular import)
        parser: Optional[ObsidianParser] = None
    ):
        """
        Initialize Obsidian Watcher

        Args:
            vault_path: Path to Obsidian vault
            ingestion_service: IngestionService instance
            parser: Optional ObsidianParser instance (creates if None)

        Raises:
            ValueError: If vault_path doesn't exist
        """
        vault_path = os.path.expanduser(vault_path)

        if not os.path.exists(vault_path):
            raise ValueError(f"Obsidian vault not found: {vault_path}")

        if not os.path.isdir(vault_path):
            raise ValueError(f"Vault path is not a directory: {vault_path}")

        self.vault_path = vault_path
        self.ingestion_service = ingestion_service
        self.parser = parser or ObsidianParser()

        self.observer: Optional[Observer] = None
        self.is_running = False

        logger.info(f"Initialized ObsidianWatcher for vault: {vault_path}")

    def start(self):
        """
        Start watching the Obsidian vault

        Raises:
            RuntimeError: If watcher is already running
        """
        if self.is_running:
            raise RuntimeError("ObsidianWatcher is already running")

        # Create file handler
        handler = ObsidianFileHandler(
            parser=self.parser,
            ingestion_callback=self._ingest_file
        )

        # Create observer
        self.observer = Observer()
        self.observer.schedule(handler, self.vault_path, recursive=True)
        self.observer.start()

        self.is_running = True

        logger.info(f"Started watching vault: {self.vault_path}")

    def stop(self):
        """
        Stop watching the Obsidian vault
        """
        if not self.is_running:
            logger.warning("ObsidianWatcher is not running")
            return

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)

        self.is_running = False

        logger.info("Stopped ObsidianWatcher")

    def scan_existing_notes(self):
        """
        Scan existing notes in vault (one-time import)

        Processes all .md files in the vault that contain conversations.
        Useful for initial import or manual sync.
        """
        logger.info(f"Scanning existing notes in: {self.vault_path}")

        count = 0

        for root, dirs, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)

                    try:
                        if self.parser.is_conversation_note(file_path):
                            self._ingest_file(file_path)
                            count += 1

                    except Exception as e:
                        logger.error(f"Failed to scan file: {file_path} - {e}")

        logger.info(f"Scanned {count} conversation note(s)")

    def _ingest_file(self, file_path: str):
        """
        Ingest a conversation note file

        Args:
            file_path: Path to the .md file
        """
        try:
            # Parse file
            parsed = self.parser.parse_file(file_path)

            if not parsed:
                logger.debug(f"No conversations to ingest: {file_path}")
                return

            # Ingest each conversation
            for conv in parsed['conversations']:
                conversation_data = {
                    'user': conv['user'],
                    'assistant': conv['assistant'],
                    'source': 'obsidian',
                    'refs': [file_path],
                    'metadata': {
                        'file_path': parsed['file_path'],
                        'wikilinks': parsed['wikilinks'],
                        'frontmatter': parsed['metadata'],
                        'conversation_index': conv['index']
                    }
                }

                # Ingest conversation
                memory_id = self.ingestion_service.ingest_conversation(
                    conversation_data
                )

                logger.info(
                    f"Ingested conversation from {file_path} "
                    f"(index {conv['index']}) -> memory_id: {memory_id}"
                )

        except Exception as e:
            logger.error(f"Failed to ingest file: {file_path} - {e}")

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
