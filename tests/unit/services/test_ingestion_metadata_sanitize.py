#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime


def test_store_memory_metadata_sanitizes_complex_values(monkeypatch):
    from src.services.ingestion import IngestionService
    from src.processing.classifier import SchemaClassifier
    from src.processing.chunker import Chunker
    from src.processing.indexer import Indexer
    from src.models import Memory, SchemaType, MemoryType

    # Mocks
    class _Vector:
        def __init__(self):
            self.add_calls = []

        def add(self, id, embedding, metadata, document):
            self.add_calls.append({"id": id, "embedding": embedding, "metadata": metadata, "document": document})

    class _Router:
        def generate_embedding(self, text):
            return [0.1, 0.2]

    vector = _Vector()
    router = _Router()
    classifier = SchemaClassifier(model_router=router)
    chunker = Chunker(max_tokens=50)
    indexer = Indexer(vector_db=vector, bm25_index=None, model_router=router)

    s = IngestionService(
        vector_db=vector,
        classifier=classifier,
        chunker=chunker,
        indexer=indexer,
        model_router=router,
    )

    mem = Memory(
        id="mem-xyz",
        schema_type=SchemaType.INCIDENT,
        content="",
        summary="sum",
        refs=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={"ok": 1, "bad_list": [1, 2], "none": None},
        memory_type=MemoryType.WORKING,
    )

    # call private method to isolate behavior
    s._store_memory_metadata(mem)

    md = vector.add_calls[-1]["metadata"]
    assert "ok" in md and md["ok"] == 1
    assert "bad_list" not in md
    assert "none" not in md

