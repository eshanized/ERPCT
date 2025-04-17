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