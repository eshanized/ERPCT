#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSH protocol implementation for ERPCT.
This module provides support for SSH authentication attacks.
"""

import socket
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

try:
    import paramiko
    SSH_AVAILABLE = True
except ImportError:
    SSH_AVAILABLE = False


class SSH(ProtocolBase):
    """SSH protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the SSH protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        if not SSH_AVAILABLE:
            self.logger.error("paramiko package is required but not installed")
            raise ImportError("paramiko package is required for SSH support")
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.timeout = int(config.get("timeout", 10))
        self.key_auth_enabled = config.get("key_auth_enabled", False)
        self.key_file = config.get("key_file", None)
        self.key_passphrase = config.get("key_passphrase", None)
        self.auth_timeout = config.get("auth_timeout", 5)
        self.banner_timeout = config.get("banner_timeout", 5)
        self.allow_agent = config.get("allow_agent", False)
        self.look_for_keys = config.get("look_for_keys", False)
        
        # Optional command to execute after login
        self.command = config.get("command", None)
        self.command_timeout = config.get("command_timeout", 10)
        
        if not self.host:
            raise ValueError("SSH host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test SSH authentication with the given credentials.
        
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
            
        ssh_client = None
        
        try:
            # Create SSH client
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare connection parameters
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'username': username,
                'timeout': self.timeout,
                'auth_timeout': self.auth_timeout,
                'banner_timeout': self.banner_timeout,
                'allow_agent': self.allow_agent,
                'look_for_keys': self.look_for_keys
            }
            
            # Choose authentication method
            if self.key_auth_enabled and self.key_file:
                # Key-based authentication
                try:
                    # Load private key
                    if self.key_passphrase:
                        pkey = paramiko.RSAKey.from_private_key_file(
                            self.key_file, 
                            password=self.key_passphrase
                        )
                    else:
                        pkey = paramiko.RSAKey.from_private_key_file(self.key_file)
                        
                    connect_kwargs['pkey'] = pkey
                except Exception as e:
                    self.logger.error(f"Failed to load SSH key: {str(e)}")
                    return False, f"Failed to load SSH key: {str(e)}"
            else:
                # Password authentication
                connect_kwargs['password'] = password
            
            # Attempt connection
            ssh_client.connect(**connect_kwargs)
            
            # If a command is specified, execute it to verify real access
            if self.command:
                stdin, stdout, stderr = ssh_client.exec_command(
                    self.command, 
                    timeout=self.command_timeout
                )
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code != 0:
                    # Command failed
                    error_output = stderr.read().decode('utf-8', errors='ignore')
                    warning_msg = f"Command execution failed with exit code {exit_code}: {error_output}"
                    self.logger.warning(warning_msg)
                    # We still return True because authentication worked
            
            # If we got here, authentication succeeded
            self.logger.info(f"SSH authentication successful for user {username}")
            return True, None
            
        except paramiko.AuthenticationException:
            # Authentication failed
            return False, "SSH authentication failed: Invalid credentials"
            
        except paramiko.SSHException as e:
            # SSH specific error
            error_msg = f"SSH error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except (socket.timeout, socket.error, ConnectionError) as e:
            # Network error
            error_msg = f"Network error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        finally:
            # Always close SSH client if it exists
            if ssh_client:
                try:
                    ssh_client.close()
                except:
                    pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for SSH protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "SSH Server",
                    "description": "Hostname or IP address of the SSH server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for SSH service (default: 22)",
                    "default": 22
                },
                "timeout": {
                    "type": "integer",
                    "title": "Connection Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 10
                },
                "auth_timeout": {
                    "type": "integer",
                    "title": "Authentication Timeout",
                    "description": "Authentication timeout in seconds",
                    "default": 5
                },
                "banner_timeout": {
                    "type": "integer",
                    "title": "Banner Timeout",
                    "description": "Time to wait for SSH banner",
                    "default": 5
                },
                "key_auth_enabled": {
                    "type": "boolean",
                    "title": "Enable Key Authentication",
                    "description": "Use key-based authentication instead of password",
                    "default": False
                },
                "key_file": {
                    "type": "string",
                    "title": "Key File",
                    "description": "Path to private key file for key-based authentication"
                },
                "key_passphrase": {
                    "type": "string",
                    "title": "Key Passphrase",
                    "description": "Passphrase for encrypted private key"
                },
                "allow_agent": {
                    "type": "boolean",
                    "title": "Allow SSH Agent",
                    "description": "Allow use of SSH agent for authentication",
                    "default": False
                },
                "look_for_keys": {
                    "type": "boolean",
                    "title": "Look for Keys",
                    "description": "Search for discoverable private keys in ~/.ssh/",
                    "default": False
                },
                "command": {
                    "type": "string",
                    "title": "Command to Execute",
                    "description": "Optional command to execute after successful login"
                },
                "command_timeout": {
                    "type": "integer",
                    "title": "Command Timeout",
                    "description": "Timeout for command execution in seconds",
                    "default": 10
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for SSH.
        
        Returns:
            Default port number
        """
        return 22
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "SSH"


# Register protocol
from src.protocols import protocol_registry
protocol_registry.register_protocol("ssh", SSH)
