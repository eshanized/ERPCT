#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core attack engine for ERPCT.
This module implements the main password cracking functionality.
"""

import os
import time
import threading
import queue
from typing import Dict, List, Optional, Tuple, Any, Callable, Set

from src.protocols.base import ProtocolBase
from src.protocols import protocol_registry
from src.utils.logging import get_logger


class AttackResult:
    """Class to store attack results."""
    
    def __init__(self, username: str, password: str, success: bool, message: Optional[str] = None):
        """Initialize attack result.
        
        Args:
            username: Tested username
            password: Tested password
            success: Whether the authentication was successful
            message: Optional additional message
        """
        self.username = username
        self.password = password
        self.success = success
        self.message = message
        self.timestamp = time.time()


class AttackStatus:
    """Class to track attack status."""
    
    def __init__(self):
        """Initialize attack status."""
        self.start_time = None
        self.end_time = None
        self.total_attempts = 0
        self.completed_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.error_attempts = 0
        self.running = False
        self.stopping = False
        self.success_results = []
        self.error_messages = []
        self._lock = threading.RLock()
    
    def start(self) -> None:
        """Mark the attack as started."""
        with self._lock:
            self.start_time = time.time()
            self.running = True
            self.stopping = False
    
    def stop(self) -> None:
        """Mark the attack as stopped."""
        with self._lock:
            self.end_time = time.time()
            self.running = False
            self.stopping = False
    
    def set_stopping(self, stopping: bool) -> None:
        """Set the stopping state.
        
        Args:
            stopping: Whether the attack is in the process of stopping
        """
        with self._lock:
            self.stopping = stopping
    
    def update(self, result: AttackResult) -> None:
        """Update attack status with a result.
        
        Args:
            result: Attack result to add
        """
        with self._lock:
            self.completed_attempts += 1
            
            if result.success:
                self.successful_attempts += 1
                self.success_results.append(result)
            else:
                self.failed_attempts += 1
                if result.message:
                    self.error_attempts += 1
                    self.error_messages.append(result.message)
    
    def get_progress(self) -> float:
        """Get attack progress as a percentage.
        
        Returns:
            Percentage of completed attempts (0-100)
        """
        with self._lock:
            if self.total_attempts == 0:
                return 0.0
            return (self.completed_attempts / self.total_attempts) * 100
    
    def get_stats(self) -> Dict[str, Any]:
        """Get attack statistics.
        
        Returns:
            Dictionary with attack statistics
        """
        with self._lock:
            elapsed = 0
            if self.start_time:
                if self.end_time:
                    elapsed = self.end_time - self.start_time
                else:
                    elapsed = time.time() - self.start_time
                    
            attempts_per_second = 0
            if elapsed > 0:
                attempts_per_second = self.completed_attempts / elapsed
                
            return {
                "running": self.running,
                "stopping": self.stopping,
                "total_attempts": self.total_attempts,
                "completed_attempts": self.completed_attempts,
                "successful_attempts": self.successful_attempts,
                "failed_attempts": self.failed_attempts,
                "error_attempts": self.error_attempts,
                "progress_percent": self.get_progress(),
                "elapsed_seconds": elapsed,
                "attempts_per_second": attempts_per_second,
                "estimated_time_remaining": (self.total_attempts - self.completed_attempts) / max(attempts_per_second, 0.001) if self.running else 0
            }


class AttackController:
    """Singleton controller for managing attacks."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance.
        
        Returns:
            AttackController: The singleton instance
        """
        if cls._instance is None:
            cls._instance = AttackController()
        return cls._instance
    
    def __init__(self):
        """Initialize the attack controller."""
        if AttackController._instance is not None:
            raise RuntimeError("AttackController is a singleton - use get_instance()")
        
        self.active_attacks = {}
    
    def register_attack(self, attack):
        """Register an active attack.
        
        Args:
            attack: Attack instance
        
        Returns:
            str: Attack ID
        """
        import uuid
        
        # Generate a unique ID
        attack_id = str(uuid.uuid4())
        
        # Store the attack
        self.active_attacks[attack_id] = attack
        
        return attack_id
    
    def unregister_attack(self, attack_id):
        """Unregister an attack.
        
        Args:
            attack_id: Attack ID
        """
        if attack_id in self.active_attacks:
            del self.active_attacks[attack_id]
    
    def get_active_attacks(self):
        """Get all active attacks.
        
        Returns:
            dict: Dictionary of active attacks
        """
        return self.active_attacks.copy()
    
    def get_active_attack_count(self):
        """Get count of active attacks.
        
        Returns:
            int: Number of active attacks
        """
        return len(self.active_attacks)


class Attack:
    """Main attack class for ERPCT."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize attack with configuration.
        
        Args:
            config: Attack configuration dictionary
        """
        self.logger = get_logger(__name__)
        self.config = config
        self.status = AttackStatus()
        
        # Validate and load configuration
        self._validate_config()
        
        # Initialize protocol
        protocol_name = self.config.get("protocol")
        if not protocol_name:
            raise ValueError("Protocol must be specified")
            
        protocol_class = protocol_registry.get_protocol(protocol_name)
        self.protocol = protocol_class(self.config)
        
        # Set up threading and queues
        self.max_threads = int(self.config.get("threads", 1))
        self.username_queue = queue.Queue()
        self.password_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        # Set up callbacks
        self.on_success_callback = None
        self.on_result_callback = None
        self.on_complete_callback = None
        
        # Load credentials
        self._load_credentials()
        
        self.attack_id = None
    
    def _validate_config(self) -> None:
        """Validate attack configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Check for required fields
        if not self.config.get("protocol"):
            raise ValueError("Protocol must be specified")
        
        # Check if we have a target directly or in a file
        if not self.config.get("target") and not self.config.get("target_file"):
            raise ValueError("Target host/IP must be specified")
        
        # Validate credentials source - we need either a username/password or files for them
        if not self.config.get("username") and not self.config.get("username_file"):
            raise ValueError("Username must be specified or a username file must be provided")
        
        if not self.config.get("password") and not self.config.get("password_file"):
            raise ValueError("Password must be specified or a password file must be provided")
        
        # Validate port if specified
        if "port" in self.config:
            port = self.config["port"]
            if not isinstance(port, int) or port <= 0 or port > 65535:
                raise ValueError(f"Invalid port number: {port}")
        
        # Validate thread count
        threads = int(self.config.get("threads", 1))
        if threads < 1:
            self.config["threads"] = 1
            self.logger.warning("Thread count adjusted to minimum value of 1")
        elif threads > 100:
            self.config["threads"] = 100
            self.logger.warning("Thread count capped at maximum value of 100")
        
        # Set default timeout if not specified
        if "timeout" not in self.config:
            self.config["timeout"] = 30
            self.logger.debug("Using default timeout of 30 seconds")
    
    def _load_credentials(self) -> None:
        """Load usernames and passwords from configuration."""
        # Load usernames
        usernames = []
        username = self.config.get("username")
        if username:
            usernames.append(username)
            
        username_list = self.config.get("username_list")
        if username_list and os.path.isfile(username_list):
            try:
                with open(username_list, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            usernames.append(line)
            except Exception as e:
                self.logger.error(f"Error loading username list {username_list}: {str(e)}")
        
        if not usernames:
            raise ValueError("No usernames specified")
            
        # Load passwords
        passwords = []
        password = self.config.get("password")
        if password:
            passwords.append(password)
            
        wordlist = self.config.get("wordlist")
        if wordlist and os.path.isfile(wordlist):
            try:
                with open(wordlist, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            passwords.append(line)
            except Exception as e:
                self.logger.error(f"Error loading wordlist {wordlist}: {str(e)}")
        
        if not passwords:
            raise ValueError("No passwords specified")
        
        # Set total attempts
        self.status.total_attempts = len(usernames) * len(passwords)
        
        # Queue usernames and passwords
        if self.config.get("username_first", True):
            # Username-first approach: For each username, try all passwords
            for username in usernames:
                for password in passwords:
                    self.username_queue.put(username)
                    self.password_queue.put(password)
        else:
            # Password-first approach: For each password, try all usernames
            for password in passwords:
                for username in usernames:
                    self.username_queue.put(username)
                    self.password_queue.put(password)
    
    def set_on_success_callback(self, callback: Callable[[AttackResult], None]) -> None:
        """Set callback for successful authentication.
        
        Args:
            callback: Function to call when authentication succeeds
        """
        self.on_success_callback = callback
    
    def set_on_result_callback(self, callback: Callable[[AttackResult], None]) -> None:
        """Set callback for any authentication result.
        
        Args:
            callback: Function to call for each authentication result
        """
        self.on_result_callback = callback
    
    def set_on_complete_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for attack completion.
        
        Args:
            callback: Function to call when attack completes
        """
        self.on_complete_callback = callback
    
    def start(self) -> None:
        """Start the attack."""
        if self.status.running:
            self.logger.warning("Attack is already running")
            return
            
        # Register with controller
        self.attack_id = AttackController.get_instance().register_attack(self)
        
        self.logger.info(f"Starting attack with {self.status.total_attempts} total attempts and {self.max_threads} threads")
        
        # Reset stop event
        self.stop_event.clear()
        
        # Start status
        self.status.start()
        
        # Start worker threads
        self.threads = []
        for i in range(self.max_threads):
            thread = threading.Thread(target=self._worker, name=f"AttackWorker-{i+1}")
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
            
        # Start result processor
        self.result_thread = threading.Thread(target=self._process_results, name="ResultProcessor")
        self.result_thread.daemon = True
        self.result_thread.start()
    
    def stop(self) -> None:
        """Stop the attack."""
        if not self.status.running:
            self.logger.warning("Attack not running")
            return
            
        # Set stop flag
        self.status.set_stopping(True)
        
        # Unregister from controller
        if self.attack_id:
            AttackController.get_instance().unregister_attack(self.attack_id)
            self.attack_id = None
        
        self.logger.info("Stopping attack")
        self.stop_event.set()
        
        # Wait for threads to complete
        for thread in self.threads:
            thread.join(timeout=2.0)
            
        # Clear queues
        while not self.username_queue.empty():
            try:
                self.username_queue.get_nowait()
            except queue.Empty:
                break
                
        while not self.password_queue.empty():
            try:
                self.password_queue.get_nowait()
            except queue.Empty:
                break
        
        # Set status
        self.status.stop()
        
        # Call on_complete callback
        if self.on_complete_callback:
            try:
                self.on_complete_callback()
            except Exception as e:
                self.logger.error(f"Error in on_complete_callback: {str(e)}")
    
    def _worker(self) -> None:
        """Worker thread function to test credentials."""
        delay = float(self.config.get("delay", 0))
        
        while not self.stop_event.is_set():
            try:
                # Get next username/password pair
                try:
                    username = self.username_queue.get(timeout=0.1)
                    password = self.password_queue.get(timeout=0.1)
                except queue.Empty:
                    # No more credentials to test
                    break
                
                # Apply delay if configured
                if delay > 0:
                    time.sleep(delay)
                
                # Test credentials
                try:
                    success, message = self.protocol.test_credentials(username, password)
                    result = AttackResult(username, password, success, message)
                    self.result_queue.put(result)
                except Exception as e:
                    self.logger.error(f"Error testing credentials: {str(e)}")
                    result = AttackResult(username, password, False, f"Error: {str(e)}")
                    self.result_queue.put(result)
                
                # Mark as done
                self.username_queue.task_done()
                self.password_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in worker thread: {str(e)}")
        
        self.logger.debug("Worker thread exiting")
    
    def _process_results(self) -> None:
        """Process results from the result queue."""
        while self.status.running or not self.result_queue.empty():
            try:
                # Get next result
                try:
                    result = self.result_queue.get(timeout=0.1)
                except queue.Empty:
                    # No results to process
                    continue
                
                # Update status
                self.status.update(result)
                
                # Call callbacks
                if result.success and self.on_success_callback:
                    try:
                        self.on_success_callback(result)
                    except Exception as e:
                        self.logger.error(f"Error in on_success_callback: {str(e)}")
                
                if self.on_result_callback:
                    try:
                        self.on_result_callback(result)
                    except Exception as e:
                        self.logger.error(f"Error in on_result_callback: {str(e)}")
                
                # Log result
                if result.success:
                    self.logger.info(f"Success: {result.username}:{result.password}")
                
                # Mark as done
                self.result_queue.task_done()
                
                # Check if attack is complete
                if self.status.completed_attempts >= self.status.total_attempts:
                    self.stop()
                    
            except Exception as e:
                self.logger.error(f"Error processing results: {str(e)}")
                
            # Check for stop event
            if self.stop_event.is_set():
                break
        
        self.logger.debug("Result processor thread exiting")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current attack status.
        
        Returns:
            Dictionary with attack status and statistics
        """
        return self.status.get_stats()
    
    def get_successful_credentials(self) -> List[Tuple[str, str]]:
        """Get list of successfully cracked credentials.
        
        Returns:
            List of (username, password) tuples
        """
        return [(result.username, result.password) for result in self.status.success_results]
