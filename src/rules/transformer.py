#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Rule Transformer.
This module provides functionality for applying password mutation rules to passwords.
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Callable

from src.utils.logging import get_logger
from src.rules.parser import RuleParser


class RuleTransformer:
    """Transformer for applying password mutation rules."""
    
    def __init__(self):
        """Initialize the rule transformer."""
        self.logger = get_logger(__name__)
        self.parser = RuleParser()
        
    def apply_rule_file(self, password: str, rule_file: str) -> List[str]:
        """Apply all rules from a rule file to a password.
        
        Args:
            password: Original password to transform
            rule_file: Path to rule file or rule file name
            
        Returns:
            List of transformed passwords
        """
        results = []
        rules = self.parser.parse_rule_file(rule_file)
        
        for rule in rules:
            transformed = apply_rule(password, rule)
            results.append(transformed)
            
        self.logger.debug(f"Applied {len(rules)} rules from file, generated {len(results)} candidates")
        return results
    
    def apply_rule_file_with_info(self, password: str, rule_file: str) -> List[Dict[str, str]]:
        """Apply rules from a file with detailed information for each transformation.
        
        Args:
            password: Original password to transform
            rule_file: Path to rule file or rule file name
            
        Returns:
            List of dictionaries with 'rule', 'password', and 'transformed' keys
        """
        results = []
        rules = self.parser.parse_rule_file(rule_file)
        
        for rule in rules:
            transformed = apply_rule(password, rule)
            results.append({
                'rule': rule,
                'password': password,
                'transformed': transformed
            })
            
        return results
    
    def apply_rules(self, password: str, rules: List[str]) -> List[str]:
        """Apply a list of rules to a password.
        
        Args:
            password: Original password to transform
            rules: List of rule strings to apply
            
        Returns:
            List of transformed passwords
        """
        results = []
        
        for rule in rules:
            transformed = apply_rule(password, rule)
            results.append(transformed)
            
        return results
    
    def apply_rules_to_wordlist(self, wordlist_file: str, rule_file: str) -> List[str]:
        """Apply rules from a file to every word in a wordlist.
        
        Args:
            wordlist_file: Path to wordlist file
            rule_file: Path to rule file
            
        Returns:
            List of transformed passwords
        """
        results = []
        rules = self.parser.parse_rule_file(rule_file)
        
        try:
            with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    password = line.strip()
                    if password:
                        for rule in rules:
                            transformed = apply_rule(password, rule)
                            if transformed:
                                results.append(transformed)
        except Exception as e:
            self.logger.error(f"Error processing wordlist: {str(e)}")
            
        return results


def apply_rule(password: str, rule: str) -> str:
    """Apply a single rule to a password.
    
    Args:
        password: Password to transform
        rule: Rule to apply
        
    Returns:
        Transformed password
    """
    result = password
    
    i = 0
    while i < len(rule):
        char = rule[i]
        
        # Process based on rule character
        if char == ':':
            # Do nothing
            pass
        elif char == 'l':
            # Lowercase
            result = result.lower()
        elif char == 'u':
            # Uppercase
            result = result.upper()
        elif char == 'c':
            # Capitalize
            if result:
                result = result[0].upper() + result[1:]
        elif char == 'r':
            # Reverse
            result = result[::-1]
        elif char == 'd':
            # Duplicate
            result = result + result
        elif char == 's' and i + 2 < len(rule):
            # Substitute
            a = rule[i+1]
            b = rule[i+2]
            result = result.replace(a, b)
            i += 2
        elif char == '@' and i + 1 < len(rule):
            # Purge character
            a = rule[i+1]
            result = result.replace(a, '')
            i += 1
        elif char == '^' and i + 1 < len(rule):
            # Prepend
            a = rule[i+1]
            result = a + result
            i += 1
        elif char == '$' and i + 1 < len(rule):
            # Append
            j = i + 1
            # Allow multi-character suffix like $2023 or $.com
            while j < len(rule) and rule[j] != ' ':
                j += 1
            suffix = rule[i+1:j]
            result = result + suffix
            i = j - 1
        elif char == '<' and i + 1 < len(rule):
            # Truncate
            j = i + 1
            while j < len(rule) and rule[j].isdigit():
                j += 1
            n = int(rule[i+1:j])
            result = result[:n]
            i = j - 1
        elif char == '>' and i + 1 < len(rule):
            # Skip first N
            j = i + 1
            while j < len(rule) and rule[j].isdigit():
                j += 1
            n = int(rule[i+1:j])
            result = result[n:]
            i = j - 1
        
        # Skip whitespace
        if i + 1 < len(rule) and rule[i+1] == ' ':
            i += 1
            
        i += 1
    
    return result


def apply_rules(password: str, rules: List[str]) -> List[str]:
    """Apply multiple rules to a password.
    
    Args:
        password: Password to transform
        rules: List of rules to apply
        
    Returns:
        List of transformed passwords
    """
    results = []
    
    for rule in rules:
        transformed = apply_rule(password, rule)
        results.append(transformed)
    
    return results
