#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace

import pytest


class _Resp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_embeddings_retry_with_prompt(monkeypatch):
    from src.models.local_llm import LocalLLMClient

    calls = []

    def fake_get(url, timeout):
        # /api/tags check
        return _Resp(200, {"models": []})

    def fake_post(url, json=None, timeout=0):
        calls.append(json)
        # First call with 'input' returns empty embedding
        if "input" in json:
            return _Resp(200, {"embedding": []})
        # Retry with 'prompt' returns a vector
        if "prompt" in json:
            return _Resp(200, {"embedding": [0.1, 0.2, 0.3]})
        return _Resp(400, {})

    import src.models.local_llm as mod

    monkeypatch.setattr(mod.requests, "get", fake_get)
    monkeypatch.setattr(mod.requests, "post", fake_post)

    client = LocalLLMClient(ollama_url="http://localhost:11434")
    vec = client.generate_embedding("hello")

    assert vec == [0.1, 0.2, 0.3]
    # ensure we tried input first then prompt
    assert calls[0].get("input") == "hello"
    assert calls[1].get("prompt") == "hello"

