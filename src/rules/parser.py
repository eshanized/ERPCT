#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Rule Parser.
This module provides functionality for parsing and validating password mutation rules.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple, Set

from src.utils.logging import get_logger


class RuleParser:
    """Parser for password mutation rules."""
    
    # Rule command syntax validation regex patterns
    COMMAND_PATTERNS = {
        ':': r'^:$',                              # Do nothing
        'l': r'^l$',                              # Lowercase
        'u': r'^u$',                              # Uppercase
        'c': r'^c$',                              # Capitalize
        'r': r'^r$',                              # Reverse
        'd': r'^d$',                              # Duplicate
        's': r'^s[a-zA-Z0-9\W][a-zA-Z0-9\W]$',    # Substitute
        '@': r'^@[a-zA-Z0-9\W]$',                 # Purge
        '^': r'^\^[a-zA-Z0-9\W]$',                # Prepend
        '$': r'^\$[a-zA-Z0-9\W]',                 # Append
        '<': r'^<\d+$',                           # Truncate
        '>': r'^>\d+$',                           # Skip first N
    }
    
    def __init__(self, rules_directory: Optional[str] = None):
        """Initialize the rule parser.
        
        Args:
            rules_directory: Directory containing rule files (optional)
        """
        self.logger = get_logger(__name__)
        
        # Default rules directories - check both program dir and user home
        self.rules_directories = []
        
        # Program rules directory (from resources)
        if os.path.exists('resources/rules'):
            self.rules_directories.append(os.path.abspath('resources/rules'))
            
        # User rules directory
        user_rules_dir = os.path.join(os.path.expanduser('~'), '.erpct', 'rules')
        if os.path.exists(user_rules_dir):
            self.rules_directories.append(user_rules_dir)
            
        # Custom rules directory
        if rules_directory and os.path.exists(rules_directory):
            self.rules_directories.append(os.path.abspath(rules_directory))
            
        # Log known rules directories
        self.logger.debug(f"Rules directories: {self.rules_directories}")
        
    def find_rule_file(self, filename: str) -> Optional[str]:
        """Find a rule file by name in known rule directories.
        
        Args:
            filename: Rule filename to find
            
        Returns:
            Path to rule file or None if not found
        """
        # If full path is provided and exists, return it
        if os.path.exists(filename):
            return filename
            
        # If just a name is provided, look in rules directories
        for directory in self.rules_directories:
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                return filepath
                
        # If filename doesn't have .rule extension, try adding it
        if not filename.endswith('.rule'):
            return self.find_rule_file(f"{filename}.rule")
            
        self.logger.warning(f"Rule file not found: {filename}")
        return None
        
    def parse_rule_file(self, filename: str) -> List[str]:
        """Parse a rule file into a list of rule strings.
        
        Args:
            filename: Path to rule file
            
        Returns:
            List of rule strings
        """
        rules = []
        filepath = self.find_rule_file(filename)
        
        if not filepath:
            self.logger.error(f"Cannot parse rule file, not found: {filename}")
            return []
            
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        rules.append(line)
                        
            self.logger.debug(f"Parsed {len(rules)} rules from {filepath}")
            return rules
            
        except Exception as e:
            self.logger.error(f"Error parsing rule file {filepath}: {str(e)}")
            return []
            
    def validate_rule(self, rule: str) -> bool:
        """Validate a single rule for correct syntax.
        
        Args:
            rule: Rule string to validate
            
        Returns:
            True if rule syntax is valid, False otherwise
        """
        if not rule:
            return False
            
        # Simple validation for common commands
        if rule in [':', 'l', 'u', 'c', 'r', 'd']:
            return True
            
        # Parse compound rules
        i = 0
        while i < len(rule):
            valid_command = False
            
            for command, pattern in self.COMMAND_PATTERNS.items():
                # Check if the rule starts with this command
                if rule[i:].startswith(command):
                    # Extract the potential full command (with parameters)
                    j = i
                    while j < len(rule) and rule[j] != ' ':
                        j += 1
                    
                    cmd = rule[i:j]
                    
                    # Validate command syntax
                    if re.match(pattern, cmd):
                        i += len(cmd)
                        valid_command = True
                        break
            
            # Skip whitespace
            if rule[i:].startswith(' '):
                i += 1
                continue
                
            if not valid_command:
                self.logger.warning(f"Invalid rule syntax at position {i}: {rule}")
                return False
                
        return True
    
    def get_available_rule_files(self) -> Dict[str, str]:
        """Get a mapping of available rule filenames to full paths.
        
        Returns:
            Dictionary mapping rule names to full paths
        """
        rule_files = {}
        
        for directory in self.rules_directories:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                if filename.endswith('.rule'):
                    # Use full path for value, but just filename for key
                    filepath = os.path.join(directory, filename)
                    rule_files[filename] = filepath
                    
        return rule_files
