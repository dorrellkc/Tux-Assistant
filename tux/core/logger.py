"""
Tux Assistant - Logging Module

Centralized logging configuration for consistent output formatting.
Logs to stderr by default, with optional file logging.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import logging
import sys
import os
from typing import Optional


# Custom formatter for cleaner output
class TuxFormatter(logging.Formatter):
    """Custom formatter with component prefixes."""

    FORMATS = {
        logging.DEBUG: "[%(name)s] %(message)s",
        logging.INFO: "[%(name)s] %(message)s",
        logging.WARNING: "[%(name)s] Warning: %(message)s",
        logging.ERROR: "[%(name)s] Error: %(message)s",
        logging.CRITICAL: "[%(name)s] CRITICAL: %(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self._fmt)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# Root logger for the application
_root_logger: Optional[logging.Logger] = None


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    verbose: bool = False
) -> logging.Logger:
    """
    Set up the root Tux Assistant logger.

    Args:
        level: Base logging level (default: INFO)
        log_file: Optional path to write logs to file
        verbose: If True, sets level to DEBUG

    Returns:
        The configured root logger
    """
    global _root_logger

    if verbose:
        level = logging.DEBUG

    # Create root logger for tux namespace
    _root_logger = logging.getLogger('tux')
    _root_logger.setLevel(level)

    # Clear any existing handlers
    _root_logger.handlers.clear()

    # Console handler (stderr)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(TuxFormatter())
    _root_logger.addHandler(console)

    # Optional file handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            _root_logger.addHandler(file_handler)
        except Exception:
            pass  # File logging is optional

    return _root_logger


def get_logger(name: str = 'tux') -> logging.Logger:
    """
    Get a logger for a specific component.

    Args:
        name: Component name (e.g., 'tux.browser', 'tux.tts')

    Returns:
        Logger instance for the component

    Usage:
        from tux.core import get_logger
        log = get_logger('tux.browser')
        log.info("Browser initialized")
        log.warning("Cache miss")
        log.error("Failed to load page")
    """
    # Ensure name is under tux namespace
    if not name.startswith('tux'):
        name = f'tux.{name}'

    return logging.getLogger(name)


# Convenience function for quick debug checks
def is_debug_enabled() -> bool:
    """Check if debug logging is enabled."""
    logger = get_logger()
    return logger.isEnabledFor(logging.DEBUG)
