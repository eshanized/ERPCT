#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Threading utilities for ERPCT.
This module provides utilities for thread management and synchronization.
"""

import threading
import queue
import time
import signal
import inspect
import functools
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, cast, Generic

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type variables for generic functions and classes
T = TypeVar('T')
R = TypeVar('R')


class ThreadPool:
    """Thread pool for parallel execution of tasks."""
    
    def __init__(self, num_workers: int = 10, name_prefix: str = "worker"):
        """Initialize a thread pool.
        
        Args:
            num_workers: Number of worker threads to create
            name_prefix: Prefix for worker thread names
        """
        self.task_queue = queue.Queue()
        self.workers: List[threading.Thread] = []
        self.running = True
        self.results: Dict[int, Any] = {}
        self.task_counter = 0
        self.result_lock = threading.Lock()
        self.name_prefix = name_prefix
        
        # Start worker threads
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._worker_thread,
                name=f"{name_prefix}-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
    
    def _worker_thread(self) -> None:
        """Worker thread function that processes tasks from the queue."""
        while self.running:
            try:
                # Get task with timeout to allow for clean shutdown
                task_id, func, args, kwargs = self.task_queue.get(timeout=0.5)
                
                try:
                    # Execute the task
                    result = func(*args, **kwargs)
                    
                    # Store the result
                    with self.result_lock:
                        self.results[task_id] = (True, result)
                except Exception as e:
                    logger.error(f"Error in worker thread {threading.current_thread().name}: {str(e)}")
                    # Store the exception
                    with self.result_lock:
                        self.results[task_id] = (False, e)
                finally:
                    # Mark task as done
                    self.task_queue.task_done()
            except queue.Empty:
                # Timeout on queue.get, just continue the loop
                continue
            except Exception as e:
                logger.error(f"Unexpected error in worker thread: {str(e)}")
    
    def submit(self, func: Callable[..., R], *args: Any, **kwargs: Any) -> int:
        """Submit a task to the thread pool.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Task ID that can be used to retrieve the result
            
        Raises:
            RuntimeError: If the thread pool is shutting down
        """
        if not self.running:
            raise RuntimeError("Thread pool is shutting down")
        
        with self.result_lock:
            task_id = self.task_counter
            self.task_counter += 1
        
        self.task_queue.put((task_id, func, args, kwargs))
        return task_id
    
    def get_result(self, task_id: int, timeout: Optional[float] = None) -> Tuple[bool, Any]:
        """Get the result of a task.
        
        Args:
            task_id: Task ID returned by submit()
            timeout: Maximum time to wait for the result in seconds
            
        Returns:
            Tuple of (success, value), where success is a boolean indicating
            whether the task completed successfully, and value is the result
            or the exception if an error occurred
            
        Raises:
            TimeoutError: If the result is not available within the timeout
            KeyError: If the task ID is not valid
        """
        end_time = time.time() + timeout if timeout else None
        
        while end_time is None or time.time() < end_time:
            with self.result_lock:
                if task_id in self.results:
                    result = self.results[task_id]
                    # Optionally clean up the stored result to save memory
                    del self.results[task_id]
                    return result
            
            # Sleep a bit before checking again
            time.sleep(0.01)
        
        raise TimeoutError(f"Timeout waiting for result of task {task_id}")
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool.
        
        Args:
            wait: If True, wait for all tasks to complete
        """
        if wait:
            self.task_queue.join()
        
        self.running = False
        
        # Wait for all workers to terminate
        if wait:
            for worker in self.workers:
                if worker.is_alive():
                    worker.join(timeout=1.0)
        
        logger.debug(f"Thread pool {self.name_prefix} shut down")


class SafeCounter:
    """Thread-safe counter class."""
    
    def __init__(self, initial_value: int = 0):
        """Initialize a thread-safe counter.
        
        Args:
            initial_value: Initial counter value
        """
        self._value = initial_value
        self._lock = threading.Lock()
    
    def increment(self, amount: int = 1) -> int:
        """Increment the counter.
        
        Args:
            amount: Amount to increment by
            
        Returns:
            New counter value
        """
        with self._lock:
            self._value += amount
            return self._value
    
    def decrement(self, amount: int = 1) -> int:
        """Decrement the counter.
        
        Args:
            amount: Amount to decrement by
            
        Returns:
            New counter value
        """
        with self._lock:
            self._value -= amount
            return self._value
    
    def get(self) -> int:
        """Get the current counter value.
        
        Returns:
            Current counter value
        """
        with self._lock:
            return self._value
    
    def set(self, value: int) -> None:
        """Set the counter value.
        
        Args:
            value: New counter value
        """
        with self._lock:
            self._value = value


class LimitedThreadPoolExecutor:
    """Thread pool with a limit on the number of concurrent tasks."""
    
    def __init__(self, max_workers: int, max_queue_size: int = 0):
        """Initialize a limited thread pool.
        
        Args:
            max_workers: Maximum number of worker threads
            max_queue_size: Maximum size of the task queue (0 for unlimited)
        """
        self.tasks_semaphore = threading.Semaphore(max_workers)
        self.task_queue = queue.Queue(max_queue_size) if max_queue_size > 0 else queue.Queue()
        self.active_workers = SafeCounter()
        self.shutdown_event = threading.Event()
    
    def submit(self, func: Callable[..., R], *args: Any, **kwargs: Any) -> 'ThreadTask[R]':
        """Submit a task for execution.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            ThreadTask object representing the execution
            
        Raises:
            RuntimeError: If the executor is shutting down
        """
        if self.shutdown_event.is_set():
            raise RuntimeError("Cannot submit task after shutdown")
        
        task = ThreadTask(func, args, kwargs, self)
        task.start()
        return task
    
    def map(self, func: Callable[[T], R], iterable: List[T]) -> List[R]:
        """Execute a function on each item in the iterable.
        
        Args:
            func: Function to execute
            iterable: Iterable of items to process
            
        Returns:
            List of results in the same order as the input iterable
        """
        tasks = [self.submit(func, item) for item in iterable]
        return [task.get_result() for task in tasks]
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool.
        
        Args:
            wait: If True, wait for all tasks to complete
        """
        self.shutdown_event.set()
        
        if wait:
            # Wait until all workers are done
            while self.active_workers.get() > 0:
                time.sleep(0.1)


class ThreadTask(Generic[R]):
    """Represents a task submitted to the LimitedThreadPoolExecutor."""
    
    def __init__(self, func: Callable[..., R], args: Tuple[Any, ...], 
                kwargs: Dict[str, Any], executor: LimitedThreadPoolExecutor):
        """Initialize a thread task.
        
        Args:
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            executor: The executor that created this task
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.executor = executor
        self.thread: Optional[threading.Thread] = None
        self.result: Optional[R] = None
        self.exception: Optional[Exception] = None
        self.done_event = threading.Event()
    
    def start(self) -> None:
        """Start the task execution."""
        self.thread = threading.Thread(target=self._execute, daemon=True)
        self.thread.start()
    
    def _execute(self) -> None:
        """Execute the task in a separate thread."""
        # Acquire a semaphore slot
        self.executor.tasks_semaphore.acquire()
        self.executor.active_workers.increment()
        
        try:
            # Execute the function
            self.result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
        finally:
            # Signal that the task is done
            self.done_event.set()
            
            # Release the semaphore slot
            self.executor.tasks_semaphore.release()
            self.executor.active_workers.decrement()
    
    def done(self) -> bool:
        """Check if the task has completed.
        
        Returns:
            True if the task has completed, False otherwise
        """
        return self.done_event.is_set()
    
    def get_result(self, timeout: Optional[float] = None) -> R:
        """Get the result of the task.
        
        Args:
            timeout: Maximum time to wait for the result in seconds
            
        Returns:
            Result of the task
            
        Raises:
            Exception: If the task raised an exception
            TimeoutError: If the result is not available within the timeout
        """
        if not self.done_event.wait(timeout):
            raise TimeoutError(f"Task did not complete within {timeout} seconds")
        
        if self.exception:
            raise self.exception
        
        return cast(R, self.result)


def synchronized(lock: Optional[threading.Lock] = None):
    """Decorator for thread-safe function execution.
    
    Args:
        lock: Lock to use (if None, a new lock will be created for each decorated function)
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        # Create a lock for this function if one was not provided
        func_lock = lock or threading.Lock()
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            with func_lock:
                return func(*args, **kwargs)
        return wrapper
    
    # Handle both @synchronized and @synchronized()
    if callable(lock):
        func, lock = lock, None
        return decorator(func)
    
    return decorator


def interruptible(func: Callable[..., R]) -> Callable[..., Optional[R]]:
    """Decorator to make a function interruptible by SIGINT (Ctrl+C).
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function that can be interrupted
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Optional[R]:
        result: Optional[R] = None
        original_handler = signal.getsignal(signal.SIGINT)
        
        def handler(sig: int, frame: Any) -> None:
            nonlocal wrapper
            logger.warning(f"Interrupted {func.__name__}")
            signal.signal(signal.SIGINT, original_handler)
            raise KeyboardInterrupt()
        
        try:
            signal.signal(signal.SIGINT, handler)
            result = func(*args, **kwargs)
            return result
        except KeyboardInterrupt:
            return None
        finally:
            signal.signal(signal.SIGINT, original_handler)
    
    return wrapper
