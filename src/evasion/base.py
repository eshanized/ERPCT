#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT evasion base module.
This module implements the base class for all evasion techniques.
"""

import time
import logging
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod

from src.utils.logging import get_logger


class EvasionBase(ABC):
    """
    Base class for all evasion techniques.
    
    This abstract class defines the interface for all evasion
    implementations. It handles configuration management and
    defines hooks for pre and post authentication actions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the evasion technique.
        
        Args:
            config: Configuration dictionary for the evasion technique
        """
        self.config = config or {}
        self.logger = get_logger(__name__)
        self.enabled = self.config.get("enabled", True)
        self.stats = {
            "pre_auth_calls": 0,
            "post_auth_calls": 0,
            "success_count": 0,
            "failure_count": 0,
            "start_time": time.time()
        }
        
        # Callbacks
        self._on_detection = None
        self._on_lockout = None
        
        self.logger.debug(f"Initialized {self.__class__.__name__} with config: {self.config}")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Perform actions before authentication attempt.
        
        This method is called before each authentication attempt.
        Implementations should override this to add custom behavior.
        
        Args:
            target: Optional target information
        """
        if not self.enabled:
            return
            
        self.stats["pre_auth_calls"] += 1
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Perform actions after authentication attempt.
        
        This method is called after each authentication attempt.
        Implementations should override this to add custom behavior.
        
        Args:
            success: Whether the authentication was successful
            response: The response object from the authentication attempt
            target: Optional target information
        """
        if not self.enabled:
            return
            
        self.stats["post_auth_calls"] += 1
        
        if success:
            self.stats["success_count"] += 1
        else:
            self.stats["failure_count"] += 1
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the evasion technique.
        
        Args:
            config: Configuration dictionary
        """
        self.config.update(config)
        self.enabled = self.config.get("enabled", True)
        self.logger.debug(f"Updated configuration: {self.config}")
    
    def enable(self) -> None:
        """Enable the evasion technique."""
        self.enabled = True
        self.logger.debug(f"Enabled {self.__class__.__name__}")
    
    def disable(self) -> None:
        """Disable the evasion technique."""
        self.enabled = False
        self.logger.debug(f"Disabled {self.__class__.__name__}")
    
    def is_enabled(self) -> bool:
        """Check if the evasion technique is enabled.
        
        Returns:
            True if enabled, False otherwise
        """
        return self.enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the evasion technique.
        
        Returns:
            Dictionary of statistics
        """
        stats = dict(self.stats)
        stats["duration"] = time.time() - stats["start_time"]
        stats["class"] = self.__class__.__name__
        return stats
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "pre_auth_calls": 0,
            "post_auth_calls": 0,
            "success_count": 0,
            "failure_count": 0,
            "start_time": time.time()
        }
        self.logger.debug(f"Reset statistics for {self.__class__.__name__}")
    
    def set_detection_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Set callback for detection events.
        
        Args:
            callback: Function to call when detection is suspected
        """
        self._on_detection = callback
    
    def set_lockout_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Set callback for lockout events.
        
        Args:
            callback: Function to call when account lockout is suspected
        """
        self._on_lockout = callback
    
    def _trigger_detection_callback(self, reason: str, data: Any = None) -> None:
        """Trigger the detection callback.
        
        Args:
            reason: Reason for detection
            data: Additional data
        """
        if self._on_detection:
            self.logger.warning(f"Detection suspected: {reason}")
            self._on_detection(reason, data)
    
    def _trigger_lockout_callback(self, reason: str, data: Any = None) -> None:
        """Trigger the lockout callback.
        
        Args:
            reason: Reason for lockout
            data: Additional data
        """
        if self._on_lockout:
            self.logger.warning(f"Account lockout suspected: {reason}")
            self._on_lockout(reason, data)
    
    def __str__(self) -> str:
        """String representation.
        
        Returns:
            String representation of the evasion technique
        """
        return f"{self.__class__.__name__}(enabled={self.enabled})" 