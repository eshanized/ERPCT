#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT timing pattern module.
This module implements timing patterns for authentication attempts.
"""

import time
import random
import math
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

from src.evasion.base import EvasionBase


class TimingPattern(EvasionBase):
    """
    Timing pattern for authentication attempts.
    
    This class implements various timing patterns to avoid detection,
    including time-of-day patterns, burst/pause patterns, and
    human-like typing patterns.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the timing pattern.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Pattern type
        self.pattern_type = self.config.get("pattern_type", "steady")
        
        # Pattern parameters
        self.burst_size = self.config.get("burst_size", 10)
        self.burst_delay = self.config.get("burst_delay", 30.0)
        self.active_hours = self.config.get("active_hours", list(range(24)))
        self.max_deviation = self.config.get("max_deviation", 0.2)
        self.weekday_weight = self.config.get("weekday_weight", 1.0)
        self.weekend_weight = self.config.get("weekend_weight", 0.5)
        
        # Custom patterns
        self.custom_pattern = self.config.get("custom_pattern", [])
        
        # State
        self.attempts = 0
        self.last_time = time.time()
        self.burst_count = 0
        self.pattern_index = 0
        
        # If using time-of-day pattern, calculate the weights
        if self.pattern_type == "time_of_day":
            self._init_time_of_day_weights()
        
        self.logger.debug(f"TimingPattern initialized with pattern_type={self.pattern_type}")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply timing pattern before authentication attempt.
        
        Args:
            target: Optional target information
        """
        super().pre_auth(target)
        
        if not self.enabled:
            return
        
        # Apply timing pattern
        delay = self._calculate_delay()
        
        if delay > 0:
            self.logger.debug(f"Waiting {delay:.2f}s according to timing pattern")
            time.sleep(delay)
        
        # Update state
        self.attempts += 1
        self.last_time = time.time()
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Update pattern state after authentication attempt.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        super().post_auth(success, response, target)
        
        if not self.enabled:
            return
        
        # Update burst count for burst pattern
        if self.pattern_type == "burst":
            self.burst_count += 1
            if self.burst_count >= self.burst_size:
                self.burst_count = 0
                self.logger.debug(f"Burst complete, next burst will start after delay")
        
        # Update pattern index for custom pattern
        elif self.pattern_type == "custom" and self.custom_pattern:
            self.pattern_index = (self.pattern_index + 1) % len(self.custom_pattern)
    
    def _calculate_delay(self) -> float:
        """
        Calculate delay based on current pattern.
        
        Returns:
            Delay in seconds
        """
        if self.pattern_type == "steady":
            return 0.0  # No additional delay, rely on other evasion techniques
        
        elif self.pattern_type == "random":
            min_delay = self.config.get("min_delay", 0.0)
            max_delay = self.config.get("max_delay", 5.0)
            return random.uniform(min_delay, max_delay)
        
        elif self.pattern_type == "burst":
            if self.burst_count >= self.burst_size:
                return self.burst_delay
            return 0.0
        
        elif self.pattern_type == "time_of_day":
            return self._time_of_day_delay()
        
        elif self.pattern_type == "human":
            return self._human_timing_delay()
        
        elif self.pattern_type == "custom" and self.custom_pattern:
            return self.custom_pattern[self.pattern_index]
        
        # Default to no delay
        return 0.0
    
    def _init_time_of_day_weights(self) -> None:
        """Initialize weights for time-of-day pattern."""
        # Create a 24-hour weight pattern
        self.hour_weights = [0.0] * 24
        
        # Set weights for active hours
        for hour in self.active_hours:
            if 0 <= hour < 24:
                # Weight based on typical business hours (higher during work hours)
                if 9 <= hour < 17:  # 9 AM - 5 PM
                    self.hour_weights[hour] = 1.0
                elif 7 <= hour < 9 or 17 <= hour < 19:  # 7-9 AM, 5-7 PM
                    self.hour_weights[hour] = 0.7
                elif 19 <= hour < 23:  # 7-11 PM
                    self.hour_weights[hour] = 0.4
                else:  # Late night/early morning
                    self.hour_weights[hour] = 0.2
        
        self.logger.debug(f"Initialized time-of-day weights: {self.hour_weights}")
    
    def _time_of_day_delay(self) -> float:
        """
        Calculate delay based on time of day.
        
        Returns:
            Delay in seconds
        """
        current_time = time.localtime()
        current_hour = current_time.tm_hour
        is_weekend = current_time.tm_wday >= 5  # 5=Saturday, 6=Sunday
        
        # Get base weight for current hour
        weight = self.hour_weights[current_hour]
        
        # Adjust weight based on weekday/weekend
        if is_weekend:
            weight *= self.weekend_weight
        else:
            weight *= self.weekday_weight
        
        # No activity during inactive hours
        if weight <= 0:
            return 3600.0  # Wait an hour during inactive times
        
        # Calculate delay - higher weight means less delay
        base_delay = self.config.get("base_delay", 5.0)
        delay = base_delay / weight
        
        # Add randomness
        if self.max_deviation > 0:
            deviation = delay * self.max_deviation
            delay += random.uniform(-deviation, deviation)
            delay = max(0.1, delay)  # Ensure positive delay
        
        return delay
    
    def _human_timing_delay(self) -> float:
        """
        Calculate delay to simulate human behavior.
        
        Returns:
            Delay in seconds
        """
        # Base delay - humans don't type passwords instantly
        base_delay = random.normalvariate(2.0, 0.5)
        base_delay = max(0.5, min(base_delay, 4.0))  # Clamp between 0.5 and 4 seconds
        
        # Occasional longer pauses (10% chance)
        if random.random() < 0.1:
            base_delay += random.uniform(2.0, 10.0)
        
        # More variance at night
        current_hour = time.localtime().tm_hour
        if current_hour < 6 or current_hour >= 22:  # Late night/early morning
            base_delay *= random.uniform(1.0, 2.0)
        
        return base_delay
    
    def set_pattern_type(self, pattern_type: str) -> None:
        """
        Set the pattern type.
        
        Args:
            pattern_type: Pattern type ("steady", "random", "burst", 
                          "time_of_day", "human", "custom")
        """
        valid_patterns = ["steady", "random", "burst", "time_of_day", "human", "custom"]
        if pattern_type not in valid_patterns:
            self.logger.warning(f"Invalid pattern type: {pattern_type}. "
                               f"Using 'steady'. Valid options: {valid_patterns}")
            pattern_type = "steady"
        
        self.pattern_type = pattern_type
        
        # Reset state
        self.burst_count = 0
        self.pattern_index = 0
        
        # Initialize time-of-day weights if needed
        if pattern_type == "time_of_day":
            self._init_time_of_day_weights()
        
        self.logger.debug(f"Set pattern type to {pattern_type}")
    
    def set_burst_config(self, burst_size: int, burst_delay: float) -> None:
        """
        Configure burst pattern.
        
        Args:
            burst_size: Number of attempts in a burst
            burst_delay: Delay between bursts in seconds
        """
        self.burst_size = max(1, burst_size)
        self.burst_delay = max(0.0, burst_delay)
        self.burst_count = 0  # Reset burst count
        self.logger.debug(f"Set burst config: size={burst_size}, delay={burst_delay}s")
    
    def set_active_hours(self, hours: List[int]) -> None:
        """
        Set active hours for time-of-day pattern.
        
        Args:
            hours: List of active hours (0-23)
        """
        self.active_hours = [h for h in hours if 0 <= h < 24]
        
        if self.pattern_type == "time_of_day":
            self._init_time_of_day_weights()
            
        self.logger.debug(f"Set active hours: {self.active_hours}")
    
    def set_custom_pattern(self, pattern: List[float]) -> None:
        """
        Set custom delay pattern.
        
        Args:
            pattern: List of delay values to cycle through
        """
        if not pattern:
            self.logger.warning("Empty pattern provided")
            return
            
        # Ensure all delays are non-negative
        self.custom_pattern = [max(0.0, delay) for delay in pattern]
        self.pattern_index = 0
        self.logger.debug(f"Set custom pattern: {self.custom_pattern}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the timing pattern.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_stats()
        
        stats.update({
            "pattern_type": self.pattern_type,
            "attempts": self.attempts,
            "burst_size": self.burst_size if self.pattern_type == "burst" else None,
            "burst_delay": self.burst_delay if self.pattern_type == "burst" else None,
            "active_hours": self.active_hours if self.pattern_type == "time_of_day" else None,
            "custom_pattern_length": len(self.custom_pattern) if self.custom_pattern else None
        })
        
        return stats
