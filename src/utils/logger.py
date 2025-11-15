#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging Utilities

Provides centralized logging configuration for the system with structured logging support.

Requirements: Requirement 13 (Configuration Management, Phase 14.3)
"""

import logging
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


def setup_logger(
    name: str = 'context_orchestrator',
    level: str = 'INFO',
    log_file: Optional[str] = None,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Setup logger with consistent formatting

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        log_to_console: Whether to log to console

    Returns:
        Configured logger

    Example:
        >>> logger = setup_logger('my_module', 'DEBUG')
        >>> logger.info('Starting...')
        2025-01-15 10:00:00 - my_module - INFO - Starting...
    """
    logger = logging.getLogger(name)

    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def setup_root_logger(level: str = 'INFO', log_file: Optional[str] = None) -> None:
    """
    Setup root logger for the entire application

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path

    Example:
        >>> setup_root_logger('INFO', '~/.context-orchestrator/app.log')
    """
    setup_logger('', level, log_file, log_to_console=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger by name

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info('Hello')
    """
    return logging.getLogger(name)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging

    Formats log records as JSON with consistent fields:
    - timestamp
    - level
    - logger
    - message
    - context (additional data)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add custom fields from record
        if hasattr(record, 'context'):
            log_data['context'] = record.context

        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation

        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        return json.dumps(log_data, ensure_ascii=False)


def setup_structured_logger(
    name: str = 'context_orchestrator',
    level: str = 'INFO',
    log_file: Optional[str] = None,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Setup logger with structured (JSON) formatting

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        log_to_console: Whether to log to console

    Returns:
        Configured logger with JSON output

    Example:
        >>> logger = setup_structured_logger('my_module', 'DEBUG')
        >>> logger.info('Starting...', extra={'context': {'user': 'john'}})
        {"timestamp": "2025-01-15T10:00:00", "level": "INFO", "logger": "my_module", "message": "Starting...", "context": {"user": "john"}}
    """
    logger = logging.getLogger(name)

    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create structured formatter
    formatter = StructuredFormatter()

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter with additional context

    Automatically adds context fields to all log messages
    """

    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        super().__init__(logger, context)
        self.context = context

    def process(self, msg, kwargs):
        """Add context to log record"""
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        # Merge adapter context with call-time extra
        kwargs['extra']['context'] = {**self.context, **kwargs['extra'].get('context', {})}

        return msg, kwargs


def get_logger_with_context(name: str, context: Dict[str, Any]) -> LoggerAdapter:
    """
    Get logger with automatic context injection

    Args:
        name: Logger name
        context: Context to include in all log messages

    Returns:
        LoggerAdapter with context

    Example:
        >>> logger = get_logger_with_context(__name__, {'service': 'ingestion', 'version': '1.0'})
        >>> logger.info('Processing item', extra={'context': {'item_id': '123'}})
        # Logs: {"service": "ingestion", "version": "1.0", "item_id": "123"}
    """
    base_logger = logging.getLogger(name)
    return LoggerAdapter(base_logger, context)


def log_operation(logger: logging.Logger, operation: str, level: int = logging.INFO):
    """
    Context manager for logging operations with timing

    Args:
        logger: Logger instance
        operation: Operation name
        level: Log level

    Example:
        >>> logger = get_logger(__name__)
        >>> with log_operation(logger, 'search'):
        ...     results = search_memory(query)
        # Logs: Operation 'search' started
        # Logs: Operation 'search' completed in 123.45ms
    """
    import time
    from contextlib import contextmanager

    @contextmanager
    def _log_operation():
        start_time = time.perf_counter()
        logger.log(level, f"Operation '{operation}' started", extra={'operation': operation})

        try:
            yield
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.log(
                logging.ERROR,
                f"Operation '{operation}' failed after {duration_ms:.2f}ms: {e}",
                extra={'operation': operation, 'duration_ms': duration_ms},
                exc_info=True
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.log(
                level,
                f"Operation '{operation}' completed in {duration_ms:.2f}ms",
                extra={'operation': operation, 'duration_ms': duration_ms}
            )

    return _log_operation()
