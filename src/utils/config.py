#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration utilities for ERPCT.
This module provides functions to manage configuration files and directories.
"""

import os
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Logger
logger = logging.getLogger(__name__)

def get_config_dir() -> str:
    """Get the configuration directory.
    
    Returns:
        Path to the configuration directory
    """
    # Try to use XDG_CONFIG_HOME first
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
    if xdg_config_home:
        config_dir = os.path.join(xdg_config_home, 'erpct')
    else:
        # Fall back to ~/.config
        config_dir = os.path.join(str(Path.home()), '.config', 'erpct')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating config directory: {str(e)}")
            # Fall back to a directory relative to the installation
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
    
    return config_dir

def get_data_dir() -> str:
    """Get the data directory.
    
    Returns:
        Path to the data directory
    """
    # Try to use XDG_DATA_HOME first
    xdg_data_home = os.environ.get('XDG_DATA_HOME')
    if xdg_data_home:
        data_dir = os.path.join(xdg_data_home, 'erpct')
    else:
        # Fall back to ~/.local/share
        data_dir = os.path.join(str(Path.home()), '.local', 'share', 'erpct')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating data directory: {str(e)}")
            # Fall back to a directory relative to the installation
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    
    return data_dir

def get_cache_dir() -> str:
    """Get the cache directory.
    
    Returns:
        Path to the cache directory
    """
    # Try to use XDG_CACHE_HOME first
    xdg_cache_home = os.environ.get('XDG_CACHE_HOME')
    if xdg_cache_home:
        cache_dir = os.path.join(xdg_cache_home, 'erpct')
    else:
        # Fall back to ~/.cache
        cache_dir = os.path.join(str(Path.home()), '.cache', 'erpct')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating cache directory: {str(e)}")
            # Fall back to a directory relative to the installation
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cache')
    
    return cache_dir

def load_config(config_name: str) -> Dict[str, Any]:
    """Load a configuration file.
    
    Args:
        config_name: Name of the configuration file (without path or extension)
        
    Returns:
        Configuration dictionary
    """
    config_path = os.path.join(get_config_dir(), f"{config_name}.json")
    
    # Check if file exists, create with defaults if it doesn't
    if not os.path.exists(config_path):
        # Check for default in the package
        default_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config',
            f"{config_name}.json"
        )
        
        if os.path.exists(default_path):
            # Copy default to user config
            try:
                with open(default_path, 'r') as f:
                    config = json.load(f)
                    
                save_config(config_name, config)
                return config
            except Exception as e:
                logger.error(f"Error loading default config: {str(e)}")
                return {}
        else:
            # No default, return empty config
            return {}
    
    # Load existing config
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config {config_name}: {str(e)}")
        return {}

def save_config(config_name: str, config: Dict[str, Any]) -> bool:
    """Save a configuration file.
    
    Args:
        config_name: Name of the configuration file (without path or extension)
        config: Configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    config_path = os.path.join(get_config_dir(), f"{config_name}.json")
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config {config_name}: {str(e)}")
        return False

def get_app_version() -> str:
    """Get the application version.
    
    Returns:
        Application version string
    """
    version_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'VERSION'
    )
    
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except Exception:
        return "unknown" 