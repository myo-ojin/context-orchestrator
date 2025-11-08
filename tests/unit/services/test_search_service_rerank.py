#!/usr/bin/env python
# -*- coding: utf-8 -*-

from types import SimpleNamespace


class _Router:
    def generate_embedding(self, text: str):
        return [0.1, 0.2]


def test_rerank_prefers_higher_vector_when_bm25_equal():
    from src.services.search import SearchService

    class _V:
        def search(self, query_embedding, top_k=50, filter_metadata=None):
            return [
                {"id": "a", "content": "A", "metadata": {}, "similarity": 0.9},
                {"id": "b", "content": "B", "metadata": {}, "similarity": 0.5},
            ]

    class _B:
        def search(self, query, top_k=50):
            # equal/zero so vector decides
            return []

    svc = SearchService(vector_db=_V(), bm25_index=_B(), model_router=_Router())
    out = svc.search("q", top_k=2)

    assert out[0]["id"] == "a"
    assert out[0]["components"]["vector"] >= out[1]["components"]["vector"]


def test_rerank_components_present_and_score_matches_weights():
    from src.services.search import SearchService

    class _V:
        def search(self, *a, **k):
            return [
                {
                    "id": "x",
                    "content": "X",
                    "metadata": {"strength": 1.0},
                    "similarity": 0.4,
                }
            ]

    class _B:
        def search(self, *a, **k):
            return [{"id": "x", "score": 1.0, "content": "X"}]

    svc = SearchService(vector_db=_V(), bm25_index=_B(), model_router=_Router())
    out = svc.search("q", top_k=1)
    r = out[0]
    c = r["components"]

    # expected combined score = 0.3*strength + 0.2*recency + 0.1*refs + 0.2*norm_bm25 + 0.2*vector
    # recency and refs depend on metadata (empty => defaults). We can just ensure components exist and score matches sum of components*weights.
    expected = (
        c["memory_strength"] * 0.3
        + c["recency"] * 0.2
        + c["refs_reliability"] * 0.1
        + c["bm25"] * 0.2
        + c["vector"] * 0.2
    )
    assert abs(r["score"] - expected) < 1e-6

