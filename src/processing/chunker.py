#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Text Chunker

Splits text into semantic chunks of maximum 512 tokens.
Preserves Markdown structure (headings, paragraphs, code blocks).

Uses tiktoken for token counting (cl100k_base encoding).

Requirements: Requirement 3 (MVP - Chunking)
"""

from typing import List, Dict, Any, Optional
import re
import logging
import uuid

try:
    import tiktoken
except ImportError:
    tiktoken = None
    logging.warning("tiktoken not installed, token counting will be approximate")

from src.models import Chunk

logger = logging.getLogger(__name__)


class Chunker:
    """
    Chunker for splitting text into semantic units

    Splits text into chunks with maximum 512 tokens.
    Respects Markdown structure:
    - Primary split: Headings (#, ##, ###)
    - Secondary split: Paragraphs (\\n\\n)
    - Never split: Code blocks (```...```)

    Attributes:
        tokenizer: tiktoken tokenizer
        max_tokens: Maximum tokens per chunk (default: 512)
    """

    def __init__(self, tokenizer_name: str = "cl100k_base", max_tokens: int = 512):
        """
        Initialize Chunker

        Args:
            tokenizer_name: tiktoken encoding name (default: cl100k_base)
            max_tokens: Maximum tokens per chunk (default: 512)
        """
        self.max_tokens = max_tokens

        # Initialize tokenizer
        if tiktoken is not None:
            try:
                self.tokenizer = tiktoken.get_encoding(tokenizer_name)
                logger.info(f"Initialized Chunker with {tokenizer_name} tokenizer")
            except Exception as e:
                logger.warning(f"Failed to load tiktoken encoding: {e}")
                self.tokenizer = None
        else:
            self.tokenizer = None
            logger.warning("tiktoken not available, using approximate token counting")

    def chunk(
        self,
        text: str,
        memory_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into chunks

        Args:
            text: Input text (Markdown format)
            memory_id: Parent memory ID
            metadata: Metadata to attach to each chunk

        Returns:
            List of Chunk objects

        Example:
            >>> chunker = Chunker()
            >>> chunks = chunker.chunk("# Title\\n\\nContent...", memory_id="mem-123")
            >>> print(len(chunks))
            3
        """
        if metadata is None:
            metadata = {}

        # Step 1: Extract and preserve code blocks
        text, code_blocks = self._extract_code_blocks(text)

        # Step 2: Split by headings
        sections = self._split_by_headings(text)

        # Step 3: Split large sections by paragraphs
        chunks_text = []
        for section in sections:
            if self._count_tokens(section) > self.max_tokens:
                # Section too large, split by paragraphs
                sub_chunks = self._split_by_paragraphs(section)
                chunks_text.extend(sub_chunks)
            else:
                chunks_text.append(section)

        # Step 4: Restore code blocks
        chunks_text = self._restore_code_blocks(chunks_text, code_blocks)

        # Step 5: Create Chunk objects
        chunks = []
        for i, chunk_text in enumerate(chunks_text):
            if not chunk_text.strip():
                continue  # Skip empty chunks

            chunk_metadata = metadata.copy()
            chunk_metadata.setdefault('memory_id', memory_id)
            chunk_metadata.setdefault('chunk_index', i)

            chunk = Chunk(
                id=f"{memory_id}-chunk-{i}",
                memory_id=memory_id,
                content=chunk_text.strip(),
                tokens=self._count_tokens(chunk_text),
                metadata=chunk_metadata
            )
            chunks.append(chunk)

        logger.debug(f"Split text into {len(chunks)} chunks (memory_id={memory_id})")
        return chunks

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken

        Args:
            text: Input text

        Returns:
            Token count

        Note:
            Falls back to word count / 0.75 if tiktoken is unavailable
        """
        if self.tokenizer is not None:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Token counting failed: {e}")

        # Fallback: approximate with word count
        # Rough estimate: 1 token ≈ 0.75 words
        word_count = len(text.split())
        return int(word_count / 0.75)

    def _extract_code_blocks(self, text: str) -> tuple[str, Dict[str, str]]:
        """
        Extract code blocks and replace with placeholders

        Args:
            text: Input text

        Returns:
            Tuple of (text with placeholders, dict of code blocks)

        Example:
            >>> text = "# Title\\n```python\\ncode\\n```\\nEnd"
            >>> result, blocks = chunker._extract_code_blocks(text)
            >>> "CODE_BLOCK_" in result
            True
        """
        code_blocks = {}
        counter = 0

        def replace_code_block(match):
            nonlocal counter
            code = match.group(0)
            placeholder = f"__CODE_BLOCK_{counter}__"
            code_blocks[placeholder] = code
            counter += 1
            return placeholder

        # Match code blocks: ```...``` (non-greedy)
        pattern = r'```[\s\S]*?```'
        text_with_placeholders = re.sub(pattern, replace_code_block, text)

        logger.debug(f"Extracted {len(code_blocks)} code blocks")
        return text_with_placeholders, code_blocks

    def _restore_code_blocks(
        self,
        chunks: List[str],
        code_blocks: Dict[str, str]
    ) -> List[str]:
        """
        Restore code blocks from placeholders

        Args:
            chunks: List of chunk texts with placeholders
            code_blocks: Dict mapping placeholders to code blocks

        Returns:
            List of chunks with restored code blocks
        """
        restored = []
        for chunk in chunks:
            for placeholder, code in code_blocks.items():
                chunk = chunk.replace(placeholder, code)
            restored.append(chunk)

        return restored

    def _split_by_headings(self, text: str) -> List[str]:
        """
        Split text by Markdown headings (#, ##, ###)

        Args:
            text: Input text

        Returns:
            List of sections (each starting with a heading or content)

        Example:
            >>> text = "# H1\\nContent\\n## H2\\nMore"
            >>> sections = chunker._split_by_headings(text)
            >>> len(sections)
            2
        """
        # Match headings: # Title, ## Subtitle, etc.
        # Split on lines starting with #
        pattern = r'^(#{1,6}\s+.+)$'

        sections = []
        current_section = []

        for line in text.split('\n'):
            if re.match(pattern, line):
                # New heading found
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        # Add last section
        if current_section:
            sections.append('\n'.join(current_section))

        # If no headings found, return whole text
        if not sections or (len(sections) == 1 and not re.match(pattern, sections[0].split('\n')[0])):
            return [text]

        logger.debug(f"Split into {len(sections)} sections by headings")
        return sections

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """
        Split text by paragraphs (double newline)

        Used when heading-based split results in chunks > max_tokens.

        Args:
            text: Input text

        Returns:
            List of paragraph chunks

        Example:
            >>> text = "Para 1\\n\\nPara 2\\n\\nPara 3"
            >>> chunks = chunker._split_by_paragraphs(text)
            >>> len(chunks)
            3
        """
        # Split by double newline
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = self._count_tokens(para)

            # If single paragraph exceeds max, split by sentences
            if para_tokens > self.max_tokens:
                # Flush current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split large paragraph by sentences
                sentence_chunks = self._split_by_sentences(para)
                chunks.extend(sentence_chunks)
                continue

            # Check if adding this paragraph would exceed max
            if current_tokens + para_tokens > self.max_tokens and current_chunk:
                # Flush current chunk
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_tokens = 0

            current_chunk.append(para)
            current_tokens += para_tokens

        # Add last chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        logger.debug(f"Split into {len(chunks)} chunks by paragraphs")
        return chunks

    def _split_by_sentences(self, text: str) -> List[str]:
        """
        Split text by sentences (last resort for very long paragraphs)

        Args:
            text: Input text

        Returns:
            List of sentence chunks
        """
        # Simple sentence splitting (end with . ! ?)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = self._count_tokens(sentence)

            # If single sentence exceeds max, just add it as-is (can't split further)
            if sentence_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                chunks.append(sentence)
                continue

            # Check if adding this sentence would exceed max
            if current_tokens + sentence_tokens > self.max_tokens and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_tokens = 0

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Add last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        logger.debug(f"Split into {len(chunks)} chunks by sentences")
        return chunks

    def chunk_conversation(
        self,
        user_message: str,
        assistant_message: str,
        memory_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Chunk a conversation (User + Assistant exchange)

        For conversations, we treat each turn as a semantic unit
        and only split if a single message exceeds max_tokens.

        Args:
            user_message: User's message
            assistant_message: Assistant's response
            memory_id: Parent memory ID
            metadata: Metadata

        Returns:
            List of Chunk objects
        """
        # Format conversation
        conversation_text = f"**User:**\n{user_message}\n\n**Assistant:**\n{assistant_message}"

        # Check if conversation fits in one chunk
        total_tokens = self._count_tokens(conversation_text)

        if total_tokens <= self.max_tokens:
            # Single chunk
            chunk_metadata = (metadata or {}).copy()
            chunk_metadata.setdefault('memory_id', memory_id)
            chunk_metadata.setdefault('chunk_index', 0)

            chunk = Chunk(
                id=f"{memory_id}-chunk-0",
                memory_id=memory_id,
                content=conversation_text,
                tokens=total_tokens,
                metadata=chunk_metadata
            )
            return [chunk]
        else:
            # Split into multiple chunks
            return self.chunk(conversation_text, memory_id, metadata)
