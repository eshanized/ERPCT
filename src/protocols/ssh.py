#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSH protocol implementation for ERPCT.
This module provides SSH authentication capabilities for password testing.
"""

import socket
import time
from typing import Dict, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger


class SSH(ProtocolBase):
    """SSH protocol implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the SSH protocol.
        
        Args:
            config: Dictionary containing SSH configuration options
        """
        self.logger = get_logger(__name__)
        
        # Check for paramiko package
        try:
            import paramiko
            self.paramiko = paramiko
        except ImportError:
            raise ImportError("SSH protocol requires paramiko package: pip install paramiko")
        
        # Basic configuration - accept both 'host' and 'target' for compatibility
        self.host = config.get("host") or config.get("target")
        if not self.host:
            self.logger.error(f"Host/target not specified in config: {config}")
            raise ValueError("Host must be specified for SSH protocol")
            
        self.port = int(config.get("port", self.default_port))
        self.timeout = int(config.get("timeout", 10))
        
        # SSH options
        self.allow_agent = bool(config.get("allow_agent", False))
        self.look_for_keys = bool(config.get("look_for_keys", False))
        self.auth_timeout = int(config.get("auth_timeout", 5))
        self.banner_timeout = int(config.get("banner_timeout", 5))
        
        # Verbose logging for debugging
        if config.get("verbose_logging", False):
            self.paramiko.common.logging.basicConfig(level=self.paramiko.common.DEBUG)

    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test SSH credentials.
        
        Args:
            username: SSH username
            password: SSH password
            
        Returns:
            Tuple containing (success_bool, optional_message)
        """
        self.logger.debug(f"Testing SSH credentials {username}:{password} on {self.host}:{self.port}")
        
        client = self.paramiko.SSHClient()
        client.set_missing_host_key_policy(self.paramiko.AutoAddPolicy())
        
        try:
            # Connect with credentials
            client.connect(
                hostname=self.host,
                port=self.port,
                username=username,
                password=password,
                timeout=self.timeout,
                allow_agent=self.allow_agent,
                look_for_keys=self.look_for_keys,
                auth_timeout=self.auth_timeout,
                banner_timeout=self.banner_timeout
            )
            
            # If we get here, authentication was successful
            self.logger.info(f"SSH authentication successful for {username} on {self.host}:{self.port}")
            
            # Try to get the hostname as additional information
            try:
                stdin, stdout, stderr = client.exec_command("hostname", timeout=5)
                hostname = stdout.read().decode('utf-8').strip()
                return True, f"Authentication successful (hostname: {hostname})"
            except:
                # If command execution fails, still return success
                return True, "Authentication successful"
            
        except self.paramiko.AuthenticationException:
            # Authentication failed
            self.logger.debug(f"SSH authentication failed for {username} on {self.host}:{self.port}")
            return False, None
            
        except socket.timeout:
            # Connection timeout
            self.logger.error(f"SSH connection timeout to {self.host}:{self.port}")
            return False, "Connection timeout"
            
        except socket.error as e:
            # Socket error
            self.logger.error(f"SSH socket error: {str(e)}")
            return False, f"Socket error: {str(e)}"
            
        except self.paramiko.SSHException as e:
            # SSH protocol error
            self.logger.error(f"SSH protocol error: {str(e)}")
            return False, f"SSH error: {str(e)}"
            
        except Exception as e:
            # Unexpected error
            self.logger.error(f"Unexpected error in SSH authentication: {str(e)}")
            return False, f"Error: {str(e)}"
            
        finally:
            # Ensure the connection is closed
            try:
                client.close()
            except:
                pass

    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema for SSH protocol.
        
        Returns:
            JSON schema object for SSH configuration
        """
        return {
            "type": "object",
            "required": ["host"],
            "properties": {
                "host": {
                    "type": "string",
                    "title": "Host",
                    "description": "SSH server hostname or IP address"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "SSH server port",
                    "default": self.default_port
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 10
                },
                "allow_agent": {
                    "type": "boolean",
                    "title": "Allow Agent",
                    "description": "Allow SSH agent for authentication",
                    "default": False
                },
                "look_for_keys": {
                    "type": "boolean",
                    "title": "Look For Keys",
                    "description": "Automatically search for SSH keys",
                    "default": False
                },
                "auth_timeout": {
                    "type": "integer",
                    "title": "Auth Timeout",
                    "description": "Authentication timeout in seconds",
                    "default": 5
                },
                "banner_timeout": {
                    "type": "integer",
                    "title": "Banner Timeout",
                    "description": "SSH banner timeout in seconds",
                    "default": 5
                },
                "verbose_logging": {
                    "type": "boolean",
                    "title": "Verbose Logging",
                    "description": "Enable verbose SSH library logging",
                    "default": False
                }
            }
        }
    
    @property
    def default_port(self) -> int:
        """Return the default SSH port.
        
        Returns:
            Default SSH port (22)
        """
        return 22
    
    @property
    def name(self) -> str:
        """Return the protocol name.
        
        Returns:
            Protocol name 'ssh'
        """
        return "ssh"
    
    def get_options(self) -> Dict[str, Dict[str, Any]]:
        """Return configurable options for SSH protocol.
        
        Returns:
            Dictionary of configuration options
        """
        return {
            "host": {
                "type": "string",
                "default": "",
                "description": "SSH server hostname or IP address"
            },
            "port": {
                "type": "integer",
                "default": self.default_port,
                "description": "SSH server port"
            },
            "timeout": {
                "type": "integer",
                "default": 10,
                "description": "Connection timeout in seconds"
            },
            "allow_agent": {
                "type": "boolean",
                "default": False,
                "description": "Allow SSH agent for authentication"
            },
            "look_for_keys": {
                "type": "boolean",
                "default": False,
                "description": "Automatically search for SSH keys"
            },
            "auth_timeout": {
                "type": "integer",
                "default": 5,
                "description": "Authentication timeout in seconds"
            },
            "banner_timeout": {
                "type": "integer",
                "default": 5,
                "description": "SSH banner timeout in seconds"
            },
            "verbose_logging": {
                "type": "boolean",
                "default": False,
                "description": "Enable verbose SSH library logging"
            }
        }
    
    def cleanup(self) -> None:
        """Clean up any resources.
        
        For SSH protocol, no cleanup is necessary.
        """
        pass


# Register this protocol with the registry
# This will be imported by the protocol registry
def register_protocol():
    """Register this protocol in the registry."""
    from src.protocols import protocol_registry
    protocol_registry.register_protocol("ssh", SSH)
