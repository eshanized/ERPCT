#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Protocol registry for ERPCT.
This module provides the protocol registry for registering and accessing protocols.
"""

import os
import sys
import importlib
import inspect
from typing import Dict, List, Type, Callable, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Dictionary of registered protocols: name -> class
_protocols: Dict[str, Type[ProtocolBase]] = {}


def register_protocol(name: str, protocol_class: Type[ProtocolBase]) -> None:
    """Register a protocol with the given name.
    
    Args:
        name: Protocol name (lowercase)
        protocol_class: Protocol class
    """
    global _protocols
    
    # Ensure name is lowercase for consistent lookup
    name = name.lower()
    
    # Check for duplicate
    if name in _protocols:
        logger.warning(f"Protocol {name} already registered, overwriting")
        
    # Register protocol
    _protocols[name] = protocol_class
    logger.debug(f"Registered protocol {name}")


def get_protocol(name: str) -> Type[ProtocolBase]:
    """Get a protocol by name.
    
    Args:
        name: Protocol name (case insensitive)
        
    Returns:
        Protocol class
        
    Raises:
        ValueError: If protocol is not found
    """
    global _protocols
    
    # Ensure name is lowercase for consistent lookup
    name = name.lower()
    
    # Check if protocol exists
    if name not in _protocols:
        raise ValueError(f"Protocol {name} not registered")
        
    # Return protocol class
    return _protocols[name]


def get_all_protocols() -> Dict[str, Type[ProtocolBase]]:
    """Get all registered protocols.
    
    Returns:
        Dictionary of protocol name -> protocol class
    """
    global _protocols
    return _protocols.copy()


def protocol_exists(name: str) -> bool:
    """Check if a protocol exists.
    
    Args:
        name: Protocol name (case insensitive)
        
    Returns:
        True if protocol exists, False otherwise
    """
    global _protocols
    
    # Ensure name is lowercase for consistent lookup
    name = name.lower()
    
    # Check if protocol exists
    return name in _protocols


def load_all_protocols() -> None:
    """Load all protocol modules in the protocols directory."""
    global _protocols
    
    # Get protocols directory
    protocol_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Initialize counters for logging
    total_protocols = 0
    loaded_protocols = 0
    
    # Get all Python files in the protocols directory
    for filename in os.listdir(protocol_dir):
        # Skip non-Python files and __init__.py
        if not filename.endswith('.py') or filename == '__init__.py' or filename == 'base.py':
            continue
            
        module_name = filename[:-3]
        total_protocols += 1
        
        try:
            # Import module
            module = importlib.import_module(f"src.protocols.{module_name}")
            
            # Find register_protocol function
            if hasattr(module, 'register_protocol'):
                # Call registration function
                module.register_protocol()
                loaded_protocols += 1
            else:
                # Alternative: auto-register if protocol class follows naming convention
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and issubclass(obj, ProtocolBase) and obj != ProtocolBase):
                        # Register class with its lowercase name
                        register_protocol(name.lower(), obj)
                        loaded_protocols += 1
                        break
                        
        except (ImportError, AttributeError, Exception) as e:
            # Log error but continue loading other protocols
            logger.error(f"Failed to load protocol {module_name}: {str(e)}")
    
    logger.info(f"Loaded {loaded_protocols} out of {total_protocols} protocols")


# Create aliases for common protocol names
def create_protocol_aliases() -> None:
    """Create aliases for common protocol names."""
    global _protocols
    
    # Define aliases as a dictionary of alias -> original
    aliases = {
        "https": "http",     # HTTPS is just HTTP with SSL
        "ftps": "ftp",       # FTPS is just FTP with SSL
        "pop3s": "pop3",     # POP3S is just POP3 with SSL
        "imaps": "imap",     # IMAPS is just IMAP with SSL
        "smtps": "smtp",     # SMTPS is just SMTP with SSL
    }
    
    # Create aliases
    for alias, original in aliases.items():
        if original in _protocols and alias not in _protocols:
            _protocols[alias] = _protocols[original]
            logger.debug(f"Created alias {alias} -> {original}")


# Load all protocols on module import
try:
    load_all_protocols()
    create_protocol_aliases()
except Exception as e:
    logger.error(f"Error during protocol initialization: {str(e)}")
    # Continue even if there's an error to at least have a partially functional system
