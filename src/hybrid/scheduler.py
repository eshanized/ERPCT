#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Attack Scheduler.
This module provides components for scheduling and executing hybrid password
attack strategies against targets.
"""

import os
import time
import threading
import queue
from typing import List, Dict, Any, Optional, Callable, Tuple, Union, Set
from concurrent.futures import ThreadPoolExecutor

from src.utils.logging import get_logger
from src.hybrid.strategy import HybridStrategy


class AttackScheduler:
    """Manages and executes multiple hybrid attack strategies."""
    
    def __init__(self, threads: int = 1):
        """Initialize the attack scheduler.
        
        Args:
            threads: Number of threads to use for parallel execution
        """
        self.logger = get_logger(__name__)
        self.strategies: List[HybridStrategy] = []
        self.threads = max(1, threads)
        self.running = False
        self.stop_event = threading.Event()
        self.status_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.success_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.target_info: Dict[str, Any] = {}
        
    def add_strategy(self, strategy: HybridStrategy) -> None:
        """Add a strategy to the scheduler.
        
        Args:
            strategy: The strategy to add
        """
        self.strategies.append(strategy)
        self.logger.info(f"Added strategy '{strategy.name}' to scheduler")
        
    def clear_strategies(self) -> None:
        """Clear all strategies from the scheduler."""
        self.strategies.clear()
        self.logger.info("Cleared all strategies from scheduler")
        
    def set_threads(self, threads: int) -> None:
        """Set the number of threads to use for parallel execution.
        
        Args:
            threads: Number of threads
        """
        self.threads = max(1, threads)
        self.logger.info(f"Set thread count to {self.threads}")
        
    def set_status_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback function for status updates.
        
        Args:
            callback: Function to call with status updates
        """
        self.status_callback = callback
        
    def set_success_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Set callback function for successful password attempts.
        
        Args:
            callback: Function to call with successful password and target info
        """
        self.success_callback = callback
        
    def set_target_info(self, target_info: Dict[str, Any]) -> None:
        """Set target information for the attack.
        
        Args:
            target_info: Dictionary containing target information
        """
        self.target_info = target_info
        
    def run_sequential(self) -> Optional[str]:
        """Run all strategies sequentially.
        
        Returns:
            The successful password if found, None otherwise
        """
        if not self.strategies:
            self.logger.warning("No strategies to run")
            return None
            
        self.running = True
        self.stop_event.clear()
        
        total_estimated = sum(s.estimated_count for s in self.strategies)
        tried_count = 0
        start_time = time.time()
        
        try:
            for strategy in self.strategies:
                self.logger.info(f"Starting strategy: {strategy.name}")
                
                for password in strategy.generate():
                    tried_count += 1
                    
                    # Check if we should stop
                    if self.stop_event.is_set():
                        self.logger.info("Attack stopped by user")
                        self.running = False
                        return None
                        
                    # Try the password
                    success = self._check_password(password)
                    if success:
                        self.logger.info(f"Password found: {password}")
                        self.running = False
                        return password
                        
                    # Periodic status update (every 1000 attempts or every second)
                    if tried_count % 1000 == 0 or (time.time() - start_time) > 1:
                        self._update_status(tried_count, total_estimated, start_time)
                        start_time = time.time()  # Reset timer
        
        except Exception as e:
            self.logger.error(f"Error in sequential execution: {str(e)}")
        
        finally:
            self.running = False
            self._update_status(tried_count, total_estimated, start_time, finished=True)
            
        return None
        
    def run_parallel(self) -> Optional[str]:
        """Run all strategies in parallel using multiple threads.
        
        Returns:
            The successful password if found, None otherwise
        """
        if not self.strategies:
            self.logger.warning("No strategies to run")
            return None
            
        if len(self.strategies) == 1:
            self.logger.info("Only one strategy, using sequential execution")
            return self.run_sequential()
            
        self.running = True
        self.stop_event.clear()
        
        # Create a queue to track successful passwords
        result_queue = queue.Queue()
        
        # Track the total number of attempts
        total_estimated = sum(s.estimated_count for s in self.strategies)
        tried_count = [0]  # Use list for mutable reference
        start_time = time.time()
        last_update_time = start_time
        
        # Start each strategy in its own thread
        threads = []
        for strategy in self.strategies:
            thread = threading.Thread(
                target=self._run_strategy_on_target_parallel,
                args=(strategy, tried_count, result_queue)
            )
            thread.daemon = True
            threads.append(thread)
            
        # Start all threads
        for thread in threads:
            thread.start()
            
        password_found = None
        
        try:
            # Monitor threads and update status
            while any(t.is_alive() for t in threads):
                time.sleep(0.1)  # Short sleep to prevent CPU spin
                
                # Check if we found a password
                try:
                    password_found = result_queue.get_nowait()
                    self.stop_event.set()  # Signal all threads to stop
                    break
                except queue.Empty:
                    pass
                    
                # Check if we should stop
                if self.stop_event.is_set():
                    self.logger.info("Attack stopped by user")
                    break
                    
                # Periodic status update
                current_time = time.time()
                if current_time - last_update_time > 1.0:  # Update once per second
                    self._update_status(tried_count[0], total_estimated, start_time)
                    last_update_time = current_time
        
        except Exception as e:
            self.logger.error(f"Error in parallel execution: {str(e)}")
        
        finally:
            self.running = False
            
            # Wait for threads to finish (they should detect stop_event)
            for thread in threads:
                thread.join(timeout=2.0)  # Give each thread 2 seconds to finish
                
            # Final status update
            self._update_status(tried_count[0], total_estimated, start_time, finished=True)
                
        return password_found
        
    def stop(self) -> None:
        """Stop all running strategies."""
        if self.running:
            self.logger.info("Stopping attack")
            self.stop_event.set()
            
    def _run_strategy_on_target(self, strategy: HybridStrategy) -> Optional[str]:
        """Run a single strategy against the target.
        
        Args:
            strategy: The strategy to execute
            
        Returns:
            The successful password if found, None otherwise
        """
        self.logger.info(f"Starting strategy: {strategy.name}")
        
        try:
            for password in strategy.generate():
                # Check if we should stop
                if self.stop_event.is_set():
                    return None
                    
                # Try the password
                if self._check_password(password):
                    return password
        
        except Exception as e:
            self.logger.error(f"Error in strategy {strategy.name}: {str(e)}")
            
        return None
        
    def _run_strategy_on_target_parallel(self, 
                                        strategy: HybridStrategy, 
                                        tried_count: List[int], 
                                        result_queue: queue.Queue) -> None:
        """Run a strategy in parallel mode.
        
        Args:
            strategy: The strategy to execute
            tried_count: Mutable reference to counter for tracking attempts
            result_queue: Queue to store successful password
        """
        try:
            for password in strategy.generate():
                # Increment counter
                tried_count[0] += 1
                
                # Check if we should stop
                if self.stop_event.is_set():
                    return
                    
                # Try the password
                if self._check_password(password):
                    result_queue.put(password)
                    return
        
        except Exception as e:
            self.logger.error(f"Error in parallel strategy {strategy.name}: {str(e)}")
            
    def _update_status(self, tried: int, total: int, start_time: float, finished: bool = False) -> None:
        """Update attack status through callback.
        
        Args:
            tried: Number of passwords tried so far
            total: Total estimated passwords to try
            start_time: When the attack started
            finished: Whether the attack has completed
        """
        if not self.status_callback:
            return
            
        elapsed = time.time() - start_time
        rate = tried / max(0.1, elapsed)  # Passwords per second
        
        remaining = total - tried
        eta = remaining / rate if rate > 0 else 0
        
        status = {
            "tried": tried,
            "total": total,
            "percent": (tried / total * 100) if total > 0 else 0,
            "elapsed": elapsed,
            "rate": rate,
            "eta": eta,
            "finished": finished
        }
        
        try:
            self.status_callback(status)
        except Exception as e:
            self.logger.error(f"Error in status callback: {str(e)}")
            
    def _check_password(self, password: str) -> bool:
        """Check if a password is correct for the target.
        
        Args:
            password: Password to check
            
        Returns:
            True if password is correct, False otherwise
        """
        if not self.success_callback:
            self.logger.warning("No success callback set, cannot check password")
            return False
            
        try:
            # Call the success callback with the password and target info
            # The callback should return True if the password is correct
            result = self.success_callback(password, self.target_info)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error checking password: {str(e)}")
            return False


class PriorityAttackScheduler(AttackScheduler):
    """Scheduler that executes strategies based on priority level."""
    
    def __init__(self, threads: int = 1):
        """Initialize the priority attack scheduler.
        
        Args:
            threads: Number of threads to use for parallel execution
        """
        super().__init__(threads)
        self.strategy_priorities: Dict[HybridStrategy, int] = {}
        
    def add_strategy(self, strategy: HybridStrategy, priority: int = 0) -> None:
        """Add a strategy with priority level.
        
        Args:
            strategy: The strategy to add
            priority: Priority level (higher values = higher priority)
        """
        super().add_strategy(strategy)
        self.strategy_priorities[strategy] = priority
        self.logger.info(f"Added strategy '{strategy.name}' with priority {priority}")
        
    def run_sequential(self) -> Optional[str]:
        """Run strategies in priority order (highest first).
        
        Returns:
            The successful password if found, None otherwise
        """
        if not self.strategies:
            self.logger.warning("No strategies to run")
            return None
            
        # Sort strategies by priority (highest first)
        sorted_strategies = sorted(
            self.strategies,
            key=lambda s: self.strategy_priorities.get(s, 0),
            reverse=True
        )
        
        # Replace the strategies list with the sorted one
        original_strategies = self.strategies
        self.strategies = sorted_strategies
        
        # Run the sequential attack
        result = super().run_sequential()
        
        # Restore the original list
        self.strategies = original_strategies
        
        return result
