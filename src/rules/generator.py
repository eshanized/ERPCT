#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Rule Generator.
This module provides functionality for generating password mutation rules.
"""

import os
import random
from typing import List, Dict, Any, Optional, Tuple, Set

from src.utils.logging import get_logger
from src.rules.parser import RuleParser


class RuleGenerator:
    """Generator for password mutation rules."""
    
    # Basic rule components that can be combined
    CASE_MODIFIERS = [':', 'l', 'u', 'c']
    TRANSFORMATIONS = ['r', 'd']
    SUBSTITUTIONS = [
        'sa@', 'sa4', 'sb8', 'sb6', 'sc(', 'se3', 'sg6', 'sg9', 'sh#',
        'si1', 'si!', 'si|', 'sl1', 'sl|', 'so0', 'ss5', 'ss$', 'st7', 'st+'
    ]
    SUFFIX_PREFIX = ['^1', '^!', '^.', '^_', '$1', '$!', '$.', '$_', '$123', '$2023']
    TRUNCATIONS = ['<5', '<6', '<7', '<8', '>1', '>2']
    PURGES = ['@a', '@e', '@i', '@o', '@u', '@s']
    
    # Lists for generating more complex rules
    NUMBERS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    SPECIAL_CHARS = ['!', '@', '#', '$', '%', '&', '*', '?', '.', '-', '_', '+']
    YEARS = ['19', '20', '2000', '2020', '2021', '2022', '2023', '2024', '23', '24']
    DOMAINS = ['.com', '.net', '.org']
    WORDS = ['admin', 'pass', 'password', 'user', 'login', 'secure']
    
    def __init__(self):
        """Initialize the rule generator."""
        self.logger = get_logger(__name__)
        self.parser = RuleParser()
        
    def generate_basic_rules(self, count: int = 10) -> List[str]:
        """Generate a list of basic password mutation rules.
        
        Args:
            count: Number of rules to generate
            
        Returns:
            List of generated rules
        """
        rules = []
        
        # Add standard basic transformations
        rules.extend(self.CASE_MODIFIERS)
        rules.extend(self.TRANSFORMATIONS)
        
        # Add some single substitutions
        rules.extend(random.sample(self.SUBSTITUTIONS, min(count // 2, len(self.SUBSTITUTIONS))))
        
        # Add some suffix/prefix rules
        rules.extend(random.sample(self.SUFFIX_PREFIX, min(count // 2, len(self.SUFFIX_PREFIX))))
        
        # Fill up to count with random combinations if needed
        while len(rules) < count:
            case = random.choice(self.CASE_MODIFIERS)
            suffix = random.choice(self.SUFFIX_PREFIX)
            rules.append(f"{case}{suffix}")
            
        return rules[:count]
    
    def generate_advanced_rules(self, count: int = 20) -> List[str]:
        """Generate a list of advanced password mutation rules.
        
        Args:
            count: Number of rules to generate
            
        Returns:
            List of generated rules
        """
        rules = []
        
        # Add single substitutions
        rules.extend(random.sample(self.SUBSTITUTIONS, min(5, len(self.SUBSTITUTIONS))))
        
        # Add combined substitutions (2-3 combinations)
        for _ in range(min(5, count // 4)):
            subs = random.sample(self.SUBSTITUTIONS, random.randint(2, 3))
            rules.append(''.join(subs))
            
        # Add case modifiers with substitutions
        for _ in range(min(5, count // 4)):
            case = random.choice(self.CASE_MODIFIERS)
            sub = random.choice(self.SUBSTITUTIONS)
            rules.append(f"{case}{sub}")
            
        # Add number suffixes
        rules.extend([f"${n}" for n in random.sample(self.NUMBERS, min(3, len(self.NUMBERS)))])
        
        # Add year suffixes
        rules.extend([f"${y}" for y in random.sample(self.YEARS, min(3, len(self.YEARS)))])
            
        # Add special character suffixes
        rules.extend([f"${c}" for c in random.sample(self.SPECIAL_CHARS, min(3, len(self.SPECIAL_CHARS)))])
        
        # Add combined substitutions with suffixes
        for _ in range(min(5, count // 4)):
            subs = random.sample(self.SUBSTITUTIONS, random.randint(1, 2))
            suffix = f"${random.choice(self.NUMBERS)}"
            rules.append(''.join(subs) + suffix)
            
        # Fill up to count with more complex combinations
        while len(rules) < count:
            components = []
            
            # Maybe add case modifier
            if random.random() > 0.5:
                components.append(random.choice(self.CASE_MODIFIERS))
                
            # Maybe add substitutions
            if random.random() > 0.3:
                subs = random.sample(self.SUBSTITUTIONS, random.randint(1, 3))
                components.extend(subs)
                
            # Maybe add suffix/prefix
            if random.random() > 0.3:
                if random.random() > 0.5:
                    components.append(f"${random.choice(self.NUMBERS)}")
                else:
                    components.append(f"${random.choice(self.SPECIAL_CHARS)}")
                    
            # Only add if we have something
            if components:
                rules.append(''.join(components))
            
        return rules[:count]
    
    def create_custom_rule_file(self, filename: str, rules: List[str], description: str = "") -> bool:
        """Create a custom rule file with provided rules.
        
        Args:
            filename: Rule file to create
            rules: List of rules to include
            description: Description for rule file header
            
        Returns:
            True if file was created successfully, False otherwise
        """
        try:
            # If the file doesn't have a .rule extension, add it
            if not filename.endswith('.rule'):
                filename += '.rule'
                
            # Default user rule directory
            user_rules_dir = os.path.join(os.path.expanduser('~'), '.erpct', 'rules')
            os.makedirs(user_rules_dir, exist_ok=True)
            
            # Full path to file
            filepath = os.path.join(user_rules_dir, filename)
            
            # Write the rule file
            with open(filepath, 'w') as f:
                # Write header
                f.write(f"# ERPCT Generated Rule File: {filename}\n")
                if description:
                    f.write(f"# {description}\n")
                f.write("# Generated by ERPCT Rule Generator\n\n")
                
                # Write rules with categories
                categories = self._categorize_rules(rules)
                for category, category_rules in categories.items():
                    f.write(f"# {category}\n")
                    for rule in category_rules:
                        f.write(f"{rule}\n")
                    f.write("\n")
                    
            self.logger.info(f"Created rule file {filepath} with {len(rules)} rules")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating rule file: {str(e)}")
            return False
            
    def generate_rule_file(self, filename: str, complexity: str = "medium", 
                         count: int = 100, description: str = "") -> bool:
        """Generate a rule file with a specific complexity level.
        
        Args:
            filename: Rule file to create
            complexity: Complexity level ('basic', 'medium', 'advanced')
            count: Number of rules to generate
            description: Description for rule file header
            
        Returns:
            True if file was created successfully, False otherwise
        """
        try:
            rules = []
            
            if complexity == "basic":
                rules = self.generate_basic_rules(count)
                if not description:
                    description = "Basic password mutation rules for common transformations"
                    
            elif complexity == "advanced":
                rules = self.generate_advanced_rules(count)
                if not description:
                    description = "Advanced password mutation rules with complex transformations"
                    
            else:  # medium
                # Mix of basic and advanced
                basic_count = count // 3
                advanced_count = count - basic_count
                rules = self.generate_basic_rules(basic_count)
                rules.extend(self.generate_advanced_rules(advanced_count))
                if not description:
                    description = "Medium complexity password mutation rules"
                    
            return self.create_custom_rule_file(filename, rules, description)
            
        except Exception as e:
            self.logger.error(f"Error generating rule file: {str(e)}")
            return False
    
    def _categorize_rules(self, rules: List[str]) -> Dict[str, List[str]]:
        """Categorize rules by type for better organization in files.
        
        Args:
            rules: List of rules to categorize
            
        Returns:
            Dictionary mapping category names to lists of rules
        """
        categories = {
            "Basic transformations": [],
            "Character substitutions": [],
            "Prefixes": [],
            "Suffixes": [],
            "Combined transformations": [],
            "Advanced transformations": []
        }
        
        for rule in rules:
            # Basic transformations
            if rule in [':', 'l', 'u', 'c', 'r', 'd']:
                categories["Basic transformations"].append(rule)
                
            # Character substitutions
            elif rule.startswith('s') and len(rule) == 3:
                categories["Character substitutions"].append(rule)
                
            # Prefixes
            elif rule.startswith('^'):
                categories["Prefixes"].append(rule)
                
            # Suffixes
            elif rule.startswith('$'):
                categories["Suffixes"].append(rule)
                
            # Combined transformations (multiple operations)
            elif any(rule.startswith(c) for c in ['l', 'u', 'c']) and len(rule) > 1:
                categories["Combined transformations"].append(rule)
                
            # Advanced transformations (everything else)
            else:
                categories["Advanced transformations"].append(rule)
                
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
