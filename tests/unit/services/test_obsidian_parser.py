#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for ObsidianParser

Tests conversation parsing functionality including:
- Conversation extraction (User/Assistant turns)
- Wikilink extraction
- YAML frontmatter parsing
- Conversation detection
"""

import pytest
from pathlib import Path
from src.services.obsidian_parser import ObsidianParser


class TestObsidianParser:
    """Test suite for ObsidianParser"""

    @pytest.fixture
    def parser(self):
        """Create ObsidianParser instance"""
        return ObsidianParser()

    @pytest.fixture
    def sample_conversation_md(self, tmp_path):
        """Create sample conversation Markdown file"""
        content = """# Debug Session

**User:** How to fix TypeError in Python?

**Assistant:** A TypeError usually occurs when you apply an operation to an object of inappropriate type.

**User:** Can you give an example?

**Assistant:** Sure! Here's an example:
```python
x = "5"
y = 10
result = x + y  # TypeError: can only concatenate str (not "int") to str
```

The fix is to convert types:
```python
result = int(x) + y  # Now it works!
```

Related: [[Python Type System]] and [[Common Errors]]
"""
        file_path = tmp_path / "conversation.md"
        file_path.write_text(content, encoding='utf-8')
        return file_path

    @pytest.fixture
    def sample_with_frontmatter(self, tmp_path):
        """Create sample Markdown with YAML frontmatter"""
        content = """---
tags: [python, debugging, error]
date: 2025-01-15
priority: high
---

# Debug Session

**User:** How to fix this error?

**Assistant:** Let me help you with that.
"""
        file_path = tmp_path / "with_frontmatter.md"
        file_path.write_text(content, encoding='utf-8')
        return file_path

    @pytest.fixture
    def sample_no_conversation(self, tmp_path):
        """Create sample Markdown without conversations"""
        content = """# Regular Notes

This is just a regular note.
No conversations here.
"""
        file_path = tmp_path / "no_conversation.md"
        file_path.write_text(content, encoding='utf-8')
        return file_path

    def test_parse_simple_conversation(self, parser, sample_conversation_md):
        """Test parsing a simple conversation"""
        result = parser.parse_file(str(sample_conversation_md))

        assert result is not None
        assert 'conversations' in result
        assert len(result['conversations']) == 2

        # First conversation
        conv1 = result['conversations'][0]
        assert 'user' in conv1
        assert 'assistant' in conv1
        assert 'How to fix TypeError in Python?' in conv1['user']
        assert 'TypeError usually occurs' in conv1['assistant']
        assert conv1['index'] == 0

        # Second conversation
        conv2 = result['conversations'][1]
        assert 'Can you give an example?' in conv2['user']
        assert "Sure! Here's an example:" in conv2['assistant']
        assert conv2['index'] == 1

    def test_extract_wikilinks(self, parser, sample_conversation_md):
        """Test extracting Wikilinks from content"""
        result = parser.parse_file(str(sample_conversation_md))

        assert result is not None
        assert 'wikilinks' in result
        assert 'Python Type System' in result['wikilinks']
        assert 'Common Errors' in result['wikilinks']

    def test_parse_frontmatter(self, parser, sample_with_frontmatter):
        """Test parsing YAML frontmatter"""
        result = parser.parse_file(str(sample_with_frontmatter))

        assert result is not None
        assert 'metadata' in result

        metadata = result['metadata']
        assert 'tags' in metadata
        assert 'date' in metadata
        assert metadata['date'] == '2025-01-15'
        assert metadata['priority'] == 'high'

    def test_no_conversation_returns_none(self, parser, sample_no_conversation):
        """Test that files without conversations return None"""
        result = parser.parse_file(str(sample_no_conversation))

        assert result is None

    def test_is_conversation_note(self, parser, sample_conversation_md, sample_no_conversation):
        """Test conversation detection"""
        assert parser.is_conversation_note(str(sample_conversation_md)) is True
        assert parser.is_conversation_note(str(sample_no_conversation)) is False

    def test_result_includes_metadata(self, parser, sample_conversation_md):
        """Test that result includes file metadata"""
        result = parser.parse_file(str(sample_conversation_md))

        assert result is not None
        assert 'file_path' in result
        assert 'timestamp' in result
        assert str(sample_conversation_md) in result['file_path']

    def test_empty_file(self, parser, tmp_path):
        """Test parsing empty file"""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding='utf-8')

        result = parser.parse_file(str(empty_file))
        assert result is None

    def test_wikilink_with_alias(self, parser, tmp_path):
        """Test Wikilink extraction with alias"""
        content = """**User:** Question

**Assistant:** See [[File Name|Display Text]]
"""
        file_path = tmp_path / "wikilink_alias.md"
        file_path.write_text(content, encoding='utf-8')

        result = parser.parse_file(str(file_path))

        assert result is not None
        assert 'File Name' in result['wikilinks']
        assert 'Display Text' not in result['wikilinks']  # Alias removed

    def test_wikilink_with_section(self, parser, tmp_path):
        """Test Wikilink extraction with section"""
        content = """**User:** Question

**Assistant:** See [[File Name#Section]]
"""
        file_path = tmp_path / "wikilink_section.md"
        file_path.write_text(content, encoding='utf-8')

        result = parser.parse_file(str(file_path))

        assert result is not None
        assert 'File Name' in result['wikilinks']
        assert 'File Name#Section' not in result['wikilinks']  # Section removed

    def test_duplicate_wikilinks_removed(self, parser, tmp_path):
        """Test that duplicate Wikilinks are removed"""
        content = """**User:** Question

**Assistant:** See [[File]] and [[File]] again
"""
        file_path = tmp_path / "duplicate_wikilinks.md"
        file_path.write_text(content, encoding='utf-8')

        result = parser.parse_file(str(file_path))

        assert result is not None
        assert result['wikilinks'].count('File') == 1

    def test_case_insensitive_conversation_markers(self, parser, tmp_path):
        """Test case-insensitive conversation markers"""
        content = """**user:** Question in lowercase

**assistant:** Answer in lowercase

**USER:** QUESTION IN UPPERCASE

**ASSISTANT:** ANSWER IN UPPERCASE
"""
        file_path = tmp_path / "case_insensitive.md"
        file_path.write_text(content, encoding='utf-8')

        result = parser.parse_file(str(file_path))

        assert result is not None
        assert len(result['conversations']) == 2

    def test_multiline_conversation(self, parser, tmp_path):
        """Test multiline conversations"""
        content = """**User:** This is a long question
that spans multiple lines
and continues here.

**Assistant:** This is a long answer
that also spans multiple lines
and contains:

- Bullet points
- Multiple paragraphs
- Code blocks

```python
def example():
    return "hello"
```

And more text.

**User:** Next question

**Assistant:** Next answer
"""
        file_path = tmp_path / "multiline.md"
        file_path.write_text(content, encoding='utf-8')

        result = parser.parse_file(str(file_path))

        assert result is not None
        assert len(result['conversations']) == 2

        # First conversation should include all multiline content
        conv1 = result['conversations'][0]
        assert 'spans multiple lines' in conv1['user']
        assert 'spans multiple lines' in conv1['assistant']
        assert 'def example():' in conv1['assistant']

    def test_file_not_found(self, parser):
        """Test handling of non-existent file"""
        result = parser.parse_file("/non/existent/file.md")
        assert result is None

    def test_invalid_encoding(self, parser, tmp_path):
        """Test handling of invalid encoding"""
        # Create file with non-UTF-8 encoding
        file_path = tmp_path / "invalid_encoding.md"
        with open(file_path, 'wb') as f:
            f.write(b'\xff\xfe Invalid UTF-8')

        result = parser.parse_file(str(file_path))
        assert result is None  # Should handle gracefully
