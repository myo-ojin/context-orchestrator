#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for ConsolidationService

Tests memory consolidation functionality including:
- Working memory migration
- Memory clustering
- Representative selection
- Memory forgetting
- Importance calculation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.consolidation import ConsolidationService


class TestConsolidationService:
    """Test suite for ConsolidationService"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for ConsolidationService"""
        vector_db = Mock()
        indexer = Mock()
        model_router = Mock()

        vector_db.list_by_metadata.return_value = []
        vector_db.update_metadata = Mock()
        vector_db.delete = Mock()

        return {
            'vector_db': vector_db,
            'indexer': indexer,
            'model_router': model_router
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create ConsolidationService instance with mocks"""
        return ConsolidationService(
            vector_db=mock_dependencies['vector_db'],
            indexer=mock_dependencies['indexer'],
            model_router=mock_dependencies['model_router'],
            similarity_threshold=0.9,
            min_cluster_size=2,
            age_threshold_days=30,
            importance_threshold=0.3,
            working_memory_retention_hours=8
        )

    def test_init(self, service, mock_dependencies):
        """Test service initialization"""
        assert service.vector_db == mock_dependencies['vector_db']
        assert service.indexer == mock_dependencies['indexer']
        assert service.model_router == mock_dependencies['model_router']
        assert service.similarity_threshold == 0.9
        assert service.min_cluster_size == 2
        assert service.age_threshold_days == 30
        assert service.importance_threshold == 0.3
        assert service.working_memory_retention_hours == 8

    def test_consolidate_success(self, service, mock_dependencies):
        """Test full consolidation process"""
        # Execute
        stats = service.consolidate()

        # Assertions
        assert isinstance(stats, dict)
        assert 'migrated_count' in stats
        assert 'clusters_created' in stats
        assert 'memories_compressed' in stats
        assert 'memories_deleted' in stats
        assert 'duration_seconds' in stats

        # Duration should be a positive number
        assert stats['duration_seconds'] >= 0

    def test_consolidate_error_handling(self, service, mock_dependencies):
        """Test consolidation with errors"""
        # Make _migrate_working_memory fail
        with patch.object(service, '_migrate_working_memory', side_effect=Exception("Migration error")):
            stats = service.consolidate()

            # Should still return stats dict
            assert isinstance(stats, dict)
            assert 'duration_seconds' in stats

    def test_migrate_working_memory(self, service, mock_dependencies):
        """Test working memory migration updates metadata"""
        cutoff = datetime.now() - timedelta(hours=10)
        mock_dependencies['vector_db'].list_by_metadata.return_value = [
            {
                'id': 'mem-123-metadata',
                'metadata': {
                    'memory_id': 'mem-123',
                    'memory_type': 'working',
                    'created_at': cutoff.isoformat()
                }
            }
        ]

        migrated_ids = service._migrate_working_memory()

        assert migrated_ids == ['mem-123']
        mock_dependencies['vector_db'].update_metadata.assert_called_once()
        call_args = mock_dependencies['vector_db'].update_metadata.call_args
        assert call_args[0][0] == 'mem-123-metadata'
        assert call_args[0][1]['memory_type'] == 'short_term'

    def test_cluster_similar_memories(self, service, mock_dependencies):
        """Test memory clustering groups similar embeddings"""
        mock_dependencies['vector_db'].list_by_metadata.return_value = [
            {
                'id': 'mem-1-metadata',
                'metadata': {'memory_id': 'mem-1', 'is_memory_entry': True},
                'embedding': [1.0, 0.0, 0.0]
            },
            {
                'id': 'mem-2-metadata',
                'metadata': {'memory_id': 'mem-2', 'is_memory_entry': True},
                'embedding': [0.95, 0.05, 0.0]
            },
            {
                'id': 'mem-3-metadata',
                'metadata': {'memory_id': 'mem-3', 'is_memory_entry': True},
                'embedding': [0.0, 1.0, 0.0]
            },
        ]

        clusters = service._cluster_similar_memories()

        assert ['mem-1', 'mem-2'] in clusters
        assert any(cluster == ['mem-3'] for cluster in clusters)

    def test_forget_old_memories(self, service, mock_dependencies):
        """Test forgetting old, low-importance memories"""
        old_created_at = (datetime.now() - timedelta(days=45)).isoformat()
        mock_dependencies['vector_db'].list_by_metadata.return_value = [
            {
                'id': 'mem-10-metadata',
                'metadata': {
                    'memory_id': 'mem-10',
                    'importance': 0.1,
                    'created_at': old_created_at
                }
            }
        ]

        with patch.object(service, '_delete_memory', return_value=True) as delete_mock:
            deleted = service._forget_old_memories()

        assert deleted == 1
        delete_mock.assert_called_once_with('mem-10')

    def test_select_representative_memory_by_length(self, service, mock_dependencies):
        """Test representative selection based on content length"""
        cluster = ['mem-1', 'mem-2', 'mem-3']

        # Mock vector_db.get to return memories with different lengths
        mock_dependencies['vector_db'].get.side_effect = [
            {
                'content': 'Short summary',
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'importance': 0.5
                }
            },
            {
                'content': 'This is a much longer and more detailed summary with lots of information',
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'importance': 0.5
                }
            },
            {
                'content': 'Medium length summary here',
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'importance': 0.5
                }
            }
        ]

        representative_id = service._select_representative_memory(cluster)

        # Should select mem-2 (longest content)
        assert representative_id == 'mem-2'

    def test_select_representative_memory_by_recency(self, service, mock_dependencies):
        """Test representative selection based on recency (when length is similar)"""
        cluster = ['mem-1', 'mem-2']

        # Mock memories with similar length but different ages
        mock_dependencies['vector_db'].get.side_effect = [
            {
                'content': 'Same length content here',
                'metadata': {
                    'created_at': (datetime.now() - timedelta(days=30)).isoformat(),
                    'importance': 0.5
                }
            },
            {
                'content': 'Same length content also',
                'metadata': {
                    'created_at': datetime.now().isoformat(),  # More recent
                    'importance': 0.5
                }
            }
        ]

        representative_id = service._select_representative_memory(cluster)

        # Should select mem-2 (more recent)
        assert representative_id == 'mem-2'

    def test_select_representative_memory_fallback(self, service, mock_dependencies):
        """Test representative selection with empty cluster"""
        cluster = ['mem-1']

        mock_dependencies['vector_db'].get.return_value = None

        representative_id = service._select_representative_memory(cluster)

        # Should fallback to first memory
        assert representative_id == 'mem-1'

    def test_mark_as_representative(self, service, mock_dependencies):
        """Test marking memory as representative"""
        memory_id = 'mem-123'
        cluster = ['mem-123', 'mem-456', 'mem-789']

        service._mark_as_representative(memory_id, cluster)

        # Verify update_metadata was called
        mock_dependencies['vector_db'].update_metadata.assert_called_once()

        # Verify the call included correct data
        call_args = mock_dependencies['vector_db'].update_metadata.call_args
        assert call_args[0][0] == f'{memory_id}-metadata'
        assert 'cluster_id' in call_args[0][1]
        assert call_args[0][1]['is_representative'] is True
        assert call_args[0][1]['cluster_size'] == 3

    def test_compress_memory(self, service, mock_dependencies):
        """Test memory compression"""
        memory_id = 'mem-123'

        service._compress_memory(memory_id)

        # Verify update_metadata was called
        mock_dependencies['vector_db'].update_metadata.assert_called_once()

        # Verify compression flag was set
        call_args = mock_dependencies['vector_db'].update_metadata.call_args
        assert call_args[0][0] == f'{memory_id}-metadata'
        assert call_args[0][1]['is_compressed'] is True
        assert 'compressed_at' in call_args[0][1]

    def test_process_clusters(self, service, mock_dependencies):
        """Test cluster processing"""
        clusters = [
            ['mem-1', 'mem-2', 'mem-3'],  # 3 members
            ['mem-4', 'mem-5'],           # 2 members
            ['mem-6']                     # 1 member (should skip)
        ]

        # Mock _select_representative_memory
        with patch.object(service, '_select_representative_memory', side_effect=['mem-1', 'mem-4']):
            compressed_count = service._process_clusters(clusters)

            # Should compress: (3-1) + (2-1) = 3 memories
            assert compressed_count == 3

    def test_forget_old_memories_no_candidates(self, service, mock_dependencies):
        """Test that no memories are forgotten when no candidates match"""
        mock_dependencies['vector_db'].list_by_metadata.return_value = []

        deleted_count = service._forget_old_memories()

        assert deleted_count == 0
        mock_dependencies['indexer'].delete_by_memory_id.assert_not_called()

    def test_delete_memory(self, service, mock_dependencies):
        """Test memory deletion"""
        memory_id = 'mem-123'

        result = service._delete_memory(memory_id)

        assert result is True

        # Verify metadata was deleted
        mock_dependencies['vector_db'].delete.assert_called_once_with(f'{memory_id}-metadata')

        # Verify chunks were deleted
        mock_dependencies['indexer'].delete_by_memory_id.assert_called_once_with(memory_id)

    def test_delete_memory_error(self, service, mock_dependencies):
        """Test memory deletion with error"""
        memory_id = 'mem-123'

        # Make delete fail
        mock_dependencies['vector_db'].delete.side_effect = Exception("Delete error")

        result = service._delete_memory(memory_id)

        assert result is False

    def test_calculate_importance_score_high_access(self, service, mock_dependencies):
        """Test importance calculation with high access count"""
        memory_id = 'mem-123'

        mock_dependencies['vector_db'].get.return_value = {
            'content': 'Test content',
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'refs': ['ref1', 'ref2', 'ref3']
            }
        }

        # High access count
        importance = service.calculate_importance_score(memory_id, access_count=50, refs_count=3)

        assert 0.0 <= importance <= 1.0
        assert importance > 0.5  # Should be high due to access count

    def test_calculate_importance_score_old_memory(self, service, mock_dependencies):
        """Test importance calculation with old memory"""
        memory_id = 'mem-123'

        mock_dependencies['vector_db'].get.return_value = {
            'content': 'Test content',
            'metadata': {
                'created_at': (datetime.now() - timedelta(days=90)).isoformat(),
                'refs': []
            }
        }

        # Old memory with low access
        importance = service.calculate_importance_score(memory_id, access_count=0, refs_count=0)

        assert 0.0 <= importance <= 1.0
        assert importance < 0.3  # Should be low due to age and no refs

    def test_calculate_importance_score_with_refs(self, service, mock_dependencies):
        """Test importance calculation with multiple refs"""
        memory_id = 'mem-123'

        mock_dependencies['vector_db'].get.return_value = {
            'content': 'Test content',
            'metadata': {
                'created_at': (datetime.now() - timedelta(days=15)).isoformat(),
                'refs': ['ref1', 'ref2', 'ref3', 'ref4', 'ref5']
            }
        }

        importance = service.calculate_importance_score(memory_id, access_count=5, refs_count=5)

        assert 0.0 <= importance <= 1.0
        assert importance > 0.5  # Should be moderately high

    def test_calculate_importance_score_missing_memory(self, service, mock_dependencies):
        """Test importance calculation with missing memory"""
        memory_id = 'mem-nonexistent'

        mock_dependencies['vector_db'].get.return_value = None

        importance = service.calculate_importance_score(memory_id)

        # Should return default value
        assert importance == 0.5

    def test_update_memory_strength_success(self, service, mock_dependencies):
        """Test memory strength update"""
        memory_id = 'mem-123'

        mock_dependencies['vector_db'].get.return_value = {
            'content': 'Test content',
            'metadata': {
                'strength': 0.5
            }
        }

        result = service.update_memory_strength(memory_id, access_boost=0.2)

        assert result is True

        # Verify update was called
        mock_dependencies['vector_db'].update_metadata.assert_called_once()

        # Verify strength was increased
        call_args = mock_dependencies['vector_db'].update_metadata.call_args
        assert call_args[0][1]['strength'] == 0.7  # 0.5 + 0.2

    def test_update_memory_strength_capped_at_one(self, service, mock_dependencies):
        """Test memory strength capped at 1.0"""
        memory_id = 'mem-123'

        mock_dependencies['vector_db'].get.return_value = {
            'content': 'Test content',
            'metadata': {
                'strength': 0.95
            }
        }

        result = service.update_memory_strength(memory_id, access_boost=0.2)

        assert result is True

        # Verify strength is capped at 1.0
        call_args = mock_dependencies['vector_db'].update_metadata.call_args
        assert call_args[0][1]['strength'] == 1.0

    def test_update_memory_strength_missing_memory(self, service, mock_dependencies):
        """Test memory strength update with missing memory"""
        memory_id = 'mem-nonexistent'

        mock_dependencies['vector_db'].get.return_value = None

        result = service.update_memory_strength(memory_id)

        assert result is False

    def test_get_consolidation_stats(self, service):
        """Test consolidation statistics"""
        stats = service.get_consolidation_stats()

        assert isinstance(stats, dict)
        assert 'working_memory_count' in stats
        assert 'short_term_count' in stats
        assert 'long_term_count' in stats
        assert 'total_clusters' in stats
        assert 'compressed_count' in stats

    def test_consolidate_with_custom_thresholds(self, mock_dependencies):
        """Test consolidation with custom thresholds"""
        service = ConsolidationService(
            vector_db=mock_dependencies['vector_db'],
            indexer=mock_dependencies['indexer'],
            model_router=mock_dependencies['model_router'],
            similarity_threshold=0.95,
            age_threshold_days=60,
            importance_threshold=0.5,
            working_memory_retention_hours=24
        )

        assert service.similarity_threshold == 0.95
        assert service.age_threshold_days == 60
        assert service.importance_threshold == 0.5
        assert service.working_memory_retention_hours == 24

        stats = service.consolidate()
        assert isinstance(stats, dict)

    def test_process_clusters_skip_small_clusters(self, service):
        """Test that single-member clusters are skipped"""
        clusters = [
            ['mem-1'],  # Should skip
            ['mem-2']   # Should skip
        ]

        compressed_count = service._process_clusters(clusters)

        # Should compress 0 memories
        assert compressed_count == 0

    def test_process_clusters_with_errors(self, service, mock_dependencies):
        """Test cluster processing with errors"""
        clusters = [
            ['mem-1', 'mem-2']
        ]

        # Make _select_representative_memory fail
        with patch.object(service, '_select_representative_memory', side_effect=Exception("Selection error")):
            compressed_count = service._process_clusters(clusters)

            # Should handle error gracefully
            assert compressed_count == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
