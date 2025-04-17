#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Memory management utilities for ERPCT.
This module provides utilities for managing memory usage and monitoring.
"""

import gc
import os
import sys
import time
import threading
import tracemalloc
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, cast

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type variable for decorator functions
F = TypeVar('F', bound=Callable[..., Any])

# Global memory monitoring state
_memory_monitoring = False
_monitoring_thread = None
_monitoring_interval = 60  # seconds
_memory_threshold = 0.85  # 85% of available memory
_peak_memory = 0
_stop_monitoring = threading.Event()


def get_memory_usage() -> Dict[str, float]:
    """Get current memory usage information.
    
    Returns:
        Dictionary with memory usage metrics in MB
    """
    if sys.platform == 'win32':
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        usage = {
            'rss': memory_info.rss / (1024 * 1024),  # Resident Set Size in MB
            'vms': memory_info.vms / (1024 * 1024),  # Virtual Memory Size in MB
        }
    else:
        # Linux/Unix systems - use resource module
        import resource
        usage = {
            'rss': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,  # in MB (Linux returns KB)
        }
        
        # Try to get additional info from /proc/self/status on Linux
        try:
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('VmSize:'):
                        usage['vms'] = float(line.split()[1]) / 1024  # in MB
                        break
        except:
            usage['vms'] = 0
    
    return usage


def get_system_memory() -> Dict[str, float]:
    """Get system memory information.
    
    Returns:
        Dictionary with system memory metrics in MB
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            'total': mem.total / (1024 * 1024),  # Total memory in MB
            'available': mem.available / (1024 * 1024),  # Available memory in MB
            'used': mem.used / (1024 * 1024),  # Used memory in MB
            'percent': mem.percent  # Percentage used
        }
    except ImportError:
        logger.warning("psutil module not available for system memory monitoring")
        return {'total': 0, 'available': 0, 'used': 0, 'percent': 0}


def enable_memory_tracking() -> None:
    """Enable detailed memory allocation tracking."""
    tracemalloc.start()
    logger.info("Memory tracking enabled")


def disable_memory_tracking() -> None:
    """Disable memory tracking and release resources."""
    if tracemalloc.is_tracing():
        tracemalloc.stop()
        logger.info("Memory tracking disabled")


def get_memory_snapshot() -> List[Tuple[str, int]]:
    """Get a snapshot of memory allocations by source.
    
    Returns:
        List of (source, size) tuples for top memory consumers
    """
    if not tracemalloc.is_tracing():
        enable_memory_tracking()
        time.sleep(0.1)  # Small delay to collect some data
        
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    result = []
    for stat in top_stats[:20]:  # Get top 20 memory consumers
        trace = str(stat.traceback)
        size = stat.size / (1024 * 1024)  # Convert to MB
        result.append((trace, size))
    
    return result


def memory_intensive(func: F) -> F:
    """Decorator for memory-intensive functions.
    
    This decorator will:
    1. Force garbage collection before and after the function
    2. Log memory usage before and after
    3. Optionally take a memory snapshot if tracking is enabled
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Force garbage collection
        gc.collect()
        
        # Get memory usage before
        before = get_memory_usage()
        logger.debug(f"Memory before {func.__name__}: {before['rss']:.2f} MB")
        
        try:
            # Call the function
            result = func(*args, **kwargs)
            return result
        finally:
            # Force garbage collection again
            gc.collect()
            
            # Get memory usage after
            after = get_memory_usage()
            logger.debug(f"Memory after {func.__name__}: {after['rss']:.2f} MB " +
                        f"(delta: {after['rss'] - before['rss']:.2f} MB)")
            
            # Take memory snapshot if tracking is enabled
            if tracemalloc.is_tracing():
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics('lineno')
                logger.debug(f"Top 3 memory allocations after {func.__name__}:")
                for i, stat in enumerate(top_stats[:3]):
                    logger.debug(f"#{i+1}: {stat}")
    
    return cast(F, wrapper)


def start_memory_monitoring(interval: int = 60, threshold: float = 0.85) -> None:
    """Start a background thread to monitor memory usage.
    
    Args:
        interval: Monitoring interval in seconds
        threshold: Memory threshold (0.0-1.0) to trigger warnings
    """
    global _memory_monitoring, _monitoring_thread, _monitoring_interval, _memory_threshold, _stop_monitoring
    
    if _memory_monitoring:
        logger.warning("Memory monitoring already active")
        return
    
    _monitoring_interval = interval
    _memory_threshold = threshold
    _stop_monitoring.clear()
    
    def monitor_thread():
        while not _stop_monitoring.is_set():
            try:
                mem_usage = get_memory_usage()
                sys_memory = get_system_memory()
                
                global _peak_memory
                if mem_usage['rss'] > _peak_memory:
                    _peak_memory = mem_usage['rss']
                
                # Check if memory usage exceeds threshold
                if sys_memory['percent'] / 100 > _memory_threshold:
                    logger.warning(
                        f"Memory usage critical: {sys_memory['percent']:.1f}% " +
                        f"(process: {mem_usage['rss']:.1f} MB, peak: {_peak_memory:.1f} MB)"
                    )
                    # Force garbage collection
                    gc.collect()
            except Exception as e:
                logger.error(f"Error in memory monitoring: {str(e)}")
            
            # Wait for the next interval or until stopped
            _stop_monitoring.wait(_monitoring_interval)
    
    _monitoring_thread = threading.Thread(target=monitor_thread, daemon=True)
    _monitoring_thread.start()
    _memory_monitoring = True
    
    logger.info(f"Memory monitoring started (interval: {interval}s, threshold: {threshold*100:.1f}%)")


def stop_memory_monitoring() -> None:
    """Stop the memory monitoring thread."""
    global _memory_monitoring, _stop_monitoring
    
    if not _memory_monitoring:
        return
    
    _stop_monitoring.set()
    if _monitoring_thread and _monitoring_thread.is_alive():
        _monitoring_thread.join(timeout=2)
    
    _memory_monitoring = False
    logger.info("Memory monitoring stopped")


def clear_memory_caches() -> None:
    """Clear memory caches and force garbage collection."""
    # Force garbage collection
    gc.collect()
    
    # Get memory usage before
    before = get_memory_usage()
    
    # Run garbage collection with more aggressive settings
    gc.collect(2)
    
    # Clear Python's internal caches
    sys._clear_type_cache()
    
    # Get memory usage after
    after = get_memory_usage()
    logger.debug(f"Memory cleared: {before['rss'] - after['rss']:.2f} MB freed")
