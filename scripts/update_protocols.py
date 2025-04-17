#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility script to update protocol implementations with the get_options method.
This script parses all protocol implementations and adds the get_options method
if it's missing, based on the data in get_config_schema or by analyzing the class.
"""

import os
import re
import sys
import glob
import inspect
import importlib.util

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from src.utils.logging import get_logger

logger = get_logger(__name__)

def add_get_options_method(file_path):
    """Add the get_options method to a protocol implementation file.
    
    Args:
        file_path: Path to the protocol implementation file
        
    Returns:
        bool: True if the file was modified, False otherwise
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Skip if already has get_options method
    if "def get_options" in content:
        logger.info(f"File {file_path} already has get_options method")
        return False
    
    # Extract class name
    class_match = re.search(r'class\s+(\w+)\s*\(', content)
    if not class_match:
        logger.warning(f"Could not find class definition in {file_path}")
        return False
    
    class_name = class_match.group(1)
    
    # Try to import the module to get properties from init method
    try:
        module_name = os.path.basename(file_path).replace('.py', '')
        module_path = f"src.protocols.{module_name}"
        
        # Try to dynamically import the module
        spec = importlib.util.find_spec(module_path)
        if spec is None:
            logger.warning(f"Could not find module {module_path}")
            # Fall back to pattern matching in file
            properties = extract_properties_from_file(content)
        else:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            class_obj = getattr(module, class_name)
            
            # Extract properties from class
            properties = extract_properties_from_class(class_obj, content)
    except Exception as e:
        logger.warning(f"Error importing module {module_path}: {str(e)}")
        # Fall back to pattern matching in file
        properties = extract_properties_from_file(content)
    
    if not properties:
        logger.warning(f"Could not extract properties for {file_path}")
        return False
    
    # Build get_options method
    get_options_method = [
        '    def get_options(self) -> Dict[str, Dict[str, Any]]:',
        '        """Return configurable options for this protocol.',
        '        ',
        '        Returns:',
        '            Dictionary of configuration options',
        '        """',
        '        return {'
    ]
    
    for prop_name, (prop_type, default, description) in properties.items():
        # Handle choices for select type
        if prop_type == 'select' and 'choices' in properties[prop_name]:
            choices = properties[prop_name]['choices']
            get_options_method.extend([
                f'            "{prop_name}": {{',
                f'                "type": "{prop_type}",',
                f'                "default": {default},',
                f'                "choices": {choices},',
                f'                "description": "{description}"',
                '            },'
            ])
        else:
            get_options_method.extend([
                f'            "{prop_name}": {{',
                f'                "type": "{prop_type}",',
                f'                "default": {default},',
                f'                "description": "{description}"',
                '            },'
            ])
    
    # Remove trailing comma from last property if there are properties
    if properties:
        get_options_method[-1] = get_options_method[-1][:-1]
    
    get_options_method.extend([
        '        }',
        '    '
    ])
    
    # Find insertion point - prefer before cleanup method
    cleanup_match = re.search(r'def\s+cleanup', content)
    name_match = re.search(r'@property\s+def\s+name', content)
    
    if cleanup_match:
        insert_pos = cleanup_match.start()
        # Find the beginning of the line
        line_start = content.rfind('\n', 0, insert_pos) + 1
        
        # Get content before and after insertion point
        content_before = content[:line_start]
        content_after = content[line_start:]
        
        # Insert get_options method
        new_content = content_before + '\n'.join(get_options_method) + '\n' + content_after
    elif name_match:
        # Find the end of the name method
        name_end = content.find('\n\n', name_match.end())
        if name_end == -1:
            name_end = content.find('\n', name_match.end())
            
        if name_end != -1:
            # Get content before and after insertion point
            content_before = content[:name_end + 1]
            content_after = content[name_end + 1:]
            
            # Insert get_options method
            new_content = content_before + '\n' + '\n'.join(get_options_method) + '\n\n' + content_after
        else:
            logger.warning(f"Could not find insertion point in {file_path}")
            return False
    else:
        # Try to find end of class
        register_match = re.search(r'# Register this protocol', content)
        if register_match:
            # Insert before registration
            insert_pos = register_match.start()
            line_start = content.rfind('\n\n', 0, insert_pos) + 1
            
            content_before = content[:line_start]
            content_after = content[line_start:]
            
            new_content = content_before + '\n'.join(get_options_method) + '\n\n' + content_after
        else:
            logger.warning(f"Could not find insertion point in {file_path}")
            return False
    
    # Write modified content back to file
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    logger.info(f"Added get_options method to {file_path}")
    return True

def extract_properties_from_class(class_obj, content):
    """Extract properties from the class object by analyzing the __init__ method.
    
    Args:
        class_obj: Class object to analyze
        content: File content as string
        
    Returns:
        Dictionary of property names and details
    """
    properties = {}
    
    # Try to extract from get_config_schema first
    schema_match = re.search(r'def\s+get_config_schema.*?return\s+({.*?})', content, re.DOTALL)
    if schema_match:
        schema_str = schema_match.group(1)
        properties_match = re.search(r'"properties"\s*:\s*({.*?})(?=\s*})', schema_str, re.DOTALL)
        
        if properties_match:
            properties_str = properties_match.group(1)
            
            # Extract property blocks
            property_blocks = re.finditer(r'"([^"]+)"\s*:\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})', properties_str, re.DOTALL)
            
            for prop_match in property_blocks:
                prop_name = prop_match.group(1)
                prop_block = prop_match.group(2)
                
                # Extract type, description, and default
                type_match = re.search(r'"type"\s*:\s*"([^"]+)"', prop_block)
                desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', prop_block)
                default_match = re.search(r'"default"\s*:\s*([\w\.]+|"[^"]+")', prop_block)
                
                prop_type = type_match.group(1) if type_match else "string"
                description = desc_match.group(1) if desc_match else ""
                
                # Map JSON schema types to our internal types
                if prop_type == "string":
                    prop_type = "string"
                elif prop_type == "integer":
                    prop_type = "integer"
                elif prop_type == "boolean":
                    prop_type = "boolean"
                
                # Check for enum which maps to select
                enum_match = re.search(r'"enum"\s*:\s*(\[[^\]]+\])', prop_block)
                if enum_match:
                    prop_type = "select"
                    properties[prop_name] = {"choices": enum_match.group(1)}
                
                if default_match:
                    default_val = default_match.group(1)
                    # Fix up strings vs non-strings
                    if default_val.startswith('"'):
                        default = default_val
                    elif prop_type == "boolean" and default_val in ["True", "False"]:
                        default = default_val
                    elif prop_type == "integer" or default_val.isdigit():
                        default = default_val
                    elif default_val == "self.default_port":
                        default = default_val
                    else:
                        default = f'"{default_val}"'
                else:
                    if prop_type == "string":
                        default = '""'
                    elif prop_type == "integer":
                        default = "0"
                    elif prop_type == "boolean":
                        default = "False"
                    else:
                        default = "None"
                
                properties[prop_name] = (prop_type, default, description)
            
            return properties
    
    # If we couldn't get from schema, try to extract from __init__
    # Look at self.* assignments in __init__
    init_match = re.search(r'def\s+__init__.*?config.*?\):(.*?)def', content, re.DOTALL)
    if init_match:
        init_code = init_match.group(1)
        
        # Look for config.get calls
        config_gets = re.finditer(r'self\.(\w+)\s*=.*?config\.get\(\s*["\']([^"\']+)["\'](?:\s*,\s*([^)]+))?', init_code)
        
        for match in config_gets:
            prop_var = match.group(1)
            prop_name = match.group(2)
            default_val = match.group(3) if match.group(3) else None
            
            # Infer type from default value or name
            if default_val:
                if default_val == "self.default_port" or re.match(r'\d+', default_val):
                    prop_type = "integer"
                    default = default_val
                elif default_val.lower() in ["true", "false"]:
                    prop_type = "boolean"
                    default = default_val.title()  # Capitalize for Python
                elif default_val.startswith('"') or default_val.startswith("'"):
                    prop_type = "string"
                    default = default_val
                else:
                    prop_type = "string"
                    default = f'"{default_val}"'
            else:
                # Best guess based on name
                if prop_name in ["port", "timeout"]:
                    prop_type = "integer"
                    default = "0"
                elif prop_name.startswith(("is_", "allow_", "use_", "verify_", "follow_")):
                    prop_type = "boolean"
                    default = "False"
                else:
                    prop_type = "string"
                    default = '""'
            
            # Description based on name
            description = f"{prop_name.replace('_', ' ').title()}"
            
            properties[prop_name] = (prop_type, default, description)
    
    return properties

def extract_properties_from_file(content):
    """Extract properties from file content by analyzing patterns.
    
    Args:
        content: File content as string
        
    Returns:
        Dictionary of property names and details
    """
    properties = {}
    
    # Try to find common configuration properties
    common_props = {
        "host": ("string", '""', "Hostname or IP address"),
        "port": ("integer", "self.default_port", "Port number"),
        "timeout": ("integer", "10", "Connection timeout in seconds"),
        "url": ("string", '""', "Target URL"),
        "username": ("string", '""', "Username"),
        "password": ("string", '""', "Password"),
        "database": ("string", '""', "Database name"),
        "verify_ssl": ("boolean", "True", "Verify SSL certificates")
    }
    
    # Check which common props are used in the file
    for prop, (prop_type, default, desc) in common_props.items():
        if re.search(rf'self\.{prop}\s*=', content) or re.search(rf'config\.get\(["\']({prop}|{prop}s)["\']', content):
            properties[prop] = (prop_type, default, desc)
    
    return properties

def main():
    """Main function to update all protocol implementations."""
    protocols_dir = os.path.join(project_root, 'src', 'protocols')
    
    # Get all protocol implementations
    protocol_files = glob.glob(os.path.join(protocols_dir, '*.py'))
    
    # Filter out __init__.py and base.py
    protocol_files = [f for f in protocol_files 
                      if not os.path.basename(f) in ['__init__.py', 'base.py']]
    
    num_updated = 0
    
    for file_path in protocol_files:
        try:
            if add_get_options_method(file_path):
                num_updated += 1
        except Exception as e:
            logger.error(f"Error updating {file_path}: {str(e)}")
    
    logger.info(f"Updated {num_updated} protocol files")

if __name__ == "__main__":
    main() 