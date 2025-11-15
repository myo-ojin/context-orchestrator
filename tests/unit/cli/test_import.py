#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace


def test_cli_import_generates_embeddings_and_writes_indexes(tmp_path, monkeypatch):
    # Arrange
    from src.cli import cmd_import

    # Prepare input file (no embeddings to force generation)
    data = {
        "memories": [
            {"id": "mem-1", "content": "Alpha content", "metadata": {"tag": "a"}},
            {"id": "mem-2", "content": "Beta content", "metadata": {"tag": "b"}},
        ]
    }
    inp = tmp_path / "import.json"
    inp.write_text(json.dumps(data), encoding="utf-8")

    # Fake config
    class _Cfg:
        class _O:
            url = "http://localhost:11434"
            embedding_model = "nomic-embed-text"
            inference_model = "qwen2.5:7b"

        class _C:
            command = "claude"

        def __init__(self):
            self.data_dir = str(tmp_path)
            self.ollama = self._O()
            self.cli = self._C()

    # Capture calls
    added = []
    bm25 = {"docs": []}

    # Stubs
    class _Vector:
        def __init__(self, *a, **k):
            pass

        def get(self, memory_id):  # nothing exists
            return None

        def add(self, id, embedding, metadata, document):
            added.append({"id": id, "embedding": embedding, "metadata": metadata, "document": document})

    class _BM25:
        def __init__(self, persist_path):
            self.persist_path = persist_path

        def add_document(self, doc_id, text):
            bm25["docs"].append((doc_id, text))

        def _save(self):
            pass

    class _Router:
        def __init__(self, *a, **k):
            pass

        def generate_embedding(self, text):
            # simple deterministic
            return [float(len(text))]

    # Monkeypatch modules used by cmd_import
    import src.cli as cli_mod

    monkeypatch.setattr(cli_mod, "load_config", lambda p=None: _Cfg())
    monkeypatch.setattr(cli_mod, "ChromaVectorDB", _Vector)
    monkeypatch.setattr("src.storage.bm25_index.BM25Index", _BM25, raising=False)
    monkeypatch.setattr(cli_mod, "ModelRouter", _Router)
    monkeypatch.setattr(cli_mod, "LocalLLMClient", lambda **k: None)
    monkeypatch.setattr(cli_mod, "CLILLMClient", lambda **k: None)

    # Act
    args = SimpleNamespace(input=str(inp), force=False, config=None)
    cmd_import(args)

    # Assert: 2 memories added with generated embeddings and bm25 entries
    assert len(added) == 2
    assert all(isinstance(a["embedding"][0], float) for a in added)
    assert len(bm25["docs"]) == 2



