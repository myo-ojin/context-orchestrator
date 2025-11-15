#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for SearchService

Tests hybrid search functionality including:
- Query embedding generation
- Vector search
- BM25 keyword search
- Result merging
- Rule-based reranking
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.search import SearchService


class TestSearchService:
    """Test suite for SearchService"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for SearchService"""
        vector_db = Mock()
        bm25_index = Mock()
        model_router = Mock()
        model_router.route.return_value = "{}"

        return {
            'vector_db': vector_db,
            'bm25_index': bm25_index,
            'model_router': model_router
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create SearchService instance with mocks"""
        return SearchService(
            vector_db=mock_dependencies['vector_db'],
            bm25_index=mock_dependencies['bm25_index'],
            model_router=mock_dependencies['model_router'],
            candidate_count=50,
            result_count=10
        )

    @pytest.fixture
    def sample_vector_results(self):
        """Sample vector search results"""
        return [
            {
                'id': 'chunk-1',
                'content': 'How to fix TypeError in Python',
                'metadata': {
                    'memory_id': 'mem-1',
                    'schema_type': 'Incident',
                    'strength': 0.8,
                    'created_at': (datetime.now() - timedelta(days=5)).isoformat()
                },
                'similarity': 0.95,
                'vector_similarity': 0.95
            },
            {
                'id': 'chunk-2',
                'content': 'Python error handling best practices',
                'metadata': {
                    'memory_id': 'mem-2',
                    'schema_type': 'Snippet',
                    'strength': 0.6,
                    'created_at': (datetime.now() - timedelta(days=10)).isoformat()
                },
                'similarity': 0.85,
                'vector_similarity': 0.85
            }
        ]

    @pytest.fixture
    def sample_bm25_results(self):
        """Sample BM25 search results"""
        return [
            {
                'id': 'chunk-1',
                'score': 15.3
            },
            {
                'id': 'chunk-3',
                'score': 12.1
            }
        ]

    def test_init(self, service, mock_dependencies):
        """Test service initialization"""
        assert service.vector_db == mock_dependencies['vector_db']
        assert service.bm25_index == mock_dependencies['bm25_index']
        assert service.model_router == mock_dependencies['model_router']
        assert service.candidate_count == 50
        assert service.result_count == 10

    def test_search_success(self, service, sample_vector_results, sample_bm25_results, mock_dependencies):
        """Test successful hybrid search"""
        query = "How to fix TypeError in Python?"

        # Setup mocks
        mock_dependencies['model_router'].generate_embedding.return_value = [0.1] * 768
        mock_dependencies['vector_db'].search.return_value = sample_vector_results

        # Mock BM25 search and enrichment
        mock_dependencies['bm25_index'].search.return_value = sample_bm25_results
        mock_dependencies['vector_db'].get.side_effect = [
            {
                'content': 'How to fix TypeError in Python',
                'metadata': {'memory_id': 'mem-1', 'strength': 0.8, 'created_at': datetime.now().isoformat()}
            },
            {
                'content': 'Another Python error example',
                'metadata': {'memory_id': 'mem-3', 'strength': 0.7, 'created_at': datetime.now().isoformat()}
            }
        ]

        # Execute
        results = service.search(query, top_k=5)

        # Assertions
        assert isinstance(results, list)
        assert len(results) <= 5

        # Verify embedding generation was called
        mock_dependencies['model_router'].generate_embedding.assert_called_once_with(query)

        # Verify vector search was called
        mock_dependencies['vector_db'].search.assert_called_once()

        # Verify BM25 search was called
        mock_dependencies['bm25_index'].search.assert_called_once()

        # Verify results have scores
        for result in results:
            assert 'score' in result
            assert 'combined_score' in result

    def test_generate_query_embedding(self, service, mock_dependencies):
        """Test query embedding generation"""
        query = "Test query"
        expected_embedding = [0.1] * 768

        mock_dependencies['model_router'].generate_embedding.return_value = expected_embedding

        embedding = service._generate_query_embedding(query)

        assert embedding == expected_embedding
        mock_dependencies['model_router'].generate_embedding.assert_called_once_with(query)

    def test_vector_search(self, service, sample_vector_results, mock_dependencies):
        """Test vector search"""
        query_embedding = [0.1] * 768
        mock_dependencies['vector_db'].search.return_value = sample_vector_results

        results = service._vector_search(query_embedding, top_k=50)

        assert len(results) == len(sample_vector_results)
        assert all('vector_similarity' in r for r in results)

        mock_dependencies['vector_db'].search.assert_called_once_with(
            query_embedding=query_embedding,
            top_k=50,
            filter_metadata=None
        )

    def test_bm25_search(self, service, sample_bm25_results, mock_dependencies):
        """Test BM25 keyword search"""
        query = "Python TypeError"

        mock_dependencies['bm25_index'].search.return_value = sample_bm25_results

        # Mock vector_db.get for enrichment
        mock_dependencies['vector_db'].get.side_effect = [
            {
                'content': 'Content for chunk-1',
                'metadata': {'memory_id': 'mem-1'}
            },
            {
                'content': 'Content for chunk-3',
                'metadata': {'memory_id': 'mem-3'}
            }
        ]

        results = service._bm25_search(query, top_k=50)

        assert isinstance(results, list)
        mock_dependencies['bm25_index'].search.assert_called_once_with(query, top_k=50)

        # Verify enrichment happened
        for result in results:
            assert 'content' in result
            assert 'metadata' in result
            assert 'bm25_score' in result

    def test_merge_results(self, service, sample_vector_results):
        """Test merging vector and BM25 results"""
        vector_results = sample_vector_results
        bm25_results = [
            {
                'id': 'chunk-1',  # Duplicate
                'content': 'Content 1',
                'metadata': {},
                'bm25_score': 15.3,
                'vector_similarity': 0.0
            },
            {
                'id': 'chunk-3',  # New
                'content': 'Content 3',
                'metadata': {},
                'bm25_score': 12.1,
                'vector_similarity': 0.0
            }
        ]

        merged = service._merge_results(vector_results, bm25_results)

        # Should have unique results
        assert len(merged) == 3  # chunk-1, chunk-2, chunk-3

        # chunk-1 should have both scores
        chunk_1 = next(r for r in merged if r['id'] == 'chunk-1')
        assert 'vector_similarity' in chunk_1
        assert 'bm25_score' in chunk_1

    def test_rerank(self, service):
        """Test reranking algorithm"""
        candidates = [
            {
                'id': 'chunk-1',
                'content': 'Content 1',
                'metadata': {
                    'strength': 0.8,
                    'created_at': (datetime.now() - timedelta(days=2)).isoformat(),
                    'refs': ['ref1', 'ref2']
                },
                'vector_similarity': 0.9,
                'bm25_score': 15.0
            },
            {
                'id': 'chunk-2',
                'content': 'Content 2',
                'metadata': {
                    'strength': 0.5,
                    'created_at': (datetime.now() - timedelta(days=20)).isoformat(),
                    'refs': []
                },
                'vector_similarity': 0.85,
                'bm25_score': 10.0
            },
            {
                'id': 'chunk-3',
                'content': 'Content 3',
                'metadata': {
                    'strength': 0.9,
                    'created_at': datetime.now().isoformat(),
                    'refs': ['ref1']
                },
                'vector_similarity': 0.88,
                'bm25_score': 20.0
            }
        ]

        reranked = service._rerank(candidates, "test query", top_k=2)

        # Should return top 2
        assert len(reranked) == 2

        # Should be sorted by score
        assert reranked[0]['score'] >= reranked[1]['score']

        # Should have component scores
        for result in reranked:
            assert 'components' in result
            assert 'memory_strength' in result['components']
            assert 'recency' in result['components']
            assert 'refs_reliability' in result['components']

    def test_normalize_bm25(self, service):
        """Test BM25 score normalization"""
        # Test various BM25 scores
        assert service._normalize_bm25(0) == 0.0
        assert 0 < service._normalize_bm25(10) < 1.0
        assert service._normalize_bm25(100) > service._normalize_bm25(10)

    def test_calculate_recency_score(self, service):
        """Test recency score calculation"""
        # Recent memory (1 day old)
        metadata_recent = {
            'created_at': (datetime.now() - timedelta(days=1)).isoformat()
        }
        score_recent = service._calculate_recency_score(metadata_recent)
        assert 0 < score_recent < 1.0

        # Old memory (60 days old)
        metadata_old = {
            'created_at': (datetime.now() - timedelta(days=60)).isoformat()
        }
        score_old = service._calculate_recency_score(metadata_old)
        assert 0.0 < score_old < score_recent

        # Missing timestamp
        metadata_missing = {}
        score_missing = service._calculate_recency_score(metadata_missing)
        assert score_missing == 0.5

    def test_calculate_refs_reliability(self, service):
        """Test refs reliability calculation"""
        # No refs
        metadata_no_refs = {'refs': []}
        assert service._calculate_refs_reliability(metadata_no_refs) == 0.0

        # Few refs
        metadata_few_refs = {'refs': ['ref1', 'ref2']}
        score_few = service._calculate_refs_reliability(metadata_few_refs)
        assert 0.0 < score_few < 0.5

        # Many refs
        metadata_many_refs = {'refs': ['ref' + str(i) for i in range(10)]}
        score_many = service._calculate_refs_reliability(metadata_many_refs)
        assert 0.9 <= score_many <= 1.0

    def test_metadata_alignment_penalizes_session_source(self, service):
        """Session logs should receive a slight penalty in metadata bonus."""
        metadata_session = {'source': 'session'}
        metadata_normal = {'source': 'scenario_app_dev'}

        penalty = service._calculate_metadata_alignment(metadata_session, "query", None, None)
        neutral = service._calculate_metadata_alignment(metadata_normal, "query", None, None)

        assert penalty < neutral
        assert penalty <= -0.05

    def test_search_with_filters(self, service, sample_vector_results, mock_dependencies):
        """Test search with metadata filters"""
        query = "Test query"
        filters = {'schema_type': 'Incident'}

        mock_dependencies['model_router'].generate_embedding.return_value = [0.1] * 768
        mock_dependencies['vector_db'].search.return_value = sample_vector_results
        mock_dependencies['bm25_index'].search.return_value = []

        results = service.search(query, filters=filters)

        # Verify filters were passed to vector search
        call_args = mock_dependencies['vector_db'].search.call_args
        assert call_args.kwargs.get('filter_metadata') == filters

        assert isinstance(results, list)

    def test_get_related_memories(self, service, mock_dependencies):
        """Test finding related memories"""
        memory_id = 'mem-123'

        # Mock source memory
        mock_dependencies['vector_db'].get.return_value = {
            'embedding': [0.1] * 768,
            'content': 'Source memory',
            'metadata': {}
        }

        # Mock search results
        mock_dependencies['vector_db'].search.return_value = [
            {'id': 'mem-123-metadata', 'content': 'Source', 'metadata': {'is_memory_entry': True}},  # Self
            {'id': 'mem-456-metadata', 'content': 'Related 1', 'metadata': {'is_memory_entry': True}},
            {'id': 'mem-789-metadata', 'content': 'Related 2', 'metadata': {'is_memory_entry': True}}
        ]

        related = service.get_related_memories(memory_id, top_k=3)

        # Should exclude self and return related
        assert len(related) <= 3
        assert all(r['id'] != f'{memory_id}-metadata' for r in related)

        # Ensure metadata filter was applied when searching for related memories
        related_call = mock_dependencies['vector_db'].search.call_args
        assert related_call.kwargs.get('filter_metadata') == {'is_memory_entry': True}

    def test_get_search_stats(self, service, mock_dependencies):
        """Test search statistics"""
        mock_dependencies['vector_db'].count.return_value = 450
        mock_dependencies['bm25_index'].count.return_value = 450

        stats = service.get_search_stats()

        assert stats['total_indexed'] == 450
        assert stats['vector_count'] == 450
        assert stats['bm25_count'] == 450

    def test_search_empty_results(self, service, mock_dependencies):
        """Test search with no results"""
        query = "Nonexistent query"

        mock_dependencies['model_router'].generate_embedding.return_value = [0.1] * 768
        mock_dependencies['vector_db'].search.return_value = []
        mock_dependencies['bm25_index'].search.return_value = []

        results = service.search(query)

        assert results == []

    def test_search_error_handling(self, service, mock_dependencies):
        """Test search with errors"""
        query = "Test query"

        # Make embedding generation fail
        mock_dependencies['model_router'].generate_embedding.side_effect = Exception("Embedding error")

        results = service.search(query)

        # Should return empty list on error
        assert results == []

    def test_rerank_with_missing_metadata(self, service):
        """Test reranking with incomplete metadata"""
        candidates = [
            {
                'id': 'chunk-1',
                'content': 'Content',
                'metadata': {},  # Missing all metadata
                'vector_similarity': 0.8,
                'bm25_score': 10.0
            }
        ]

        reranked = service._rerank(candidates, "query", top_k=1)

        # Should still work with default values
        assert len(reranked) == 1
        assert 'score' in reranked[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
