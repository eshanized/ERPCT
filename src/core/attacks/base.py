#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT attack base module.
This module defines the base class for different attack implementations.
"""

import abc
import time
import threading
from typing import Dict, List, Optional, Any, Callable

from src.core.attack import AttackResult, AttackStatus
from src.utils.logging import get_logger


class AttackBase(abc.ABC):
    """Abstract base class for all attack implementations.
    
    This class defines the interface that all attack implementations must follow.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the attack with configuration.
        
        Args:
            config: Attack configuration dictionary
        """
        self.logger = get_logger(__name__)
        self.config = config
        self.status = AttackStatus()
        self.on_success_callback = None
        self.on_result_callback = None
        self.on_complete_callback = None
        self.stop_event = threading.Event()
        
        # Validate configuration
        self._validate_config()
    
    @abc.abstractmethod
    def _validate_config(self) -> None:
        """Validate attack configuration.
        
        Each subclass must implement this method to validate its specific
        configuration requirements.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        pass
    
    @abc.abstractmethod
    def start(self) -> None:
        """Start the attack.
        
        Each subclass must implement this method to start the attack with
        the configured parameters.
        """
        pass
    
    def stop(self) -> None:
        """Stop the attack.
        
        This method signals the attack to stop. The default implementation
        sets the stop event, but subclasses may need to override this method
        to perform additional cleanup.
        """
        self.logger.info("Stopping attack")
        self.stop_event.set()
    
    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the attack.
        
        Returns:
            Dictionary with status information
        """
        pass
    
    def set_on_success_callback(self, callback: Callable[[AttackResult], None]) -> None:
        """Set callback for successful authentication.
        
        Args:
            callback: Function to call when authentication succeeds
        """
        self.on_success_callback = callback
    
    def set_on_result_callback(self, callback: Callable[[AttackResult], None]) -> None:
        """Set callback for any authentication result.
        
        Args:
            callback: Function to call for any authentication result
        """
        self.on_result_callback = callback
    
    def set_on_complete_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for attack completion.
        
        Args:
            callback: Function to call when attack completes
        """
        self.on_complete_callback = callback
    
    def _handle_success(self, username: str, password: str, message: Optional[str] = None) -> None:
        """Handle a successful authentication.
        
        Args:
            username: The successful username
            password: The successful password
            message: Optional message with additional details
        """
        # Create result object
        result = AttackResult(
            username=username,
            password=password,
            success=True,
            message=message
        )
        
        # Log the success
        self.logger.info(f"Authentication successful: {username}:{password}")
        
        # Update status
        self.status.successful_attempts += 1
        
        # Call callbacks
        if self.on_success_callback:
            try:
                self.on_success_callback(result)
            except Exception as e:
                self.logger.error(f"Error in success callback: {str(e)}")
        
        if self.on_result_callback:
            try:
                self.on_result_callback(result)
            except Exception as e:
                self.logger.error(f"Error in result callback: {str(e)}")
    
    def _handle_failure(self, username: str, password: str, message: Optional[str] = None) -> None:
        """Handle a failed authentication.
        
        Args:
            username: The failed username
            password: The failed password
            message: Optional message with failure details
        """
        # Create result object
        result = AttackResult(
            username=username,
            password=password,
            success=False,
            message=message
        )
        
        # Update status
        self.status.failed_attempts += 1
        
        # Call result callback if registered
        if self.on_result_callback:
            try:
                self.on_result_callback(result)
            except Exception as e:
                self.logger.error(f"Error in result callback: {str(e)}")
    
    def _handle_completion(self) -> None:
        """Handle attack completion."""
        self.status.running = False
        self.status.end_time = time.time()
        
        self.logger.info("Attack completed")
        
        # Call completion callback if registered
        if self.on_complete_callback:
            try:
                self.on_complete_callback()
            except Exception as e:
                self.logger.error(f"Error in completion callback: {str(e)}")


class DictionaryAttack(AttackBase):
    """Dictionary attack implementation.
    
    This class implements a dictionary attack against the target.
    """
    
    def _validate_config(self) -> None:
        """Validate attack configuration."""
        if "target" not in self.config:
            raise ValueError("Target must be specified")
            
        if "protocol" not in self.config:
            raise ValueError("Protocol must be specified")
            
        if "wordlist" not in self.config and "password" not in self.config:
            raise ValueError("Either wordlist or password must be specified")
            
        if "username" not in self.config and "username_list" not in self.config:
            raise ValueError("Either username or username_list must be specified")
    
    def start(self) -> None:
        """Start the dictionary attack."""
        # Set up attack status
        self.status.running = True
        self.status.start_time = time.time()
        
        # Load usernames and passwords
        usernames = self._load_usernames()
        passwords = self._load_passwords()
        
        # Get other configuration
        threads = int(self.config.get("threads", 1))
        delay = float(self.config.get("delay", 0))
        username_first = bool(self.config.get("username_first", True))
        
        # Calculate total attempts
        self.status.total_attempts = len(usernames) * len(passwords)
        
        # Start attack threads
        self.attack_threads = []
        if username_first:
            # For each username, try all passwords
            for username in usernames:
                thread = threading.Thread(
                    target=self._attack_username,
                    args=(username, passwords.copy(), delay),
                    daemon=True
                )
                thread.start()
                self.attack_threads.append(thread)
                
                # Limit number of concurrent threads
                while sum(1 for t in self.attack_threads if t.is_alive()) >= threads:
                    time.sleep(0.1)
                    
                    # Check if we should stop
                    if self.stop_event.is_set():
                        break
                
                if self.stop_event.is_set():
                    break
        else:
            # For each password, try all usernames
            for password in passwords:
                thread = threading.Thread(
                    target=self._attack_password,
                    args=(password, usernames.copy(), delay),
                    daemon=True
                )
                thread.start()
                self.attack_threads.append(thread)
                
                # Limit number of concurrent threads
                while sum(1 for t in self.attack_threads if t.is_alive()) >= threads:
                    time.sleep(0.1)
                    
                    # Check if we should stop
                    if self.stop_event.is_set():
                        break
                
                if self.stop_event.is_set():
                    break
        
        # Wait for all threads to complete (unless stopped)
        if not self.stop_event.is_set():
            for thread in self.attack_threads:
                thread.join()
        
        # Mark attack as completed
        self._handle_completion()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the attack.
        
        Returns:
            Dictionary with status information
        """
        # Calculate derived statistics
        completed_attempts = self.status.successful_attempts + self.status.failed_attempts
        progress_percent = 0
        if self.status.total_attempts > 0:
            progress_percent = (completed_attempts / self.status.total_attempts) * 100
            
        elapsed_time = 0
        if self.status.start_time > 0:
            if self.status.end_time > 0:
                elapsed_time = self.status.end_time - self.status.start_time
            else:
                elapsed_time = time.time() - self.status.start_time
                
        attempts_per_second = 0
        if elapsed_time > 0:
            attempts_per_second = completed_attempts / elapsed_time
            
        estimated_time_remaining = 0
        if attempts_per_second > 0 and self.status.total_attempts > completed_attempts:
            remaining_attempts = self.status.total_attempts - completed_attempts
            estimated_time_remaining = remaining_attempts / attempts_per_second
        
        # Return status dictionary
        return {
            "running": self.status.running,
            "start_time": self.status.start_time,
            "end_time": self.status.end_time,
            "elapsed_time": elapsed_time,
            "total_attempts": self.status.total_attempts,
            "completed_attempts": completed_attempts,
            "successful_attempts": self.status.successful_attempts,
            "failed_attempts": self.status.failed_attempts,
            "progress_percent": progress_percent,
            "attempts_per_second": attempts_per_second,
            "estimated_time_remaining": estimated_time_remaining
        }
    
    def _load_usernames(self) -> List[str]:
        """Load usernames from configuration.
        
        Returns:
            List of usernames to test
        """
        if "username" in self.config:
            return [self.config["username"]]
            
        if "username_list" in self.config:
            filename = self.config["username_list"]
            usernames = []
            
            try:
                with open(filename, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            usernames.append(line)
                            
                self.logger.info(f"Loaded {len(usernames)} usernames from {filename}")
                return usernames
            except Exception as e:
                self.logger.error(f"Error loading usernames from {filename}: {str(e)}")
                return []
        
        return []
    
    def _load_passwords(self) -> List[str]:
        """Load passwords from configuration.
        
        Returns:
            List of passwords to test
        """
        if "password" in self.config:
            return [self.config["password"]]
            
        if "wordlist" in self.config:
            filename = self.config["wordlist"]
            passwords = []
            
            try:
                with open(filename, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            passwords.append(line)
                            
                self.logger.info(f"Loaded {len(passwords)} passwords from {filename}")
                return passwords
            except Exception as e:
                self.logger.error(f"Error loading passwords from {filename}: {str(e)}")
                return []
        
        return []
    
    def _attack_username(self, username: str, passwords: List[str], delay: float) -> None:
        """Attack a single username with multiple passwords.
        
        Args:
            username: The username to attack
            passwords: List of passwords to try
            delay: Delay between attempts in seconds
        """
        for password in passwords:
            # Check if we should stop
            if self.stop_event.is_set():
                break
                
            # Try the password
            result = self._try_auth(username, password)
            
            # Handle result
            if result.success:
                self._handle_success(username, password, result.message)
            else:
                self._handle_failure(username, password, result.message)
            
            # Delay between attempts
            if delay > 0:
                time.sleep(delay)
    
    def _attack_password(self, password: str, usernames: List[str], delay: float) -> None:
        """Attack a single password with multiple usernames.
        
        Args:
            password: The password to use
            usernames: List of usernames to try
            delay: Delay between attempts in seconds
        """
        for username in usernames:
            # Check if we should stop
            if self.stop_event.is_set():
                break
                
            # Try the credentials
            result = self._try_auth(username, password)
            
            # Handle result
            if result.success:
                self._handle_success(username, password, result.message)
            else:
                self._handle_failure(username, password, result.message)
            
            # Delay between attempts
            if delay > 0:
                time.sleep(delay)
    
    def _try_auth(self, username: str, password: str) -> AttackResult:
        """Try authentication with given credentials.
        
        Args:
            username: Username to try
            password: Password to try
            
        Returns:
            AttackResult object with the result
        """
        # Get protocol handler and try authentication
        from src.protocols import protocol_registry
        
        try:
            protocol_name = self.config.get("protocol")
            protocol_class = protocol_registry.get_protocol(protocol_name)
            
            # Create protocol instance
            protocol_config = self.config.copy()
            protocol_config["username"] = username
            protocol_config["password"] = password
            
            protocol = protocol_class(protocol_config)
            
            # Try authentication
            success, message = protocol.authenticate()
            
            return AttackResult(
                username=username,
                password=password,
                success=success,
                message=message
            )
        except Exception as e:
            self.logger.error(f"Error during authentication with {username}:{password}: {str(e)}")
            return AttackResult(
                username=username,
                password=password,
                success=False,
                message=f"Error: {str(e)}"
            ) 