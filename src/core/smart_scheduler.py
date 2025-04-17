#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smart attack scheduler module for ERPCT.
This module implements advanced scheduling strategies for password attacks.
"""

import time
import copy
import random
from typing import Dict, List, Any, Optional, Tuple

from src.utils.logging import get_logger


class AttackStats:
    """Class to track statistics for an attack strategy."""
    
    def __init__(self, attack_config: Dict[str, Any]):
        """Initialize attack statistics.
        
        Args:
            attack_config: Attack configuration dictionary
        """
        self.config = copy.deepcopy(attack_config)
        self.attempts = 0
        self.successes = 0
        self.failures = 0
        self.last_run_time = 0
        self.total_run_time = 0
        self.attempts_per_second = 0
        self.success_rate = 0
        self.score = 0
    
    def update(self, stats: Dict[str, Any]) -> None:
        """Update statistics with results from a completed attack.
        
        Args:
            stats: Dictionary with attack statistics
        """
        # Update attempt counts
        completed = stats.get("completed_attempts", 0)
        successful = stats.get("successful_attempts", 0)
        self.attempts += completed
        self.successes += successful
        self.failures += (completed - successful)
        
        # Update timing stats
        elapsed = stats.get("elapsed_seconds", 0)
        self.last_run_time = elapsed
        self.total_run_time += elapsed
        
        # Calculate derived metrics
        if elapsed > 0:
            self.attempts_per_second = completed / elapsed
            
        if self.attempts > 0:
            self.success_rate = self.successes / self.attempts
            
        # Calculate score
        self._calculate_score()
    
    def _calculate_score(self) -> None:
        """Calculate a score for prioritizing this attack strategy."""
        # Base score from success rate
        success_score = self.success_rate * 100
        
        # Performance score
        perf_score = min(50, self.attempts_per_second)
        
        # Adjust for attack types
        attack_type = self.config.get("type", "")
        type_multiplier = 1.0
        
        if attack_type == "dictionary":
            # Dictionary attacks are usually faster
            type_multiplier = 1.2
        elif attack_type == "rule-based":
            # Rule-based can be very effective
            type_multiplier = 1.1
        elif attack_type == "brute-force":
            # Brute force is usually slow
            type_multiplier = 0.7
        
        # Combine scores
        self.score = (success_score * 0.6 + perf_score * 0.4) * type_multiplier
        
        # Adjust for recency
        if time.time() - self.last_run_time > 86400:  # More than a day old
            self.score *= 0.9
    
    def get_stats(self) -> Dict[str, Any]:
        """Get attack statistics.
        
        Returns:
            Dictionary with attack statistics
        """
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "last_run_time": self.last_run_time,
            "total_run_time": self.total_run_time,
            "attempts_per_second": self.attempts_per_second,
            "success_rate": self.success_rate,
            "score": self.score,
            "attack_type": self.config.get("type", ""),
            "attack_name": self.config.get("name", "")
        }


class SmartScheduler:
    """Smart attack scheduler class.
    
    The SmartScheduler uses adaptive strategies to prioritize attacks based on
    past performance metrics, success rates, and attack characteristics.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the smart scheduler with configuration.
        
        Args:
            config: Dictionary containing scheduler configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Extract configuration for smart scheduling
        self.learning_rate = float(config.get("learning_rate", 0.1))
        self.exploration_rate = float(config.get("exploration_rate", 0.2))
        self.strategy = config.get("scheduling_strategy", "success_rate")
        
        # Internal state
        self.attack_queue = []
        self.attack_stats = {}  # Maps attack_id to AttackStats
        self.completed_attacks = []
        self.attack_history = []
        self.initialized = False
    
    def initialize(self, attack_configs: List[Dict[str, Any]]) -> None:
        """Initialize the scheduler with attack configurations.
        
        Args:
            attack_configs: List of attack configuration dictionaries
        """
        self.logger.info("Initializing smart scheduler")
        
        # Create a deep copy of the attack configs
        self.attack_queue = copy.deepcopy(attack_configs)
        
        # Initialize attack stats
        for attack in self.attack_queue:
            attack_id = self._get_attack_id(attack)
            if attack_id not in self.attack_stats:
                self.attack_stats[attack_id] = AttackStats(attack)
        
        # Apply initial prioritization
        self._prioritize_attacks()
        
        self.initialized = True
        self.logger.info(f"Smart scheduler initialized with {len(self.attack_queue)} attacks")
    
    def _get_attack_id(self, attack: Dict[str, Any]) -> str:
        """Generate a unique ID for an attack.
        
        Args:
            attack: Attack configuration dictionary
            
        Returns:
            Unique attack ID
        """
        # Create a unique identifier for this attack
        attack_name = attack.get("name", "")
        attack_type = attack.get("type", "")
        
        if attack_name:
            # Use name if available
            return f"{attack_type}_{attack_name}"
        else:
            # Create a hash of relevant attack parameters
            import hashlib
            hash_str = str(sorted([(k, v) for k, v in attack.items() 
                               if k not in ["id", "priority"]]))
            hash_obj = hashlib.md5(hash_str.encode())
            return f"{attack_type}_{hash_obj.hexdigest()[:8]}"
    
    def get_next_attacks(self, count: int = 1) -> List[Dict[str, Any]]:
        """Get the next attacks to execute.
        
        Args:
            count: Number of attacks to return
            
        Returns:
            List of attack configuration dictionaries
        """
        if not self.initialized:
            self.logger.warning("Smart scheduler not initialized")
            return []
            
        if not self.attack_queue:
            self.logger.info("No more attacks in queue")
            return []
        
        # Check if we should explore (try a random attack)
        if random.random() < self.exploration_rate:
            self.logger.debug("Exploration: selecting random attacks")
            # Select random attacks
            selected = []
            remaining = copy.copy(self.attack_queue)
            
            for _ in range(min(count, len(remaining))):
                attack = random.choice(remaining)
                selected.append(attack)
                remaining.remove(attack)
                
            # Remove selected attacks from queue
            for attack in selected:
                if attack in self.attack_queue:
                    self.attack_queue.remove(attack)
                    
            return copy.deepcopy(selected)
        
        # Otherwise, use the prioritized queue
        selected = []
        for _ in range(min(count, len(self.attack_queue))):
            attack = self.attack_queue.pop(0)
            selected.append(attack)
            
        return copy.deepcopy(selected)
    
    def update_attack_stats(self, attack_config: Dict[str, Any], 
                           stats: Dict[str, Any]) -> None:
        """Update statistics for an attack that has completed.
        
        Args:
            attack_config: Attack configuration dictionary
            stats: Dictionary with attack statistics
        """
        attack_id = self._get_attack_id(attack_config)
        
        if attack_id not in self.attack_stats:
            self.attack_stats[attack_id] = AttackStats(attack_config)
            
        # Update stats
        self.attack_stats[attack_id].update(stats)
        
        # Add to history
        self.attack_history.append((attack_id, stats.get("elapsed_seconds", 0), 
                                  stats.get("successful_attempts", 0)))
        
        # Add to completed attacks
        self.completed_attacks.append(attack_config)
        
        # Use results to generate new attacks if appropriate
        self._generate_new_attacks(attack_config, stats)
        
        # Re-prioritize attacks
        self._prioritize_attacks()
    
    def _prioritize_attacks(self) -> None:
        """Prioritize attacks based on the selected strategy."""
        if not self.attack_queue:
            return
            
        self.logger.debug(f"Prioritizing {len(self.attack_queue)} attacks")
        
        # Calculate scores based on strategy
        if self.strategy == "success_rate":
            # Prioritize based on success rate
            def get_score(attack):
                attack_id = self._get_attack_id(attack)
                if attack_id in self.attack_stats:
                    return self.attack_stats[attack_id].score
                # If no stats yet, use initial score from attack type
                return self._get_initial_score(attack)
                
            self.attack_queue.sort(key=get_score, reverse=True)
            
        elif self.strategy == "bandits":
            # Multi-armed bandit approach (Thompson sampling)
            def get_bandit_score(attack):
                attack_id = self._get_attack_id(attack)
                if attack_id in self.attack_stats:
                    stats = self.attack_stats[attack_id]
                    # Beta distribution sampling
                    return random.betavariate(stats.successes + 1, stats.failures + 1)
                # If no stats yet, use random value
                return random.random()
                
            self.attack_queue.sort(key=get_bandit_score, reverse=True)
            
        else:
            # Default to basic score
            self.attack_queue.sort(
                key=lambda x: self._get_initial_score(x), 
                reverse=True
            )
    
    def _get_initial_score(self, attack: Dict[str, Any]) -> float:
        """Get initial score for an attack with no history.
        
        Args:
            attack: Attack configuration dictionary
            
        Returns:
            Initial score
        """
        # Default scores by attack type
        type_scores = {
            "dictionary": 90,
            "hybrid": 80,
            "rule-based": 70,
            "mask": 60,
            "brute-force": 40
        }
        
        attack_type = attack.get("type", "")
        base_score = type_scores.get(attack_type, 50)
        
        # Adjust score based on other factors
        modifiers = 0
        
        # Dictionary attacks with common passwords should be higher priority
        if attack_type == "dictionary" and "common_passwords" in attack.get("dictionary_path", "").lower():
            modifiers += 10
            
        # Shorter password length ranges should be higher priority
        if "min_length" in attack and "max_length" in attack:
            length_range = attack["max_length"] - attack["min_length"]
            if length_range <= 2:
                modifiers += 5
            elif length_range >= 8:
                modifiers -= 10
                
        # User-defined priority
        modifiers += attack.get("priority", 0) * 5
        
        return base_score + modifiers
    
    def _generate_new_attacks(self, attack_config: Dict[str, Any], 
                             stats: Dict[str, Any]) -> None:
        """Generate new attacks based on results of a completed attack.
        
        Args:
            attack_config: Configuration of completed attack
            stats: Statistics from the completed attack
        """
        # Only generate new attacks if this one was successful
        successful_attempts = stats.get("successful_attempts", 0)
        if successful_attempts <= 0:
            return
            
        attack_type = attack_config.get("type", "")
        successful_passwords = stats.get("successful_passwords", [])
        
        if not successful_passwords:
            return
            
        # Create new attacks based on successful passwords
        if attack_type == "dictionary":
            # Create rule-based attack using successful passwords
            self._generate_rule_attack(successful_passwords)
            
        elif attack_type == "rule-based":
            # Create mask attack based on password patterns
            self._generate_mask_attack(successful_passwords)
    
    def _generate_rule_attack(self, passwords: List[str]) -> None:
        """Generate a rule-based attack from successful passwords.
        
        Args:
            passwords: List of successful passwords
        """
        if not passwords:
            return
            
        # Create rule-based attack
        new_attack = {
            "type": "rule-based",
            "name": "Generated from successful passwords",
            "base_words": passwords[:20],  # Limit to first 20 passwords
            "rules": [
                "c", "C",                # Capitalize first letter, all caps
                "t", "T",                # Toggle case
                "$1", "$2", "$3",        # Append digits
                "^1", "^2", "^3",        # Prepend digits
                "$!", "$@", "$#"         # Append special characters
            ],
            "priority": 90
        }
        
        # Add to queue with high priority
        self.attack_queue.insert(0, new_attack)
        self.logger.info("Generated new rule-based attack from successful passwords")
    
    def _generate_mask_attack(self, passwords: List[str]) -> None:
        """Generate a mask attack based on password patterns.
        
        Args:
            passwords: List of successful passwords
        """
        if not passwords:
            return
            
        # Analyze password patterns
        length_counts = {}
        for password in passwords:
            length = len(password)
            if length in length_counts:
                length_counts[length] += 1
            else:
                length_counts[length] = 1
        
        # Find most common password length
        most_common_length = max(length_counts.items(), key=lambda x: x[1])[0]
        
        # Create mask attack
        new_attack = {
            "type": "mask",
            "name": "Generated from password patterns",
            "mask": "?a" * most_common_length,  # Use all character types
            "priority": 85
        }
        
        # Add to queue with high priority
        self.attack_queue.insert(0, new_attack)
        self.logger.info(f"Generated new mask attack with length {most_common_length}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics.
        
        Returns:
            Dictionary with scheduler statistics
        """
        all_attacks_count = len(self.attack_queue) + len(self.completed_attacks)
        
        return {
            "total_attacks": all_attacks_count,
            "remaining_attacks": len(self.attack_queue),
            "completed_attacks": len(self.completed_attacks),
            "strategy": self.strategy,
            "exploration_rate": self.exploration_rate,
            "attack_stats": {
                attack_id: stats.get_stats() 
                for attack_id, stats in self.attack_stats.items()
            }
        }
    
    def reset(self) -> None:
        """Reset the scheduler to its initial state."""
        self.attack_queue = []
        self.attack_stats = {}
        self.completed_attacks = []
        self.attack_history = []
        self.initialized = False
