#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom protocol implementation for ERPCT.
This module provides a flexible framework for defining custom protocol tests.
"""

import importlib
import json
import os
import socket
import subprocess
import time
from typing import Dict, List, Optional, Tuple, Any, Callable

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger


class Custom(ProtocolBase):
    """Custom protocol implementation for password attacks.
    
    This allows for flexible protocol testing using:
    1. Python script with a test_auth(username, password) function
    2. External command execution with username and password parameters
    3. JSON schema for defining request/response validation
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Custom protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Extract common configuration
        self.name_value = config.get("name", "Custom Protocol")
        self.host = config.get("host", "")
        self.port = int(config.get("port", 0))
        self.timeout = config.get("timeout", 10)
        
        # Determine method type
        self.method_type = config.get("method_type", "script").lower()  # script, command, json
        
        # Script-specific configuration
        if self.method_type == "script":
            self.script_path = config.get("script_path", "")
            self.function_name = config.get("function_name", "test_auth")
            self.script_module = None
            self.script_function = None
            
            if not self.script_path:
                raise ValueError("Script path must be specified for custom script method")
                
            # Load script and function
            self._load_script()
            
        # Command-specific configuration
        elif self.method_type == "command":
            self.command = config.get("command", "")
            self.username_placeholder = config.get("username_placeholder", "{username}")
            self.password_placeholder = config.get("password_placeholder", "{password}")
            self.success_exit_code = config.get("success_exit_code", 0)
            self.success_output = config.get("success_output", "")
            self.failure_output = config.get("failure_output", "")
            
            if not self.command:
                raise ValueError("Command must be specified for custom command method")
                
        # JSON-specific configuration
        elif self.method_type == "json":
            self.request_template = config.get("request_template", {})
            self.success_criteria = config.get("success_criteria", {})
            self.failure_criteria = config.get("failure_criteria", {})
            self.username_jsonpath = config.get("username_jsonpath", "$.username")
            self.password_jsonpath = config.get("password_jsonpath", "$.password")
            self.headers = config.get("headers", {"Content-Type": "application/json"})
            
            if not self.request_template:
                raise ValueError("Request template must be specified for custom JSON method")
                
            # Check if requests is available for JSON method
            try:
                import requests
                self.requests_available = True
            except ImportError:
                self.logger.error("requests package is required for JSON method but not installed")
                self.requests_available = False
                raise ImportError("requests package is required for custom JSON method")
        else:
            raise ValueError(f"Unsupported method type: {self.method_type}")
    
    def _load_script(self) -> None:
        """Load the custom Python script and extract the authentication function."""
        if not os.path.isfile(self.script_path):
            raise FileNotFoundError(f"Script file not found: {self.script_path}")
            
        try:
            # Add script directory to path if needed
            script_dir = os.path.dirname(os.path.abspath(self.script_path))
            script_name = os.path.basename(self.script_path)
            
            if script_name.endswith('.py'):
                script_name = script_name[:-3]
                
            # Try to import from path
            spec = importlib.util.spec_from_file_location(script_name, self.script_path)
            if spec and spec.loader:
                self.script_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(self.script_module)
            else:
                # Fallback to importlib if spec_from_file_location fails
                sys_path_modified = False
                if script_dir not in importlib.sys.path:
                    importlib.sys.path.insert(0, script_dir)
                    sys_path_modified = True
                    
                try:
                    self.script_module = importlib.import_module(script_name)
                finally:
                    # Clean up sys.path if we modified it
                    if sys_path_modified:
                        importlib.sys.path.remove(script_dir)
            
            # Get the function
            if not hasattr(self.script_module, self.function_name):
                raise AttributeError(f"Function '{self.function_name}' not found in script {self.script_path}")
                
            self.script_function = getattr(self.script_module, self.function_name)
            
            # Check if it's callable
            if not callable(self.script_function):
                raise TypeError(f"'{self.function_name}' is not a callable function in {self.script_path}")
                
        except (ImportError, SyntaxError) as e:
            error_msg = f"Error loading script: {str(e)}"
            self.logger.error(error_msg)
            raise ImportError(error_msg)
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test authentication with the given credentials using the custom method.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Tuple containing (success_bool, optional_message)
                success_bool: True if authentication succeeded, False otherwise
                optional_message: Additional information or error message
        """
        if not username:
            return False, "Username must not be empty"
            
        try:
            # Choose method based on configuration
            if self.method_type == "script":
                return self._test_with_script(username, password)
            elif self.method_type == "command":
                return self._test_with_command(username, password)
            elif self.method_type == "json":
                return self._test_with_json(username, password)
            else:
                return False, f"Unsupported method type: {self.method_type}"
                
        except Exception as e:
            # Catch all other exceptions
            error_msg = f"Unexpected error in custom protocol: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _test_with_script(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test authentication using a custom Python script.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            # Check if script and function are loaded
            if not self.script_function:
                self._load_script()
                
            # Call the script function with username and password
            result = self.script_function(
                username=username,
                password=password,
                host=self.host,
                port=self.port,
                timeout=self.timeout,
                config=self.config
            )
            
            # Handle different return types
            if isinstance(result, bool):
                # Boolean result
                if result:
                    self.logger.info(f"Custom script authentication successful for user {username}")
                    return True, None
                else:
                    return False, "Authentication failed"
            elif isinstance(result, tuple) and len(result) == 2:
                # Tuple containing (success_bool, message)
                success, message = result
                if success:
                    self.logger.info(f"Custom script authentication successful for user {username}")
                return success, message
            else:
                # Unexpected return type
                error_msg = f"Invalid return type from script function: {type(result)}"
                self.logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            # Script execution error
            error_msg = f"Script execution error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _test_with_command(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test authentication using a custom command.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            # Replace placeholders in command
            cmd = self.command
            cmd = cmd.replace(self.username_placeholder, username)
            cmd = cmd.replace(self.password_placeholder, password)
            
            # Execute command
            process = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # Get output and exit code
            stdout = process.stdout
            stderr = process.stderr
            exit_code = process.returncode
            
            # Check success based on exit code
            if exit_code == self.success_exit_code:
                # If success_output is specified, check if it's in stdout
                if self.success_output and self.success_output not in stdout:
                    return False, f"Command exit code indicates success, but success output not found"
                
                self.logger.info(f"Custom command authentication successful for user {username}")
                return True, None
            else:
                # Check failure output if specified
                if self.failure_output and self.failure_output in stderr:
                    return False, f"Authentication failed: {stderr}"
                
                return False, f"Command failed with exit code {exit_code}: {stderr}"
                
        except subprocess.TimeoutExpired:
            # Command timed out
            return False, f"Command timed out after {self.timeout} seconds"
            
        except subprocess.SubprocessError as e:
            # Command execution error
            error_msg = f"Command execution error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _test_with_json(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test authentication using a JSON request/response model.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            import requests
            from jsonpath_ng import parse
            
            # Deep copy the request template to avoid modifying the original
            request_data = json.loads(json.dumps(self.request_template))
            
            # Set username and password in request using JSONPath
            username_expr = parse(self.username_jsonpath)
            password_expr = parse(self.password_jsonpath)
            
            # Apply the JSONPath expressions to set values
            request_data = username_expr.update(request_data, username)
            request_data = password_expr.update(request_data, password)
            
            # Make request
            response = requests.post(
                url=f"http://{self.host}:{self.port}" if self.host and self.port else self.config.get("url", ""),
                json=request_data,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                # Not a JSON response
                response_data = {"text": response.text}
            
            # Check success criteria
            if self._check_criteria(response_data, self.success_criteria):
                self.logger.info(f"Custom JSON authentication successful for user {username}")
                return True, None
                
            # Check failure criteria
            if self._check_criteria(response_data, self.failure_criteria):
                return False, "Authentication failed according to failure criteria"
                
            # If no criteria matched, use status code
            if 200 <= response.status_code < 300:
                self.logger.info(f"Custom JSON authentication successful for user {username} (based on status code)")
                return True, None
            else:
                return False, f"Authentication failed with status code {response.status_code}"
                
        except requests.RequestException as e:
            # Request error
            error_msg = f"Request error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except ImportError:
            # Missing dependencies
            error_msg = "Missing dependencies for JSON method: requests and jsonpath-ng are required"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _check_criteria(self, data: Any, criteria: Dict[str, Any]) -> bool:
        """Check if the response data matches the specified criteria.
        
        Args:
            data: Response data to check
            criteria: Criteria to match against
            
        Returns:
            True if the data matches all criteria, False otherwise
        """
        if not criteria:
            return False
            
        try:
            from jsonpath_ng import parse
            
            # Check each criterion
            for path, expected_value in criteria.items():
                # Parse JSONPath expression
                jsonpath_expr = parse(path)
                
                # Find matches
                matches = jsonpath_expr.find(data)
                
                # No matches found
                if not matches:
                    return False
                    
                # Check if any match equals the expected value
                if not any(match.value == expected_value for match in matches):
                    return False
                    
            # All criteria matched
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking criteria: {str(e)}")
            return False
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for Custom protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        common_props = {
            "name": {
                "type": "string",
                "title": "Protocol Name",
                "description": "Name of this custom protocol",
                "default": "Custom Protocol"
            },
            "host": {
                "type": "string",
                "title": "Host",
                "description": "Hostname or IP address (optional)"
            },
            "port": {
                "type": "integer",
                "title": "Port",
                "description": "Port number (optional)"
            },
            "timeout": {
                "type": "integer",
                "title": "Timeout",
                "description": "Timeout in seconds",
                "default": 10
            },
            "method_type": {
                "type": "string",
                "title": "Method Type",
                "description": "Type of custom authentication method",
                "enum": ["script", "command", "json"],
                "default": "script"
            }
        }
        
        script_props = {
            "script_path": {
                "type": "string",
                "title": "Script Path",
                "description": "Path to Python script file"
            },
            "function_name": {
                "type": "string",
                "title": "Function Name",
                "description": "Name of the authentication test function in the script",
                "default": "test_auth"
            }
        }
        
        command_props = {
            "command": {
                "type": "string",
                "title": "Command",
                "description": "Command to execute for authentication test"
            },
            "username_placeholder": {
                "type": "string",
                "title": "Username Placeholder",
                "description": "Placeholder for username in command",
                "default": "{username}"
            },
            "password_placeholder": {
                "type": "string",
                "title": "Password Placeholder",
                "description": "Placeholder for password in command",
                "default": "{password}"
            },
            "success_exit_code": {
                "type": "integer",
                "title": "Success Exit Code",
                "description": "Exit code indicating successful authentication",
                "default": 0
            },
            "success_output": {
                "type": "string",
                "title": "Success Output",
                "description": "String in stdout indicating successful authentication"
            },
            "failure_output": {
                "type": "string",
                "title": "Failure Output",
                "description": "String in stderr indicating failed authentication"
            }
        }
        
        json_props = {
            "request_template": {
                "type": "object",
                "title": "Request Template",
                "description": "JSON template for authentication request"
            },
            "url": {
                "type": "string",
                "title": "URL",
                "description": "URL for the authentication endpoint"
            },
            "username_jsonpath": {
                "type": "string",
                "title": "Username JSONPath",
                "description": "JSONPath expression for setting username in request",
                "default": "$.username"
            },
            "password_jsonpath": {
                "type": "string",
                "title": "Password JSONPath",
                "description": "JSONPath expression for setting password in request",
                "default": "$.password"
            },
            "headers": {
                "type": "object",
                "title": "Headers",
                "description": "HTTP headers for the request",
                "default": {"Content-Type": "application/json"}
            },
            "success_criteria": {
                "type": "object",
                "title": "Success Criteria",
                "description": "JSONPath expressions and values indicating successful authentication"
            },
            "failure_criteria": {
                "type": "object",
                "title": "Failure Criteria",
                "description": "JSONPath expressions and values indicating failed authentication"
            }
        }
        
        # Create schema with appropriate properties
        schema = {
            "type": "object",
            "properties": common_props,
            "required": ["method_type"],
            "dependencies": {
                "method_type": {
                    "oneOf": [
                        {
                            "properties": {
                                "method_type": {"enum": ["script"]},
                                **script_props
                            },
                            "required": ["script_path"]
                        },
                        {
                            "properties": {
                                "method_type": {"enum": ["command"]},
                                **command_props
                            },
                            "required": ["command"]
                        },
                        {
                            "properties": {
                                "method_type": {"enum": ["json"]},
                                **json_props
                            },
                            "required": ["request_template"]
                        }
                    ]
                }
            }
        }
        
        return schema
    
    @property
    def default_port(self) -> int:
        """Return the default port for Custom protocol.
        
        Returns:
            Default port number (0 means unspecified)
        """
        return 0
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return self.name_value

    def get_options(self) -> Dict[str, Dict[str, Any]]:
        """Return configurable options for this protocol.
        
        Returns:
            Dictionary of configuration options
        """
        return {
            "name": {
                "type": "string",
                "default": "Custom Protocol",
                "description": "Name"
            },
            "host": {
                "type": "string",
                "default": "",
                "description": "Host"
            },
            "port": {
                "type": "integer",
                "default": 0,
                "description": "Port"
            },
            "timeout": {
                "type": "integer",
                "default": 10,
                "description": "Timeout"
            },
            "method_type": {
                "type": "string",
                "default": "script",
                "description": "Method Type"
            },
            "script_path": {
                "type": "string",
                "default": "",
                "description": "Script Path"
            },
            "function_name": {
                "type": "string",
                "default": "test_auth",
                "description": "Function Name"
            },
            "command": {
                "type": "string",
                "default": "",
                "description": "Command"
            },
            "username_placeholder": {
                "type": "string",
                "default": "{username}",
                "description": "Username Placeholder"
            },
            "password_placeholder": {
                "type": "string",
                "default": "{password}",
                "description": "Password Placeholder"
            },
            "success_exit_code": {
                "type": "integer",
                "default": 0,
                "description": "Success Exit Code"
            },
            "success_output": {
                "type": "string",
                "default": "",
                "description": "Success Output"
            },
            "failure_output": {
                "type": "string",
                "default": "",
                "description": "Failure Output"
            },
            "request_template": {
                "type": "string",
                "default": "{}",
                "description": "Request Template"
            },
            "success_criteria": {
                "type": "string",
                "default": "{}",
                "description": "Success Criteria"
            },
            "failure_criteria": {
                "type": "string",
                "default": "{}",
                "description": "Failure Criteria"
            },
            "username_jsonpath": {
                "type": "string",
                "default": "$.username",
                "description": "Username Jsonpath"
            },
            "password_jsonpath": {
                "type": "string",
                "default": "$.password",
                "description": "Password Jsonpath"
            },
            "headers": {
                "type": "string",
                "default": "{"Content-Type": "application/json"}",
                "description": "Headers"
            }
        }
    



# Register protocol
from src.protocols import protocol_registry
protocol_registry.register_protocol("custom", Custom)
