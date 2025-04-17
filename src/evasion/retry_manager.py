#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT retry manager module.
This module implements smart retry logic for handling transient failures.
"""

import time
import random
from typing import Dict, Any, Optional, List, Callable, Union

from src.evasion.base import EvasionBase


class RetryManager(EvasionBase):
    """
    Retry manager for handling transient failures.
    
    This class implements smart retry logic to handle connection failures,
    timeouts, rate limiting, and other transient errors.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the retry manager.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Default configuration
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 5.0)
        self.backoff_factor = self.config.get("backoff_factor", 2.0)
        self.jitter = self.config.get("jitter", 0.1)
        
        # Special error handling
        self.rate_limit_detection = self.config.get("rate_limit_detection", True)
        self.rate_limit_delay = self.config.get("rate_limit_delay", 30.0)
        self.service_unreachable_detection = self.config.get("service_unreachable_detection", True)
        self.service_unreachable_delay = self.config.get("service_unreachable_delay", 60.0)
        
        # Retry state
        self.retry_counts = {}  # target -> count
        self.last_retry_time = {}  # target -> time
        self.errors = {}  # target -> list of error messages
        
        # Error classifications
        self.connection_errors = [
            "connection refused", "timed out", "no route to host",
            "network unreachable", "connection reset", "broken pipe"
        ]
        self.rate_limit_errors = [
            "too many requests", "rate limit exceeded", "throttled",
            "429", "try again later", "quota exceeded"
        ]
        self.service_unreachable_errors = [
            "service unavailable", "503", "temporarily unavailable",
            "maintenance", "server busy"
        ]
        
        self.logger.debug(f"RetryManager initialized with max_retries={self.max_retries}, "
                          f"retry_delay={self.retry_delay}, backoff_factor={self.backoff_factor}")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Process before authentication attempt.
        
        Args:
            target: Optional target information
        """
        super().pre_auth(target)
        
        if not self.enabled or not target:
            return
        
        target_id = self._get_target_id(target)
        
        # Check if we need to wait based on previous errors
        if target_id in self.last_retry_time:
            wait_time = time.time() - self.last_retry_time[target_id]
            needed_delay = self._get_current_delay(target_id)
            
            if wait_time < needed_delay:
                remaining = needed_delay - wait_time
                self.logger.debug(f"Waiting {remaining:.2f}s before retry for {target_id}")
                time.sleep(remaining)
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Process after authentication attempt.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        super().post_auth(success, response, target)
        
        if not self.enabled or not target:
            return
        
        target_id = self._get_target_id(target)
        
        # Reset retry count on success
        if success:
            if target_id in self.retry_counts:
                self.retry_counts.pop(target_id, None)
                self.last_retry_time.pop(target_id, None)
                self.errors.pop(target_id, None)
                self.logger.debug(f"Reset retry count for {target_id} after success")
    
    def handle_error(self, error: Exception, target: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle an error and determine retry behavior.
        
        Args:
            error: The error that occurred
            target: Optional target information
            
        Returns:
            Dictionary with retry information
        """
        if not self.enabled or not target:
            return {"retry": False, "reason": "retry disabled"}
        
        target_id = self._get_target_id(target)
        error_message = str(error).lower()
        
        # Add to error history
        if target_id not in self.errors:
            self.errors[target_id] = []
        self.errors[target_id].append(error_message)
        
        # Initialize retry count if not present
        if target_id not in self.retry_counts:
            self.retry_counts[target_id] = 0
        
        # Increment retry count
        self.retry_counts[target_id] += 1
        
        # Check if max retries exceeded
        if self.retry_counts[target_id] > self.max_retries:
            return {
                "retry": False,
                "reason": f"max retries ({self.max_retries}) exceeded",
                "target_id": target_id,
                "retry_count": self.retry_counts[target_id]
            }
        
        # Classify the error
        error_type = self._classify_error(error_message)
        
        # Calculate retry delay based on error type
        if error_type == "rate_limit" and self.rate_limit_detection:
            delay = self.rate_limit_delay
            self.logger.warning(f"Rate limit detected for {target_id}: {error_message}")
        elif error_type == "service_unreachable" and self.service_unreachable_detection:
            delay = self.service_unreachable_delay
            self.logger.warning(f"Service unavailable for {target_id}: {error_message}")
        else:
            # Standard exponential backoff
            delay = self.retry_delay * (self.backoff_factor ** (self.retry_counts[target_id] - 1))
            
            # Add jitter
            if self.jitter > 0:
                jitter_amount = delay * self.jitter
                delay += random.uniform(-jitter_amount, jitter_amount)
                delay = max(delay, 0)  # Ensure non-negative
        
        # Record retry time
        self.last_retry_time[target_id] = time.time()
        
        self.logger.debug(f"Scheduling retry {self.retry_counts[target_id]}/{self.max_retries} "
                          f"for {target_id} in {delay:.2f}s (error type: {error_type})")
        
        return {
            "retry": True,
            "delay": delay,
            "reason": error_type,
            "target_id": target_id,
            "retry_count": self.retry_counts[target_id],
            "max_retries": self.max_retries
        }
    
    def reset(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Reset retry state.
        
        Args:
            target: Optional target information (if None, reset all)
        """
        if target:
            target_id = self._get_target_id(target)
            self.retry_counts.pop(target_id, None)
            self.last_retry_time.pop(target_id, None)
            self.errors.pop(target_id, None)
            self.logger.debug(f"Reset retry state for {target_id}")
        else:
            self.retry_counts = {}
            self.last_retry_time = {}
            self.errors = {}
            self.logger.debug("Reset all retry state")
    
    def get_retry_count(self, target: Dict[str, Any]) -> int:
        """
        Get the current retry count for a target.
        
        Args:
            target: Target information
            
        Returns:
            Current retry count
        """
        target_id = self._get_target_id(target)
        return self.retry_counts.get(target_id, 0)
    
    def get_retry_history(self, target: Dict[str, Any]) -> List[str]:
        """
        Get the error history for a target.
        
        Args:
            target: Target information
            
        Returns:
            List of error messages
        """
        target_id = self._get_target_id(target)
        return self.errors.get(target_id, [])
    
    def should_retry(self, target: Dict[str, Any]) -> bool:
        """
        Check if a target should be retried.
        
        Args:
            target: Target information
            
        Returns:
            True if the target should be retried, False otherwise
        """
        if not self.enabled:
            return False
            
        target_id = self._get_target_id(target)
        
        # Check if max retries exceeded
        if self.get_retry_count(target) > self.max_retries:
            return False
        
        # Check if we've waited long enough
        if target_id in self.last_retry_time:
            wait_time = time.time() - self.last_retry_time[target_id]
            needed_delay = self._get_current_delay(target_id)
            
            if wait_time < needed_delay:
                return False
        
        return True
    
    def _get_target_id(self, target: Dict[str, Any]) -> str:
        """
        Generate a unique identifier for a target.
        
        Args:
            target: Target information
            
        Returns:
            Target identifier string
        """
        # Prefer the target's explicit ID if available
        if "id" in target:
            return str(target["id"])
        
        # Otherwise, create a composite ID from host and port
        host = target.get("host", "")
        port = target.get("port", "")
        username = target.get("username", "")
        
        return f"{host}:{port}:{username}" if port else f"{host}:{username}"
    
    def _classify_error(self, error_message: str) -> str:
        """
        Classify an error message by type.
        
        Args:
            error_message: Error message string
            
        Returns:
            Error classification ("connection", "rate_limit", "service_unreachable", or "other")
        """
        error_message = error_message.lower()
        
        # Check for connection errors
        for err in self.connection_errors:
            if err in error_message:
                return "connection"
        
        # Check for rate limiting
        for err in self.rate_limit_errors:
            if err in error_message:
                return "rate_limit"
        
        # Check for service unavailability
        for err in self.service_unreachable_errors:
            if err in error_message:
                return "service_unreachable"
        
        # Default to other
        return "other"
    
    def _get_current_delay(self, target_id: str) -> float:
        """
        Calculate the current delay for a target.
        
        Args:
            target_id: Target identifier
            
        Returns:
            Delay in seconds
        """
        if target_id not in self.retry_counts:
            return 0
        
        # Get the most recent error
        if target_id in self.errors and self.errors[target_id]:
            error_message = self.errors[target_id][-1]
            error_type = self._classify_error(error_message)
            
            if error_type == "rate_limit" and self.rate_limit_detection:
                return self.rate_limit_delay
            elif error_type == "service_unreachable" and self.service_unreachable_detection:
                return self.service_unreachable_delay
        
        # Standard exponential backoff
        return self.retry_delay * (self.backoff_factor ** (self.retry_counts[target_id] - 1))
    
    def add_error_patterns(self, error_type: str, patterns: List[str]) -> None:
        """
        Add custom error patterns for classification.
        
        Args:
            error_type: Error type ("connection", "rate_limit", or "service_unreachable")
            patterns: List of regex patterns to match
        """
        if error_type == "connection":
            self.connection_errors.extend(patterns)
        elif error_type == "rate_limit":
            self.rate_limit_errors.extend(patterns)
        elif error_type == "service_unreachable":
            self.service_unreachable_errors.extend(patterns)
        else:
            self.logger.warning(f"Unknown error type: {error_type}")
        
        self.logger.debug(f"Added {len(patterns)} patterns for {error_type} errors")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the retry manager.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_stats()
        
        # Count error types
        error_types = {"connection": 0, "rate_limit": 0, "service_unreachable": 0, "other": 0}
        for target_id, error_list in self.errors.items():
            for error in error_list:
                error_type = self._classify_error(error)
                error_types[error_type] += 1
        
        # Calculate retry statistics
        total_retries = sum(self.retry_counts.values())
        max_target_retries = max(self.retry_counts.values()) if self.retry_counts else 0
        
        stats.update({
            "total_targets": len(self.retry_counts),
            "total_retries": total_retries,
            "max_target_retries": max_target_retries,
            "retry_counts": dict(self.retry_counts),
            "error_types": error_types
        })
        
        return stats
