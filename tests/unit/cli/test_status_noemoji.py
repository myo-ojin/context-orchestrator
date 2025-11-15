#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys


def test_cli_status_noemoji_runs_without_unicode_errors(monkeypatch):
    import src.cli as cli

    # Fake config and dependencies to avoid network/files
    class _Cfg:
        class _O:
            url = "http://localhost:11434"
            embedding_model = "nomic-embed-text"
            inference_model = "qwen2.5:7b"

        class _C:
            command = "claude"

        def __init__(self):
            self.data_dir = "."
            self.ollama = self._O()
            self.cli = self._C()
            self.obsidian_vault_path = None
            class _L: session_log_dir = "."
            self.logging = _L()
            class _Cons: schedule = "0 3 * * *"
            self.consolidation = _Cons()

    monkeypatch.setattr(cli, "load_config", lambda p=None: _Cfg())

    class _Local:
        def __init__(self, **k): pass
    monkeypatch.setattr(cli, "LocalLLMClient", _Local)

    class _Vec:
        def __init__(self, **k):
            class C: 
                def count(self): return 0
            self.collection = C()
    monkeypatch.setattr(cli, "ChromaVectorDB", _Vec)

    # Simulate argv for main
    monkeypatch.setattr(sys, "argv", ["prog", "--no-emoji", "status"])

    # Run main and ensure it does not raise
    cli.main()
