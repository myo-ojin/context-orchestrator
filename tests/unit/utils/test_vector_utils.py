#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for vector utility functions
"""

import pytest
import math
from src.utils.vector_utils import (
    cosine_similarity,
    normalize_vector,
    dot_product,
    vector_magnitude
)


class TestCosineSimilarity:
    """Test cosine similarity calculation"""

    def test_identical_vectors(self):
        """Test that identical vectors have similarity 1.0"""
        v1 = [1.0, 2.0, 3.0]
        v2 = [1.0, 2.0, 3.0]
        assert cosine_similarity(v1, v2) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Test that orthogonal vectors have similarity 0.0"""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        assert cosine_similarity(v1, v2) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """Test that opposite vectors have similarity -1.0"""
        v1 = [1.0, 2.0, 3.0]
        v2 = [-1.0, -2.0, -3.0]
        assert cosine_similarity(v1, v2) == pytest.approx(-1.0)

    def test_similar_vectors(self):
        """Test vectors with known similarity"""
        # 45 degree angle -> cos(45°) ≈ 0.707
        v1 = [1.0, 0.0]
        v2 = [1.0, 1.0]
        expected = 1.0 / math.sqrt(2)  # ≈ 0.707
        assert cosine_similarity(v1, v2) == pytest.approx(expected, rel=1e-5)

    def test_high_dimensional_vectors(self):
        """Test with 384-dimensional vectors (nomic-embed-text size)"""
        # Create two similar high-dimensional vectors
        v1 = [0.1] * 384
        v2 = [0.1] * 383 + [0.2]  # Slightly different
        similarity = cosine_similarity(v1, v2)
        # Should be very high but not exactly 1.0
        assert 0.99 < similarity < 1.0

    def test_zero_vector_handling(self):
        """Test that zero vectors return 0.0 similarity"""
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 2.0, 3.0]
        assert cosine_similarity(v1, v2) == 0.0

    def test_different_dimensions_error(self):
        """Test error when vectors have different dimensions"""
        v1 = [1.0, 2.0]
        v2 = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError, match="same dimension"):
            cosine_similarity(v1, v2)

    def test_empty_vector_error(self):
        """Test error when vector is empty"""
        with pytest.raises(ValueError, match="cannot be empty"):
            cosine_similarity([], [1.0])

    def test_realistic_query_similarity(self):
        """Test with realistic embedding-like vectors"""
        # Simulate two semantically similar queries
        # (values chosen to represent typical embedding patterns)
        v1 = [0.8, 0.1, -0.3, 0.5]
        v2 = [0.75, 0.15, -0.25, 0.48]
        similarity = cosine_similarity(v1, v2)
        # Should be high similarity (> 0.9)
        assert similarity > 0.9


class TestNormalizeVector:
    """Test vector normalization"""

    def test_simple_normalization(self):
        """Test normalization of simple vector"""
        v = [3.0, 4.0]  # magnitude = 5
        normalized = normalize_vector(v)
        assert normalized == pytest.approx([0.6, 0.8])

    def test_normalized_magnitude(self):
        """Test that normalized vector has magnitude 1.0"""
        v = [1.0, 2.0, 3.0, 4.0]
        normalized = normalize_vector(v)
        magnitude = math.sqrt(sum(x * x for x in normalized))
        assert magnitude == pytest.approx(1.0)

    def test_unit_vector_unchanged(self):
        """Test that unit vector remains unchanged"""
        v = [1.0, 0.0, 0.0]
        normalized = normalize_vector(v)
        assert normalized == pytest.approx([1.0, 0.0, 0.0])

    def test_zero_vector_error(self):
        """Test error when normalizing zero vector"""
        with pytest.raises(ValueError, match="zero vector"):
            normalize_vector([0.0, 0.0, 0.0])

    def test_empty_vector_error(self):
        """Test error when vector is empty"""
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_vector([])

    def test_negative_values(self):
        """Test normalization with negative values"""
        v = [-3.0, 4.0]
        normalized = normalize_vector(v)
        assert normalized == pytest.approx([-0.6, 0.8])
        # Check magnitude
        magnitude = math.sqrt(sum(x * x for x in normalized))
        assert magnitude == pytest.approx(1.0)


class TestDotProduct:
    """Test dot product calculation"""

    def test_simple_dot_product(self):
        """Test basic dot product"""
        v1 = [1.0, 2.0, 3.0]
        v2 = [4.0, 5.0, 6.0]
        # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
        assert dot_product(v1, v2) == pytest.approx(32.0)

    def test_orthogonal_vectors_zero(self):
        """Test that orthogonal vectors have zero dot product"""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        assert dot_product(v1, v2) == pytest.approx(0.0)

    def test_normalized_vectors_equals_cosine(self):
        """Test that dot product of normalized vectors equals cosine similarity"""
        v1 = [3.0, 4.0]
        v2 = [1.0, 0.0]

        # Method 1: Cosine similarity
        cos_sim = cosine_similarity(v1, v2)

        # Method 2: Normalize then dot product
        n1 = normalize_vector(v1)
        n2 = normalize_vector(v2)
        dot = dot_product(n1, n2)

        assert cos_sim == pytest.approx(dot)

    def test_different_dimensions_error(self):
        """Test error when vectors have different dimensions"""
        v1 = [1.0, 2.0]
        v2 = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError, match="same dimension"):
            dot_product(v1, v2)

    def test_empty_vector_error(self):
        """Test error when vector is empty"""
        with pytest.raises(ValueError, match="cannot be empty"):
            dot_product([], [1.0])


class TestVectorMagnitude:
    """Test vector magnitude calculation"""

    def test_simple_magnitude(self):
        """Test magnitude of simple vector"""
        v = [3.0, 4.0]
        # sqrt(9 + 16) = sqrt(25) = 5
        assert vector_magnitude(v) == pytest.approx(5.0)

    def test_unit_vector_magnitude(self):
        """Test magnitude of unit vector"""
        v = [1.0, 0.0, 0.0]
        assert vector_magnitude(v) == pytest.approx(1.0)

    def test_zero_vector_magnitude(self):
        """Test magnitude of zero vector is 0"""
        v = [0.0, 0.0, 0.0]
        assert vector_magnitude(v) == pytest.approx(0.0)

    def test_negative_values(self):
        """Test magnitude with negative values"""
        v = [-3.0, -4.0]
        # Magnitude is always positive
        assert vector_magnitude(v) == pytest.approx(5.0)

    def test_empty_vector_error(self):
        """Test error when vector is empty"""
        with pytest.raises(ValueError, match="cannot be empty"):
            vector_magnitude([])


class TestPerformance:
    """Test performance characteristics"""

    def test_high_dimensional_performance(self):
        """Test that calculations are fast for high-dimensional vectors"""
        import time

        # Create two 384-dimensional vectors (nomic-embed-text size)
        v1 = [0.1] * 384
        v2 = [0.2] * 384

        # Measure time for 1000 similarity calculations
        start = time.perf_counter()
        for _ in range(1000):
            cosine_similarity(v1, v2)
        duration = time.perf_counter() - start

        # Should complete in less than 100ms for 1000 calculations
        # (average < 0.1ms per calculation)
        assert duration < 0.1, f"Too slow: {duration:.3f}s for 1000 calculations"

    def test_normalization_optimization(self):
        """Test that normalized vectors allow faster similarity calculation"""
        import time

        v1 = [0.1] * 384
        v2 = [0.2] * 384

        # Method 1: Standard cosine similarity
        start1 = time.perf_counter()
        for _ in range(1000):
            cosine_similarity(v1, v2)
        time1 = time.perf_counter() - start1

        # Method 2: Pre-normalize and use dot product
        n1 = normalize_vector(v1)
        n2 = normalize_vector(v2)
        start2 = time.perf_counter()
        for _ in range(1000):
            dot_product(n1, n2)
        time2 = time.perf_counter() - start2

        # Dot product should be significantly faster (no magnitude calculation)
        # Note: This is informational, not a strict assertion
        print(f"\nCosine similarity: {time1*1000:.2f}ms for 1000 ops")
        print(f"Normalized dot product: {time2*1000:.2f}ms for 1000 ops")
        print(f"Speedup: {time1/time2:.1f}x")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_small_values(self):
        """Test with very small values (near machine epsilon)"""
        v1 = [1e-10, 1e-10, 1e-10]
        v2 = [2e-10, 2e-10, 2e-10]
        # Should still work correctly
        similarity = cosine_similarity(v1, v2)
        assert similarity == pytest.approx(1.0)

    def test_mixed_magnitudes(self):
        """Test vectors with very different magnitudes"""
        v1 = [1e-5, 1e-5]
        v2 = [1e5, 1e5]
        # Direction is same, magnitude doesn't matter for cosine
        similarity = cosine_similarity(v1, v2)
        assert similarity == pytest.approx(1.0)

    def test_single_dimension(self):
        """Test with single-dimensional vectors"""
        v1 = [5.0]
        v2 = [3.0]
        # Both positive -> similarity = 1.0
        assert cosine_similarity(v1, v2) == pytest.approx(1.0)

        v3 = [-3.0]
        # Opposite directions -> similarity = -1.0
        assert cosine_similarity(v1, v3) == pytest.approx(-1.0)
