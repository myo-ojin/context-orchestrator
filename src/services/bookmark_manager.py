#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bookmark Manager Service

Handles search bookmark operations:
- Create, read, update, delete bookmarks
- Execute saved searches
- Track bookmark usage statistics
- Recommend frequently used searches

Inspired by NotebookLM's smart query approach.

Requirements: Phase 15 - Search Enhancement
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from src.models import SearchBookmark
from src.storage.bookmark_storage import BookmarkStorage

logger = logging.getLogger(__name__)


class BookmarkManager:
    """
    Service for managing search bookmarks

    Bookmarks enable users to save frequently used search queries
    for quick access and improved workflow efficiency.

    Attributes:
        bookmark_storage: BookmarkStorage instance for persistence
    """

    def __init__(self, bookmark_storage: BookmarkStorage):
        """
        Initialize Bookmark Manager

        Args:
            bookmark_storage: BookmarkStorage instance
        """
        self.bookmark_storage = bookmark_storage

        logger.info("Initialized BookmarkManager")

    def create_bookmark(
        self,
        name: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        description: str = ""
    ) -> SearchBookmark:
        """
        Create a new search bookmark

        Args:
            name: Bookmark name (e.g., "React Errors")
            query: Search query string
            filters: Optional search filters (e.g., {"schema_type": "Incident"})
            description: Optional description

        Returns:
            Created SearchBookmark instance

        Raises:
            ValueError: If bookmark with same name already exists

        Example:
            >>> manager = BookmarkManager(...)
            >>> bookmark = manager.create_bookmark(
            ...     name="React Errors",
            ...     query="React hooks エラー処理",
            ...     filters={"schema_type": "Incident"},
            ...     description="Common React hooks errors"
            ... )
            >>> print(bookmark.id)
        """
        # Check if bookmark with same name exists
        existing = self.bookmark_storage.find_by_name(name)
        if existing:
            raise ValueError(f"Bookmark with name '{name}' already exists (ID: {existing.id})")

        # Create new bookmark
        bookmark = SearchBookmark(
            id=str(uuid.uuid4()),
            name=name,
            query=query,
            filters=filters or {},
            created_at=datetime.now(),
            usage_count=0,
            last_used=datetime.now(),
            description=description
        )

        # Save to storage
        self.bookmark_storage.save_bookmark(bookmark)

        logger.info(f"Created bookmark: {bookmark.id} ({bookmark.name})")
        return bookmark

    def get_bookmark(self, bookmark_id: str) -> Optional[SearchBookmark]:
        """
        Get bookmark by ID

        Args:
            bookmark_id: Unique bookmark ID

        Returns:
            SearchBookmark instance, or None if not found
        """
        return self.bookmark_storage.load_bookmark(bookmark_id)

    def get_bookmark_by_name(self, name: str) -> Optional[SearchBookmark]:
        """
        Get bookmark by name (case-insensitive)

        Args:
            name: Bookmark name

        Returns:
            SearchBookmark instance, or None if not found
        """
        return self.bookmark_storage.find_by_name(name)

    def list_bookmarks(self) -> List[SearchBookmark]:
        """
        List all bookmarks

        Returns:
            List of all bookmarks, sorted by usage_count (descending)
        """
        return self.bookmark_storage.list_bookmarks()

    def update_bookmark(
        self,
        bookmark_id: str,
        name: Optional[str] = None,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> Optional[SearchBookmark]:
        """
        Update bookmark fields

        Args:
            bookmark_id: Bookmark ID to update
            name: New name (optional)
            query: New query (optional)
            filters: New filters (optional)
            description: New description (optional)

        Returns:
            Updated SearchBookmark instance, or None if not found

        Note:
            Only provided fields will be updated. None values are ignored.
        """
        bookmark = self.bookmark_storage.load_bookmark(bookmark_id)

        if not bookmark:
            logger.warning(f"Cannot update: bookmark {bookmark_id} not found")
            return None

        # Update fields
        if name is not None:
            bookmark.name = name

        if query is not None:
            bookmark.query = query

        if filters is not None:
            bookmark.filters = filters

        if description is not None:
            bookmark.description = description

        # Save updated bookmark
        self.bookmark_storage.update_bookmark(bookmark)

        logger.info(f"Updated bookmark: {bookmark_id}")
        return bookmark

    def delete_bookmark(self, bookmark_id: str) -> bool:
        """
        Delete a bookmark

        Args:
            bookmark_id: Bookmark ID to delete

        Returns:
            True if deleted, False if not found
        """
        success = self.bookmark_storage.delete_bookmark(bookmark_id)

        if success:
            logger.info(f"Deleted bookmark: {bookmark_id}")
        else:
            logger.warning(f"Cannot delete: bookmark {bookmark_id} not found")

        return success

    def execute_bookmark(self, bookmark_id: str) -> Optional[Dict[str, Any]]:
        """
        Get bookmark query and filters for execution

        Args:
            bookmark_id: Bookmark ID to execute

        Returns:
            Dict with 'query' and 'filters' keys, or None if not found

        Note:
            This method increments usage count and updates last_used timestamp.
            Actual search execution is handled by SearchService.

        Example:
            >>> bookmark_data = manager.execute_bookmark(bookmark_id)
            >>> if bookmark_data:
            ...     results = search_service.search(
            ...         query=bookmark_data['query'],
            ...         filters=bookmark_data['filters']
            ...     )
        """
        bookmark = self.bookmark_storage.load_bookmark(bookmark_id)

        if not bookmark:
            logger.warning(f"Cannot execute: bookmark {bookmark_id} not found")
            return None

        # Increment usage count
        self.bookmark_storage.increment_usage(bookmark_id)

        logger.info(f"Executed bookmark: {bookmark_id} ({bookmark.name})")

        return {
            'query': bookmark.query,
            'filters': bookmark.filters,
            'bookmark_name': bookmark.name
        }

    def execute_bookmark_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Execute bookmark by name

        Args:
            name: Bookmark name

        Returns:
            Dict with 'query' and 'filters' keys, or None if not found
        """
        bookmark = self.bookmark_storage.find_by_name(name)

        if not bookmark:
            logger.warning(f"Cannot execute: bookmark '{name}' not found")
            return None

        return self.execute_bookmark(bookmark.id)

    def get_most_used(self, limit: int = 5) -> List[SearchBookmark]:
        """
        Get most frequently used bookmarks

        Args:
            limit: Maximum number of bookmarks to return (default: 5)

        Returns:
            List of SearchBookmarks sorted by usage_count (descending)

        Example:
            >>> bookmarks = manager.get_most_used(limit=3)
            >>> for bookmark in bookmarks:
            ...     print(f"{bookmark.name}: {bookmark.usage_count} uses")
        """
        return self.bookmark_storage.get_most_used(limit)

    def get_recent(self, limit: int = 5) -> List[SearchBookmark]:
        """
        Get recently used bookmarks

        Args:
            limit: Maximum number of bookmarks to return (default: 5)

        Returns:
            List of SearchBookmarks sorted by last_used (descending)
        """
        return self.bookmark_storage.get_recent(limit)

    def get_bookmark_stats(self, bookmark_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a bookmark

        Args:
            bookmark_id: Bookmark ID

        Returns:
            Dict with stats (usage_count, created_at, last_used, etc.),
            or None if bookmark not found
        """
        bookmark = self.bookmark_storage.load_bookmark(bookmark_id)

        if not bookmark:
            return None

        return {
            'bookmark_id': bookmark.id,
            'name': bookmark.name,
            'query': bookmark.query,
            'filters': bookmark.filters,
            'usage_count': bookmark.usage_count,
            'created_at': bookmark.created_at.isoformat(),
            'last_used': bookmark.last_used.isoformat(),
            'description': bookmark.description
        }

    def recommend_bookmarks(self, query: str, limit: int = 3) -> List[SearchBookmark]:
        """
        Recommend bookmarks based on query similarity

        Args:
            query: User's current query
            limit: Maximum number of recommendations (default: 3)

        Returns:
            List of recommended SearchBookmarks

        Implementation:
            Simple keyword matching for now. Future: use embeddings for
            semantic similarity.

        Example:
            >>> query = "React error handling"
            >>> recommendations = manager.recommend_bookmarks(query)
            >>> for bookmark in recommendations:
            ...     print(f"Try: {bookmark.name}")
        """
        all_bookmarks = self.bookmark_storage.list_bookmarks()

        if not all_bookmarks:
            return []

        # Simple keyword matching (case-insensitive)
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score bookmarks by keyword overlap
        scored_bookmarks = []

        for bookmark in all_bookmarks:
            # Combine query and name for matching
            bookmark_text = f"{bookmark.query} {bookmark.name}".lower()
            bookmark_words = set(bookmark_text.split())

            # Calculate overlap score
            overlap = len(query_words & bookmark_words)

            if overlap > 0:
                # Boost score by usage count (popular bookmarks get priority)
                score = overlap + (bookmark.usage_count * 0.1)
                scored_bookmarks.append((bookmark, score))

        # Sort by score (descending) and take top N
        scored_bookmarks.sort(key=lambda x: x[1], reverse=True)
        recommendations = [bookmark for bookmark, _ in scored_bookmarks[:limit]]

        logger.debug(f"Recommended {len(recommendations)} bookmarks for query: {query}")

        return recommendations
