#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom Errors

Defines custom exception classes for error handling.

Requirements: Requirement 13 (Configuration Management)
"""


class ContextOrchestratorError(Exception):
    """Base exception for Context Orchestrator"""
    pass


class OllamaConnectionError(ContextOrchestratorError):
    """
    Ollama is not running or not accessible

    Example:
        >>> raise OllamaConnectionError()
        OllamaConnectionError: Ollama is not running. Please start Ollama: 'ollama serve'
    """
    def __init__(self):
        super().__init__(
            "Ollama is not running. Please start Ollama: 'ollama serve'"
        )


class ModelNotFoundError(ContextOrchestratorError):
    """
    Required model is not installed

    Example:
        >>> raise ModelNotFoundError('nomic-embed-text')
        ModelNotFoundError: Model 'nomic-embed-text' is not installed.
        Please install: 'ollama pull nomic-embed-text'
    """
    def __init__(self, model_name: str):
        super().__init__(
            f"Model '{model_name}' is not installed. "
            f"Please install: 'ollama pull {model_name}'"
        )


class CLICallError(ContextOrchestratorError):
    """
    CLI call failed

    Example:
        >>> raise CLICallError('claude', 'Command not found')
        CLICallError: CLI call to 'claude' failed: Command not found
    """
    def __init__(self, cli_command: str, error_message: str):
        super().__init__(
            f"CLI call to '{cli_command}' failed: {error_message}"
        )


class DatabaseError(ContextOrchestratorError):
    """
    Database operation failed

    Example:
        >>> raise DatabaseError('Failed to connect to Chroma DB')
        DatabaseError: Failed to connect to Chroma DB
    """
    pass


class ConfigurationError(ContextOrchestratorError):
    """
    Configuration error

    Example:
        >>> raise ConfigurationError('Invalid config file')
        ConfigurationError: Invalid config file
    """
    pass


class SessionNotFoundError(ContextOrchestratorError):
    """
    Session not found

    Example:
        >>> raise SessionNotFoundError('session-123')
        SessionNotFoundError: Session not found: session-123
    """
    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}")


class MemoryNotFoundError(ContextOrchestratorError):
    """
    Memory not found

    Example:
        >>> raise MemoryNotFoundError('mem-123')
        MemoryNotFoundError: Memory not found: mem-123
    """
    def __init__(self, memory_id: str):
        super().__init__(f"Memory not found: {memory_id}")


class IngestionError(ContextOrchestratorError):
    """
    Ingestion failed

    Example:
        >>> raise IngestionError('Failed to process conversation')
        IngestionError: Failed to process conversation
    """
    pass


class SearchError(ContextOrchestratorError):
    """
    Search failed

    Example:
        >>> raise SearchError('Vector search failed')
        SearchError: Vector search failed
    """
    pass


class ConsolidationError(ContextOrchestratorError):
    """
    Consolidation failed

    Example:
        >>> raise ConsolidationError('Failed to cluster memories')
        ConsolidationError: Failed to cluster memories
    """
    pass


class ValidationError(ContextOrchestratorError):
    """
    Validation error (invalid input data)

    Example:
        >>> raise ValidationError('conversation', 'Missing required field: assistant')
        ValidationError: Invalid conversation: Missing required field: assistant
    """
    def __init__(self, data_type: str, message: str):
        super().__init__(f"Invalid {data_type}: {message}")


class ObsidianError(ContextOrchestratorError):
    """
    Obsidian integration error

    Example:
        >>> raise ObsidianError('Failed to parse markdown file')
        ObsidianError: Failed to parse markdown file
    """
    pass


class ChunkingError(ContextOrchestratorError):
    """
    Chunking failed

    Example:
        >>> raise ChunkingError('Content exceeds maximum token limit')
        ChunkingError: Content exceeds maximum token limit
    """
    pass


class EmbeddingError(ContextOrchestratorError):
    """
    Embedding generation failed

    Example:
        >>> raise EmbeddingError('Failed to generate embedding for text')
        EmbeddingError: Failed to generate embedding for text
    """
    pass
