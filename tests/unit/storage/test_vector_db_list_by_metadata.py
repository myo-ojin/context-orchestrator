#!/usr/bin/env python
# -*- coding: utf-8 -*-

import types


def test_list_by_metadata_multiple_keys_filters_client_side(tmp_path, monkeypatch):
    # Patch chroma symbols so we can instantiate without real dependency
    import src.storage.vector_db as mod

    class _Settings:
        def __init__(self, **k):
            pass

    class _Client:
        def __init__(self, path, settings):
            self._col = types.SimpleNamespace()

        def get_or_create_collection(self, name, metadata):
            class _Dummy:
                def count(self):
                    return 0
            # Will be replaced on instance later for get(); count() is used in __init__ log
            return _Dummy()

    monkeypatch.setattr(mod, "Settings", _Settings, raising=False)
    monkeypatch.setattr(mod, "chromadb", types.SimpleNamespace(PersistentClient=_Client), raising=False)

    from src.storage.vector_db import ChromaVectorDB

    db = ChromaVectorDB(persist_directory=str(tmp_path / "chroma"))

    # Replace collection with a stub that returns mixed metadata
    class _Col:
        def get(self, where=None, include=None, limit=None):
            return {
                "ids": ["a", "b", "c"],
                "metadatas": [
                    {"k": 1, "m": "x"},
                    {"k": 2, "m": "x"},
                    {"k": 1, "m": "y"},
                ],
                "documents": ["A", "B", "C"],
            }

    db.collection = _Col()

    res = db.list_by_metadata({"k": 1, "m": "x"}, include_documents=True)

    # Only one item matches both conditions
    assert len(res) == 1
    assert res[0]["id"] == "a"
    assert res[0]["content"] == "A"
