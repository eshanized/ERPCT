#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validator module for ERPCT.
This module provides the interface for validating passwords against
various authentication mechanisms.
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable, Union

from src.utils.logging import get_logger


class Validator:
    """Base validator class.
    
    The Validator class provides an interface for validating passwords
    against various authentication mechanisms such as hash comparison,
    network authentication, etc.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize validator with configuration.
        
        Args:
            config: Dictionary containing validator configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Rate limiting
        self.rate_limit = config.get("rate_limit", 0)  # attempts per second
        self._last_attempt_time = 0
        self._attempt_interval = 0 if self.rate_limit <= 0 else 1.0 / self.rate_limit
        self._rate_limit_lock = threading.Lock()
        
        # Stats
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        
        # Callback function for successful validations
        self.success_callback = None
    
    def validate(self, password: str, username: Optional[str] = None) -> bool:
        """Validate a password.
        
        This is the main method that should be implemented by subclasses.
        
        Args:
            password: Password to validate
            username: Optional username associated with the password
            
        Returns:
            True if the password is valid, False otherwise
        """
        # Apply rate limiting if configured
        if self.rate_limit > 0:
            with self._rate_limit_lock:
                current_time = time.time()
                time_since_last = current_time - self._last_attempt_time
                
                if time_since_last < self._attempt_interval:
                    # Sleep to enforce rate limit
                    time.sleep(self._attempt_interval - time_since_last)
                    
                self._last_attempt_time = time.time()
        
        # Track attempt
        self.total_attempts += 1
        
        # Perform validation (to be implemented by subclasses)
        result = self._validate_implementation(password, username)
        
        # Update stats
        if result:
            self.successful_attempts += 1
            if self.success_callback:
                try:
                    self.success_callback(password, username)
                except Exception as e:
                    self.logger.error(f"Error in success callback: {str(e)}")
        else:
            self.failed_attempts += 1
            
        return result
    
    def _validate_implementation(self, password: str, username: Optional[str] = None) -> bool:
        """Implementation of password validation.
        
        This method should be overridden by subclasses to provide specific
        validation logic.
        
        Args:
            password: Password to validate
            username: Optional username associated with the password
            
        Returns:
            True if the password is valid, False otherwise
        """
        self.logger.warning("Using base validator implementation which always returns False")
        return False
    
    def set_success_callback(self, callback: Callable[[str, Optional[str]], None]) -> None:
        """Set callback function for successful password validations.
        
        Args:
            callback: Function to call when a password is validated.
                     Function should accept (password, username) as arguments.
        """
        self.success_callback = callback
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics.
        
        Returns:
            Dictionary of validation statistics
        """
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": self.successful_attempts / max(1, self.total_attempts)
        }


class HashValidator(Validator):
    """Validator for hash-based password authentication."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize hash validator with configuration.
        
        Args:
            config: Dictionary containing validator configuration
                   Must include 'hash_type' and 'target' (the hash to compare against)
        """
        super().__init__(config)
        
        # Load hash configuration
        self.hash_type = config.get("hash_type", "")
        self.target_hash = config.get("target", "")
        
        if not self.target_hash:
            raise ValueError("Target hash must be specified")
            
        if not self.hash_type:
            self.logger.warning("Hash type not specified, attempting to auto-detect")
            self._detect_hash_type()
    
    def _detect_hash_type(self) -> None:
        """Attempt to detect hash type from the hash string."""
        from src.utils.crypto import analyze_hash
        
        hash_type, _ = analyze_hash(self.target_hash)
        
        if hash_type == "unknown":
            self.logger.warning("Could not detect hash type, defaulting to SHA-256")
            self.hash_type = "sha256"
        else:
            self.logger.info(f"Detected hash type: {hash_type}")
            self.hash_type = hash_type
    
    def _validate_implementation(self, password: str, username: Optional[str] = None) -> bool:
        """Validate password against target hash.
        
        Args:
            password: Password to validate
            username: Ignored for hash validation
            
        Returns:
            True if the password matches the target hash, False otherwise
        """
        from src.utils.crypto import verify_password
        
        try:
            return verify_password(password, self.target_hash, self.hash_type)
        except Exception as e:
            self.logger.error(f"Error validating hash: {str(e)}")
            return False


class NetworkValidator(Validator):
    """Validator for network-based password authentication."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize network validator with configuration.
        
        Args:
            config: Dictionary containing validator configuration
                   Must include 'protocol', 'host', and 'username'
        """
        super().__init__(config)
        
        # Load network configuration
        self.protocol = config.get("protocol", "").lower()
        self.host = config.get("host", "")
        self.port = config.get("port", 0)
        self.username = config.get("username", "")
        self.timeout = config.get("timeout", 5)
        
        if not self.protocol:
            raise ValueError("Protocol must be specified")
            
        if not self.host:
            raise ValueError("Host must be specified")
            
        if not self.port:
            self.port = self._get_default_port(self.protocol)
    
    def _get_default_port(self, protocol: str) -> int:
        """Get default port for a protocol.
        
        Args:
            protocol: Protocol name
            
        Returns:
            Default port number
        """
        default_ports = {
            "http": 80,
            "https": 443,
            "ftp": 21,
            "ssh": 22,
            "telnet": 23,
            "smtp": 25,
            "pop3": 110,
            "imap": 143,
            "ldap": 389,
            "smb": 445,
            "rdp": 3389
        }
        
        return default_ports.get(protocol.lower(), 0)
    
    def _validate_implementation(self, password: str, username: Optional[str] = None) -> bool:
        """Validate password against network service.
        
        Args:
            password: Password to validate
            username: Username to use (falls back to configured username if None)
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        # Use provided username or fall back to configured username
        effective_username = username or self.username
        
        if not effective_username:
            self.logger.error("No username provided for network validation")
            return False
        
        # Import the appropriate validator
        from src.core.password_validator import PasswordValidator
        
        # Create configuration for validator
        validator_config = {
            "target_type": "network",
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "username": effective_username,
            "timeout": self.timeout
        }
        
        # Create validator and validate
        validator = PasswordValidator(validator_config)
        return validator.validate_password(password)


# Registry of validator types
validator_registry = {
    "hash": HashValidator,
    "network": NetworkValidator
}


def create_validator(config: Dict[str, Any]) -> Validator:
    """Create a validator instance based on configuration.
    
    Args:
        config: Dictionary containing validator configuration
               Must include 'validator_type'
    
    Returns:
        Validator instance
        
    Raises:
        ValueError: If validator type is not supported
    """
    validator_type = config.get("validator_type", "hash").lower()
    
    validator_class = validator_registry.get(validator_type)
    
    if not validator_class:
        raise ValueError(f"Unsupported validator type: {validator_type}")
        
    return validator_class(config)
