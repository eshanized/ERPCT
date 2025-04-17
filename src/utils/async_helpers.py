#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Asynchronous operation helpers for ERPCT.
This module provides utility functions for working with asynchronous operations.
"""

import asyncio
import functools
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar, Union, cast

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type variables for generic functions
T = TypeVar('T')
R = TypeVar('R')

# Global thread pool executor
_thread_pool = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Get or create the global thread pool executor.
    
    Returns:
        ThreadPoolExecutor instance
    """
    global _thread_pool
    if _thread_pool is None:
        # Use max_workers based on CPU count with a reasonable maximum
        import multiprocessing
        max_workers = min(32, multiprocessing.cpu_count() * 2 + 4)
        _thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    return _thread_pool


async def run_in_thread(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking function in a thread pool.
    
    Args:
        func: The function to run
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        get_thread_pool(),
        functools.partial(func, *args, **kwargs)
    )


def sync_to_async(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """Decorator to convert a synchronous function to an asynchronous one.
    
    Args:
        func: The synchronous function to convert
        
    Returns:
        An asynchronous version of the function
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await run_in_thread(func, *args, **kwargs)
    return wrapper


def async_to_sync(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """Decorator to convert an asynchronous function to a synchronous one.
    
    Args:
        func: The asynchronous function to convert
        
    Returns:
        A synchronous version of the function
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper


async def gather_with_concurrency(limit: int, *tasks: Coroutine) -> List[Any]:
    """Run coroutines with a concurrency limit.
    
    Args:
        limit: Maximum number of coroutines to run concurrently
        *tasks: Coroutines to run
        
    Returns:
        List of results from the coroutines
    """
    semaphore = asyncio.Semaphore(limit)
    
    async def semaphore_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*(semaphore_task(task) for task in tasks))


class AsyncRateLimiter:
    """Rate limiter for asynchronous operations."""
    
    def __init__(self, calls_per_second: float):
        """Initialize the rate limiter.
        
        Args:
            calls_per_second: Maximum number of calls allowed per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to proceed, waiting if necessary."""
        async with self._lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time
            
            if time_since_last_call < self.min_interval:
                wait_time = self.min_interval - time_since_last_call
                await asyncio.sleep(wait_time)
            
            self.last_call_time = time.time()
