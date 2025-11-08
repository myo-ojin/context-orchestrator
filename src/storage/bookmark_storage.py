#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bookmark Storage

Provides persistent storage for SearchBookmark metadata using JSON.
Enables saving frequently used searches for quick access.

Requirements: Phase 15 - Search Enhancement
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
from datetime import datetime

from src.models import SearchBookmark

logger = logging.getLogger(__name__)


class BookmarkStorage:
    """
    Bookmark storage with JSON persistence

    Manages search bookmark storage in a human-readable JSON file.
    Bookmarks are stored in-memory and persisted to disk after each modification.

    Attributes:
        persist_path: Path to JSON file for persistence
        bookmarks: Dict mapping bookmark_id to SearchBookmark instance
    """

    def __init__(self, persist_path: str):
        """
        Initialize bookmark storage

        Args:
            persist_path: Path to JSON file (e.g., ~/.context-orchestrator/bookmarks.json)
        """
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory storage
        self.bookmarks: Dict[str, SearchBookmark] = {}

        # Load existing bookmarks if available
        self._load()

        logger.info(f"Initialized BookmarkStorage at {self.persist_path}")
        logger.info(f"Loaded {len(self.bookmarks)} bookmarks")

    def save_bookmark(self, bookmark: SearchBookmark) -> None:
        """
        Save a bookmark to storage

        Args:
            bookmark: SearchBookmark instance to save

        Note:
            If bookmark with same ID exists, it will be replaced.
        """
        if bookmark.id in self.bookmarks:
            logger.debug(f"Bookmark {bookmark.id} already exists, updating")

        self.bookmarks[bookmark.id] = bookmark
        self._save()

        logger.debug(f"Saved bookmark: {bookmark.id} ({bookmark.name})")

    def load_bookmark(self, bookmark_id: str) -> Optional[SearchBookmark]:
        """
        Load a bookmark by ID

        Args:
            bookmark_id: Unique bookmark ID

        Returns:
            SearchBookmark instance, or None if not found
        """
        bookmark = self.bookmarks.get(bookmark_id)

        if bookmark:
            logger.debug(f"Loaded bookmark: {bookmark_id}")
        else:
            logger.debug(f"Bookmark not found: {bookmark_id}")

        return bookmark

    def list_bookmarks(self) -> List[SearchBookmark]:
        """
        List all bookmarks

        Returns:
            List of all SearchBookmark instances, sorted by usage_count (descending)
        """
        bookmarks = list(self.bookmarks.values())

        # Sort by usage_count (most used first), then by last_used
        bookmarks.sort(key=lambda b: (b.usage_count, b.last_used), reverse=True)

        logger.debug(f"Listed {len(bookmarks)} bookmarks")
        return bookmarks

    def delete_bookmark(self, bookmark_id: str) -> bool:
        """
        Delete a bookmark from storage

        Args:
            bookmark_id: Unique bookmark ID

        Returns:
            True if bookmark was deleted, False if not found
        """
        if bookmark_id not in self.bookmarks:
            logger.warning(f"Bookmark not found for deletion: {bookmark_id}")
            return False

        bookmark_name = self.bookmarks[bookmark_id].name
        del self.bookmarks[bookmark_id]
        self._save()

        logger.info(f"Deleted bookmark: {bookmark_id} ({bookmark_name})")
        return True

    def update_bookmark(self, bookmark: SearchBookmark) -> None:
        """
        Update an existing bookmark

        Args:
            bookmark: SearchBookmark instance with updated fields

        Note:
            Equivalent to save_bookmark(). Provided for API clarity.
        """
        if bookmark.id not in self.bookmarks:
            logger.warning(f"Bookmark {bookmark.id} not found, creating new entry")

        self.save_bookmark(bookmark)

    def find_by_name(self, name: str) -> Optional[SearchBookmark]:
        """
        Find bookmark by name (case-insensitive)

        Args:
            name: Bookmark name to search

        Returns:
            First matching SearchBookmark, or None if not found
        """
        name_lower = name.lower()

        for bookmark in self.bookmarks.values():
            if bookmark.name.lower() == name_lower:
                logger.debug(f"Found bookmark by name: {name} -> {bookmark.id}")
                return bookmark

        logger.debug(f"No bookmark found with name: {name}")
        return None

    def increment_usage(self, bookmark_id: str) -> None:
        """
        Increment usage count and update last_used timestamp

        Args:
            bookmark_id: Unique bookmark ID

        Note:
            Called when bookmark is executed.
            Used for usage-based sorting and recommendations.
        """
        bookmark = self.bookmarks.get(bookmark_id)

        if not bookmark:
            logger.warning(f"Cannot increment usage: bookmark {bookmark_id} not found")
            return

        bookmark.usage_count += 1
        bookmark.last_used = datetime.now()
        self._save()

        logger.debug(f"Incremented usage for bookmark {bookmark_id}: {bookmark.usage_count}")

    def get_most_used(self, limit: int = 5) -> List[SearchBookmark]:
        """
        Get most frequently used bookmarks

        Args:
            limit: Maximum number of bookmarks to return (default: 5)

        Returns:
            List of SearchBookmarks sorted by usage_count (descending)
        """
        bookmarks = list(self.bookmarks.values())

        # Sort by usage_count descending
        bookmarks.sort(key=lambda b: b.usage_count, reverse=True)

        result = bookmarks[:limit]
        logger.debug(f"Retrieved {len(result)} most used bookmarks")

        return result

    def get_recent(self, limit: int = 5) -> List[SearchBookmark]:
        """
        Get recently used bookmarks

        Args:
            limit: Maximum number of bookmarks to return (default: 5)

        Returns:
            List of SearchBookmarks sorted by last_used (descending)
        """
        bookmarks = list(self.bookmarks.values())

        # Sort by last_used descending
        bookmarks.sort(key=lambda b: b.last_used, reverse=True)

        result = bookmarks[:limit]
        logger.debug(f"Retrieved {len(result)} recent bookmarks")

        return result

    def count(self) -> int:
        """
        Get total number of bookmarks

        Returns:
            Number of bookmarks in storage
        """
        return len(self.bookmarks)

    def _save(self) -> None:
        """
        Save bookmarks to disk (JSON format)

        Saves all bookmarks as a JSON array with human-readable formatting.
        """
        try:
            # Convert all bookmarks to dict format
            data = {
                'bookmarks': [
                    bookmark.to_dict() for bookmark in self.bookmarks.values()
                ],
                'version': '1.0',  # For future schema migrations
                'last_updated': datetime.now().isoformat()
            }

            # Write to file with pretty formatting
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(self.bookmarks)} bookmarks to {self.persist_path}")

        except Exception as e:
            logger.error(f"Failed to save bookmarks: {e}")
            # Don't raise - continue operation even if save fails

    def _load(self) -> None:
        """
        Load bookmarks from disk

        If file doesn't exist or is corrupted, starts with empty storage.
        """
        if not self.persist_path.exists():
            logger.debug("No existing bookmarks file found, starting fresh")
            return

        try:
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load bookmarks from array
            bookmarks_data = data.get('bookmarks', [])

            for bookmark_dict in bookmarks_data:
                bookmark = SearchBookmark.from_dict(bookmark_dict)
                self.bookmarks[bookmark.id] = bookmark

            logger.info(f"Loaded {len(self.bookmarks)} bookmarks from disk")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse bookmarks JSON: {e}")
            logger.warning("Starting with empty storage")
            self.bookmarks = {}

        except Exception as e:
            logger.error(f"Failed to load bookmarks: {e}")
            logger.warning("Starting with empty storage")
            self.bookmarks = {}
