#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Hybrid Strategy.
This module provides components for defining hybrid password attack strategies
that combine multiple attack methods.
"""

import os
import random
import itertools
from typing import List, Dict, Any, Optional, Iterator, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from src.utils.logging import get_logger


class HybridStrategy(ABC):
    """Abstract base class for hybrid attack strategies."""
    
    def __init__(self, name: str):
        """Initialize the strategy.
        
        Args:
            name: Name of the strategy
        """
        self.name = name
        self.logger = get_logger(f"{__name__}.{name}")
        self.estimated_count = 0
    
    @abstractmethod
    def generate(self) -> Iterator[str]:
        """Generate passwords based on the strategy.
        
        Returns:
            Iterator yielding passwords
        """
        pass


class DictionaryStrategy(HybridStrategy):
    """Strategy based on dictionary words."""
    
    def __init__(self, name: str, dictionary_path: str, 
                 transforms: Optional[List[Callable[[str], str]]] = None,
                 max_words: Optional[int] = None):
        """Initialize a dictionary-based strategy.
        
        Args:
            name: Name of the strategy
            dictionary_path: Path to dictionary file
            transforms: List of functions to transform words (optional)
            max_words: Maximum number of words to use (optional)
        
        Raises:
            FileNotFoundError: If dictionary file doesn't exist
        """
        super().__init__(name)
        
        if not os.path.exists(dictionary_path):
            raise FileNotFoundError(f"Dictionary file not found: {dictionary_path}")
            
        self.dictionary_path = dictionary_path
        self.transforms = transforms or []
        self.max_words = max_words
        
        # Calculate estimated count
        self._calculate_estimated_count()
    
    def _calculate_estimated_count(self) -> None:
        """Calculate estimated number of passwords to try."""
        try:
            with open(self.dictionary_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Count lines in dictionary
                if self.max_words:
                    count = min(sum(1 for _ in f), self.max_words)
                else:
                    count = sum(1 for _ in f)
                
            # Multiply by transforms (including original form)
            transform_count = max(1, len(self.transforms))
            self.estimated_count = count * transform_count
            
        except Exception as e:
            self.logger.error(f"Error calculating estimated count: {str(e)}")
            self.estimated_count = 1000  # Fallback estimate
    
    def generate(self) -> Iterator[str]:
        """Generate passwords from dictionary.
        
        Returns:
            Iterator yielding passwords
        """
        try:
            word_count = 0
            with open(self.dictionary_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    word = line.strip()
                    if not word:
                        continue
                        
                    # Yield original word
                    yield word
                    
                    # Apply transforms
                    for transform in self.transforms:
                        try:
                            transformed = transform(word)
                            if transformed != word:
                                yield transformed
                        except Exception as e:
                            self.logger.error(f"Transform error on word '{word}': {str(e)}")
                    
                    word_count += 1
                    if self.max_words and word_count >= self.max_words:
                        break
                        
        except Exception as e:
            self.logger.error(f"Error generating passwords: {str(e)}")


class BruteForceStrategy(HybridStrategy):
    """Strategy based on brute force character combinations."""
    
    def __init__(self, name: str, charset: str, min_length: int, max_length: int,
                 prefix: str = "", suffix: str = ""):
        """Initialize a brute force strategy.
        
        Args:
            name: Name of the strategy
            charset: String containing characters to use
            min_length: Minimum password length
            max_length: Maximum password length
            prefix: Fixed prefix for all generated passwords (optional)
            suffix: Fixed suffix for all generated passwords (optional)
            
        Raises:
            ValueError: If min_length > max_length or if charset is empty
        """
        super().__init__(name)
        
        if min_length > max_length:
            raise ValueError("min_length must be <= max_length")
            
        if not charset:
            raise ValueError("charset must not be empty")
            
        self.charset = charset
        self.min_length = min_length
        self.max_length = max_length
        self.prefix = prefix
        self.suffix = suffix
        
        # Calculate estimated count
        self._calculate_estimated_count()
    
    def _calculate_estimated_count(self) -> None:
        """Calculate estimated number of passwords to try."""
        try:
            charset_size = len(self.charset)
            count = 0
            
            # Sum up charset_size^length for each length from min to max
            for length in range(self.min_length, self.max_length + 1):
                count += charset_size ** length
                
            self.estimated_count = count
            
        except Exception as e:
            self.logger.error(f"Error calculating estimated count: {str(e)}")
            self.estimated_count = 1000000  # Fallback estimate
    
    def generate(self) -> Iterator[str]:
        """Generate passwords by brute force.
        
        Returns:
            Iterator yielding passwords
        """
        for length in range(self.min_length, self.max_length + 1):
            # Generate all combinations of charset with given length
            for combo in itertools.product(self.charset, repeat=length):
                password = self.prefix + ''.join(combo) + self.suffix
                yield password


class RuleBasedStrategy(HybridStrategy):
    """Strategy based on word mangling rules."""
    
    def __init__(self, name: str, words: List[str], rules: List[Callable[[str], str]]):
        """Initialize a rule-based strategy.
        
        Args:
            name: Name of the strategy
            words: List of base words to apply rules to
            rules: List of rule functions to apply to words
        """
        super().__init__(name)
        self.words = words
        self.rules = rules
        
        # Calculate estimated count
        self.estimated_count = len(words) * len(rules)
    
    def generate(self) -> Iterator[str]:
        """Generate passwords by applying rules to words.
        
        Returns:
            Iterator yielding passwords
        """
        for word in self.words:
            # Yield the original word
            yield word
            
            # Apply each rule
            for rule in self.rules:
                try:
                    mangled = rule(word)
                    if mangled != word:
                        yield mangled
                except Exception as e:
                    self.logger.error(f"Rule application error on word '{word}': {str(e)}")


class MaskStrategy(HybridStrategy):
    """Strategy based on password masks."""
    
    def __init__(self, name: str, mask: str, custom_charsets: Optional[Dict[str, str]] = None):
        """Initialize a mask-based strategy.
        
        Args:
            name: Name of the strategy
            mask: Password mask pattern (e.g., "?d?d?d?u?l?l?l?l")
            custom_charsets: Dictionary mapping custom charset symbols to charsets
            
        The mask uses the following built-in placeholders:
            ?d - Digit (0-9)
            ?l - Lowercase letter (a-z)
            ?u - Uppercase letter (A-Z)
            ?s - Special character (!@#$%^&*()_+-=[]{}|;:,.<>?/~`)
            ?a - All ASCII printable characters
            ?h - Hexadecimal digit (0-9, a-f)
            ?H - Uppercase hexadecimal digit (0-9, A-F)
            
        Custom charsets can be defined in the custom_charsets dictionary,
        with keys as single characters and values as strings containing
        the characters in the custom charset.
        """
        super().__init__(name)
        self.mask = mask
        
        # Define default charsets
        self.charsets = {
            'd': '0123456789',
            'l': 'abcdefghijklmnopqrstuvwxyz',
            'u': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            's': '!@#$%^&*()_+-=[]{}|;:,.<>?/~`',
            'a': ''.join(chr(i) for i in range(32, 127)),
            'h': '0123456789abcdef',
            'H': '0123456789ABCDEF'
        }
        
        # Add custom charsets
        if custom_charsets:
            self.charsets.update(custom_charsets)
            
        # Parse the mask
        self.parsed_mask = self._parse_mask()
        
        # Calculate estimated count
        self._calculate_estimated_count()
    
    def _parse_mask(self) -> List[str]:
        """Parse the mask pattern into a list of character sets.
        
        Returns:
            List of character sets corresponding to each position in the mask
        
        Raises:
            ValueError: If mask contains invalid placeholder
        """
        result = []
        i = 0
        
        while i < len(self.mask):
            if i + 1 < len(self.mask) and self.mask[i] == '?':
                placeholder = self.mask[i+1]
                if placeholder in self.charsets:
                    result.append(self.charsets[placeholder])
                    i += 2
                else:
                    raise ValueError(f"Invalid mask placeholder: ?{placeholder}")
            else:
                # Literal character
                result.append(self.mask[i])
                i += 1
                
        return result
    
    def _calculate_estimated_count(self) -> None:
        """Calculate estimated number of passwords to try."""
        try:
            count = 1
            for charset in self.parsed_mask:
                if len(charset) > 1:  # If it's a charset, not a literal
                    count *= len(charset)
                    
            self.estimated_count = count
            
        except Exception as e:
            self.logger.error(f"Error calculating estimated count: {str(e)}")
            self.estimated_count = 1000000  # Fallback estimate
    
    def generate(self) -> Iterator[str]:
        """Generate passwords according to the mask.
        
        Returns:
            Iterator yielding passwords
        """
        char_lists = []
        
        # Prepare character lists for product
        for charset in self.parsed_mask:
            if len(charset) == 1:
                # This is a literal character
                char_lists.append([charset])
            else:
                # This is a charset
                char_lists.append(list(charset))
        
        # Generate all combinations
        for combo in itertools.product(*char_lists):
            password = ''.join(combo)
            yield password


class CombinationStrategy(HybridStrategy):
    """Strategy combining multiple strategies."""
    
    def __init__(self, name: str, strategies: List[HybridStrategy]):
        """Initialize a combination strategy.
        
        Args:
            name: Name of the strategy
            strategies: List of strategies to combine
        """
        super().__init__(name)
        self.strategies = strategies
        
        # Calculate estimated count (sum of all strategies)
        self.estimated_count = sum(s.estimated_count for s in strategies)
    
    def generate(self) -> Iterator[str]:
        """Generate passwords from all strategies.
        
        Returns:
            Iterator yielding passwords
        """
        # Chain iterators from all strategies
        for strategy in self.strategies:
            try:
                for password in strategy.generate():
                    yield password
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy.name}: {str(e)}")


# Common transform functions for dictionary strategies
def capitalize_first(word: str) -> str:
    """Capitalize the first letter of the word."""
    return word.capitalize() if word else word

def all_uppercase(word: str) -> str:
    """Convert word to all uppercase."""
    return word.upper() if word else word

def all_lowercase(word: str) -> str:
    """Convert word to all lowercase."""
    return word.lower() if word else word

def leet_speak(word: str) -> str:
    """Convert word to leet speak."""
    leet_map = {
        'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7',
        'A': '4', 'E': '3', 'I': '1', 'O': '0', 'S': '5', 'T': '7'
    }
    return ''.join(leet_map.get(c, c) for c in word)

def append_digits(word: str) -> str:
    """Append common digit sequences."""
    suffixes = ['123', '1234', '12345', '123456', '2020', '2021', '2022', '2023', '0', '1', '12']
    return word + random.choice(suffixes)

def prepend_digits(word: str) -> str:
    """Prepend common digit sequences."""
    prefixes = ['123', '1234', '2020', '2021', '2022', '2023', '0', '1', '12']
    return random.choice(prefixes) + word

def reverse_word(word: str) -> str:
    """Reverse the word."""
    return word[::-1] if word else word

def toggle_case(word: str) -> str:
    """Toggle case of each character."""
    return ''.join(c.lower() if c.isupper() else c.upper() for c in word)


# Rule functions for rule-based strategies
def add_year(word: str) -> str:
    """Append a recent year to the word."""
    years = ['2020', '2021', '2022', '2023']
    return word + random.choice(years)

def add_special_chars(word: str) -> str:
    """Add special characters to the word."""
    special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '?']
    return word + random.choice(special_chars)

def add_number_sequence(word: str) -> str:
    """Add a number sequence to the word."""
    sequences = ['123', '1234', '12345', '123456', '654321', '54321']
    return word + random.choice(sequences)

def substitute_chars(word: str) -> str:
    """Substitute characters in the word."""
    subs = {'a': '@', 'e': '3', 'i': '!', 'o': '0', 's': '$'}
    return ''.join(subs.get(c.lower(), c) for c in word)

def capitalize_random(word: str) -> str:
    """Capitalize random letters in the word."""
    result = ""
    for c in word:
        if random.random() > 0.5:
            result += c.upper()
        else:
            result += c.lower()
    return result
