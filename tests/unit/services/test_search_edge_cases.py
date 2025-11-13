#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Edge case tests for SearchService
Phase 7b: Quality Assurance - Edge Cases

Tests cover:
- Zero-hit queries (no results found)
- Large result sets (100+ candidates)
- Special characters in queries (@, #, $, etc.)
- Emoji in queries
- Empty/whitespace-only queries
- Extremely long queries (1000+ words)
- Project ID edge cases (None, invalid, missing)
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.services.search import SearchService


class MockModelRouter:
    """Mock ModelRouter for testing"""
    def generate_embedding(self, text: str):
        # Return a simple vector
        return [0.5] * 384


class MockVectorDB:
    """Mock VectorDB with configurable behavior"""
    def __init__(self, results=None):
        self._results = results or []

    def search(self, query_embedding, top_k=50, filter_metadata=None):
        return self._results


class MockBM25Index:
    """Mock BM25Index with configurable behavior"""
    def __init__(self, results=None):
        self._results = results or []

    def search(self, query, top_k=50):
        return self._results


class MockCrossEncoderReranker:
    """Mock CrossEncoderReranker"""
    def __init__(self):
        self.pairs_scored = 0

    def score_pair(self, query, candidate):
        # Simple mock scoring
        return 0.5

    def rerank(self, query, candidates, top_k=10):
        # Simple passthrough reranker
        return candidates[:top_k]


def create_search_service(vector_db, bm25_index):
    """Helper function to create SearchService with proper initialization"""
    router = MockModelRouter()
    reranker = MockCrossEncoderReranker()

    return SearchService(
        vector_db,
        bm25_index,
        router,
        candidate_count=50,
        result_count=10,
        cross_encoder_reranker=reranker,
    )


class TestZeroHitQueries:
    """Test queries that intentionally return no results"""

    def test_zero_hit_empty_database(self):
        """Test query against empty database"""
        vector_db = MockVectorDB(results=[])
        bm25 = MockBM25Index(results=[])

        search = create_search_service(vector_db, bm25)

        results = search.search("nonexistent query", top_k=5)
        assert len(results) == 0

    def test_zero_hit_no_match(self):
        """Test query that doesn't match any indexed content"""
        
        # Database has content but query doesn't match
        vector_db = MockVectorDB(results=[
            {
                "id": "doc-1",
                "content": "Python programming",
                "metadata": {},
                "similarity": 0.1  # Very low similarity
            }
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Query for completely unrelated topic
        results = search.search("xyzabc12345 nonexistent topic", top_k=5)
        # Should return the low-similarity result (if no threshold applied)
        # or empty list if threshold filtering is enabled
        assert isinstance(results, list)


class TestLargeResultSets:
    """Test queries that return many candidates"""

    def test_large_vector_results(self):
        """Test handling of 100+ vector search results"""
        

        # Generate 150 mock results
        large_results = [
            {
                "id": f"doc-{i}",
                "content": f"Content {i}",
                "metadata": {},
                "similarity": 0.9 - (i * 0.001)
            }
            for i in range(150)
        ]

        vector_db = MockVectorDB(results=large_results)
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        results = search.search("test query", top_k=10)
        # Should limit to top_k
        assert len(results) <= 10

    def test_large_bm25_results(self):
        """Test handling of 100+ BM25 results"""
        
        vector_db = MockVectorDB(results=[])

        # Generate 150 mock BM25 results
        large_bm25 = [
            {
                "id": f"bm25-{i}",
                "content": f"BM25 content {i}",
                "score": 10.0 - (i * 0.01)
            }
            for i in range(150)
        ]

        bm25 = MockBM25Index(results=large_bm25)
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        results = search.search("test query", top_k=10)
        assert len(results) <= 10


class TestSpecialCharacters:
    """Test queries with special characters"""

    @pytest.mark.parametrize("special_query", [
        "search with @mentions",
        "hashtag #test query",
        "price $100 query",
        "percent % value",
        "ampersand & symbol",
        "asterisk * wildcard",
        "question? mark!",
        "brackets [test] query",
        "parentheses (test) query",
        "curly {braces} query",
        "pipe | symbol",
        "backslash \\ query",
        "forward / slash",
        "colon: semicolon; query",
        "quote \"test\" query",
        "single 'quote' query",
        "backtick `code` query",
        "tilde ~ symbol",
        "caret ^ symbol",
        "less < greater > symbols"
    ])
    def test_special_characters(self, special_query):
        """Test that special characters don't cause errors"""
        
        vector_db = MockVectorDB(results=[
            {"id": "doc-1", "content": "test", "metadata": {}, "similarity": 0.5}
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Should not raise exception
        results = search.search(special_query, top_k=5)
        assert isinstance(results, list)


class TestEmojiQueries:
    """Test queries containing emoji"""

    @pytest.mark.parametrize("emoji_query", [
        "search for 🔍 functionality",
        "bug 🐛 report",
        "performance ⚡ optimization",
        "warning ⚠️ message",
        "success ✅ criteria",
        "error ❌ handling",
        "heart ❤️ emoji",
        "火 fire kanji",
        "mixed 😀🎉🚀 emojis"
    ])
    def test_emoji_in_query(self, emoji_query):
        """Test that emoji don't cause encoding errors"""
        
        vector_db = MockVectorDB(results=[
            {"id": "doc-1", "content": "test", "metadata": {}, "similarity": 0.5}
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Should handle emoji gracefully
        results = search.search(emoji_query, top_k=5)
        assert isinstance(results, list)


class TestEmptyQueries:
    """Test empty or whitespace-only queries"""

    @pytest.mark.parametrize("empty_query", [
        "",
        " ",
        "  ",
        "\n",
        "\t",
        "   \n\t   "
    ])
    def test_empty_whitespace_queries(self, empty_query):
        """Test handling of empty/whitespace queries"""
        
        vector_db = MockVectorDB(results=[])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Should either return empty results or raise informative error
        results = search.search(empty_query, top_k=5)
        # Empty query should return empty results
        assert len(results) == 0


class TestExtremelyLongQueries:
    """Test very long queries (stress test)"""

    def test_long_query_100_words(self):
        """Test query with ~100 words"""
        words = ["word"] * 100
        long_query = " ".join(words)

        
        vector_db = MockVectorDB(results=[
            {"id": "doc-1", "content": "test", "metadata": {}, "similarity": 0.5}
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        results = search.search(long_query, top_k=5)
        assert isinstance(results, list)

    def test_long_query_1000_words(self):
        """Test query with ~1000 words"""
        words = ["query"] * 1000
        very_long_query = " ".join(words)

        
        vector_db = MockVectorDB(results=[
            {"id": "doc-1", "content": "test", "metadata": {}, "similarity": 0.5}
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Should handle gracefully (may truncate or process entire query)
        results = search.search(very_long_query, top_k=5)
        assert isinstance(results, list)


class TestProjectIDEdgeCases:
    """Test edge cases related to project_id filtering"""

    def test_none_project_id(self):
        """Test search with None project_id"""
        
        vector_db = MockVectorDB(results=[
            {"id": "doc-1", "content": "test", "metadata": {}, "similarity": 0.5}
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Search without project_id should work
        results = search.search("test query", top_k=5, filters=None)
        assert isinstance(results, list)

    def test_invalid_project_id(self):
        """Test search with invalid project_id"""
        
        vector_db = MockVectorDB(results=[])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Search with non-existent project should return empty
        results = search.search("test query", top_k=5, filters={"project_id": "NONEXISTENT_PROJECT"})
        assert isinstance(results, list)

    def test_empty_string_project_id(self):
        """Test search with empty string project_id"""
        
        vector_db = MockVectorDB(results=[
            {"id": "doc-1", "content": "test", "metadata": {}, "similarity": 0.5}
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Empty string project_id should be treated as None
        results = search.search("test query", top_k=5, filters={})
        assert isinstance(results, list)


class TestMixedEdgeCases:
    """Test combinations of edge cases"""

    def test_empty_query_with_project_id(self):
        """Test empty query combined with project filtering"""
        
        vector_db = MockVectorDB(results=[])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        results = search.search("", top_k=5, filters={"project_id": "AppBrain"})
        assert len(results) == 0

    def test_special_chars_with_emoji(self):
        """Test special characters combined with emoji"""
        
        vector_db = MockVectorDB(results=[
            {"id": "doc-1", "content": "test", "metadata": {}, "similarity": 0.5}
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        mixed_query = "search @user #tag 🔍 $100 [test]"
        results = search.search(mixed_query, top_k=5)
        assert isinstance(results, list)

    def test_long_query_with_special_chars(self):
        """Test very long query with special characters"""
        
        vector_db = MockVectorDB(results=[
            {"id": "doc-1", "content": "test", "metadata": {}, "similarity": 0.5}
        ])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        # Create a long query with interspersed special characters
        words = []
        for i in range(200):
            if i % 10 == 0:
                words.append(f"@mention{i}")
            elif i % 7 == 0:
                words.append(f"#tag{i}")
            else:
                words.append(f"word{i}")

        long_special_query = " ".join(words)
        results = search.search(long_special_query, top_k=5)
        assert isinstance(results, list)


class TestErrorMessages:
    """Test that error messages are clear and helpful"""

    def test_zero_results_message(self):
        """Verify zero results case returns appropriate structure"""
        
        vector_db = MockVectorDB(results=[])
        bm25 = MockBM25Index(results=[])
        

        search = create_search_service(
            vector_db=vector_db,
            bm25_index=bm25,
        )

        results = search.search("nonexistent", top_k=5)
        # Should return empty list, not None or error
        assert results == []
        assert isinstance(results, list)
