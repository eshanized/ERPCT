#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT utility modules.
This package contains utility functions and classes used across the application.
"""

# Import and re-export common utility functions for easier access
from src.utils.logging import configure_logging, get_logger
from src.utils.file_handler import load_json_file, save_json_file, ensure_directory
from src.utils.async_helpers import sync_to_async, async_to_sync, run_in_thread
from src.utils.memory_manager import get_memory_usage, memory_intensive
from src.utils.performance import timed, measure_time, benchmark
from src.utils.networking import is_valid_ip, is_port_open, get_local_ip
from src.utils.threading import synchronized, ThreadPool, SafeCounter

# Export the most commonly used functions
__all__ = [
    # Logging
    'configure_logging', 'get_logger',
    
    # File handling
    'load_json_file', 'save_json_file', 'ensure_directory',
    
    # Async helpers
    'sync_to_async', 'async_to_sync', 'run_in_thread',
    
    # Memory management
    'get_memory_usage', 'memory_intensive',
    
    # Performance
    'timed', 'measure_time', 'benchmark',
    
    # Networking
    'is_valid_ip', 'is_port_open', 'get_local_ip',
    
    # Threading
    'synchronized', 'ThreadPool', 'SafeCounter',
]
