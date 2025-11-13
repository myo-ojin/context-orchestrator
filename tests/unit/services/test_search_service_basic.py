#!/usr/bin/env python
# -*- coding: utf-8 -*-

from types import SimpleNamespace


class _Router:
    def __init__(self):
        self.calls = 0

    def generate_embedding(self, text: str):
        self.calls += 1
        # simple vector stub
        return [0.5, 0.1, 0.9]

    def route(self, task_type: str, **kwargs):
        return "{}"


class _VectorDB:
    def __init__(self):
        self.last_filters = None

    def search(self, query_embedding, top_k=50, filter_metadata=None):
        self.last_filters = filter_metadata
        # two results; include similarity so SearchService copies to vector_similarity
        return [
            {
                "id": "doc-1",
                "content": "Alpha content about TypeError",
                "metadata": {"k": 1},
                "similarity": 0.8,
            },
            {
                "id": "doc-2",
                "content": "Beta other topic",
                "metadata": {"k": 2},
                "similarity": 0.6,
            },
        ]


class _BM25:
    def search(self, query, top_k=50):
        # one result overlapping id to exercise merge
        return [
            {"id": "doc-2", "score": 2.0, "content": "Beta other topic"},
            {"id": "doc-3", "score": 1.0, "content": "Gamma matching"},
        ]


def _make_service():
    from src.services.search import SearchService

    vec = _VectorDB()
    bm25 = _BM25()
    router = _Router()
    svc = SearchService(
        vector_db=vec,
        bm25_index=bm25,
        model_router=router,
        candidate_count=50,
        result_count=10,
    )
    return svc, vec, bm25


def test_search_top_k_limit_and_single_embedding_call():
    svc, vec, _ = _make_service()
    results = svc.search("TypeError", top_k=2)

    # top_k respected
    assert len(results) <= 2

    # router called exactly once for query embedding
    assert isinstance(svc.model_router.calls, int)
    assert svc.model_router.calls == 1


def test_search_passes_filters_to_vector_db():
    svc, vec, _ = _make_service()
    filters = {"k": 1}
    _ = svc.search("TypeError", top_k=3, filters=filters)
    assert vec.last_filters == filters
