#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vector utility functions for semantic similarity calculations

Provides efficient vector operations for semantic cache matching.
Phase 3: Semantic similarity-based cache implementation
"""

from typing import List
import math


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Cosine similarity = dot(v1, v2) / (||v1|| * ||v2||)
    Returns value in range [-1, 1], where:
    - 1.0 = identical direction
    - 0.0 = orthogonal
    - -1.0 = opposite direction

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score

    Raises:
        ValueError: If vectors have different dimensions or are empty

    Examples:
        >>> v1 = [1.0, 0.0, 0.0]
        >>> v2 = [1.0, 0.0, 0.0]
        >>> cosine_similarity(v1, v2)
        1.0

        >>> v1 = [1.0, 0.0]
        >>> v2 = [0.0, 1.0]
        >>> cosine_similarity(v1, v2)
        0.0
    """
    if not vec1 or not vec2:
        raise ValueError("Vectors cannot be empty")

    if len(vec1) != len(vec2):
        raise ValueError(
            f"Vectors must have same dimension (got {len(vec1)} and {len(vec2)})"
        )

    # Calculate dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    # Handle zero vectors
    if magnitude1 == 0.0 or magnitude2 == 0.0:
        return 0.0

    # Calculate cosine similarity
    similarity = dot_product / (magnitude1 * magnitude2)

    # Clamp to [-1, 1] to handle floating point errors
    return max(-1.0, min(1.0, similarity))


def normalize_vector(vec: List[float]) -> List[float]:
    """
    Normalize a vector to unit length.

    Normalized vector has magnitude 1.0, which allows faster
    similarity calculations (dot product = cosine similarity).

    Args:
        vec: Input vector

    Returns:
        Normalized vector (magnitude = 1.0)

    Raises:
        ValueError: If vector is empty or zero vector

    Examples:
        >>> v = [3.0, 4.0]
        >>> normalized = normalize_vector(v)
        >>> sum(x * x for x in normalized)  # Should be ~1.0
        1.0
    """
    if not vec:
        raise ValueError("Vector cannot be empty")

    magnitude = math.sqrt(sum(x * x for x in vec))

    if magnitude == 0.0:
        raise ValueError("Cannot normalize zero vector")

    return [x / magnitude for x in vec]


def dot_product(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate dot product of two vectors.

    For normalized vectors, dot product equals cosine similarity.
    This can be used as an optimization when vectors are pre-normalized.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Dot product

    Raises:
        ValueError: If vectors have different dimensions or are empty

    Examples:
        >>> v1 = [1.0, 2.0, 3.0]
        >>> v2 = [4.0, 5.0, 6.0]
        >>> dot_product(v1, v2)
        32.0
    """
    if not vec1 or not vec2:
        raise ValueError("Vectors cannot be empty")

    if len(vec1) != len(vec2):
        raise ValueError(
            f"Vectors must have same dimension (got {len(vec1)} and {len(vec2)})"
        )

    return sum(a * b for a, b in zip(vec1, vec2))


def vector_magnitude(vec: List[float]) -> float:
    """
    Calculate magnitude (L2 norm) of a vector.

    Magnitude = sqrt(sum(x^2 for x in vec))

    Args:
        vec: Input vector

    Returns:
        Magnitude

    Raises:
        ValueError: If vector is empty

    Examples:
        >>> v = [3.0, 4.0]
        >>> vector_magnitude(v)
        5.0
    """
    if not vec:
        raise ValueError("Vector cannot be empty")

    return math.sqrt(sum(x * x for x in vec))
