#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for IngestionService

Tests the conversation ingestion pipeline including:
- Schema classification
- Summary generation
- Memory creation
- Chunking
- Indexing
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.services.ingestion import IngestionService
from src.models import Memory, Chunk, SchemaType, MemoryType


class TestIngestionService:
    """Test suite for IngestionService"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for IngestionService"""
        vector_db = Mock()
        classifier = Mock()
        chunker = Mock()
        indexer = Mock()
        model_router = Mock()

        return {
            'vector_db': vector_db,
            'classifier': classifier,
            'chunker': chunker,
            'indexer': indexer,
            'model_router': model_router
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create IngestionService instance with mocks"""
        return IngestionService(**mock_dependencies)

    @pytest.fixture
    def sample_conversation(self):
        """Sample conversation for testing"""
        return {
            'user': 'How to fix TypeError in Python?',
            'assistant': 'Check for None values before accessing attributes.',
            'timestamp': '2025-01-15T10:30:00Z',
            'source': 'cli',
            'refs': ['https://example.com/python-errors']
        }

    def test_init(self, service, mock_dependencies):
        """Test service initialization"""
        assert service.vector_db == mock_dependencies['vector_db']
        assert service.classifier == mock_dependencies['classifier']
        assert service.chunker == mock_dependencies['chunker']
        assert service.indexer == mock_dependencies['indexer']
        assert service.model_router == mock_dependencies['model_router']

    def test_ingest_conversation_success(self, service, sample_conversation, mock_dependencies):
        """Test successful conversation ingestion"""
        # Setup mocks
        mock_dependencies['classifier'].classify_conversation.return_value = SchemaType.INCIDENT
        mock_dependencies['model_router'].route.return_value = "Summary of the conversation"

        # Create mock chunks
        mock_chunk = Chunk(
            id='mem-123-chunk-0',
            memory_id='mem-123',
            content='Test content',
            tokens=50,
            metadata={'source': 'cli'}
        )
        mock_dependencies['chunker'].chunk_conversation.return_value = [mock_chunk]

        # Execute
        memory_id = service.ingest_conversation(sample_conversation)

        # Assertions
        assert memory_id is not None
        assert memory_id.startswith('mem-')

        # Verify classifier was called
        mock_dependencies['classifier'].classify_conversation.assert_called_once()

        # Verify model router was called for summary
        mock_dependencies['model_router'].route.assert_called()

        # Verify chunker was called
        mock_dependencies['chunker'].chunk_conversation.assert_called_once()

        # Verify indexer was called
        mock_dependencies['indexer'].index.assert_called_once()

        # Verify vector_db add was called for metadata
        mock_dependencies['vector_db'].add.assert_called()

    def test_ingest_conversation_classification_failure(self, service, sample_conversation, mock_dependencies):
        """Test ingestion when classification fails (should fallback to PROCESS)"""
        # Setup mocks
        mock_dependencies['classifier'].classify_conversation.side_effect = Exception("Classification error")
        mock_dependencies['model_router'].route.return_value = "Summary"

        mock_chunk = Chunk(
            id='mem-123-chunk-0',
            memory_id='mem-123',
            content='Test content',
            tokens=50,
            metadata={}
        )
        mock_dependencies['chunker'].chunk_conversation.return_value = [mock_chunk]

        # Execute
        memory_id = service.ingest_conversation(sample_conversation)

        # Should still succeed with fallback
        assert memory_id is not None
        assert memory_id.startswith('mem-')

    def test_ingest_conversation_summary_failure(self, service, sample_conversation, mock_dependencies):
        """Test ingestion when summary generation fails (should use fallback)"""
        # Setup mocks
        mock_dependencies['classifier'].classify_conversation.return_value = SchemaType.SNIPPET
        mock_dependencies['model_router'].route.side_effect = Exception("Summary error")

        mock_chunk = Chunk(
            id='mem-123-chunk-0',
            memory_id='mem-123',
            content='Test content',
            tokens=50,
            metadata={}
        )
        mock_dependencies['chunker'].chunk_conversation.return_value = [mock_chunk]

        # Execute
        memory_id = service.ingest_conversation(sample_conversation)

        # Should still succeed with fallback summary
        assert memory_id is not None

    def test_classify_schema(self, service, sample_conversation, mock_dependencies):
        """Test schema classification"""
        mock_dependencies['classifier'].classify_conversation.return_value = SchemaType.INCIDENT

        result = service._classify_schema(sample_conversation)

        assert result == SchemaType.INCIDENT
        mock_dependencies['classifier'].classify_conversation.assert_called_once_with(
            sample_conversation['user'],
            sample_conversation['assistant'],
            {}
        )

    def test_generate_summary(self, service, sample_conversation, mock_dependencies):
        """Test summary generation"""
        expected_summary = "Short summary of the conversation"
        mock_dependencies['model_router'].route.return_value = expected_summary

        result = service._generate_summary(sample_conversation)

        assert result == expected_summary
        mock_dependencies['model_router'].route.assert_called_once()

        # Verify it uses 'short_summary' task type
        call_args = mock_dependencies['model_router'].route.call_args
        assert call_args[1]['task_type'] == 'short_summary'

    def test_create_memory(self, service, sample_conversation):
        """Test memory creation"""
        schema_type = SchemaType.INCIDENT
        summary = "Test summary"

        memory = service._create_memory(sample_conversation, schema_type, summary)

        assert isinstance(memory, Memory)
        assert memory.id.startswith('mem-')
        assert memory.schema_type == schema_type
        assert memory.summary == summary
        assert 'cli' in memory.metadata['source']
        assert memory.memory_type == MemoryType.WORKING
        assert len(memory.refs) == 1

    def test_chunk_content(self, service, sample_conversation, mock_dependencies):
        """Test content chunking"""
        memory_id = 'mem-test-123'
        metadata = {'source': 'cli'}

        mock_chunk = Chunk(
            id=f'{memory_id}-chunk-0',
            memory_id=memory_id,
            content='User: test\n\nAssistant: response',
            tokens=20,
            metadata=metadata
        )
        mock_dependencies['chunker'].chunk_conversation.return_value = [mock_chunk]

        chunks = service._chunk_content(sample_conversation, memory_id, metadata)

        assert len(chunks) == 1
        assert chunks[0].memory_id == memory_id
        mock_dependencies['chunker'].chunk_conversation.assert_called_once()

    def test_index_chunks(self, service, mock_dependencies):
        """Test chunk indexing"""
        mock_chunk = Chunk(
            id='chunk-1',
            memory_id='mem-123',
            content='Test content',
            tokens=10,
            metadata={}
        )
        chunks = [mock_chunk]

        service._index_chunks(chunks)

        mock_dependencies['indexer'].index.assert_called_once_with(chunks)

    def test_store_memory_metadata(self, service, mock_dependencies):
        """Test memory metadata storage"""
        memory = Memory(
            id='mem-test-123',
            schema_type=SchemaType.SNIPPET,
            content='Test content',
            summary='Test summary',
            refs=['http://example.com'],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        mock_dependencies['model_router'].generate_embedding.return_value = [0.1] * 768

        service._store_memory_metadata(memory)

        # Verify embedding was generated
        mock_dependencies['model_router'].generate_embedding.assert_called_once_with(memory.summary)

        # Verify vector_db.add was called
        mock_dependencies['vector_db'].add.assert_called_once()

        # Verify the ID has -metadata suffix
        call_args = mock_dependencies['vector_db'].add.call_args
        assert call_args[1]['id'] == 'mem-test-123-metadata'

    def test_get_memory(self, service, mock_dependencies):
        """Test memory retrieval"""
        memory_id = 'mem-test-123'

        # Mock vector_db.get return value
        mock_dependencies['vector_db'].get.return_value = {
            'content': 'Test summary',
            'metadata': {
                'memory_id': memory_id,
                'schema_type': 'Incident',
                'memory_type': 'working',
                'strength': 1.0,
                'importance': 0.5,
                'created_at': '2025-01-15T10:30:00',
                'tags': ['test']
            }
        }

        memory = service.get_memory(memory_id)

        assert memory is not None
        assert memory.id == memory_id
        assert memory.schema_type == SchemaType.INCIDENT
        mock_dependencies['vector_db'].get.assert_called_once_with(f'{memory_id}-metadata')

    def test_get_memory_not_found(self, service, mock_dependencies):
        """Test memory retrieval when memory doesn't exist"""
        memory_id = 'mem-nonexistent'
        mock_dependencies['vector_db'].get.return_value = None

        memory = service.get_memory(memory_id)

        assert memory is None

    def test_delete_memory(self, service, mock_dependencies):
        """Test memory deletion"""
        memory_id = 'mem-test-123'

        result = service.delete_memory(memory_id)

        assert result is True
        mock_dependencies['vector_db'].delete.assert_called_once_with(f'{memory_id}-metadata')
        mock_dependencies['indexer'].delete_by_memory_id.assert_called_once_with(memory_id)

    def test_ingest_batch(self, service, sample_conversation, mock_dependencies):
        """Test batch conversation ingestion"""
        # Setup mocks
        mock_dependencies['classifier'].classify_conversation.return_value = SchemaType.PROCESS
        mock_dependencies['model_router'].route.return_value = "Summary"

        mock_chunk = Chunk(
            id='mem-123-chunk-0',
            memory_id='mem-123',
            content='Test content',
            tokens=50,
            metadata={}
        )
        mock_dependencies['chunker'].chunk_conversation.return_value = [mock_chunk]

        # Create 3 conversations
        conversations = [sample_conversation, sample_conversation.copy(), sample_conversation.copy()]

        memory_ids = service.ingest_batch(conversations)

        assert len(memory_ids) == 3
        assert all(mid.startswith('mem-') for mid in memory_ids)

    def test_get_ingestion_stats(self, service, mock_dependencies):
        """Test ingestion statistics"""
        mock_dependencies['indexer'].get_index_stats.return_value = {
            'vector_db_count': 450,
            'bm25_count': 450
        }

        stats = service.get_ingestion_stats()

        assert 'total_memories' in stats
        assert 'total_chunks' in stats
        assert stats['total_chunks'] == 450

    def test_timestamp_parsing(self, service, sample_conversation, mock_dependencies):
        """Test various timestamp formats"""
        # Setup mocks
        mock_dependencies['classifier'].classify_conversation.return_value = SchemaType.PROCESS
        mock_dependencies['model_router'].route.return_value = "Summary"
        mock_chunk = Chunk(
            id='mem-123-chunk-0',
            memory_id='mem-123',
            content='Test',
            tokens=10,
            metadata={}
        )
        mock_dependencies['chunker'].chunk_conversation.return_value = [mock_chunk]

        # Test with various timestamp formats
        test_cases = [
            '2025-01-15T10:30:00Z',
            '2025-01-15T10:30:00+00:00',
            None  # Should use current time
        ]

        for timestamp in test_cases:
            conv = sample_conversation.copy()
            conv['timestamp'] = timestamp

            memory_id = service.ingest_conversation(conv)
            assert memory_id is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
