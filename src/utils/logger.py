#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging Utilities

Provides centralized logging configuration for the system.

Requirements: Requirement 13 (Configuration Management)
"""

import logging
import sys
from pathlib import Path
from typing import Optional


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
