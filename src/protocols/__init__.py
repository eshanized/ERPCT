#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Protocol modules.
This package contains protocol implementations for different authentication methods.
"""

import os
import json
import importlib
from typing import Dict, List, Type, Any

from src.protocols.base import ProtocolBase


class ProtocolRegistry:
    """Registry for protocol implementations."""
    
    def __init__(self):
        """Initialize the protocol registry."""
        self._protocols = {}
        self._config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "config", 
            "protocols.json"
        )
        self._load_protocols()
    
    def _load_protocols(self) -> None:
        """Load protocols from the configuration file."""
        if not os.path.exists(self._config_file):
            # If the file doesn't exist, we'll create it with default protocols later
            return
            
        try:
            with open(self._config_file, 'r') as f:
                protocol_data = json.load(f)
                
            for protocol in protocol_data.get('protocols', []):
                try:
                    module_name = protocol['module']
                    class_name = protocol['class']
                    module = importlib.import_module(module_name)
                    protocol_class = getattr(module, class_name)
                    self._protocols[protocol['name']] = protocol_class
                except (ImportError, AttributeError, KeyError) as e:
                    # Log the error but continue loading other protocols
                    print(f"Error loading protocol {protocol.get('name', 'unknown')}: {str(e)}")
        except Exception as e:
            print(f"Error loading protocol configuration: {str(e)}")
    
    def get_protocol(self, name: str) -> Type[ProtocolBase]:
        """Get a protocol implementation by name.
        
        Args:
            name: Name of the protocol
            
        Returns:
            Protocol class
            
        Raises:
            ValueError: If protocol is not found
        """
        if name not in self._protocols:
            raise ValueError(f"Protocol '{name}' not found")
        return self._protocols[name]
    
    def get_all_protocols(self) -> Dict[str, Type[ProtocolBase]]:
        """Get all registered protocols.
        
        Returns:
            Dictionary mapping protocol names to protocol classes
        """
        return self._protocols.copy()
    
    def register_protocol(self, name: str, protocol_class: Type[ProtocolBase]) -> None:
        """Register a new protocol implementation.
        
        Args:
            name: Name of the protocol
            protocol_class: Protocol class implementation
        """
        self._protocols[name] = protocol_class


# Create a singleton instance of the registry
protocol_registry = ProtocolRegistry()
