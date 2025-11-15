#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Keyword extraction utilities for cache key generation

Extracts important keywords from queries to enable partial matching
in the cache, improving cache hit rates for semantically similar queries.

Phase 2: Keyword-based cache implementation
"""

from typing import List, Set
import re
import logging

logger = logging.getLogger(__name__)

# Stop words to filter out (common words with low semantic value)
STOP_WORDS: Set[str] = {
    # English stop words
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
    'could', 'may', 'might', 'can', 'must', 'this', 'that', 'these', 'those',
    'it', 'its', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
    # Japanese particles and common words
    'の', 'は', 'が', 'を', 'に', 'へ', 'と', 'で', 'や', 'か', 'も',
    'から', 'まで', 'より', 'など', 'として', 'について', 'による',
    'こと', 'もの', 'ため', 'よう', 'これ', 'それ', 'あれ', 'どれ',
}


def extract_keywords(
    query: str,
    top_n: int = 3,
    min_length: int = 3
) -> List[str]:
    """
    Extract top N important keywords from a query string.

    Algorithm:
    1. Normalize: lowercase, remove special characters
    2. Tokenize: split by whitespace and hyphens
    3. Filter: remove stop words and short words
    4. Score: longer words are more important
    5. Return: top N keywords

    Args:
        query: Search query string
        top_n: Number of keywords to extract (default: 3)
        min_length: Minimum word length to consider (default: 3)

    Returns:
        List of important keywords, sorted by importance (length)

    Examples:
        >>> extract_keywords("change feed ingestion errors")
        ['ingestion', 'change', 'errors']

        >>> extract_keywords("dashboard pilot deployment")
        ['deployment', 'dashboard', 'pilot']

        >>> extract_keywords("governance guardrails policy")
        ['governance', 'guardrails', 'policy']
    """
    if not query or not isinstance(query, str):
        return []

    # Normalize: lowercase and strip
    normalized = query.lower().strip()

    # Remove common punctuation except hyphens (keep compound words)
    normalized = re.sub(r'[^\w\s\-]', ' ', normalized)

    # Tokenize: split by whitespace and hyphens
    words = re.split(r'[\s\-_]+', normalized)

    # Filter: remove stop words, empty strings, and short words
    important = [
        w for w in words
        if w and w not in STOP_WORDS and len(w) >= min_length
    ]

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for word in important:
        if word not in seen:
            seen.add(word)
            unique.append(word)

    # Sort by length (longer words are typically more specific/important)
    # Then alphabetically for stability
    sorted_words = sorted(unique, key=lambda w: (-len(w), w))

    # Return top N
    result = sorted_words[:top_n]

    logger.debug(f"Extracted keywords from '{query[:50]}...': {result}")
    return result


def build_keyword_signature(keywords: List[str]) -> str:
    """
    Build a normalized signature from keywords for cache key generation.

    The signature is deterministic (sorted) to ensure that queries with
    the same keywords in different orders produce the same cache key.

    Args:
        keywords: List of keywords

    Returns:
        Normalized signature string (e.g., "change+errors+ingestion")
        Empty string if keywords is empty

    Examples:
        >>> build_keyword_signature(['ingestion', 'change', 'errors'])
        'change+errors+ingestion'

        >>> build_keyword_signature(['dashboard', 'pilot'])
        'dashboard+pilot'

        >>> build_keyword_signature([])
        ''
    """
    if not keywords:
        return ''

    # Sort for deterministic ordering
    sorted_keywords = sorted(keywords)

    # Join with + separator
    signature = '+'.join(sorted_keywords)

    return signature


def extract_and_build_signature(
    query: str,
    top_n: int = 3,
    min_length: int = 3
) -> str:
    """
    Convenience function: extract keywords and build signature in one call.

    Args:
        query: Search query string
        top_n: Number of keywords to extract
        min_length: Minimum word length

    Returns:
        Keyword signature string, empty if no keywords found

    Examples:
        >>> extract_and_build_signature("change feed ingestion errors")
        'change+errors+ingestion'
    """
    keywords = extract_keywords(query, top_n=top_n, min_length=min_length)
    return build_keyword_signature(keywords)
