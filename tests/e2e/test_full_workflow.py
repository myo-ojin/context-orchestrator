#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
End-to-end validation tests for Context Orchestrator

Tests the complete workflow:
1. Record conversation (ingestion)
2. Search for memory
3. Retrieve and verify results
4. Consolidation workflow
5. Session logging

Requirements: All Requirements (Phase 14.1)
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

from src.services.ingestion import IngestionService
from src.services.search import SearchService
from src.services.consolidation import ConsolidationService
from src.services.session_manager import SessionManager
from src.processing.classifier import SchemaClassifier
from src.processing.chunker import Chunker
from src.processing.indexer import Indexer
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index
from src.models.local_llm import LocalLLMClient


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_local_llm():
    """Mock LocalLLMClient for testing"""
    client = Mock(spec=LocalLLMClient)

    # Mock embedding generation (returns deterministic vectors)
    def generate_embedding_side_effect(text: str):
        # Generate deterministic embedding based on text hash
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # Generate 384-dim embedding (nomic-embed-text dimension)
        return [(hash_val % 1000 + i) / 1000.0 for i in range(384)]

    client.generate_embedding.side_effect = generate_embedding_side_effect

    # Mock classification
    client.generate.return_value = "Incident"

    return client


@pytest.fixture
def test_services(temp_data_dir, mock_local_llm):
    """Initialize all services for end-to-end testing"""
    # Initialize storage
    vector_db = ChromaVectorDB(
        persist_directory=str(Path(temp_data_dir) / "chroma_db")
    )

    bm25_index = BM25Index(
        index_path=str(Path(temp_data_dir) / "bm25_index.pkl")
    )

    # Initialize processing components
    classifier = SchemaClassifier(llm_client=mock_local_llm)
    chunker = Chunker()
    indexer = Indexer(vector_db=vector_db, bm25_index=bm25_index)

    # Initialize services
    ingestion_service = IngestionService(
        classifier=classifier,
        chunker=chunker,
        indexer=indexer,
        llm_client=mock_local_llm
    )

    search_service = SearchService(
        vector_db=vector_db,
        bm25_index=bm25_index,
        llm_client=mock_local_llm
    )

    consolidation_service = ConsolidationService(
        vector_db=vector_db,
        bm25_index=bm25_index,
        llm_client=mock_local_llm
    )

    return {
        'ingestion': ingestion_service,
        'search': search_service,
        'consolidation': consolidation_service,
        'vector_db': vector_db,
        'bm25_index': bm25_index
    }


class TestEndToEndWorkflow:
    """End-to-end workflow validation tests"""

    def test_basic_ingestion_and_retrieval(self, test_services):
        """Test: Ingest conversation → Search → Retrieve"""
        ingestion = test_services['ingestion']
        search = test_services['search']

        # Step 1: Ingest a conversation
        conversation = {
            'user': 'How do I fix a TypeError in Python?',
            'assistant': 'A TypeError occurs when you apply an operation to an object of inappropriate type. Here is an example:\n```python\nx = "5"\ny = 10\nresult = x + y  # TypeError\n```\nTo fix it, convert the types:\n```python\nresult = int(x) + y  # Now it works\n```',
            'source': 'claude_cli',
            'refs': ['https://docs.python.org/3/tutorial/errors.html']
        }

        memory_id = ingestion.ingest_conversation(conversation)

        assert memory_id is not None
        assert len(memory_id) > 0

        # Step 2: Search for the conversation
        results = search.search("Python TypeError fix", limit=5)

        assert len(results) > 0

        # Step 3: Verify retrieved memory contains original content
        found = False
        for result in results:
            if 'TypeError occurs' in result['content'] or 'TypeError' in result['content']:
                found = True
                assert result['memory_id'] == memory_id
                assert result['schema'] == 'Incident'
                assert 'https://docs.python.org/3/tutorial/errors.html' in result['refs']
                break

        assert found, "Ingested conversation not found in search results"

    def test_multiple_conversations_retrieval(self, test_services):
        """Test: Ingest multiple conversations → Search → Verify ranking"""
        ingestion = test_services['ingestion']
        search = test_services['search']

        # Ingest multiple conversations
        conversations = [
            {
                'user': 'How to implement binary search in Python?',
                'assistant': 'Binary search is an efficient algorithm for searching sorted arrays. Here is the implementation:\n```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n```',
                'source': 'claude_cli',
                'refs': []
            },
            {
                'user': 'What is the time complexity of binary search?',
                'assistant': 'Binary search has O(log n) time complexity because it divides the search space in half with each iteration.',
                'source': 'claude_cli',
                'refs': []
            },
            {
                'user': 'How to sort a list in Python?',
                'assistant': 'You can sort a list using the built-in sorted() function or the list.sort() method:\n```python\n# Using sorted() - returns new list\nnumbers = [3, 1, 4, 1, 5]\nsorted_numbers = sorted(numbers)\n\n# Using sort() - sorts in place\nnumbers.sort()\n```',
                'source': 'claude_cli',
                'refs': []
            }
        ]

        memory_ids = []
        for conv in conversations:
            memory_id = ingestion.ingest_conversation(conv)
            memory_ids.append(memory_id)

        # Search for binary search related content
        results = search.search("binary search algorithm", limit=10)

        assert len(results) >= 2  # Should find at least the two binary search conversations

        # Verify that binary search results rank higher
        top_result = results[0]
        assert 'binary search' in top_result['content'].lower()

    def test_consolidation_workflow(self, test_services):
        """Test: Ingest → Consolidate → Verify clustering"""
        ingestion = test_services['ingestion']
        consolidation = test_services['consolidation']
        search = test_services['search']

        # Ingest similar conversations (should cluster)
        similar_conversations = [
            {
                'user': 'How to create a virtual environment in Python?',
                'assistant': 'Use `python -m venv .venv` to create a virtual environment.',
                'source': 'claude_cli',
                'refs': [],
                'timestamp': (datetime.now() - timedelta(days=2)).isoformat()
            },
            {
                'user': 'How do I activate a Python virtual environment?',
                'assistant': 'On Windows: `.venv\\Scripts\\Activate.ps1`, on Unix: `source .venv/bin/activate`',
                'source': 'claude_cli',
                'refs': [],
                'timestamp': (datetime.now() - timedelta(days=1)).isoformat()
            }
        ]

        memory_ids = []
        for conv in similar_conversations:
            memory_id = ingestion.ingest_conversation(conv)
            memory_ids.append(memory_id)

        # Run consolidation
        stats = consolidation.consolidate()

        assert stats is not None
        assert 'migrated' in stats
        assert 'clustered' in stats
        assert 'forgotten' in stats

        # Verify memories still searchable after consolidation
        results = search.search("Python virtual environment", limit=5)
        assert len(results) > 0

    def test_search_with_no_results(self, test_services):
        """Test: Search for non-existent content"""
        search = test_services['search']

        # Search before any ingestion
        results = search.search("quantum computing blockchain AI", limit=10)

        # Should return empty results, not crash
        assert results == [] or len(results) == 0

    def test_search_with_special_characters(self, test_services):
        """Test: Ingest and search with special characters"""
        ingestion = test_services['ingestion']
        search = test_services['search']

        conversation = {
            'user': 'How to use regex pattern [a-z]+ in Python?',
            'assistant': 'Use the `re` module: `import re; re.findall(r"[a-z]+", "Hello World")`',
            'source': 'claude_cli',
            'refs': []
        }

        memory_id = ingestion.ingest_conversation(conversation)

        # Search with special characters
        results = search.search("[a-z]+ regex pattern", limit=5)

        assert len(results) > 0
        found = any(memory_id in result['memory_id'] for result in results)
        assert found

    def test_ingestion_with_long_content(self, test_services):
        """Test: Ingest long conversation (tests chunking)"""
        ingestion = test_services['ingestion']
        search = test_services['search']

        # Create long content (should be split into multiple chunks)
        long_assistant_response = "# Understanding Neural Networks\n\n" + "\n\n".join([
            f"## Section {i}\n\nThis is section {i} with detailed explanation of neural network concepts. " * 50
            for i in range(10)
        ])

        conversation = {
            'user': 'Explain neural networks in detail',
            'assistant': long_assistant_response,
            'source': 'claude_cli',
            'refs': []
        }

        memory_id = ingestion.ingest_conversation(conversation)

        assert memory_id is not None

        # Search should find the content
        results = search.search("neural network concepts", limit=5)
        assert len(results) > 0

    def test_japanese_text_handling(self, test_services):
        """Test: Ingest and search Japanese text"""
        ingestion = test_services['ingestion']
        search = test_services['search']

        conversation = {
            'user': 'Pythonでエラーハンドリングを実装する方法は？',
            'assistant': '`try-except`ブロックを使用します：\n```python\ntry:\n    risky_operation()\nexcept ValueError as e:\n    print(f"エラー: {e}")\n```',
            'source': 'claude_cli',
            'refs': []
        }

        memory_id = ingestion.ingest_conversation(conversation)

        # Search in Japanese
        results = search.search("Pythonエラーハンドリング", limit=5)

        # Should handle Japanese text without crashing
        assert memory_id is not None

    def test_ingestion_with_code_blocks(self, test_services):
        """Test: Ingest conversation with multiple code blocks"""
        ingestion = test_services['ingestion']
        search = test_services['search']

        conversation = {
            'user': 'Show me different sorting algorithms',
            'assistant': '''Here are three sorting algorithms:

## Bubble Sort
```python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
```

## Quick Sort
```python
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
```

## Merge Sort
```python
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)
```
''',
            'source': 'claude_cli',
            'refs': []
        }

        memory_id = ingestion.ingest_conversation(conversation)

        # Search for specific algorithm
        results = search.search("quick sort algorithm", limit=5)

        assert len(results) > 0
        # Verify code blocks are preserved
        found_code = False
        for result in results:
            if '```python' in result['content'] or 'def quick_sort' in result['content']:
                found_code = True
                break

        assert found_code, "Code blocks should be preserved in chunks"

    def test_search_result_ranking(self, test_services):
        """Test: Verify search results are properly ranked by relevance"""
        ingestion = test_services['ingestion']
        search = test_services['search']

        # Ingest conversations with varying relevance
        conversations = [
            {
                'user': 'What is machine learning?',
                'assistant': 'Machine learning is a subset of artificial intelligence that enables systems to learn from data.',
                'source': 'claude_cli',
                'refs': []
            },
            {
                'user': 'Explain neural networks and deep learning in machine learning',
                'assistant': 'Neural networks are the foundation of deep learning, a powerful machine learning technique inspired by the human brain. Deep learning uses multiple layers of neural networks to learn complex patterns in data.',
                'source': 'claude_cli',
                'refs': ['https://example.com/deep-learning']
            },
            {
                'user': 'How to install Python packages?',
                'assistant': 'Use pip: `pip install package_name`',
                'source': 'claude_cli',
                'refs': []
            }
        ]

        for conv in conversations:
            ingestion.ingest_conversation(conv)

        # Search for machine learning
        results = search.search("deep learning neural networks machine learning", limit=10)

        assert len(results) > 0

        # The second conversation should rank highest (most relevant)
        top_result = results[0]
        assert 'neural network' in top_result['content'].lower() or 'deep learning' in top_result['content'].lower()


class TestErrorHandling:
    """Test error handling across the system"""

    def test_ingestion_with_missing_fields(self, test_services):
        """Test: Ingest conversation with missing required fields"""
        ingestion = test_services['ingestion']

        # Missing 'assistant' field
        invalid_conversation = {
            'user': 'This is a question',
            'source': 'claude_cli'
        }

        with pytest.raises(Exception):
            ingestion.ingest_conversation(invalid_conversation)

    def test_ingestion_with_empty_content(self, test_services):
        """Test: Ingest conversation with empty content"""
        ingestion = test_services['ingestion']

        conversation = {
            'user': '',
            'assistant': '',
            'source': 'claude_cli',
            'refs': []
        }

        # Should handle gracefully (may raise error or return None)
        try:
            memory_id = ingestion.ingest_conversation(conversation)
            # If it succeeds, verify it's handled properly
            if memory_id:
                assert len(memory_id) > 0
        except Exception:
            # Error is acceptable for empty content
            pass

    def test_search_with_empty_query(self, test_services):
        """Test: Search with empty query"""
        search = test_services['search']

        # Empty query should return empty results or raise error
        try:
            results = search.search("", limit=10)
            # If it succeeds, should return empty
            assert results == [] or len(results) == 0
        except Exception:
            # Error is acceptable for empty query
            pass


class TestPerformance:
    """Performance validation tests"""

    def test_search_latency(self, test_services):
        """Test: Verify search latency is within acceptable bounds"""
        import time

        ingestion = test_services['ingestion']
        search = test_services['search']

        # Ingest test data
        for i in range(20):
            conversation = {
                'user': f'Question {i} about Python programming',
                'assistant': f'Answer {i}: Python is a high-level programming language. ' * 10,
                'source': 'claude_cli',
                'refs': []
            }
            ingestion.ingest_conversation(conversation)

        # Measure search latency
        start_time = time.time()
        results = search.search("Python programming", limit=10)
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000

        # Target: ≤200ms (from requirements)
        # Note: May be higher in test environment without optimizations
        assert latency_ms < 2000, f"Search latency {latency_ms}ms exceeds reasonable bounds (should be <2000ms in test env)"

        # Log the latency for monitoring
        print(f"\nSearch latency: {latency_ms:.2f}ms")

    def test_batch_ingestion_performance(self, test_services):
        """Test: Batch ingestion performance"""
        import time

        ingestion = test_services['ingestion']

        # Ingest multiple conversations
        conversations = [
            {
                'user': f'Question {i}',
                'assistant': f'Answer {i}: This is a detailed response. ' * 20,
                'source': 'claude_cli',
                'refs': []
            }
            for i in range(10)
        ]

        start_time = time.time()
        for conv in conversations:
            ingestion.ingest_conversation(conv)
        end_time = time.time()

        total_time = end_time - start_time
        avg_time_per_conv = total_time / len(conversations)

        # Target: <5 seconds per conversation (from requirements)
        # Note: Mock LLM should be fast, but file I/O may vary
        assert avg_time_per_conv < 10, f"Average ingestion time {avg_time_per_conv:.2f}s per conversation exceeds bounds"

        print(f"\nBatch ingestion: {len(conversations)} conversations in {total_time:.2f}s ({avg_time_per_conv:.2f}s per conversation)")


def test_full_system_integration():
    """
    Integration test stub for manual validation

    This test requires:
    - Actual Ollama service running
    - Real models installed (nomic-embed-text, qwen2.5:7b)
    - Actual data directory

    Run manually with: pytest tests/e2e/test_full_workflow.py::test_full_system_integration -v
    """
    pytest.skip("Manual integration test - requires Ollama service")
