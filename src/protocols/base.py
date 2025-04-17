#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base protocol implementation for ERPCT.
This module provides the abstract base class that all protocol modules must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any


class ProtocolBase(ABC):
    """Base class for all protocol implementations."""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """Initialize the protocol with configuration.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        pass
    
    @abstractmethod
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test a single username/password combination.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Tuple containing (success_bool, optional_message)
                success_bool: True if authentication succeeded, False otherwise
                optional_message: Additional information or error message
        """
        pass
    
    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for this protocol.
        
        Used by the UI to generate protocol-specific configuration fields.
        
        Returns:
            JSON schema for protocol configuration
        """
        pass
        
    @property
    @abstractmethod
    def default_port(self) -> int:
        """Return the default port for this protocol.
        
        Returns:
            Default port number as integer
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this protocol.
        
        Returns:
            Protocol name as string
        """
        pass
    
    @property
    def supports_username_enumeration(self) -> bool:
        """Whether this protocol supports username enumeration.
        
        Returns:
            True if the protocol can enumerate usernames, False otherwise
        """
        return False
    
    def cleanup(self) -> None:
        """Clean up any resources. Called when attack is complete."""
        pass
