#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logging utilities for ERPCT.
This module provides consistent logging functionality across the application.
"""

import os
import sys
import logging
import datetime
from typing import Dict, Optional


# Configure logging levels
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Default log directory
DEFAULT_LOG_DIR = os.path.join(os.path.expanduser("~"), ".erpct", "logs")

# Global logger configuration
_log_level = logging.INFO
_log_format = DEFAULT_LOG_FORMAT
_log_file = None
_loggers = {}  # Cache for created loggers


def configure_logging(level: str = "info", log_file: Optional[str] = None, 
                      log_format: Optional[str] = None, console: bool = True) -> None:
    """Configure global logging settings.
    
    Args:
        level: Log level (debug, info, warning, error, critical)
        log_file: Path to log file (None for no file logging)
        log_format: Log message format string
        console: Whether to log to console
    """
    global _log_level, _log_format, _log_file
    
    # Set log level
    if level.lower() in LOG_LEVELS:
        _log_level = LOG_LEVELS[level.lower()]
    else:
        raise ValueError(f"Invalid log level: {level}")
    
    # Set log format
    _log_format = log_format or DEFAULT_LOG_FORMAT
    
    # Set log file
    _log_file = log_file
    
    # Create log directory if needed
    if _log_file:
        log_dir = os.path.dirname(os.path.abspath(_log_file))
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creating log directory {log_dir}: {str(e)}", file=sys.stderr)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(_log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(_log_format))
        root_logger.addHandler(console_handler)
    
    # Add file handler if log file is specified
    if _log_file:
        try:
            file_handler = logging.FileHandler(_log_file)
            file_handler.setFormatter(logging.Formatter(_log_format))
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Error setting up log file {_log_file}: {str(e)}", file=sys.stderr)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Configured logger instance
    """
    global _loggers
    
    # Check cache first
    if name in _loggers:
        return _loggers[name]
    
    # Create new logger
    logger = logging.getLogger(name)
    logger.setLevel(_log_level)
    
    # Cache and return
    _loggers[name] = logger
    return logger


def setup_default_logging() -> None:
    """Set up default logging configuration."""
    # Create default log directory if needed
    if not os.path.exists(DEFAULT_LOG_DIR):
        try:
            os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
        except Exception:
            # If we can't create the directory, we'll log to console only
            configure_logging(level="info", log_file=None)
            return
    
    # Default log file with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_log_file = os.path.join(DEFAULT_LOG_DIR, f"erpct_{timestamp}.log")
    
    # Configure logging
    configure_logging(level="info", log_file=default_log_file)


# Initialize logging with default settings
setup_default_logging()
