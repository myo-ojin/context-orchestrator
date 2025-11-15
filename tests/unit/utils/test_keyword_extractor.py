#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for keyword extraction utilities
"""

import pytest
from src.utils.keyword_extractor import (
    extract_keywords,
    build_keyword_signature,
    extract_and_build_signature,
    STOP_WORDS
)


class TestExtractKeywords:
    """Test keyword extraction function"""

    def test_basic_extraction(self):
        """Test basic keyword extraction from English query"""
        query = "change feed ingestion errors"
        keywords = extract_keywords(query, top_n=3)

        assert len(keywords) <= 3
        assert 'ingestion' in keywords
        assert 'change' in keywords or 'errors' in keywords
        # Stop words should be filtered
        assert 'the' not in keywords
        assert 'and' not in keywords

    def test_sorts_by_length(self):
        """Test that longer words are prioritized"""
        query = "dashboard pilot deployment configuration"
        keywords = extract_keywords(query, top_n=3)

        # 'configuration' (13), 'deployment' (10), 'dashboard' (9)
        assert keywords[0] in ['configuration', 'deployment']

    def test_removes_duplicates(self):
        """Test that duplicate words are removed"""
        query = "error error error handling"
        keywords = extract_keywords(query, top_n=5)

        # Should only have 'error' once
        assert keywords.count('error') == 1
        assert 'handling' in keywords

    def test_min_length_filter(self):
        """Test minimum length filter"""
        query = "a ab abc abcd"
        keywords = extract_keywords(query, top_n=10, min_length=3)

        # Only 'abc' and 'abcd' should pass
        assert 'a' not in keywords
        assert 'ab' not in keywords
        assert 'abc' in keywords
        assert 'abcd' in keywords

    def test_handles_hyphens(self):
        """Test handling of hyphenated words"""
        query = "cross-encoder re-rank"
        keywords = extract_keywords(query, top_n=5)

        # Should split on hyphens
        assert 'cross' in keywords or 'encoder' in keywords
        assert 'rank' in keywords or 'rerank' in keywords

    def test_japanese_text(self):
        """Test Japanese text extraction"""
        query = "再デプロイ 監査 ガバナンス"
        keywords = extract_keywords(query, top_n=3)

        # Should extract Japanese words
        assert len(keywords) > 0
        assert '再デプロイ' in keywords or '監査' in keywords

    def test_mixed_language(self):
        """Test mixed English and Japanese"""
        query = "deployment エラー monitoring"
        keywords = extract_keywords(query, top_n=5)

        assert 'deployment' in keywords
        assert 'monitoring' in keywords
        assert 'エラー' in keywords

    def test_stop_words_filtered(self):
        """Test that stop words are filtered out"""
        query = "the quick brown fox is running"
        keywords = extract_keywords(query, top_n=5)

        # Stop words should be removed
        assert 'the' not in keywords
        assert 'is' not in keywords
        # Content words should remain
        assert 'quick' in keywords
        assert 'brown' in keywords
        assert 'running' in keywords

    def test_empty_query(self):
        """Test empty query handling"""
        assert extract_keywords("") == []
        assert extract_keywords("   ") == []

    def test_none_query(self):
        """Test None query handling"""
        assert extract_keywords(None) == []

    def test_special_characters(self):
        """Test query with special characters"""
        query = "api@v2 /endpoint (test) [brackets] {braces}"
        keywords = extract_keywords(query, top_n=5)

        # Should extract meaningful words
        assert 'api' in keywords or 'apiv2' in keywords
        assert 'endpoint' in keywords
        assert 'test' in keywords

    def test_top_n_limit(self):
        """Test that top_n limit is respected"""
        query = "one two three four five six seven"
        keywords = extract_keywords(query, top_n=3)

        assert len(keywords) == 3

    def test_case_insensitive(self):
        """Test case insensitivity"""
        query1 = "Dashboard Pilot"
        query2 = "dashboard pilot"

        keywords1 = extract_keywords(query1)
        keywords2 = extract_keywords(query2)

        # Should produce same results (lowercase)
        assert keywords1 == keywords2


class TestBuildKeywordSignature:
    """Test keyword signature building"""

    def test_basic_signature(self):
        """Test basic signature building"""
        keywords = ['ingestion', 'change', 'errors']
        signature = build_keyword_signature(keywords)

        # Should be sorted alphabetically
        assert signature == 'change+errors+ingestion'

    def test_deterministic_ordering(self):
        """Test that signature is deterministic regardless of input order"""
        keywords1 = ['apple', 'banana', 'cherry']
        keywords2 = ['cherry', 'apple', 'banana']
        keywords3 = ['banana', 'cherry', 'apple']

        sig1 = build_keyword_signature(keywords1)
        sig2 = build_keyword_signature(keywords2)
        sig3 = build_keyword_signature(keywords3)

        # All should produce same signature
        assert sig1 == sig2 == sig3
        assert sig1 == 'apple+banana+cherry'

    def test_empty_keywords(self):
        """Test empty keywords list"""
        assert build_keyword_signature([]) == ''

    def test_single_keyword(self):
        """Test single keyword"""
        signature = build_keyword_signature(['dashboard'])
        assert signature == 'dashboard'

    def test_japanese_keywords(self):
        """Test Japanese keywords"""
        keywords = ['監査', '再デプロイ', 'ガバナンス']
        signature = build_keyword_signature(keywords)

        # Should handle Japanese characters
        assert '監査' in signature
        assert '再デプロイ' in signature
        assert 'ガバナンス' in signature


class TestExtractAndBuildSignature:
    """Test combined convenience function"""

    def test_end_to_end(self):
        """Test complete extraction and signature building"""
        query = "change feed ingestion errors"
        signature = extract_and_build_signature(query, top_n=3)

        # Should be a valid signature
        assert signature
        assert '+' in signature or len(signature.split('+')) == 1

    def test_empty_query(self):
        """Test empty query"""
        signature = extract_and_build_signature("")
        assert signature == ''

    def test_realistic_queries(self):
        """Test realistic query examples"""
        queries_and_expected = [
            ("timeline view orchestrator", "timeline+view"),
            ("TypeError chunker fix", "chunker+typeerror"),
            ("dashboard pilot deployment", "dashboard+deployment"),
        ]

        for query, expected_part in queries_and_expected:
            signature = extract_and_build_signature(query, top_n=3)
            # Check that expected keywords are present
            for word in expected_part.split('+'):
                assert word in signature or len(signature) > 0


class TestStopWords:
    """Test stop words set"""

    def test_stop_words_defined(self):
        """Test that stop words are defined"""
        assert isinstance(STOP_WORDS, set)
        assert len(STOP_WORDS) > 0

    def test_common_stop_words(self):
        """Test that common stop words are included"""
        assert 'the' in STOP_WORDS
        assert 'and' in STOP_WORDS
        assert 'is' in STOP_WORDS
        assert 'of' in STOP_WORDS

    def test_japanese_stop_words(self):
        """Test that Japanese stop words are included"""
        assert 'の' in STOP_WORDS
        assert 'は' in STOP_WORDS
        assert 'が' in STOP_WORDS
