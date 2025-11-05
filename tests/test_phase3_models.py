#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic tests for Phase 3: Local LLM Client Layer

Tests LocalLLMClient, CLILLMClient, and ModelRouter
"""

import pytest
from src.models import (
    LocalLLMClient,
    CLILLMClient,
    ModelRouter,
    OllamaConnectionError,
    ModelNotFoundError,
    CLICallError
)


class TestLocalLLMClient:
    """Tests for LocalLLMClient"""

    def test_init(self):
        """Test initialization"""
        # This will fail if Ollama is not running
        try:
            client = LocalLLMClient()
            assert client.ollama_url == "http://localhost:11434"
        except OllamaConnectionError:
            pytest.skip("Ollama is not running")

    def test_check_connection_failure(self):
        """Test connection check with invalid URL"""
        with pytest.raises(OllamaConnectionError):
            LocalLLMClient(ollama_url="http://invalid-url:9999")

    @pytest.mark.skipif(True, reason="Requires running Ollama with models")
    def test_generate_embedding(self):
        """Test embedding generation"""
        client = LocalLLMClient()
        embedding = client.generate_embedding("Hello world")
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.skipif(True, reason="Requires running Ollama with models")
    def test_generate(self):
        """Test text generation"""
        client = LocalLLMClient()
        result = client.generate("Say hello", max_tokens=10)
        assert isinstance(result, str)
        assert len(result) > 0


class TestCLILLMClient:
    """Tests for CLILLMClient"""

    def test_init(self):
        """Test initialization"""
        client = CLILLMClient(cli_command="claude")
        assert client.cli_command == "claude"

    def test_init_with_codex(self):
        """Test initialization with codex"""
        client = CLILLMClient(cli_command="codex")
        assert client.cli_command == "codex"

    @pytest.mark.skipif(True, reason="Requires claude CLI installed")
    def test_generate(self):
        """Test text generation via CLI"""
        client = CLILLMClient()
        result = client.generate("Say hello")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skipif(True, reason="Requires claude CLI installed")
    def test_generate_with_fallback(self):
        """Test generate with fallback"""
        client = CLILLMClient()
        result = client.generate_with_fallback(
            "Say hello",
            fallback_text="Fallback response"
        )
        assert isinstance(result, str)


class TestModelRouter:
    """Tests for ModelRouter"""

    def test_init(self):
        """Test initialization"""
        try:
            local_client = LocalLLMClient()
            cli_client = CLILLMClient()
            router = ModelRouter(local_client, cli_client)

            assert router.local_llm_client == local_client
            assert router.cli_llm_client == cli_client
            assert router.embedding_model == "nomic-embed-text"
            assert router.inference_model == "qwen2.5:7b"
        except OllamaConnectionError:
            pytest.skip("Ollama is not running")

    def test_is_lightweight_task(self):
        """Test lightweight task detection"""
        try:
            local_client = LocalLLMClient()
            cli_client = CLILLMClient()
            router = ModelRouter(local_client, cli_client)

            # Local tasks
            assert router.is_lightweight_task('embedding') is True
            assert router.is_lightweight_task('classification') is True
            assert router.is_lightweight_task('short_summary') is True

            # Cloud tasks
            assert router.is_lightweight_task('long_summary') is False
            assert router.is_lightweight_task('reasoning') is False
            assert router.is_lightweight_task('consolidation') is False
        except OllamaConnectionError:
            pytest.skip("Ollama is not running")

    def test_invalid_task_type(self):
        """Test invalid task type"""
        try:
            local_client = LocalLLMClient()
            cli_client = CLILLMClient()
            router = ModelRouter(local_client, cli_client)

            with pytest.raises(ValueError, match="Invalid task_type"):
                router.route(task_type='invalid_task', prompt="test")
        except OllamaConnectionError:
            pytest.skip("Ollama is not running")

    @pytest.mark.skipif(True, reason="Requires running Ollama with models")
    def test_route_embedding(self):
        """Test routing embedding task"""
        local_client = LocalLLMClient()
        cli_client = CLILLMClient()
        router = ModelRouter(local_client, cli_client)

        embedding = router.route(task_type='embedding', text="Hello world")
        assert isinstance(embedding, list)
        assert len(embedding) > 0

    @pytest.mark.skipif(True, reason="Requires running Ollama with models")
    def test_generate_embedding_convenience(self):
        """Test convenience method for embedding"""
        local_client = LocalLLMClient()
        cli_client = CLILLMClient()
        router = ModelRouter(local_client, cli_client)

        embedding = router.generate_embedding("Hello world")
        assert isinstance(embedding, list)
        assert len(embedding) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
