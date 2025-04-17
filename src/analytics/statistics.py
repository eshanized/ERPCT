#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Attack statistics module for ERPCT.
This module provides statistical analysis of password cracking operations.
"""

import math
import time
import datetime
from typing import Dict, List, Tuple, Any, Optional, Union
from collections import Counter, defaultdict

from src.utils.logging import get_logger
from src.core.attack import AttackResult


class AttackStatistics:
    """Class to calculate and store attack statistics."""
    
    def __init__(self, attack_id: Optional[str] = None):
        """Initialize attack statistics tracker.
        
        Args:
            attack_id: Optional attack identifier
        """
        self.logger = get_logger(__name__)
        self.attack_id = attack_id
        self.start_time = None
        self.end_time = None
        self.total_attempts = 0
        self.success_attempts = 0
        self.failed_attempts = 0
        self.error_attempts = 0
        
        # Store timing information
        self.attempt_times = []  # List of (timestamp, success_bool) tuples
        
        # Store username/password statistics
        self.usernames_tried = set()
        self.passwords_tried = set()
        self.successful_credentials = []  # List of (username, password) tuples
        
        # Categorized statistics
        self.stats_by_username = defaultdict(lambda: {"success": 0, "failure": 0, "error": 0})
        self.stats_by_password_length = defaultdict(lambda: {"success": 0, "failure": 0})
        self.stats_by_password_pattern = defaultdict(lambda: {"success": 0, "failure": 0})
        
        # Error tracking
        self.error_messages = Counter()
    
    def record_attempt(self, result: AttackResult) -> None:
        """Record an attack attempt result.
        
        Args:
            result: AttackResult object with attempt information
        """
        if not self.start_time:
            self.start_time = time.time()
        
        # Update counters
        self.total_attempts += 1
        
        if result.success:
            self.success_attempts += 1
            self.successful_credentials.append((result.username, result.password))
        else:
            self.failed_attempts += 1
            if result.message:
                self.error_attempts += 1
                self.error_messages[result.message] += 1
        
        # Store timing information
        self.attempt_times.append((result.timestamp, result.success))
        
        # Track unique usernames and passwords
        self.usernames_tried.add(result.username)
        self.passwords_tried.add(result.password)
        
        # Update categorized statistics
        username_stats = self.stats_by_username[result.username]
        if result.success:
            username_stats["success"] += 1
        elif result.message:
            username_stats["error"] += 1
        else:
            username_stats["failure"] += 1
        
        # Password length statistics
        password_length = len(result.password)
        if result.success:
            self.stats_by_password_length[password_length]["success"] += 1
        else:
            self.stats_by_password_length[password_length]["failure"] += 1
        
        # Password pattern statistics (simple categorization)
        pattern = self._categorize_password(result.password)
        if result.success:
            self.stats_by_password_pattern[pattern]["success"] += 1
        else:
            self.stats_by_password_pattern[pattern]["failure"] += 1
    
    def _categorize_password(self, password: str) -> str:
        """Categorize password by pattern.
        
        Args:
            password: Password to categorize
            
        Returns:
            String describing the password pattern
        """
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        if has_upper and has_lower and has_digit and has_special:
            return "complex"
        elif has_upper and has_lower and has_digit:
            return "alphanumeric_mixed"
        elif (has_upper or has_lower) and has_digit:
            return "alphanumeric"
        elif has_upper and has_lower:
            return "alpha_mixed"
        elif has_upper or has_lower:
            return "alpha"
        elif has_digit:
            return "numeric"
        else:
            return "special"
    
    def mark_complete(self) -> None:
        """Mark the statistics collection as complete."""
        self.end_time = time.time()
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time for the attack.
        
        Returns:
            Elapsed time in seconds
        """
        if not self.start_time:
            return 0.0
            
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    def get_attempts_per_second(self) -> float:
        """Calculate attempts per second.
        
        Returns:
            Attempts per second
        """
        elapsed = self.get_elapsed_time()
        if elapsed == 0:
            return 0.0
        return self.total_attempts / elapsed
    
    def get_success_rate(self) -> float:
        """Calculate success rate.
        
        Returns:
            Success rate as a percentage
        """
        if self.total_attempts == 0:
            return 0.0
        return (self.success_attempts / self.total_attempts) * 100
    
    def get_time_to_first_success(self) -> Optional[float]:
        """Get time until first successful attempt.
        
        Returns:
            Time in seconds, or None if no successes
        """
        if not self.successful_credentials or not self.start_time:
            return None
            
        # Find first success timestamp
        for timestamp, success in self.attempt_times:
            if success:
                return timestamp - self.start_time
        return None
    
    def get_most_vulnerable_usernames(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get usernames with highest success rate.
        
        Args:
            limit: Maximum number of usernames to return
            
        Returns:
            List of (username, success_count) tuples
        """
        username_successes = [(username, stats["success"]) 
                            for username, stats in self.stats_by_username.items()]
        return sorted(username_successes, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics.
        
        Returns:
            Dictionary with summary statistics
        """
        elapsed = self.get_elapsed_time()
        
        return {
            "attack_id": self.attack_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_seconds": elapsed,
            "elapsed_formatted": str(datetime.timedelta(seconds=int(elapsed))),
            "total_attempts": self.total_attempts,
            "successful_attempts": self.success_attempts,
            "failed_attempts": self.failed_attempts,
            "error_attempts": self.error_attempts,
            "success_rate": self.get_success_rate(),
            "attempts_per_second": self.get_attempts_per_second(),
            "unique_usernames": len(self.usernames_tried),
            "unique_passwords": len(self.passwords_tried),
            "successful_credentials": len(self.successful_credentials),
            "time_to_first_success": self.get_time_to_first_success(),
            "common_errors": dict(self.error_messages.most_common(5))
        }


def calculate_success_rate(attack_results: List[AttackResult]) -> float:
    """Calculate success rate from a list of attack results.
    
    Args:
        attack_results: List of attack results
        
    Returns:
        Success rate as a percentage
    """
    if not attack_results:
        return 0.0
        
    successes = sum(1 for result in attack_results if result.success)
    return (successes / len(attack_results)) * 100


def calculate_attempt_rate(attack_results: List[AttackResult], 
                         start_time: float, end_time: float) -> float:
    """Calculate attempt rate from a list of attack results.
    
    Args:
        attack_results: List of attack results
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        Attempts per second
    """
    if not attack_results or end_time <= start_time:
        return 0.0
        
    duration = end_time - start_time
    return len(attack_results) / duration


def calculate_protocol_stats(attack_results: List[AttackResult], 
                           protocol: str) -> Dict[str, Any]:
    """Calculate statistics for a specific protocol.
    
    Args:
        attack_results: List of attack results
        protocol: Protocol name
        
    Returns:
        Dictionary with protocol statistics
    """
    if not attack_results:
        return {
            "protocol": protocol,
            "total_attempts": 0,
            "success_rate": 0.0,
            "common_usernames": [],
            "common_passwords": []
        }
        
    # Count successes
    successes = sum(1 for result in attack_results if result.success)
    success_rate = (successes / len(attack_results)) * 100
    
    # Track common usernames and passwords in successful attempts
    successful_usernames = [result.username for result in attack_results if result.success]
    successful_passwords = [result.password for result in attack_results if result.success]
    
    # Count occurrences
    username_counter = Counter(successful_usernames)
    password_counter = Counter(successful_passwords)
    
    return {
        "protocol": protocol,
        "total_attempts": len(attack_results),
        "successful_attempts": successes,
        "success_rate": success_rate,
        "common_usernames": username_counter.most_common(5),
        "common_passwords": password_counter.most_common(5)
    }


def calculate_time_distribution(attack_results: List[AttackResult]) -> Dict[str, int]:
    """Calculate distribution of attempts over time.
    
    Args:
        attack_results: List of attack results
        
    Returns:
        Dictionary mapping hour to attempt count
    """
    if not attack_results:
        return {}
        
    # Group by hour of day
    hour_distribution = defaultdict(int)
    
    for result in attack_results:
        hour = datetime.datetime.fromtimestamp(result.timestamp).hour
        hour_distribution[hour] += 1
        
    return dict(hour_distribution)


def extract_common_patterns(successful_passwords: List[str]) -> Dict[str, int]:
    """Extract common patterns from successful passwords.
    
    Args:
        successful_passwords: List of successful passwords
        
    Returns:
        Dictionary mapping pattern to count
    """
    if not successful_passwords:
        return {}
        
    patterns = {
        "has_digits": 0,
        "has_uppercase": 0,
        "has_lowercase": 0,
        "has_special": 0,
        "length_1_4": 0,
        "length_5_8": 0,
        "length_9_12": 0,
        "length_13_plus": 0,
        "ends_with_digit": 0,
        "starts_with_uppercase": 0
    }
    
    for password in successful_passwords:
        # Check patterns
        if any(c.isdigit() for c in password):
            patterns["has_digits"] += 1
        
        if any(c.isupper() for c in password):
            patterns["has_uppercase"] += 1
            
        if any(c.islower() for c in password):
            patterns["has_lowercase"] += 1
            
        if any(not c.isalnum() for c in password):
            patterns["has_special"] += 1
            
        # Check length
        length = len(password)
        if 1 <= length <= 4:
            patterns["length_1_4"] += 1
        elif 5 <= length <= 8:
            patterns["length_5_8"] += 1
        elif 9 <= length <= 12:
            patterns["length_9_12"] += 1
        else:
            patterns["length_13_plus"] += 1
            
        # Check prefixes/suffixes
        if password and password[-1].isdigit():
            patterns["ends_with_digit"] += 1
            
        if password and password[0].isupper():
            patterns["starts_with_uppercase"] += 1
            
    return patterns
