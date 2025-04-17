#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File handling utilities for ERPCT.
This module provides utility functions for working with files and directories.
"""

import os
import json
import csv
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Iterator, TextIO

from src.utils.logging import get_logger

logger = get_logger(__name__)


def ensure_directory(directory: str) -> str:
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to ensure exists
        
    Returns:
        Absolute path to the directory
        
    Raises:
        OSError: If directory cannot be created
    """
    directory = os.path.abspath(directory)
    os.makedirs(directory, exist_ok=True)
    return directory


def safe_filename(filename: str) -> str:
    """Convert a string to a safe filename.
    
    Args:
        filename: Input string
        
    Returns:
        Safe filename string with invalid characters replaced
    """
    # Replace invalid filename characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        name = name[:255 - len(ext) - 1]
        filename = name + ext
        
    return filename


def load_json_file(filepath: str, default: Optional[Any] = None) -> Any:
    """Load JSON data from a file.
    
    Args:
        filepath: Path to the JSON file
        default: Default value to return if file doesn't exist or is invalid
        
    Returns:
        Parsed JSON data or default value
    """
    try:
        if not os.path.exists(filepath):
            return default
            
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {filepath}: {str(e)}")
        return default


def save_json_file(filepath: str, data: Any, indent: int = 4) -> bool:
    """Save data to a JSON file.
    
    Args:
        filepath: Path to save the JSON file
        data: Data to save
        indent: Number of spaces for indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Write to a temporary file first for atomic write
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8',
            dir=os.path.dirname(filepath), 
            delete=False
        ) as temp_file:
            json.dump(data, temp_file, indent=indent)
            temp_file_path = temp_file.name
            
        # Rename the temporary file to the target file
        shutil.move(temp_file_path, filepath)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file {filepath}: {str(e)}")
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        return False


def load_csv_file(filepath: str, has_header: bool = True) -> List[Dict[str, str]]:
    """Load data from a CSV file.
    
    Args:
        filepath: Path to the CSV file
        has_header: Whether the CSV file has a header row
        
    Returns:
        List of dictionaries if has_header=True, otherwise list of lists
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")
        
    result = []
    with open(filepath, 'r', encoding='utf-8', newline='') as f:
        if has_header:
            reader = csv.DictReader(f)
            for row in reader:
                result.append(dict(row))
        else:
            reader = csv.reader(f)
            for row in reader:
                result.append(row)
    
    return result


def save_csv_file(filepath: str, data: List[Union[Dict[str, Any], List[Any]]], 
                 headers: Optional[List[str]] = None) -> bool:
    """Save data to a CSV file.
    
    Args:
        filepath: Path to save the CSV file
        data: List of dictionaries or list of lists to save
        headers: List of column headers (optional if data is list of dicts)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            if data and isinstance(data[0], dict):
                # Use keys from first dict if headers not provided
                fieldnames = headers or list(data[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                writer.writerows(data)
        
        return True
    except Exception as e:
        logger.error(f"Error saving CSV file {filepath}: {str(e)}")
        return False


def atomic_write_file(filepath: str, content: str) -> bool:
    """Write content to a file atomically.
    
    Args:
        filepath: Path to the file
        content: Content to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Write to a temporary file first
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8',
            dir=os.path.dirname(filepath), 
            delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
            
        # Rename the temporary file to the target file
        shutil.move(temp_file_path, filepath)
        return True
    except Exception as e:
        logger.error(f"Error writing file {filepath}: {str(e)}")
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        return False
