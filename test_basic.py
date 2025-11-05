#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic implementation test for Phase 1 & 2

This script validates that the implemented components work correctly.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_data_models():
    """Test Memory, Chunk, and Config data models"""
    from models import Memory, Chunk, Config, SchemaType, MemoryType
    from datetime import datetime

    print("Testing data models...")

    # Test Memory
    memory = Memory(
        id="test-001",
        schema_type=SchemaType.INCIDENT,
        content="Test incident",
        summary="Test summary",
        refs=["https://example.com"],
        tags=["test"]
    )

    # Test serialization
    memory_dict = memory.to_dict()
    assert memory_dict['id'] == "test-001"
    assert memory_dict['schema_type'] == "Incident"

    # Test deserialization
    memory2 = Memory.from_dict(memory_dict)
    assert memory2.id == "test-001"
    assert memory2.schema_type == SchemaType.INCIDENT

    # Test Chunk
    chunk = Chunk(
        id="chunk-001",
        memory_id="test-001",
        content="Test chunk content",
        tokens=10
    )

    chunk_dict = chunk.to_dict()
    assert chunk_dict['id'] == "chunk-001"

    # Test Config
    config = Config()
    assert config.ollama_url == "http://localhost:11434"
    assert config.embedding_model == "nomic-embed-text"

    print("[OK] Data models working correctly")


def test_bm25_index():
    """Test BM25 index"""
    from storage.bm25_index import BM25Index

    print("\nTesting BM25 index...")

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "test_index.pkl"

        # Create index
        index = BM25Index(str(index_path))

        # Add documents
        index.add_document("doc1", "Python is a programming language")
        index.add_document("doc2", "JavaScript is also a programming language")
        index.add_document("doc3", "Coffee is a drink")

        # Test search
        results = index.search("programming language", top_k=2)
        assert len(results) == 2
        assert results[0]['id'] in ["doc1", "doc2"]

        # Test count
        assert index.count() == 3

        # Test get
        doc1 = index.get("doc1")
        assert doc1 == "Python is a programming language"

        # Test delete
        index.delete("doc3")
        assert index.count() == 2

        print("[OK] BM25 index working correctly")


def test_vector_db():
    """Test Chroma vector database"""
    # Note: This requires chromadb to be installed
    # Skip if not available
    try:
        from storage.vector_db import ChromaVectorDB
    except ImportError:
        print("\n[skip] Skipping vector DB test (chromadb not installed)")
        return

    print("\nTesting Chroma vector DB...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_chroma"

        # Create database
        try:
            db = ChromaVectorDB(str(db_path))
        except ImportError:
            print("\n[skip] Skipping vector DB test (chromadb runtime unavailable)")
            return

        # Add memory with dummy embedding
        embedding = [0.1] * 384  # 384-dimensional vector (nomic-embed-text dimension)
        metadata = {
            "schema_type": "Incident",
            "timestamp": "2025-01-01T00:00:00",
            "tags": ["test"]
        }

        db.add(
            id="mem-001",
            embedding=embedding,
            metadata=metadata,
            document="Test memory content"
        )

        # Test count
        assert db.count() == 1

        # Test get
        memory = db.get("mem-001")
        assert memory is not None
        assert memory['id'] == "mem-001"
        assert memory['content'] == "Test memory content"

        # Test search
        results = db.search(embedding, top_k=1)
        assert len(results) == 1
        assert results[0]['id'] == "mem-001"

        # Test delete
        db.delete("mem-001")
        assert db.count() == 0

        print("✓ Chroma vector DB working correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1 & 2 Implementation Test")
    print("=" * 60)

    try:
        test_data_models()
        test_bm25_index()
        test_vector_db()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
