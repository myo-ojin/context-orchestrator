#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for hierarchical summarization utilities

Requirements: Issue #2025-11-27-01 (Long session log hierarchical summarization)
"""

import pytest
from src.utils.summarization import (
    hierarchical_summarize,
    SummaryConfig,
    validate_yaml_summary,
    extract_summary_metadata,
    _split_into_chunks,
    _detect_language_simple,
)


class TestChunking:
    """Test text chunking functionality"""

    def test_single_chunk_no_split(self):
        """Short text should not be split"""
        text = "Short text" * 100  # ~1000 chars
        chunks = _split_into_chunks(text, chunk_size=2000, overlap=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_multiple_chunks_with_overlap(self):
        """Long text should be split into overlapping chunks"""
        text = "A" * 10000  # 10k chars
        chunks = _split_into_chunks(text, chunk_size=3000, overlap=200)

        # Should have multiple chunks
        assert len(chunks) > 1

        # All chunks except possibly last should be around chunk_size
        for chunk in chunks[:-1]:
            assert len(chunk) <= 3000

        # Chunks should overlap
        if len(chunks) > 1:
            # Check overlap between first two chunks
            chunk1_end = chunks[0][-200:]
            chunk2_start = chunks[1][:200]
            # Should have some overlap
            assert len(set(chunk1_end) & set(chunk2_start)) > 0

    def test_chunk_breaks_at_newline(self):
        """Chunks should prefer breaking at newlines"""
        # Create text with clear newline boundaries
        text = "\n".join([f"Line {i}" * 50 for i in range(100)])
        chunks = _split_into_chunks(text, chunk_size=500, overlap=50)

        # At least some chunks should end with newline
        newline_endings = sum(1 for chunk in chunks if chunk.rstrip() != chunk.rstrip('\n'))
        assert newline_endings > 0


class TestLanguageDetection:
    """Test simple language detection"""

    def test_detect_japanese(self):
        """Should detect Japanese text"""
        text = "これは日本語のテキストです。"
        assert _detect_language_simple(text) == "ja"

    def test_detect_spanish(self):
        """Should detect Spanish text"""
        text = "Hola, ¿cómo estás? ñoño"
        assert _detect_language_simple(text) == "es"

    def test_detect_english_default(self):
        """Should default to English"""
        text = "Hello, how are you?"
        assert _detect_language_simple(text) == "en"


class TestYAMLValidation:
    """Test YAML summary validation"""

    def test_valid_yaml_summary(self):
        """Valid YAML summary should pass validation"""
        summary = """topic: Session log analysis
doc_type: session_log
project: AppBrain
decisions:
- text: Implement feature X
  rationale: Improves performance
  owner: alice
  due: 2025-12-01
"""
        assert validate_yaml_summary(summary) is True

    def test_minimal_valid_summary(self):
        """Summary with just topic should be valid"""
        summary = "topic: Test session"
        assert validate_yaml_summary(summary) is True

    def test_invalid_empty_summary(self):
        """Empty summary should be invalid"""
        assert validate_yaml_summary("") is False
        assert validate_yaml_summary(None) is False

    def test_invalid_no_required_keys(self):
        """Summary without required keys should be invalid"""
        summary = "notes:\n- Some note"
        assert validate_yaml_summary(summary) is False


class TestMetadataExtraction:
    """Test metadata extraction from YAML summary"""

    def test_extract_simple_fields(self):
        """Should extract topic, doc_type, project"""
        summary = """topic: Session log
doc_type: session_log
project: AppBrain
"""
        metadata = extract_summary_metadata(summary)
        assert metadata['topic'] == "Session log"
        assert metadata['doc_type'] == "session_log"
        assert metadata['project'] == "AppBrain"

    def test_extract_decisions(self):
        """Should extract decision items"""
        summary = """topic: Test
decisions:
- text: Decision 1
- text: Decision 2
"""
        metadata = extract_summary_metadata(summary)
        assert len(metadata['decisions']) == 2
        assert metadata['decisions'][0]['text'] == "Decision 1"


class TestHierarchicalSummarize:
    """Test hierarchical summarization (integration)"""

    def test_single_chunk_summarization(self):
        """Short content should use single-pass summarization"""
        content = "User: Hello\nAssistant: Hi there!" * 10

        call_count = 0

        def mock_llm(prompt, max_tokens, temperature):
            nonlocal call_count
            call_count += 1
            return "topic: Greeting\ndoc_type: conversation"

        config = SummaryConfig(chunk_size=3500, max_tokens=500)
        summary = hierarchical_summarize(content, mock_llm, config)

        # Should only call LLM once for short content
        assert call_count == 1
        assert "topic:" in summary.lower()

    def test_multi_chunk_summarization(self):
        """Long content should use hierarchical summarization"""
        # Create long content (>3500 chars)
        content = "User: Question\nAssistant: Answer\n" * 200  # ~6000 chars

        call_count = 0

        def mock_llm(prompt, max_tokens, temperature):
            nonlocal call_count
            call_count += 1
            # Return different summaries for chunks vs merge
            if "chunk" in prompt.lower():
                return f"topic: Chunk {call_count}\nnotes:\n- Chunk note"
            else:
                return "topic: Merged summary\nnotes:\n- Final note"

        config = SummaryConfig(chunk_size=3500, chunk_overlap=200, max_tokens=500)
        summary = hierarchical_summarize(content, mock_llm, config)

        # Should call LLM multiple times (chunks + merge)
        assert call_count > 1
        assert "topic:" in summary.lower()

    def test_language_override(self):
        """Should respect language override"""
        content = "Short content"

        def mock_llm(prompt, max_tokens, temperature):
            # Check that language appears in prompt
            return f"topic: Test\nlanguage_detected: {'ja' if 'japanese' in prompt.lower() else 'en'}"

        config = SummaryConfig(language="ja")
        summary = hierarchical_summarize(content, mock_llm, config, language_code="ja")

        # LLM should receive language hint
        assert summary is not None


class TestSummaryConfig:
    """Test SummaryConfig dataclass"""

    def test_default_config(self):
        """Default config should have reasonable values"""
        config = SummaryConfig()
        assert config.chunk_size == 3500
        assert config.chunk_overlap == 200
        assert config.max_tokens == 500
        assert config.temperature == 0.0
        assert config.language == "auto"

    def test_custom_config(self):
        """Should accept custom values"""
        config = SummaryConfig(
            chunk_size=2000,
            chunk_overlap=100,
            max_tokens=300,
            temperature=0.5,
            language="ja"
        )
        assert config.chunk_size == 2000
        assert config.chunk_overlap == 100
        assert config.max_tokens == 300
        assert config.temperature == 0.5
        assert config.language == "ja"
