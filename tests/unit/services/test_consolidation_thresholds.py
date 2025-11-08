#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta


class _VecDB:
    def __init__(self, entries):
        self._entries = entries
        self.updated = []

    def list_by_metadata(self, filter_dict, include_embeddings=False):
        # Return predefined embedding entries
        if include_embeddings:
            return self._entries
        return []

    def update_metadata(self, id, metadata):
        self.updated.append((id, metadata))

    def get(self, id):
        # return simple metadata for representative selection
        return {"content": "X" * 10, "metadata": {"created_at": datetime.now().isoformat(), "importance": 0.5}}


class _Indexer:
    def delete_by_memory_id(self, memory_id):
        pass


class _Router:
    pass


def test_cluster_threshold_and_min_cluster_size():
    from src.services.consolidation import ConsolidationService

    # Two memories with cosine similarity just above threshold
    emb_a = [1.0, 0.0]
    emb_b = [0.95, 0.0]  # cosine ~0.95 (above 0.9)

    entries = [
        {"metadata": {"memory_id": "ma", "created_at": datetime.now().isoformat(), "importance": 0.5}, "embedding": emb_a},
        {"metadata": {"memory_id": "mb", "created_at": datetime.now().isoformat(), "importance": 0.5}, "embedding": emb_b},
    ]

    vec = _VecDB(entries)
    svc = ConsolidationService(
        vector_db=vec,
        indexer=_Indexer(),
        model_router=_Router(),
        similarity_threshold=0.9,
        min_cluster_size=2,
    )

    stats = svc.consolidate()
    # With a cluster of size 2, one should be representative, the other compressed
    # update_metadata should be called at least once for representative/others
    assert any('is_representative' in m[1] for m in vec.updated)


def test_cluster_below_threshold_no_processing():
    from src.services.consolidation import ConsolidationService

    # Similarity below threshold -> no cluster of size >=2
    emb_a = [1.0, 0.0]
    emb_b = [0.0, 1.0]  # cosine 0

    entries = [
        {"metadata": {"memory_id": "ma", "created_at": datetime.now().isoformat(), "importance": 0.5}, "embedding": emb_a},
        {"metadata": {"memory_id": "mb", "created_at": datetime.now().isoformat(), "importance": 0.5}, "embedding": emb_b},
    ]

    vec = _VecDB(entries)
    svc = ConsolidationService(
        vector_db=vec,
        indexer=_Indexer(),
        model_router=_Router(),
        similarity_threshold=0.9,
        min_cluster_size=2,
    )

    stats = svc.consolidate()
    # No representative/compress marks expected
    assert all('is_representative' not in m[1] for m in vec.updated)

