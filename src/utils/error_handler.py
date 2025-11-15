#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Error Handler Utility

Provides centralized error handling with consistent messaging and structured logging.

Requirements: Requirement 13 (Phase 14.3)
"""

import logging
import traceback
import sys
from typing import Optional, Dict, Any, Callable
from functools import wraps

from .errors import (
    ContextOrchestratorError,
    OllamaConnectionError,
    ModelNotFoundError,
    DatabaseError,
    ConfigurationError,
    IngestionError,
    SearchError,
    ConsolidationError,
    ValidationError
)

logger = logging.getLogger(__name__)


class ErrorContext:
    """
    Context for error handling with structured information

    Attributes:
        operation: Name of the operation that failed
        context: Additional context information
        user_message: User-friendly error message
        technical_details: Technical details for logging
        suggestions: List of suggestions to fix the error
    """

    def __init__(
        self,
        operation: str,
        context: Dict[str, Any] = None,
        user_message: str = None,
        technical_details: str = None,
        suggestions: list = None
    ):
        self.operation = operation
        self.context = context or {}
        self.user_message = user_message
        self.technical_details = technical_details
        self.suggestions = suggestions or []


class ErrorHandler:
    """Centralized error handler with structured logging"""

    @staticmethod
    def format_user_message(error: Exception, context: ErrorContext = None) -> str:
        """
        Format user-friendly error message

        Args:
            error: The exception that occurred
            context: Error context information

        Returns:
            Formatted user-friendly message
        """
        if context and context.user_message:
            return context.user_message

        # Use exception message if available
        if str(error):
            return str(error)

        # Fallback to exception type
        return f"An error occurred: {error.__class__.__name__}"

    @staticmethod
    def format_technical_details(error: Exception, context: ErrorContext = None) -> str:
        """
        Format technical error details for logging

        Args:
            error: The exception that occurred
            context: Error context information

        Returns:
            Formatted technical details
        """
        details = []

        if context:
            details.append(f"Operation: {context.operation}")

            if context.context:
                details.append(f"Context: {context.context}")

            if context.technical_details:
                details.append(f"Details: {context.technical_details}")

        details.append(f"Exception: {error.__class__.__name__}")
        details.append(f"Message: {str(error)}")

        return " | ".join(details)

    @staticmethod
    def log_error(
        error: Exception,
        context: ErrorContext = None,
        include_traceback: bool = True,
        level: int = logging.ERROR
    ):
        """
        Log error with structured information

        Args:
            error: The exception to log
            context: Error context information
            include_traceback: Whether to include full traceback
            level: Logging level (default: ERROR)
        """
        # Format technical details
        technical_msg = ErrorHandler.format_technical_details(error, context)

        # Log the error
        logger.log(level, technical_msg)

        # Log traceback if requested
        if include_traceback:
            logger.log(level, traceback.format_exc())

        # Log suggestions if available
        if context and context.suggestions:
            logger.log(level, f"Suggestions: {', '.join(context.suggestions)}")

    @staticmethod
    def handle_error(
        error: Exception,
        context: ErrorContext = None,
        reraise: bool = True,
        include_traceback: bool = True
    ) -> Optional[str]:
        """
        Handle error with logging and optional re-raising

        Args:
            error: The exception to handle
            context: Error context information
            reraise: Whether to re-raise the exception
            include_traceback: Whether to include traceback in logs

        Returns:
            User-friendly error message (if not reraising)

        Raises:
            Exception: The original exception if reraise=True
        """
        # Log the error
        ErrorHandler.log_error(error, context, include_traceback)

        # Re-raise if requested
        if reraise:
            raise

        # Return user-friendly message
        return ErrorHandler.format_user_message(error, context)


def with_error_handling(
    operation: str,
    user_message: str = None,
    reraise: bool = True,
    include_traceback: bool = True
):
    """
    Decorator for automatic error handling

    Args:
        operation: Name of the operation
        user_message: Custom user-friendly message
        reraise: Whether to re-raise exceptions
        include_traceback: Whether to include traceback in logs

    Example:
        @with_error_handling("search", "Failed to search memories")
        def search_memory(query: str):
            # Search implementation
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    operation=operation,
                    context={'function': func.__name__, 'args': str(args), 'kwargs': str(kwargs)},
                    user_message=user_message
                )

                return ErrorHandler.handle_error(
                    e,
                    context,
                    reraise=reraise,
                    include_traceback=include_traceback
                )

        return wrapper
    return decorator


def create_error_context(
    operation: str,
    **kwargs
) -> ErrorContext:
    """
    Helper function to create ErrorContext

    Args:
        operation: Name of the operation
        **kwargs: Additional context, user_message, technical_details, suggestions

    Returns:
        ErrorContext instance
    """
    return ErrorContext(
        operation=operation,
        context=kwargs.get('context'),
        user_message=kwargs.get('user_message'),
        technical_details=kwargs.get('technical_details'),
        suggestions=kwargs.get('suggestions')
    )


def get_error_suggestions(error: Exception) -> list:
    """
    Get contextual suggestions based on error type

    Args:
        error: The exception

    Returns:
        List of suggestions
    """
    suggestions = []

    if isinstance(error, OllamaConnectionError):
        suggestions = [
            "Check if Ollama is running: 'ollama serve'",
            "Verify Ollama URL in config.yaml",
            "Check firewall settings"
        ]
    elif isinstance(error, ModelNotFoundError):
        suggestions = [
            "Install required model with 'ollama pull <model-name>'",
            "Run setup wizard: 'python scripts/setup.py'"
        ]
    elif isinstance(error, DatabaseError):
        suggestions = [
            "Check data directory permissions",
            "Verify Chroma DB is not corrupted",
            "Run 'python -m src.cli doctor' for diagnostics"
        ]
    elif isinstance(error, ConfigurationError):
        suggestions = [
            "Verify config.yaml syntax",
            "Check file paths are absolute and exist",
            "Run setup wizard to regenerate config"
        ]
    elif isinstance(error, ValidationError):
        suggestions = [
            "Check input data format",
            "Ensure all required fields are provided",
            "Verify data types match schema"
        ]

    return suggestions
