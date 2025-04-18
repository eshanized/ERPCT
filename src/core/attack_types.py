#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT attack types module.
This module defines the types of attacks that can be performed.
"""

from enum import Enum, auto
from typing import Dict, List, Any, Optional


class AttackType(Enum):
    """Enumeration of attack types supported by the application."""
    
    DICTIONARY = auto()
    BRUTE_FORCE = auto()
    HYBRID = auto()
    RULE_BASED = auto()
    MASK = auto()
    TARGETED = auto()
    DISTRIBUTED = auto()
    SMART = auto()
    
    @classmethod
    def get_description(cls, attack_type) -> str:
        """Get a description of the attack type.
        
        Args:
            attack_type: The attack type to describe
            
        Returns:
            Description string
        """
        descriptions = {
            cls.DICTIONARY: "Dictionary attack using wordlists",
            cls.BRUTE_FORCE: "Brute force attack trying all possible combinations",
            cls.HYBRID: "Hybrid attack combining dictionary and brute force methods",
            cls.RULE_BASED: "Rule-based attack applying transformation rules to passwords",
            cls.MASK: "Mask attack using specific character patterns",
            cls.TARGETED: "Targeted attack using intelligence about the target",
            cls.DISTRIBUTED: "Distributed attack across multiple systems",
            cls.SMART: "Smart attack using AI-based optimization"
        }
        return descriptions.get(attack_type, "Unknown attack type")
    
    @classmethod
    def get_config_template(cls, attack_type) -> Dict[str, Any]:
        """Get a configuration template for the attack type.
        
        Args:
            attack_type: The attack type to get a template for
            
        Returns:
            Configuration dictionary template
        """
        templates = {
            cls.DICTIONARY: {
                "wordlist": "",
                "username_list": "",
                "username_first": True
            },
            cls.BRUTE_FORCE: {
                "min_length": 1,
                "max_length": 8,
                "charset": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                "username_list": ""
            },
            cls.HYBRID: {
                "wordlist": "",
                "min_suffix": 1,
                "max_suffix": 4,
                "suffix_charset": "0123456789",
                "username_list": ""
            },
            cls.RULE_BASED: {
                "wordlist": "",
                "rules_file": "",
                "username_list": ""
            },
            cls.MASK: {
                "mask": "?a?a?a?a?a?a?a?a",  # 8 characters, any type
                "username_list": ""
            },
            cls.TARGETED: {
                "target_info": {},
                "custom_wordlist": True,
                "use_common_patterns": True,
                "username_list": ""
            },
            cls.DISTRIBUTED: {
                "nodes": [],
                "attack_type": "DICTIONARY",
                "wordlist": "",
                "username_list": ""
            },
            cls.SMART: {
                "learning_rate": 0.01,
                "initial_wordlist": "",
                "username_list": "",
                "optimization_metric": "success_rate"
            }
        }
        return templates.get(attack_type, {})
        
    @classmethod
    def get_business_constraints(cls, attack_type) -> Dict[str, Any]:
        """Get business-level constraints for the attack type.
        
        These constraints implement security policies and ethical guidelines.
        
        Args:
            attack_type: The attack type to get constraints for
            
        Returns:
            Dictionary of constraints
        """
        # Default to fairly restrictive limits
        default_constraints = {
            "max_attempts_per_account": 5,  # Default lockout threshold
            "delay_between_attempts": 2.0,  # Default delay in seconds
            "max_parallel_connections": 5,  # Default connection limit
            "requires_authorization": True,  # Require explicit authorization
            "allowed_environments": ["dev", "test", "authorized"],  # Where can this be used
            "cooldown_period": 60,  # Seconds to wait between attack sessions
            "max_runtime": 3600,  # Maximum runtime in seconds (1 hour)
            "log_level": "high",  # Detailed logging for accountability
            "allowed_hours": [(9, 17)],  # Business hours (9am-5pm)
        }
        
        constraints = {
            cls.DICTIONARY: {
                "max_attempts_per_account": 10,
                "max_runtime": 7200,  # 2 hours
                "max_parallel_connections": 10,
                "wordlist_max_size": 1000000,  # Limit wordlist size
            },
            cls.BRUTE_FORCE: {
                "max_attempts_per_account": 3,  # More restrictive for brute force
                "delay_between_attempts": 5.0,  # Longer delay
                "max_charset_length": 62,  # a-z, A-Z, 0-9
                "max_password_length": 8,  # Limit to reasonable lengths
                "max_runtime": 1800,  # 30 minutes
                "requires_executive_approval": True,  # Higher approval level
                "legal_disclaimer_required": True,  # Show legal warning
            },
            cls.HYBRID: {
                "max_attempts_per_account": 8,
                "wordlist_max_size": 500000,
                "max_suffix_length": 4,
            },
            cls.RULE_BASED: {
                "max_attempts_per_account": 15,
                "max_rules": 50,  # Limit number of rules
                "wordlist_max_size": 500000,
            },
            cls.MASK: {
                "max_attempts_per_account": 5,
                "max_mask_length": 10,
                "max_mask_combinations": 10000000,  # Limit total combinations
            },
            cls.TARGETED: {
                "max_attempts_per_account": 20,  # Higher for targeted attacks
                "requires_explicit_consent": True,
                "requires_documentation": True,  # Document justification
                "evidence_collection_required": True,  # Must store evidence
            },
            cls.DISTRIBUTED: {
                "max_nodes": 5,  # Limit distributed nodes
                "requires_executive_approval": True,
                "requires_coordinator": True,  # Designated coordinator
                "source_ip_restrictions": True,  # Only from approved IPs
                "max_parallel_connections": 3,  # Per node
            },
            cls.SMART: {
                "max_attempts_per_account": 25,
                "requires_monitoring": True,  # Continuous human monitoring
                "max_learning_iterations": 100,
                "data_retention_policy": "14d",  # Store data maximum 14 days
            }
        }
        
        # Merge with default constraints, allowing attack-specific overrides
        attack_constraints = constraints.get(attack_type, {})
        result = default_constraints.copy()
        result.update(attack_constraints)
        return result
        
    @classmethod
    def validate_configuration(cls, attack_type, config: Dict[str, Any]) -> List[str]:
        """Validate a configuration against business constraints.
        
        Args:
            attack_type: The attack type
            config: Configuration to validate
            
        Returns:
            List of validation error messages, empty if valid
        """
        errors = []
        constraints = cls.get_business_constraints(attack_type)
        
        # Common validations
        if "delay_between_attempts" in config:
            min_delay = constraints.get("delay_between_attempts", 0)
            if config["delay_between_attempts"] < min_delay:
                errors.append(f"Delay between attempts must be at least {min_delay} seconds")
                
        if "threads" in config:
            max_threads = constraints.get("max_parallel_connections", 1)
            if config["threads"] > max_threads:
                errors.append(f"Maximum allowed threads/connections is {max_threads}")
                
        # Attack-specific validations
        if attack_type == cls.BRUTE_FORCE:
            if "max_length" in config and config["max_length"] > constraints.get("max_password_length", 8):
                errors.append(f"Maximum password length is limited to {constraints['max_password_length']}")
                
            if "charset" in config and len(set(config["charset"])) > constraints.get("max_charset_length", 62):
                errors.append(f"Character set is limited to {constraints['max_charset_length']} unique characters")
                
        elif attack_type == cls.MASK:
            if "mask" in config and len(config["mask"]) > constraints.get("max_mask_length", 10):
                errors.append(f"Mask pattern cannot exceed {constraints['max_mask_length']} characters")
                
        # Check wordlist size constraints
        if "wordlist" in config and config["wordlist"]:
            try:
                import os
                wordlist_size = os.path.getsize(config["wordlist"])
                max_size = constraints.get("wordlist_max_size", 1000000) * 12  # Rough average line length
                if wordlist_size > max_size:
                    errors.append(f"Wordlist exceeds maximum allowed size of {max_size} bytes")
            except (OSError, IOError):
                errors.append("Could not access wordlist file")
                
        return errors
        
    @classmethod
    def estimate_resource_usage(cls, attack_type, config: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate resource usage for the attack configuration.
        
        Args:
            attack_type: The attack type
            config: Attack configuration
            
        Returns:
            Dictionary with estimated resources (memory, CPU, time, etc.)
        """
        resources = {
            "memory_mb": 50,  # Base memory usage
            "cpu_usage": 0.1,  # Base CPU usage (0.1 = 10%)
            "estimated_duration": 60,  # Base duration in seconds
            "network_traffic_mb": 1,  # Base network traffic
            "disk_usage_mb": 5,  # Base disk usage
        }
        
        # Adjust based on attack type
        if attack_type == cls.DICTIONARY:
            # Dictionary attacks scale with wordlist size and threads
            wordlist_size = cls._estimate_wordlist_size(config.get("wordlist", ""))
            threads = config.get("threads", 1)
            resources["memory_mb"] += wordlist_size * 0.1  # ~10% of wordlist in memory
            resources["cpu_usage"] += 0.05 * threads
            resources["estimated_duration"] = cls._estimate_dictionary_duration(config)
            resources["network_traffic_mb"] += 0.5 * threads * (resources["estimated_duration"] / 60)
        
        elif attack_type == cls.BRUTE_FORCE:
            # Brute force scales exponentially with length
            max_length = config.get("max_length", 8)
            charset_size = len(set(config.get("charset", "abcdefghijklmnopqrstuvwxyz0123456789")))
            resources["cpu_usage"] = 0.3 + (0.1 * max_length)
            resources["estimated_duration"] = cls._estimate_bruteforce_duration(charset_size, max_length)
            resources["memory_mb"] += 50 * max_length  # Rough estimate
        
        # Scale by threads
        threads = config.get("threads", 1)
        resources["memory_mb"] *= (0.5 + (0.5 * threads))  # Memory scales sublinearly with threads
        resources["disk_usage_mb"] *= threads
        
        return resources
    
    @classmethod
    def _estimate_wordlist_size(cls, wordlist_path: str) -> int:
        """Estimate the size of a wordlist in MB.
        
        Args:
            wordlist_path: Path to wordlist file
            
        Returns:
            Estimated size in MB
        """
        try:
            import os
            if os.path.exists(wordlist_path):
                return os.path.getsize(wordlist_path) / (1024 * 1024)
        except (OSError, IOError):
            pass
        return 10  # Default to 10MB if we can't determine
    
    @classmethod
    def _estimate_dictionary_duration(cls, config: Dict[str, Any]) -> int:
        """Estimate duration for dictionary attack in seconds.
        
        Args:
            config: Attack configuration
            
        Returns:
            Estimated duration in seconds
        """
        wordlist_path = config.get("wordlist", "")
        threads = config.get("threads", 1)
        delay = config.get("delay_between_attempts", 0)
        
        try:
            # Count lines in wordlist
            import os
            if os.path.exists(wordlist_path):
                with open(wordlist_path, 'r') as f:
                    line_count = sum(1 for _ in f)
                
                # Basic estimation formula accounting for parallelism and delay
                return (line_count / max(1, threads)) * (delay + 0.2)  # 0.2s base time per attempt
        except (OSError, IOError):
            pass
        
        return 600  # Default to 10 minutes if we can't determine
    
    @classmethod
    def _estimate_bruteforce_duration(cls, charset_size: int, max_length: int) -> int:
        """Estimate duration for brute force attack in seconds.
        
        Args:
            charset_size: Size of character set
            max_length: Maximum password length
            
        Returns:
            Estimated duration in seconds
        """
        # Calculate total combinations
        import math
        combinations = 0
        for length in range(1, max_length + 1):
            combinations += charset_size ** length
        
        # Assume 1000 attempts per second as baseline (adjusted by actual threads/delay)
        return combinations / 1000 