from unittest.mock import Mock

from src.processing.indexer import Indexer


def make_indexer():
    vector_db = Mock()
    bm25_index = Mock()
    model_router = Mock()
    return Indexer(vector_db, bm25_index, model_router), vector_db, bm25_index, model_router


def test_delete_by_memory_id_removes_chunks():
    indexer, vector_db, bm25_index, _ = make_indexer()

    vector_db.list_by_metadata.return_value = [
        {'id': 'mem-123-chunk-0', 'metadata': {'memory_id': 'mem-123', 'chunk_index': 0}},
        {'id': 'mem-123-metadata', 'metadata': {'memory_id': 'mem-123', 'is_memory_entry': True}},
    ]

    indexer.delete_by_memory_id('mem-123')

    vector_db.list_by_metadata.assert_called_once_with({'memory_id': 'mem-123'})
    vector_db.delete.assert_called_once_with('mem-123-chunk-0')
    bm25_index.delete.assert_called_once_with('mem-123-chunk-0')


def test_delete_by_memory_id_no_chunks():
    indexer, vector_db, bm25_index, _ = make_indexer()

    vector_db.list_by_metadata.return_value = []

    indexer.delete_by_memory_id('mem-456')

    vector_db.list_by_metadata.assert_called_once_with({'memory_id': 'mem-456'})
    vector_db.delete.assert_not_called()
    bm25_index.delete.assert_not_called()
