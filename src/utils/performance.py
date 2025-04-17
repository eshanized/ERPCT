#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Performance utilities for ERPCT.
This module provides tools for measuring and optimizing application performance.
"""

import time
import functools
import statistics
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, cast
from contextlib import contextmanager

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type variable for decorator functions
F = TypeVar('F', bound=Callable[..., Any])

# Global performance tracking
_performance_stats = {}


@contextmanager
def measure_time(name: str, log_level: str = "debug"):
    """Context manager for measuring execution time of a code block.
    
    Args:
        name: Name of the operation being measured
        log_level: Log level to use (debug, info, warning, error)
    
    Yields:
        None
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        
        # Update performance stats
        if name not in _performance_stats:
            _performance_stats[name] = []
        _performance_stats[name].append(elapsed)
        
        # Truncate the list if it gets too long
        if len(_performance_stats[name]) > 1000:
            _performance_stats[name] = _performance_stats[name][-1000:]
        
        # Log based on specified level
        if log_level == "debug":
            logger.debug(f"{name} completed in {elapsed:.4f} seconds")
        elif log_level == "info":
            logger.info(f"{name} completed in {elapsed:.4f} seconds")
        elif log_level == "warning":
            logger.warning(f"{name} completed in {elapsed:.4f} seconds")
        elif log_level == "error":
            logger.error(f"{name} completed in {elapsed:.4f} seconds")


def timed(func: F = None, *, name: Optional[str] = None, log_level: str = "debug") -> F:
    """Decorator for measuring execution time of a function.
    
    Args:
        func: The function to decorate
        name: Optional custom name for the timing (defaults to function name)
        log_level: Log level to use (debug, info, warning, error)
    
    Returns:
        Decorated function
    """
    def decorator(f: F) -> F:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            operation_name = name or f.__name__
            with measure_time(operation_name, log_level):
                return f(*args, **kwargs)
        return cast(F, wrapper)
    
    if func is None:
        return decorator
    return decorator(func)


def get_performance_stats() -> Dict[str, Dict[str, float]]:
    """Get statistics about measured performance.
    
    Returns:
        Dictionary mapping operation names to performance statistics
    """
    result = {}
    
    for name, times in _performance_stats.items():
        if not times:
            continue
            
        stats = {
            'count': len(times),
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times),
            'median': statistics.median(times) if len(times) > 0 else 0,
            'recent': times[-1],
        }
        
        # Calculate percentiles if we have enough data
        if len(times) >= 10:
            stats['p90'] = statistics.quantiles(times, n=10)[-1]  # 90th percentile
            stats['p95'] = statistics.quantiles(times, n=20)[-1]  # 95th percentile
        
        result[name] = stats
    
    return result


def clear_performance_stats() -> None:
    """Clear all collected performance statistics."""
    global _performance_stats
    _performance_stats = {}
    logger.debug("Performance statistics cleared")


def profile_function(func: F, *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    """Profile a function call and return the result and execution time.
    
    Args:
        func: Function to profile
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        Tuple of (function_result, execution_time)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    execution_time = time.time() - start_time
    return result, execution_time


def benchmark(func: Callable[[], Any], iterations: int = 10) -> Dict[str, float]:
    """Benchmark a function by executing it multiple times.
    
    Args:
        func: Function to benchmark (should take no arguments)
        iterations: Number of iterations to run
    
    Returns:
        Dictionary with benchmark statistics
    """
    if iterations < 1:
        raise ValueError("Iterations must be at least 1")
    
    times = []
    for _ in range(iterations):
        start_time = time.time()
        func()
        elapsed = time.time() - start_time
        times.append(elapsed)
    
    return {
        'min': min(times),
        'max': max(times),
        'avg': sum(times) / len(times),
        'median': statistics.median(times),
        'total': sum(times),
        'iterations': iterations
    }


class PerformanceMonitor:
    """Context manager for extended performance monitoring."""
    
    def __init__(self, name: str, track_memory: bool = False):
        """Initialize the performance monitor.
        
        Args:
            name: Name of the operation being monitored
            track_memory: Whether to track memory usage as well
        """
        self.name = name
        self.track_memory = track_memory
        self.start_time = 0
        self.start_memory = None
    
    def __enter__(self):
        """Start monitoring."""
        self.start_time = time.time()
        
        if self.track_memory:
            try:
                from src.utils.memory_manager import get_memory_usage
                self.start_memory = get_memory_usage()
            except ImportError:
                logger.warning("Cannot track memory - memory_manager module not available")
                self.track_memory = False
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop monitoring and log results."""
        elapsed = time.time() - self.start_time
        
        log_message = f"{self.name} completed in {elapsed:.4f} seconds"
        
        if self.track_memory and self.start_memory:
            try:
                from src.utils.memory_manager import get_memory_usage
                end_memory = get_memory_usage()
                memory_delta = end_memory['rss'] - self.start_memory['rss']
                log_message += f" (memory delta: {memory_delta:.2f} MB)"
            except:
                pass
        
        if exc_type:
            # Error occurred
            log_message += f" with error: {exc_type.__name__}"
            logger.error(log_message)
        else:
            # Success
            logger.info(log_message)
        
        # Update performance stats
        if self.name not in _performance_stats:
            _performance_stats[self.name] = []
        _performance_stats[self.name].append(elapsed)
