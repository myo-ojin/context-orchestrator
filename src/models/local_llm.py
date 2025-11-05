#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Local LLM Client via Ollama

Provides embedding generation and text completion using local models.
Uses Ollama API for zero-cost, privacy-preserving inference.

Requirements: Requirement 10 (MVP - Model Routing)
"""

from typing import List, Optional
import requests
import logging
import json

logger = logging.getLogger(__name__)


class OllamaConnectionError(Exception):
    """Raised when Ollama is unreachable"""
    pass


class ModelNotFoundError(Exception):
    """Raised when requested model is not available"""
    pass


class LocalLLMClient:
    """
    Client for local LLM via Ollama

    Ollama provides a local API server for running LLMs.
    All processing stays local, preserving privacy.

    Attributes:
        ollama_url: Ollama API URL (default: http://localhost:11434)
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        inference_model: str = "qwen2.5:7b"
    ):
        """
        Initialize Ollama client

        Args:
            ollama_url: Ollama API URL (default: http://localhost:11434)
            embedding_model: Model name for embeddings (default: nomic-embed-text)
            inference_model: Model name for inference (default: qwen2.5:7b)
        """
        self.ollama_url = ollama_url.rstrip('/')
        self.embedding_model = embedding_model
        self.inference_model = inference_model

        # Verify Ollama is running
        self._check_connection()

        logger.info(f"Initialized LocalLLMClient with Ollama at {self.ollama_url}")
        logger.info(f"  Embedding model: {self.embedding_model}")
        logger.info(f"  Inference model: {self.inference_model}")

    def _check_connection(self) -> None:
        """
        Check if Ollama is accessible

        Raises:
            OllamaConnectionError: If Ollama is not reachable
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            logger.debug("Ollama connection verified")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.ollama_url}. "
                "Please ensure Ollama is running (try: ollama serve)"
            ) from e

    def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding vector for text

        Args:
            text: Input text
            model: Embedding model name (default: self.embedding_model)

        Returns:
            Embedding vector (list of floats)

        Raises:
            OllamaConnectionError: If Ollama is unreachable
            ModelNotFoundError: If model is not available

        Example:
            >>> client = LocalLLMClient()
            >>> embedding = client.generate_embedding("Hello world")
            >>> len(embedding)
            768  # nomic-embed-text dimension
        """
        # Use instance's embedding model if not specified
        if model is None:
            model = self.embedding_model

        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": model,
                    "input": text
                },
                timeout=30
            )

            if response.status_code == 404:
                logger.error(f"Model {model} not found")
                raise ModelNotFoundError(
                    f"Model '{model}' not found. "
                    f"Please install it: ollama pull {model}"
                )

            response.raise_for_status()
            result = response.json()

            embedding = result.get('embedding', [])
            if not embedding:
                raise ValueError("Empty embedding returned")

            logger.debug(f"Generated embedding (dim={len(embedding)}) for text: {text[:50]}...")
            return embedding

        except requests.exceptions.RequestException as e:
            logger.error(f"Embedding generation failed: {e}")
            raise OllamaConnectionError(f"Failed to generate embedding: {e}") from e

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """
        Generate text completion

        Args:
            prompt: Input prompt
            model: Model name (default: self.inference_model)
            max_tokens: Maximum tokens to generate (None = no limit)
            temperature: Sampling temperature (0.0-1.0)
            stream: Stream response (not implemented yet)

        Returns:
            Generated text

        Raises:
            OllamaConnectionError: If Ollama is unreachable
            ModelNotFoundError: If model is not available

        Example:
            >>> client = LocalLLMClient()
            >>> result = client.generate("Classify this as Incident or Snippet: Bug in login")
            >>> print(result)
            "Incident"
        """
        # Use instance's inference model if not specified
        if model is None:
            model = self.inference_model

        try:
            # Build request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,  # Always use non-streaming for simplicity
                "options": {
                    "temperature": temperature
                }
            }

            if max_tokens is not None:
                payload["options"]["num_predict"] = max_tokens

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60  # Longer timeout for generation
            )

            if response.status_code == 404:
                logger.error(f"Model {model} not found")
                raise ModelNotFoundError(
                    f"Model '{model}' not found. "
                    f"Please install it: ollama pull {model}"
                )

            response.raise_for_status()
            result = response.json()

            generated_text = result.get('response', '').strip()

            logger.debug(f"Generated {len(generated_text)} chars with {model}")
            logger.debug(f"Prompt: {prompt[:100]}...")
            logger.debug(f"Response: {generated_text[:100]}...")

            return generated_text

        except requests.exceptions.RequestException as e:
            logger.error(f"Text generation failed: {e}")
            raise OllamaConnectionError(f"Failed to generate text: {e}") from e

    def list_models(self) -> List[str]:
        """
        List available models

        Returns:
            List of model names

        Example:
            >>> client = LocalLLMClient()
            >>> models = client.list_models()
            >>> print(models)
            ['nomic-embed-text', 'qwen2.5:7b']
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()

            data = response.json()
            models = [model['name'] for model in data.get('models', [])]

            logger.debug(f"Available models: {models}")
            return models

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def check_model_available(self, model: str) -> bool:
        """
        Check if a model is available

        Args:
            model: Model name

        Returns:
            True if model is available, False otherwise

        Example:
            >>> client = LocalLLMClient()
            >>> client.check_model_available("nomic-embed-text")
            True
        """
        models = self.list_models()
        return model in models
