#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT core engine module.
This module implements the main engine that orchestrates password attacks.
"""

import threading
import time
from typing import Dict, List, Any, Optional, Callable, Tuple, Set

from src.core.attack import Attack, AttackResult, AttackStatus
from src.core.scheduler import Scheduler
from src.core.validator import PasswordValidator
from src.core.result_handler import ResultHandler
from src.utils.logging import get_logger


class Engine:
    """Main password cracking engine class.
    
    The Engine class orchestrates the entire password cracking operation,
    coordinating between the attack, scheduler, validator and result handler components.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the engine with configuration.
        
        Args:
            config: Dictionary containing engine configuration parameters
        """
        self.logger = get_logger(__name__)
        self.config = config
        self.attack_threads = []
        self.running = False
        self.stop_event = threading.Event()
        
        # Initialize components
        self.scheduler = Scheduler(config)
        self.validator = PasswordValidator(config)
        self.result_handler = ResultHandler(config)
        
        # Stats and results tracking
        self.results = []
        self.successful_credentials: Set[Tuple[str, str]] = set()
        self.start_time = None
        self.end_time = None
        
        # Callbacks
        self.on_success_callback = None
        self.on_progress_callback = None
        self.on_complete_callback = None
    
    def set_on_success_callback(self, callback: Callable[[AttackResult], None]) -> None:
        """Set callback for successful authentication.
        
        Args:
            callback: Function to call when authentication succeeds
        """
        self.on_success_callback = callback
    
    def set_on_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback for attack progress updates.
        
        Args:
            callback: Function to call with progress information
        """
        self.on_progress_callback = callback
    
    def set_on_complete_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback for attack completion.
        
        Args:
            callback: Function to call when attack completes
        """
        self.on_complete_callback = callback
    
    def start(self) -> None:
        """Start the password cracking engine."""
        if self.running:
            self.logger.warning("Engine is already running")
            return
        
        self.logger.info("Starting password cracking engine")
        self.running = True
        self.stop_event.clear()
        self.start_time = time.time()
        
        # Configure components
        try:
            self.scheduler.initialize()
            self.validator.initialize()
            self.result_handler.initialize()
            
            # Prepare attacks based on scheduler
            scheduled_attacks = self.scheduler.get_next_attacks()
            
            for attack_config in scheduled_attacks:
                # Create and configure attack
                attack = Attack(attack_config)
                
                # Set up attack callbacks
                attack.set_on_success_callback(self._handle_success)
                attack.set_on_result_callback(self._handle_result)
                attack.set_on_complete_callback(self._handle_attack_complete)
                
                # Start attack in a new thread
                attack_thread = threading.Thread(target=self._run_attack, args=(attack,))
                attack_thread.daemon = True
                attack_thread.start()
                self.attack_threads.append((attack, attack_thread))
                
            # Start status monitor thread
            self.monitor_thread = threading.Thread(target=self._monitor_progress)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
        except Exception as e:
            self.logger.error(f"Error starting engine: {str(e)}")
            self.stop()
    
    def stop(self) -> None:
        """Stop the password cracking engine."""
        if not self.running:
            return
            
        self.logger.info("Stopping password cracking engine")
        self.stop_event.set()
        
        # Stop all attacks
        for attack, _ in self.attack_threads:
            attack.stop()
        
        # Wait for threads to finish
        for _, thread in self.attack_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        self.running = False
        self.end_time = time.time()
        
        # Notify completion
        if self.on_complete_callback:
            try:
                self.on_complete_callback(self.get_status())
            except Exception as e:
                self.logger.error(f"Error in completion callback: {str(e)}")
    
    def _run_attack(self, attack: Attack) -> None:
        """Run a single attack in a separate thread.
        
        Args:
            attack: Attack instance to run
        """
        try:
            attack.start()
        except Exception as e:
            self.logger.error(f"Error running attack: {str(e)}")
        finally:
            # Check if we need to schedule a new attack
            if self.running and not self.stop_event.is_set():
                try:
                    # Get next attack from scheduler if available
                    next_attacks = self.scheduler.get_next_attacks(count=1)
                    if next_attacks:
                        next_attack_config = next_attacks[0]
                        next_attack = Attack(next_attack_config)
                        
                        # Set up attack callbacks
                        next_attack.set_on_success_callback(self._handle_success)
                        next_attack.set_on_result_callback(self._handle_result)
                        next_attack.set_on_complete_callback(self._handle_attack_complete)
                        
                        # Start new attack
                        attack_thread = threading.Thread(target=self._run_attack, args=(next_attack,))
                        attack_thread.daemon = True
                        attack_thread.start()
                        
                        # Update thread list (remove old, add new)
                        self.attack_threads = [(a, t) for a, t in self.attack_threads if a != attack and t.is_alive()]
                        self.attack_threads.append((next_attack, attack_thread))
                except Exception as e:
                    self.logger.error(f"Error scheduling next attack: {str(e)}")
    
    def _handle_success(self, result: AttackResult) -> None:
        """Handle successful authentication result.
        
        Args:
            result: Attack result with successful authentication
        """
        # Add to successful credentials set
        credential = (result.username, result.password)
        self.successful_credentials.add(credential)
        
        # Process through result handler
        self.result_handler.handle_success(result)
        
        # Call success callback if defined
        if self.on_success_callback:
            try:
                self.on_success_callback(result)
            except Exception as e:
                self.logger.error(f"Error in success callback: {str(e)}")
    
    def _handle_result(self, result: AttackResult) -> None:
        """Handle any authentication result.
        
        Args:
            result: Attack result
        """
        # Add to results list
        self.results.append(result)
        
        # Validate password (useful for analytics and improving wordlists)
        self.validator.validate(result.password, result.success)
        
        # Process through result handler
        self.result_handler.handle_result(result)
    
    def _handle_attack_complete(self) -> None:
        """Handle completion of an attack."""
        # Check if all attacks are complete
        active_attacks = [a for a, t in self.attack_threads if a.status.running]
        if not active_attacks and self.running:
            # All attacks complete, check if we should stop
            if not self.scheduler.has_next_attack():
                self.stop()
    
    def _monitor_progress(self) -> None:
        """Monitor and report progress of attacks."""
        update_interval = float(self.config.get("status_update_interval", 1.0))
        
        while self.running and not self.stop_event.is_set():
            try:
                # Get status and call progress callback
                status = self.get_status()
                
                if self.on_progress_callback:
                    try:
                        self.on_progress_callback(status)
                    except Exception as e:
                        self.logger.error(f"Error in progress callback: {str(e)}")
                
                # Sleep for update interval
                time.sleep(update_interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring progress: {str(e)}")
                time.sleep(update_interval)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status.
        
        Returns:
            Dictionary with engine status information
        """
        # Calculate elapsed time
        elapsed = 0
        if self.start_time:
            if self.end_time:
                elapsed = self.end_time - self.start_time
            else:
                elapsed = time.time() - self.start_time
        
        # Aggregate attack stats
        total_attempts = 0
        completed_attempts = 0
        successful_attempts = 0
        error_attempts = 0
        estimated_total = 0
        
        for attack, _ in self.attack_threads:
            attack_stats = attack.get_status()
            total_attempts += attack_stats["total_attempts"]
            completed_attempts += attack_stats["completed_attempts"]
            successful_attempts += attack_stats["successful_attempts"]
            error_attempts += attack_stats["error_attempts"]
            estimated_total += attack_stats["total_attempts"]
        
        # Add scheduler's estimated future attempts
        estimated_total += self.scheduler.get_estimated_remaining_attempts()
        
        # Calculate speed and progress
        attempts_per_second = completed_attempts / max(elapsed, 0.001)
        progress_percent = (completed_attempts / max(estimated_total, 1)) * 100
        estimated_remaining = (estimated_total - completed_attempts) / max(attempts_per_second, 0.001)
        
        return {
            "running": self.running,
            "elapsed_seconds": elapsed,
            "total_attempts": total_attempts,
            "completed_attempts": completed_attempts,
            "successful_attempts": successful_attempts,
            "error_attempts": error_attempts,
            "estimated_total_attempts": estimated_total,
            "attempts_per_second": attempts_per_second,
            "progress_percent": progress_percent,
            "estimated_time_remaining": estimated_remaining,
            "successful_credentials_count": len(self.successful_credentials)
        }
    
    def get_successful_credentials(self) -> List[Tuple[str, str]]:
        """Get list of successful credentials.
        
        Returns:
            List of (username, password) tuples for successful logins
        """
        return list(self.successful_credentials)
