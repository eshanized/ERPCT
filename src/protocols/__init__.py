#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Protocol modules.
This package contains protocol implementations for different authentication methods.
"""

import os
import sys
import json
import importlib
from typing import Dict, List, Type, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

logger = get_logger(__name__)


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
        self._loaded = False
    
    def _register_builtin_protocols(self):
        """Register built-in protocol implementations."""
        # Import protocols directly to avoid issues with class name detection
        try:
            from src.protocols.ssh import SSH
            self._protocols["ssh"] = SSH
            logger.debug("Registered protocol: ssh")
        except Exception as e:
            logger.error(f"Error loading SSH protocol: {str(e)}")
        
        try:
            from src.protocols.ftp import FTPProtocol
            self._protocols["ftp"] = FTPProtocol
            logger.debug("Registered protocol: ftp")
        except Exception as e:
            logger.error(f"Error loading FTP protocol: {str(e)}")
            
        # Add HTTP Form protocol if it exists
        try:
            from src.protocols.http_form import HTTPFormProtocol
            self._protocols["http-form"] = HTTPFormProtocol
            logger.debug("Registered protocol: http-form")
        except ImportError:
            # Not an error, just not implemented yet
            pass
    
    def _load_protocol_module(self, module_name: str, class_name: str, protocol_name: str) -> None:
        """Load a protocol module and register it.
        
        Args:
            module_name: Name of the module to import
            class_name: Name of the protocol class in the module
            protocol_name: Name to register the protocol under
        """
        try:
            module = importlib.import_module(module_name)
            protocol_class = getattr(module, class_name)
            self._protocols[protocol_name] = protocol_class
            logger.debug(f"Registered protocol: {protocol_name}")
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load protocol {protocol_name}: {str(e)}")
            raise
    
    def _load_protocols(self) -> None:
        """Load protocols from the configuration file and built-in modules."""
        if self._loaded:
            return
            
        # First register built-in protocols
        self._register_builtin_protocols()
        
        # Then load from configuration file if it exists
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r') as f:
                    protocol_data = json.load(f)
                    
                for protocol in protocol_data.get('protocols', []):
                    try:
                        module_name = protocol['module']
                        class_name = protocol['class']
                        protocol_name = protocol['name']
                        self._load_protocol_module(module_name, class_name, protocol_name)
                    except (ImportError, AttributeError, KeyError) as e:
                        # Log the error but continue loading other protocols
                        logger.error(f"Error loading protocol {protocol.get('name', 'unknown')}: {str(e)}")
            except Exception as e:
                logger.error(f"Error loading protocol configuration: {str(e)}")
        
        self._loaded = True
    
    def get_protocol(self, name: str) -> Type[ProtocolBase]:
        """Get a protocol implementation by name.
        
        Args:
            name: Name of the protocol
            
        Returns:
            Protocol class
            
        Raises:
            ValueError: If protocol is not found
        """
        # Ensure protocols are loaded
        self._load_protocols()
        
        name = name.lower()
        if name not in self._protocols:
            raise ValueError(f"Protocol '{name}' not found")
        return self._protocols[name]
    
    def get_all_protocols(self) -> Dict[str, Type[ProtocolBase]]:
        """Get all registered protocols.
        
        Returns:
            Dictionary mapping protocol names to protocol classes
        """
        # Ensure protocols are loaded
        self._load_protocols()
        
        return self._protocols.copy()
    
    def register_protocol(self, name: str, protocol_class: Type[ProtocolBase]) -> None:
        """Register a new protocol implementation.
        
        Args:
            name: Name of the protocol
            protocol_class: Protocol class implementation
        """
        name = name.lower()
        self._protocols[name] = protocol_class
        logger.debug(f"Registered protocol: {name}")


# Create a singleton instance of the registry
protocol_registry = ProtocolRegistry()
