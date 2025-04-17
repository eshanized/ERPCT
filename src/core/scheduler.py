#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT attack scheduler module.
This module implements scheduling and prioritization for password attacks.
"""

import copy
import time
from typing import Dict, List, Any, Optional, Tuple

from src.utils.logging import get_logger


class Scheduler:
    """Attack scheduler class.
    
    The Scheduler determines which attacks to run next based on various
    strategies and priorities. It can dynamically adjust attack strategies
    based on results from previous attacks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the scheduler with configuration.
        
        Args:
            config: Dictionary containing scheduler configuration parameters
        """
        self.logger = get_logger(__name__)
        self.config = config
        self.attack_queue = []
        self.completed_attacks = []
        self.current_attacks = []
        self.initialized = False
        
        # Extract scheduler-specific config
        self.max_concurrent_attacks = int(config.get("max_concurrent_attacks", 1))
        self.smart_scheduling = bool(config.get("smart_scheduling", False))
        self.priority_rules = config.get("priority_rules", [])
        
        # If smart scheduling is enabled, we'll use a more sophisticated
        # approach based on attack success rates and other metrics
        if self.smart_scheduling:
            self.attack_stats = {}
            try:
                from src.core.smart_scheduler import SmartScheduler
                self.smart_scheduler = SmartScheduler(config)
            except ImportError:
                self.logger.warning("Smart scheduler module not found, falling back to basic scheduling")
                self.smart_scheduling = False
    
    def initialize(self) -> None:
        """Initialize the scheduler and prepare initial attack queue."""
        if self.initialized:
            return
            
        self.logger.info("Initializing attack scheduler")
        
        # Get attack configurations from main config
        attack_configs = self.config.get("attacks", [])
        if not attack_configs:
            self.logger.warning("No attack configurations found in config")
            
        # Apply configuration transformations based on strategy
        self._build_initial_queue(attack_configs)
        
        # Initialize smart scheduler if enabled
        if self.smart_scheduling:
            try:
                self.smart_scheduler.initialize(copy.deepcopy(self.attack_queue))
            except Exception as e:
                self.logger.error(f"Error initializing smart scheduler: {str(e)}")
                self.smart_scheduling = False
        
        self.initialized = True
        self.logger.info(f"Scheduler initialized with {len(self.attack_queue)} attack configurations")
    
    def _build_initial_queue(self, attack_configs: List[Dict[str, Any]]) -> None:
        """Build initial attack queue from configuration.
        
        Args:
            attack_configs: List of attack configuration dictionaries
        """
        # First, copy all attacks
        queue = copy.deepcopy(attack_configs)
        
        # Apply priority rules if defined
        if self.priority_rules:
            queue = self._apply_priority_rules(queue)
        else:
            # Default ordering based on expected success rate and performance
            queue.sort(key=lambda x: self._get_attack_priority_score(x), reverse=True)
        
        self.attack_queue = queue
    
    def _apply_priority_rules(self, queue: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply priority rules to sort the attack queue.
        
        Args:
            queue: List of attack configuration dictionaries
            
        Returns:
            Sorted list of attack configurations
        """
        for rule in self.priority_rules:
            rule_type = rule.get("type", "")
            if rule_type == "order_by_type":
                # Order attacks by type according to specified order
                type_order = rule.get("order", [])
                if type_order:
                    def get_type_priority(attack):
                        attack_type = attack.get("type", "")
                        if attack_type in type_order:
                            return type_order.index(attack_type)
                        return len(type_order)  # Put unknown types at the end
                    
                    queue.sort(key=get_type_priority)
                    
            elif rule_type == "filter_by_type":
                # Filter attacks to include only specified types
                include_types = rule.get("include", [])
                if include_types:
                    queue = [a for a in queue if a.get("type", "") in include_types]
                    
            elif rule_type == "limit":
                # Limit number of attacks
                limit = rule.get("count", 0)
                if limit > 0 and limit < len(queue):
                    queue = queue[:limit]
        
        return queue
    
    def _get_attack_priority_score(self, attack_config: Dict[str, Any]) -> float:
        """Calculate priority score for an attack configuration.
        
        Args:
            attack_config: Attack configuration dictionary
            
        Returns:
            Priority score (higher is higher priority)
        """
        # Default scores by attack type
        type_scores = {
            "dictionary": 90,
            "hybrid": 80,
            "rule-based": 70,
            "mask": 60,
            "brute-force": 40
        }
        
        attack_type = attack_config.get("type", "")
        base_score = type_scores.get(attack_type, 50)
        
        # Adjust score based on other factors
        modifiers = 0
        
        # Dictionary attacks with common passwords should be higher priority
        if attack_type == "dictionary" and "common_passwords" in attack_config.get("dictionary_path", "").lower():
            modifiers += 10
            
        # Shorter password length ranges should be higher priority
        if "min_length" in attack_config and "max_length" in attack_config:
            length_range = attack_config["max_length"] - attack_config["min_length"]
            if length_range <= 2:
                modifiers += 5
            elif length_range >= 8:
                modifiers -= 10
                
        # User-defined priority
        modifiers += attack_config.get("priority", 0) * 5
        
        return base_score + modifiers
    
    def get_next_attacks(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get next attack configurations to run.
        
        Args:
            count: Number of attack configurations to return (default: max_concurrent_attacks)
            
        Returns:
            List of attack configuration dictionaries
        """
        if not self.initialized:
            self.initialize()
            
        if count is None:
            count = self.max_concurrent_attacks - len(self.current_attacks)
            
        # If smart scheduling is enabled, use it to get next attacks
        if self.smart_scheduling:
            try:
                return self.smart_scheduler.get_next_attacks(count)
            except Exception as e:
                self.logger.error(f"Error in smart scheduler: {str(e)}")
                # Fall back to basic scheduling
        
        # Basic scheduling: take the next 'count' attacks from the queue
        next_attacks = []
        while len(next_attacks) < count and self.attack_queue:
            next_attacks.append(self.attack_queue.pop(0))
            
        # Add to current attacks
        self.current_attacks.extend(next_attacks)
        
        return next_attacks
    
    def has_next_attack(self) -> bool:
        """Check if there are more attacks to schedule.
        
        Returns:
            True if there are more attacks in the queue
        """
        return len(self.attack_queue) > 0
    
    def get_estimated_remaining_attempts(self) -> int:
        """Get estimated number of password attempts remaining in queue.
        
        Returns:
            Estimated number of remaining password attempts
        """
        estimated = 0
        
        for attack_config in self.attack_queue:
            # Different attack types have different estimation methods
            attack_type = attack_config.get("type", "")
            
            if attack_type == "dictionary":
                # Estimate based on dictionary size
                dict_path = attack_config.get("dictionary_path", "")
                dict_size = self._estimate_dictionary_size(dict_path)
                transformations = len(attack_config.get("transformations", [])) or 1
                estimated += dict_size * transformations
                
            elif attack_type == "brute-force":
                # Estimate based on character set and length range
                charset = attack_config.get("charset", "")
                charset_size = len(charset) or 62  # Default to alphanumeric
                min_length = attack_config.get("min_length", 1)
                max_length = attack_config.get("max_length", 8)
                
                # Calculate sum of charset_size^length for each length in range
                for length in range(min_length, max_length + 1):
                    estimated += charset_size ** length
                    
            elif attack_type == "mask":
                # Estimate based on mask pattern
                mask = attack_config.get("mask", "")
                estimated += self._estimate_mask_attempts(mask)
                
            elif attack_type == "rule-based":
                # Estimate based on dictionary size and rule count
                dict_path = attack_config.get("dictionary_path", "")
                dict_size = self._estimate_dictionary_size(dict_path)
                rule_count = len(attack_config.get("rules", [])) or 1
                estimated += dict_size * rule_count
                
            elif attack_type == "hybrid":
                # Estimate based on specific hybrid strategy
                strategy = attack_config.get("strategy", {})
                estimated += strategy.get("estimated_count", 1000000)
                
            else:
                # Default estimate for unknown attack types
                estimated += 1000000
        
        return estimated
    
    def _estimate_dictionary_size(self, dict_path: str) -> int:
        """Estimate the size of a dictionary file.
        
        Args:
            dict_path: Path to dictionary file
            
        Returns:
            Estimated number of words in dictionary
        """
        # Try to get exact count if file exists
        try:
            with open(dict_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Count non-empty lines
                return sum(1 for line in f if line.strip())
        except:
            # Fall back to estimation based on file type
            if "rockyou" in dict_path.lower():
                return 14000000
            elif "common" in dict_path.lower():
                return 10000
            else:
                return 1000000  # Default estimate
    
    def _estimate_mask_attempts(self, mask: str) -> int:
        """Estimate number of attempts for a given mask pattern.
        
        Args:
            mask: Password mask pattern
            
        Returns:
            Estimated number of password attempts
        """
        if not mask:
            return 1000000
            
        # Standard hashcat mask character sets
        charsets = {
            '?l': 26,    # Lowercase letters
            '?u': 26,    # Uppercase letters
            '?d': 10,    # Digits
            '?s': 33,    # Special characters
            '?a': 95,    # All ASCII printable characters
            '?h': 16,    # Lowercase hex characters
            '?H': 16,    # Uppercase hex characters
        }
        
        # Parse mask and calculate permutations
        i = 0
        total = 1
        while i < len(mask):
            if mask[i] == '?' and i + 1 < len(mask):
                charset_key = mask[i:i+2]
                charset_size = charsets.get(charset_key, 1)
                total *= charset_size
                i += 2
            else:
                # Fixed character
                i += 1
                
        return total
    
    def mark_attack_completed(self, attack_config: Dict[str, Any], 
                              stats: Dict[str, Any]) -> None:
        """Mark an attack as completed with statistics.
        
        Args:
            attack_config: The attack configuration that completed
            stats: Statistics about the attack execution
        """
        if attack_config in self.current_attacks:
            self.current_attacks.remove(attack_config)
            
        # Add to completed attacks
        self.completed_attacks.append((attack_config, stats))
        
        # Update smart scheduler if enabled
        if self.smart_scheduling:
            try:
                self.smart_scheduler.update_attack_stats(attack_config, stats)
            except Exception as e:
                self.logger.error(f"Error updating smart scheduler: {str(e)}")
                
        # Potentially adjust queue based on results
        if stats.get("successful_attempts", 0) > 0:
            self._adjust_queue_based_on_success(attack_config, stats)
    
    def _adjust_queue_based_on_success(self, successful_config: Dict[str, Any],
                                      stats: Dict[str, Any]) -> None:
        """Adjust attack queue based on successful attack.
        
        Args:
            successful_config: Configuration of successful attack
            stats: Statistics about the successful attack
        """
        attack_type = successful_config.get("type", "")
        
        # Reorder attacks of same type to higher priority
        for i, attack in enumerate(self.attack_queue):
            if attack.get("type", "") == attack_type:
                # Move this attack higher in the queue
                if i > 0:
                    # Swap with an attack higher in the queue
                    swap_idx = max(0, i - 2)
                    self.attack_queue[swap_idx], self.attack_queue[i] = self.attack_queue[i], self.attack_queue[swap_idx]
        
        # For dictionary attacks, if we found successful passwords,
        # add a rule-based attack using those passwords as base
        if attack_type == "dictionary" and stats.get("successful_attempts", 0) > 0:
            successful_passwords = stats.get("successful_passwords", [])
            if successful_passwords:
                # Create a new rule-based attack using these passwords
                new_attack = {
                    "type": "rule-based",
                    "name": "Generated from successful passwords",
                    "base_words": successful_passwords,
                    "rules": ["c", "C", "t", "$1", "$2", "$3"],
                    "priority": 90
                }
                
                # Insert at the beginning of the queue
                self.attack_queue.insert(0, new_attack)
