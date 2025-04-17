#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Password Combiner.
This module provides components for combining different password sources
in hybrid attacks.
"""

import os
import itertools
from typing import List, Iterator, Dict, Any, Optional, Callable, Tuple

from src.utils.logging import get_logger


class PasswordCombiner:
    """Class for combining different password sources in various ways."""
    
    def __init__(self):
        """Initialize the password combiner."""
        self.logger = get_logger(__name__)
        self.sources = []
        self.current_index = 0
        self.combination_method = None
    
    def add_source(self, source_generator: Iterator[str]) -> None:
        """Add a password source generator.
        
        Args:
            source_generator: Iterator that yields passwords
        """
        self.sources.append(source_generator)
    
    def set_method(self, method: str) -> None:
        """Set the combination method.
        
        Args:
            method: Method name: 'chain', 'cartesian', 'zip', 'interleave'
        
        Raises:
            ValueError: If the method is unknown
        """
        if method not in ('chain', 'cartesian', 'zip', 'interleave'):
            raise ValueError(f"Unknown combination method: {method}")
        
        self.combination_method = method
    
    def clear(self) -> None:
        """Clear all sources and reset the combiner."""
        self.sources = []
        self.current_index = 0
        self.combination_method = None
    
    def combine(self, limit: Optional[int] = None) -> Iterator[str]:
        """Combine the password sources according to the set method.
        
        Args:
            limit: Optional limit on number of passwords to generate
        
        Returns:
            Iterator yielding combined passwords
        
        Raises:
            ValueError: If no sources are added or no method is set
        """
        if not self.sources:
            raise ValueError("No password sources have been added")
        
        if not self.combination_method:
            raise ValueError("No combination method has been set")
        
        count = 0
        max_count = limit if limit is not None else float('inf')
        
        try:
            if self.combination_method == 'chain':
                # Simply chain all sources one after another
                for source in self.sources:
                    for password in source:
                        yield password
                        count += 1
                        if count >= max_count:
                            return
            
            elif self.combination_method == 'cartesian':
                # Generate all combinations from all sources
                # This requires materializing the iterators into lists
                password_lists = [list(source) for source in self.sources]
                
                for combination in itertools.product(*password_lists):
                    yield ''.join(combination)
                    count += 1
                    if count >= max_count:
                        return
            
            elif self.combination_method == 'zip':
                # Combine corresponding elements from each source
                # Stops when the shortest source is exhausted
                password_lists = [list(source) for source in self.sources]
                min_length = min(len(passwords) for passwords in password_lists)
                
                for i in range(min_length):
                    result = ''.join(passwords[i] for passwords in password_lists)
                    yield result
                    count += 1
                    if count >= max_count:
                        return
            
            elif self.combination_method == 'interleave':
                # Interleave passwords from all sources
                # Store generators and consume one from each source in a round-robin fashion
                sources_copy = list(self.sources)
                while sources_copy:
                    for i in range(len(sources_copy) - 1, -1, -1):
                        try:
                            password = next(sources_copy[i])
                            yield password
                            count += 1
                            if count >= max_count:
                                return
                        except StopIteration:
                            # Remove exhausted sources
                            sources_copy.pop(i)
                
        except Exception as e:
            self.logger.error(f"Error in password combination: {str(e)}")
            raise


class FilteredPasswordCombiner(PasswordCombiner):
    """Extended password combiner with filtering capabilities."""
    
    def __init__(self):
        """Initialize the filtered password combiner."""
        super().__init__()
        self.filters = []
    
    def add_filter(self, filter_func: Callable[[str], bool]) -> None:
        """Add a filter function for passwords.
        
        Args:
            filter_func: Function that takes a password and returns True if it should be included
        """
        self.filters.append(filter_func)
    
    def combine(self, limit: Optional[int] = None) -> Iterator[str]:
        """Combine the password sources with filtering.
        
        Args:
            limit: Optional limit on number of passwords to generate
        
        Returns:
            Iterator yielding filtered, combined passwords
        """
        count = 0
        max_count = limit if limit is not None else float('inf')
        
        # Get the base generator from the parent class
        base_generator = super().combine(None)  # No limit, we'll handle it here
        
        try:
            for password in base_generator:
                # Apply all filters
                if all(f(password) for f in self.filters):
                    yield password
                    count += 1
                    if count >= max_count:
                        return
        except Exception as e:
            self.logger.error(f"Error in filtered password combination: {str(e)}")
            raise
    
    def clear(self) -> None:
        """Clear all sources, filters, and reset the combiner."""
        super().clear()
        self.filters = []


class CustomCombiner(PasswordCombiner):
    """Password combiner with custom combination logic."""
    
    def __init__(self):
        """Initialize the custom combiner."""
        super().__init__()
        self.combination_func = None
    
    def set_custom_method(self, func: Callable[[List[Iterator[str]]], Iterator[str]]) -> None:
        """Set a custom combination function.
        
        Args:
            func: Function that takes a list of password generators and returns an iterator of combined passwords
        """
        self.combination_func = func
        self.combination_method = 'custom'
    
    def combine(self, limit: Optional[int] = None) -> Iterator[str]:
        """Combine the password sources using the custom function.
        
        Args:
            limit: Optional limit on number of passwords to generate
        
        Returns:
            Iterator yielding combined passwords
        
        Raises:
            ValueError: If no custom combination function is set
        """
        if self.combination_method != 'custom' or self.combination_func is None:
            raise ValueError("No custom combination function has been set")
        
        count = 0
        max_count = limit if limit is not None else float('inf')
        
        try:
            # Use the custom combination function
            custom_generator = self.combination_func(self.sources)
            
            for password in custom_generator:
                yield password
                count += 1
                if count >= max_count:
                    return
        except Exception as e:
            self.logger.error(f"Error in custom password combination: {str(e)}")
            raise
