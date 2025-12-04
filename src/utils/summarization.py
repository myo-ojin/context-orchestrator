#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hierarchical Summarization Utilities

Provides functions for summarizing long documents (session logs, conversations)
using hierarchical chunking and merging strategies.

Requirements: Issue #2025-11-27-01 (Long session log hierarchical summarization)
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    """Configuration for hierarchical summarization"""

    chunk_size: int = 3500  # characters per chunk
    chunk_overlap: int = 200  # overlap between chunks
    max_tokens: int = 500  # max tokens for summary output
    temperature: float = 0.0  # LLM temperature
    language: str = "auto"  # output language (auto, ja, en, es)


def hierarchical_summarize(
    content: str,
    llm_function: Callable[[str, int, float], str],
    config: Optional[SummaryConfig] = None,
    language_code: Optional[str] = None
) -> str:
    """
    Perform hierarchical summarization on long content

    Process:
    1. Split content into overlapping chunks
    2. Summarize each chunk with structured YAML schema
    3. If multiple chunks, merge chunk summaries into final summary
    4. If single chunk, return its summary directly

    Args:
        content: Full text content to summarize
        llm_function: Function that takes (prompt, max_tokens, temperature) and returns summary
        config: SummaryConfig instance (optional, uses defaults if None)
        language_code: Language code override (ja, en, es, etc.)

    Returns:
        Structured YAML summary with Decision/Rationale/Risks/NextSteps

    Example:
        >>> def my_llm(prompt, max_tokens, temp):
        ...     return model_router.route('short_summary', prompt, max_tokens=max_tokens)
        >>> summary = hierarchical_summarize(long_log, my_llm)
        >>> print(summary)
        topic: Session log analysis
        decisions:
        - text: Implement feature X
          rationale: Improves performance
          owner: alice
          due: 2025-12-01
        ...
    """
    if config is None:
        config = SummaryConfig()

    # Override language if specified
    if language_code:
        config.language = language_code

    # Detect language from content if auto
    if config.language == "auto":
        config.language = _detect_language_simple(content)

    # Check if content needs chunking
    if len(content) <= config.chunk_size:
        # Single chunk - summarize directly
        logger.debug(f"Content size {len(content)} chars, single chunk summarization")
        prompt = _build_summary_prompt(content, config.language, is_chunk=False)
        return llm_function(prompt, config.max_tokens, config.temperature)

    # Multiple chunks - hierarchical summarization
    logger.info(f"Content size {len(content)} chars, using hierarchical summarization")

    # Step 1: Split into chunks
    chunks = _split_into_chunks(content, config.chunk_size, config.chunk_overlap)
    logger.debug(f"Split into {len(chunks)} chunks")

    # Step 2: Summarize each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        logger.debug(f"Summarizing chunk {i+1}/{len(chunks)}")
        prompt = _build_summary_prompt(chunk, config.language, is_chunk=True, chunk_index=i+1)
        chunk_summary = llm_function(prompt, config.max_tokens, config.temperature)
        chunk_summaries.append(chunk_summary)

    # Step 3: Merge chunk summaries
    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    logger.debug(f"Merging {len(chunk_summaries)} chunk summaries")
    merged_content = "\n\n---\n\n".join(chunk_summaries)
    merge_prompt = _build_merge_prompt(merged_content, config.language)

    return llm_function(merge_prompt, config.max_tokens, config.temperature)


def _split_into_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into overlapping chunks

    Args:
        text: Full text
        chunk_size: Max characters per chunk
        overlap: Overlap characters between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If not the last chunk, try to break at newline
        if end < len(text):
            # Look for newline in last 10% of chunk
            search_start = end - (chunk_size // 10)
            newline_pos = text.rfind('\n', search_start, end)
            if newline_pos != -1:
                end = newline_pos + 1

        chunks.append(text[start:end])

        # Move start forward by (chunk_size - overlap)
        start = end - overlap if end < len(text) else end

    return chunks


def _build_summary_prompt(
    content: str,
    language: str,
    is_chunk: bool = False,
    chunk_index: Optional[int] = None
) -> str:
    """
    Build structured summary prompt with YAML schema

    Args:
        content: Content to summarize
        language: Target language (ja, en, es)
        is_chunk: Whether this is a chunk of larger document
        chunk_index: Index of chunk (for logging)

    Returns:
        Prompt string
    """
    chunk_note = f" (chunk {chunk_index})" if is_chunk and chunk_index else ""

    # Short prompt (~60 tokens) as specified in issue #2025-11-27-01
    prompt = f"""Summarize the dialog{chunk_note}. Output YAML with keys: topic, doc_type, project,
decisions[], risks[], next_steps[], notes[]. Each value ≤30 tokens.
decisions items: text, rationale, owner, due. risks: text, mitigation.
next_steps: text, owner, due. Omit empty keys. Use source language.

Dialog:
---
{content}
---

Summary (YAML):"""

    return prompt


def _build_merge_prompt(chunk_summaries: str, language: str) -> str:
    """
    Build prompt for merging multiple chunk summaries

    Args:
        chunk_summaries: Concatenated chunk summaries
        language: Target language

    Returns:
        Merge prompt string
    """
    prompt = f"""Merge these partial summaries into one coherent summary. Output YAML with keys:
topic, doc_type, project, decisions[], risks[], next_steps[], notes[].
Each value ≤30 tokens. decisions items: text, rationale, owner, due.
risks: text, mitigation. next_steps: text, owner, due.
Omit empty keys. Use source language.

Partial summaries:
---
{chunk_summaries}
---

Merged summary (YAML):"""

    return prompt


def _detect_language_simple(text: str) -> str:
    """
    Simple language detection (fallback if langdetect unavailable)

    Args:
        text: Text to detect language from

    Returns:
        Language code (ja, en, es, etc.)
    """
    # Japanese pattern (Hiragana, Katakana, Kanji)
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text):
        return "ja"

    # Spanish pattern (common Spanish words/characters)
    if re.search(r'[áéíóúñ¿¡]', text.lower()):
        return "es"

    # Default to English
    return "en"


def validate_yaml_summary(summary: str) -> bool:
    """
    Validate that summary follows expected YAML schema

    Args:
        summary: Summary string to validate

    Returns:
        True if valid, False otherwise
    """
    if not summary or not summary.strip():
        return False

    # Check for at least one required key (topic, doc_type, or project)
    required_pattern = r'^(topic|doc_type|project):\s*.+$'
    has_required = bool(re.search(required_pattern, summary, re.MULTILINE))

    if not has_required:
        logger.warning("Summary validation failed: missing required keys")
        return False

    return True


def extract_summary_metadata(summary: str) -> Dict[str, Any]:
    """
    Extract structured metadata from YAML summary

    Args:
        summary: YAML summary string

    Returns:
        Dictionary with extracted metadata
    """
    metadata = {
        'topic': None,
        'doc_type': None,
        'project': None,
        'decisions': [],
        'risks': [],
        'next_steps': [],
        'notes': []
    }

    # Simple regex extraction (for basic validation)
    # For production, use proper YAML parser

    # Extract simple fields
    topic_match = re.search(r'^topic:\s*(.+)$', summary, re.MULTILINE | re.IGNORECASE)
    if topic_match:
        metadata['topic'] = topic_match.group(1).strip()

    doc_type_match = re.search(r'^doc_type:\s*(.+)$', summary, re.MULTILINE | re.IGNORECASE)
    if doc_type_match:
        metadata['doc_type'] = doc_type_match.group(1).strip()

    project_match = re.search(r'^project:\s*(.+)$', summary, re.MULTILINE | re.IGNORECASE)
    if project_match:
        metadata['project'] = project_match.group(1).strip()

    # Extract list items (simplified - just count items)
    decisions_matches = re.findall(r'^\s*-\s*text:\s*(.+)$', summary, re.MULTILINE)
    metadata['decisions'] = [{'text': m.strip()} for m in decisions_matches]

    return metadata
