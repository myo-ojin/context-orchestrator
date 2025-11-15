#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for ProjectMemoryPool

Requirements: Issue #2025-11-11-03 - Project Memory Pool
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from src.services.project_memory_pool import ProjectMemoryPool


@pytest.fixture
def mock_vector_db():
    """Mock ChromaVectorDB"""
    db = Mock()
    db.list_by_metadata = Mock(return_value=[])
    return db


@pytest.fixture
def mock_model_router():
    """Mock ModelRouter"""
    router = Mock()
    router.generate_embedding = Mock(return_value=[0.1] * 768)
    return router


@pytest.fixture
def memory_pool(mock_vector_db, mock_model_router):
    """Create ProjectMemoryPool instance"""
    return ProjectMemoryPool(
        vector_db=mock_vector_db,
        model_router=mock_model_router,
        max_memories_per_project=10,
        pool_ttl_seconds=3600
    )


def test_init(memory_pool):
    """Test ProjectMemoryPool initialization"""
    assert memory_pool.max_memories_per_project == 10
    assert memory_pool.pool_ttl_seconds == 3600
    assert memory_pool._pools == {}


def test_load_project_empty(memory_pool, mock_vector_db):
    """Test loading project with no memories"""
    mock_vector_db.list_by_metadata.return_value = []

    pool = memory_pool.load_project("proj-123")

    assert pool['project_id'] == "proj-123"
    assert pool['memory_count'] == 0
    assert pool['embeddings'] == {}
    assert pool['metadata'] == {}


def test_load_project_with_memories(memory_pool, mock_vector_db, mock_model_router):
    """Test loading project with memories"""
    mock_memories = [
        {
            'id': 'mem-1',
            'content': 'Test memory 1',
            'metadata': {'created_at': '2025-01-01T00:00:00', 'topic': 'test'}
        },
        {
            'id': 'mem-2',
            'content': 'Test memory 2',
            'metadata': {'created_at': '2025-01-02T00:00:00', 'topic': 'test'}
        }
    ]
    mock_vector_db.list_by_metadata.return_value = mock_memories

    pool = memory_pool.load_project("proj-123")

    assert pool['project_id'] == "proj-123"
    assert pool['memory_count'] == 2
    assert 'mem-1' in pool['embeddings']
    assert 'mem-2' in pool['embeddings']
    assert len(pool['embeddings']['mem-1']) == 768
    assert mock_model_router.generate_embedding.call_count == 2


def test_load_project_respects_max_memories(memory_pool, mock_vector_db):
    """Test that load_project respects max_memories_per_project"""
    # Create 15 memories (more than max of 10)
    mock_memories = [
        {
            'id': f'mem-{i}',
            'content': f'Test memory {i}',
            'metadata': {'created_at': f'2025-01-{i:02d}T00:00:00'}
        }
        for i in range(1, 16)
    ]
    mock_vector_db.list_by_metadata.return_value = mock_memories

    pool = memory_pool.load_project("proj-123")

    # Should only load max_memories_per_project (10)
    assert pool['memory_count'] == 10


def test_load_project_caches_result(memory_pool, mock_vector_db):
    """Test that load_project caches the result"""
    mock_vector_db.list_by_metadata.return_value = [
        {'id': 'mem-1', 'content': 'Test', 'metadata': {}}
    ]

    # First load
    pool1 = memory_pool.load_project("proj-123")
    call_count_1 = mock_vector_db.list_by_metadata.call_count

    # Second load (should use cache)
    pool2 = memory_pool.load_project("proj-123")
    call_count_2 = mock_vector_db.list_by_metadata.call_count

    assert pool1 == pool2
    assert call_count_1 == call_count_2  # No additional DB call


def test_warm_cache(memory_pool, mock_vector_db):
    """Test warm_cache integration with reranker"""
    mock_memories = [
        {'id': 'mem-1', 'content': 'Test 1', 'metadata': {}},
        {'id': 'mem-2', 'content': 'Test 2', 'metadata': {}}
    ]
    mock_vector_db.list_by_metadata.return_value = mock_memories

    mock_reranker = Mock()
    mock_reranker.warm_semantic_cache_from_pool = Mock(return_value=2)

    stats = memory_pool.warm_cache(mock_reranker, "proj-123")

    assert stats['project_id'] == "proj-123"
    assert stats['memories_loaded'] == 2
    assert stats['cache_entries_added'] == 2
    assert mock_reranker.warm_semantic_cache_from_pool.called


def test_get_pool_stats(memory_pool, mock_vector_db):
    """Test get_pool_stats"""
    mock_vector_db.list_by_metadata.return_value = [
        {'id': 'mem-1', 'content': 'Test', 'metadata': {}}
    ]

    # Load project first
    memory_pool.load_project("proj-123")

    # Get stats
    stats = memory_pool.get_pool_stats("proj-123")

    assert stats is not None
    assert stats['project_id'] == "proj-123"
    assert stats['memory_count'] == 1
    assert stats['is_fresh'] is True

    # Stats for non-existent project
    stats_none = memory_pool.get_pool_stats("proj-999")
    assert stats_none is None


def test_clear_pool(memory_pool, mock_vector_db):
    """Test clear_pool"""
    mock_vector_db.list_by_metadata.return_value = [
        {'id': 'mem-1', 'content': 'Test', 'metadata': {}}
    ]

    # Load project
    memory_pool.load_project("proj-123")
    assert "proj-123" in memory_pool._pools

    # Clear pool
    result = memory_pool.clear_pool("proj-123")
    assert result is True
    assert "proj-123" not in memory_pool._pools

    # Clear non-existent pool
    result_false = memory_pool.clear_pool("proj-999")
    assert result_false is False


def test_clear_all_pools(memory_pool, mock_vector_db):
    """Test clear_all_pools"""
    mock_vector_db.list_by_metadata.return_value = [
        {'id': 'mem-1', 'content': 'Test', 'metadata': {}}
    ]

    # Load multiple projects
    memory_pool.load_project("proj-1")
    memory_pool.load_project("proj-2")
    memory_pool.load_project("proj-3")

    assert len(memory_pool._pools) == 3

    # Clear all
    count = memory_pool.clear_all_pools()
    assert count == 3
    assert len(memory_pool._pools) == 0


def test_pool_ttl_expiry(memory_pool, mock_vector_db):
    """Test that expired pools are reloaded"""
    mock_vector_db.list_by_metadata.return_value = [
        {'id': 'mem-1', 'content': 'Test', 'metadata': {}}
    ]

    # Load project with very short TTL
    memory_pool.pool_ttl_seconds = 1
    memory_pool.load_project("proj-123")
    call_count_1 = mock_vector_db.list_by_metadata.call_count

    # Wait for TTL to expire
    time.sleep(1.5)

    # Load again (should reload from DB)
    memory_pool.load_project("proj-123")
    call_count_2 = mock_vector_db.list_by_metadata.call_count

    assert call_count_2 > call_count_1  # New DB call was made


def test_load_project_handles_empty_content(memory_pool, mock_vector_db):
    """Test that memories with empty content are skipped"""
    mock_memories = [
        {'id': 'mem-1', 'content': 'Valid content', 'metadata': {}},
        {'id': 'mem-2', 'content': '', 'metadata': {}},  # Empty content
        {'id': 'mem-3', 'content': 'Another valid', 'metadata': {}}
    ]
    mock_vector_db.list_by_metadata.return_value = mock_memories

    pool = memory_pool.load_project("proj-123")

    # Should only have 2 embeddings (mem-2 skipped)
    assert pool['memory_count'] == 2
    assert 'mem-1' in pool['embeddings']
    assert 'mem-2' not in pool['embeddings']
    assert 'mem-3' in pool['embeddings']


def test_load_project_handles_missing_id(memory_pool, mock_vector_db):
    """Test that memories without IDs are skipped"""
    mock_memories = [
        {'id': 'mem-1', 'content': 'Test 1', 'metadata': {}},
        {'content': 'No ID', 'metadata': {}},  # Missing ID
        {'id': None, 'content': 'Null ID', 'metadata': {}},  # Null ID
    ]
    mock_vector_db.list_by_metadata.return_value = mock_memories

    pool = memory_pool.load_project("proj-123")

    # Should only have 1 embedding
    assert pool['memory_count'] == 1
    assert 'mem-1' in pool['embeddings']
