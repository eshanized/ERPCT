#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telnet protocol implementation for ERPCT.
This module provides support for Telnet authentication attacks.
"""

import re
import socket
import time
from typing import Dict, List, Optional, Tuple, Any

# Use our custom telnetlib implementation
from src.utils.telnetlib import Telnet as TelnetClient
from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger


class Telnet(ProtocolBase):
    """Telnet protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Telnet protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.timeout = int(config.get("timeout", 10))
        self.read_timeout = int(config.get("read_timeout", 5))
        self.login_prompt = config.get("login_prompt", b"login:|username:|user:|user name:")
        self.password_prompt = config.get("password_prompt", b"password:|pass:")
        self.success_message = config.get("success_message", b"welcome|#|\\$|>|%")
        self.failure_message = config.get("failure_message", b"incorrect|failed|denied|invalid|wrong|error|failure")
        self.prompt_case_sensitive = config.get("prompt_case_sensitive", False)
        
        # Convert string prompts to bytes if they're not already
        if isinstance(self.login_prompt, str):
            self.login_prompt = self.login_prompt.encode('ascii')
        if isinstance(self.password_prompt, str):
            self.password_prompt = self.password_prompt.encode('ascii')
        if isinstance(self.success_message, str):
            self.success_message = self.success_message.encode('ascii')
        if isinstance(self.failure_message, str):
            self.failure_message = self.failure_message.encode('ascii')
            
        # Compile regex patterns with appropriate case sensitivity
        flags = 0 if self.prompt_case_sensitive else re.IGNORECASE
        self.login_pattern = re.compile(self.login_prompt, flags)
        self.password_pattern = re.compile(self.password_prompt, flags)
        self.success_pattern = re.compile(self.success_message, flags)
        self.failure_pattern = re.compile(self.failure_message, flags)
        
        if not self.host:
            raise ValueError("Telnet host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test Telnet authentication with the given credentials.
        
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
            
        telnet_client = None
        
        try:
            # Create Telnet client using our custom implementation
            telnet_client = TelnetClient()
            
            # Connect with timeout
            telnet_client.open(self.host, self.port, self.timeout)
            
            # Wait for login prompt - using a generic expected value since we're using regex
            response = telnet_client.read_until(b"\n", self.read_timeout)
            
            # Check for login prompt
            if not self.login_pattern.search(response):
                # Try to read more if we didn't get the prompt
                additional_response = telnet_client.read_until(b"\n", self.read_timeout)
                response += additional_response
                if not self.login_pattern.search(response):
                    return False, f"Login prompt not found: {response.decode('ascii', errors='ignore')}"
            
            # Send username
            telnet_client.write(username.encode('ascii') + b"\r\n")
            
            # Wait for password prompt 
            response = telnet_client.read_until(b"\n", self.read_timeout)
            
            # Check for password prompt
            if not self.password_pattern.search(response):
                # Try to read more if we didn't get the prompt
                additional_response = telnet_client.read_until(b"\n", self.read_timeout)
                response += additional_response
                if not self.password_pattern.search(response):
                    return False, f"Password prompt not found: {response.decode('ascii', errors='ignore')}"
            
            # Send password
            telnet_client.write(password.encode('ascii') + b"\r\n")
            
            # Wait for response - read multiple lines to look for success/failure patterns
            response = b""
            for _ in range(5):  # Try to read up to 5 lines
                response += telnet_client.read_until(b"\n", self.read_timeout)
                if self.success_pattern.search(response) or self.failure_pattern.search(response):
                    break
            
            # Convert to string for logging
            response_str = response.decode('ascii', errors='ignore')
            
            # Check for success or failure
            if self.success_pattern.search(response):
                self.logger.info(f"Telnet authentication successful for user {username}")
                return True, None
            elif self.failure_pattern.search(response):
                # Authentication failed
                return False, "Authentication failed: Invalid credentials"
            else:
                # Neither success nor failure pattern found
                self.logger.warning(f"No success or failure message found: {response_str}")
                return False, f"No success or failure message found: {response_str}"
            
        except (socket.timeout, socket.error, ConnectionError, EOFError) as e:
            # Network or connection error
            error_msg = f"Telnet connection error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        finally:
            # Always close Telnet client if it exists
            if telnet_client:
                try:
                    telnet_client.close()
                except:
                    pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for Telnet protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "Telnet Server",
                    "description": "Hostname or IP address of the Telnet server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for Telnet service (default: 23)",
                    "default": 23
                },
                "timeout": {
                    "type": "integer",
                    "title": "Connection Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 10
                },
                "read_timeout": {
                    "type": "integer",
                    "title": "Read Timeout",
                    "description": "Read timeout in seconds",
                    "default": 5
                },
                "login_prompt": {
                    "type": "string",
                    "title": "Login Prompt",
                    "description": "Regular expression to match login prompt",
                    "default": "login:|username:|user:|user name:"
                },
                "password_prompt": {
                    "type": "string",
                    "title": "Password Prompt",
                    "description": "Regular expression to match password prompt",
                    "default": "password:|pass:"
                },
                "success_message": {
                    "type": "string",
                    "title": "Success Message",
                    "description": "Regular expression to match success message",
                    "default": "welcome|#|\\$|>|%"
                },
                "failure_message": {
                    "type": "string",
                    "title": "Failure Message",
                    "description": "Regular expression to match failure message",
                    "default": "incorrect|failed|denied|invalid|wrong|error|failure"
                },
                "prompt_case_sensitive": {
                    "type": "boolean",
                    "title": "Case Sensitive Prompts",
                    "description": "Whether prompts and messages are case sensitive",
                    "default": False
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for Telnet.
        
        Returns:
            Default port number
        """
        return 23
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "Telnet"

    def get_options(self) -> Dict[str, Dict[str, Any]]:
        """Return configurable options for this protocol.
        
        Returns:
            Dictionary of configuration options
        """
        return {
            "host": {
                "type": "string",
                "default": "",
                "description": "Hostname or IP address"
            },
            "port": {
                "type": "integer",
                "default": self.default_port,
                "description": "Port number"
            },
            "timeout": {
                "type": "integer",
                "default": 10,
                "description": "Connection timeout in seconds"
            }
        }
    



# Register protocol

def register_protocol():
    """Register this protocol with the protocol registry."""
    from src.protocols import register_protocol
    register_protocol("telnet", Telnet)
