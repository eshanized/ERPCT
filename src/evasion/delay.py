#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT delay management module.
This module implements time-based evasion techniques.
"""

import time
import random
import math
from typing import Dict, Any, Optional, Tuple, Union, List

from src.evasion.base import EvasionBase


class DelayManager(EvasionBase):
    """
    Delay manager for time-based evasion techniques.
    
    This class handles various delay strategies to avoid detection:
    - Fixed delay: Wait a fixed time between attempts
    - Random delay: Wait a random time within a range
    - Exponential backoff: Increase delay after failures
    - Adaptive delay: Adjust delay based on server response
    - Pattern-based: Follow predefined patterns
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the delay manager.
        
        Args:
            config: Configuration dictionary with delay settings
        """
        super().__init__(config)
        
        # Default configuration
        self.min_delay = self.config.get("min_delay", 0.0)
        self.max_delay = self.config.get("max_delay", 0.0)
        self.jitter = self.config.get("jitter", 0.1)  # Randomness factor
        self.strategy = self.config.get("strategy", "fixed")
        
        # Backoff settings
        self.backoff_enabled = self.config.get("backoff", {}).get("enabled", False)
        self.backoff_factor = self.config.get("backoff", {}).get("factor", 2.0)
        self.backoff_max = self.config.get("backoff", {}).get("max_delay", 60.0)
        self.current_backoff = self.min_delay
        self.consecutive_failures = 0
        
        # Pattern settings
        self.pattern = self.config.get("pattern", [])
        self.pattern_index = 0
        
        # Human timing simulation
        self.human_timing = self.config.get("human_timing", False)
        
        # Timing statistics
        self.total_delay_time = 0.0
        self.last_auth_time = time.time()
        
        self.logger.debug(f"DelayManager initialized with strategy={self.strategy}, "
                          f"min_delay={self.min_delay}, max_delay={self.max_delay}")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Delay before authentication attempt.
        
        Args:
            target: Optional target information
        """
        super().pre_auth(target)
        
        if not self.enabled:
            return
        
        # Calculate delay based on strategy
        delay = self._calculate_delay()
        
        # Apply the delay
        if delay > 0:
            self.logger.debug(f"Waiting {delay:.2f} seconds before authentication")
            time.sleep(delay)
            self.total_delay_time += delay
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Handle result after authentication attempt.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        super().post_auth(success, response, target)
        
        if not self.enabled:
            return
        
        # Record time of authentication
        current_time = time.time()
        auth_duration = current_time - self.last_auth_time
        self.last_auth_time = current_time
        
        # Update backoff state if enabled
        if self.backoff_enabled:
            if success:
                # Reset backoff on success
                self.consecutive_failures = 0
                self.current_backoff = self.min_delay
            else:
                # Increase backoff on failure
                self.consecutive_failures += 1
                self.current_backoff = min(
                    self.current_backoff * self.backoff_factor,
                    self.backoff_max
                )
        
        # Move to next pattern index if using patterns
        if self.pattern:
            self.pattern_index = (self.pattern_index + 1) % len(self.pattern)
    
    def _calculate_delay(self) -> float:
        """
        Calculate delay based on current strategy.
        
        Returns:
            Delay in seconds
        """
        if self.strategy == "fixed":
            delay = self.min_delay
        
        elif self.strategy == "random":
            delay = random.uniform(self.min_delay, self.max_delay)
        
        elif self.strategy == "backoff" and self.backoff_enabled:
            delay = self.current_backoff
            # Add jitter to backoff
            if self.jitter > 0:
                jitter_amount = delay * self.jitter
                delay += random.uniform(-jitter_amount, jitter_amount)
                delay = max(delay, 0)  # Ensure non-negative
        
        elif self.strategy == "pattern" and self.pattern:
            delay = self.pattern[self.pattern_index]
        
        elif self.strategy == "human":
            # Simulate human typing/interaction
            delay = self._human_delay()
        
        else:
            # Default to fixed delay
            delay = self.min_delay
        
        # Apply jitter to all strategies except backoff (already applied)
        if self.jitter > 0 and self.strategy != "backoff":
            jitter_amount = delay * self.jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(delay, 0)  # Ensure non-negative
        
        return delay
    
    def _human_delay(self) -> float:
        """
        Generate a delay that mimics human behavior.
        
        Returns:
            Delay in seconds
        """
        # Base delay between 0.5 and 2 seconds
        base_delay = random.normalvariate(1.0, 0.3)
        base_delay = max(0.5, min(base_delay, 2.0))
        
        # Occasionally add a longer pause (10% chance)
        if random.random() < 0.1:
            base_delay += random.uniform(1.0, 3.0)
        
        return base_delay
    
    def set_strategy(self, strategy: str) -> None:
        """
        Set the delay strategy.
        
        Args:
            strategy: Delay strategy ("fixed", "random", "backoff", "pattern", "human")
        """
        valid_strategies = ["fixed", "random", "backoff", "pattern", "human"]
        if strategy not in valid_strategies:
            self.logger.warning(f"Invalid strategy: {strategy}. "
                               f"Using 'fixed'. Valid options: {valid_strategies}")
            strategy = "fixed"
        
        self.strategy = strategy
        self.logger.debug(f"Set delay strategy to {strategy}")
    
    def set_delay_range(self, min_delay: float, max_delay: float) -> None:
        """
        Set the delay range.
        
        Args:
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
        """
        if min_delay < 0:
            min_delay = 0
        
        if max_delay < min_delay:
            max_delay = min_delay
        
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.logger.debug(f"Set delay range to {min_delay}-{max_delay} seconds")
    
    def set_pattern(self, pattern: List[float]) -> None:
        """
        Set a delay pattern.
        
        Args:
            pattern: List of delay values to cycle through
        """
        if not pattern:
            self.logger.warning("Empty pattern provided. Using min_delay instead.")
            self.pattern = []
            return
        
        # Sanitize pattern (ensure all values are non-negative)
        self.pattern = [max(0, delay) for delay in pattern]
        self.pattern_index = 0
        self.logger.debug(f"Set delay pattern: {self.pattern}")
    
    def set_backoff_config(self, enabled: bool, factor: float = 2.0, max_delay: float = 60.0) -> None:
        """
        Configure exponential backoff.
        
        Args:
            enabled: Whether backoff is enabled
            factor: Multiplier for increasing delay after failures
            max_delay: Maximum backoff delay in seconds
        """
        self.backoff_enabled = enabled
        self.backoff_factor = max(1.0, factor)
        self.backoff_max = max(self.min_delay, max_delay)
        
        # Reset backoff state
        self.consecutive_failures = 0
        self.current_backoff = self.min_delay
        
        self.logger.debug(f"Set backoff config: enabled={enabled}, "
                         f"factor={factor}, max_delay={max_delay}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the delay manager.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_stats()
        stats.update({
            "strategy": self.strategy,
            "min_delay": self.min_delay,
            "max_delay": self.max_delay,
            "total_delay_time": self.total_delay_time,
            "average_delay": (self.total_delay_time / max(1, self.stats["pre_auth_calls"])),
            "backoff_enabled": self.backoff_enabled,
            "current_backoff": self.current_backoff,
            "consecutive_failures": self.consecutive_failures
        })
        return stats
