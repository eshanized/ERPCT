#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VNC protocol implementation for ERPCT.
This module provides support for VNC authentication attacks.
"""

import socket
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

try:
    from vncdotool import api
    VNC_AVAILABLE = True
except ImportError:
    try:
        import paramiko
        PARAMIKO_AVAILABLE = True
    except ImportError:
        PARAMIKO_AVAILABLE = False
    VNC_AVAILABLE = False


class VNC(ProtocolBase):
    """VNC protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the VNC protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        if not VNC_AVAILABLE and not PARAMIKO_AVAILABLE:
            self.logger.error("Either vncdotool or paramiko package is required but not installed")
            raise ImportError("Either vncdotool or paramiko package is required for VNC support")
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.display = config.get("display", None)
        self.connection_timeout = int(config.get("timeout", 10))
        self.authentication_timeout = int(config.get("auth_timeout", 5))
        self.prefer_ssh_tunnel = config.get("prefer_ssh_tunnel", False) and PARAMIKO_AVAILABLE
        
        # SSH tunnel settings (if using paramiko tunnel)
        if self.prefer_ssh_tunnel:
            self.ssh_host = config.get("ssh_host", self.host)
            self.ssh_port = int(config.get("ssh_port", 22))
            self.ssh_username = config.get("ssh_username", "")
            self.ssh_password = config.get("ssh_password", "")
            self.ssh_key_file = config.get("ssh_key_file", None)
        
        if not self.host:
            raise ValueError("VNC host must be specified")
            
        # If display is specified, adjust port
        if self.display is not None:
            # VNC displays typically start at 5900 + display number
            self.port = 5900 + int(self.display)
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test VNC authentication with the given credentials.
        
        Args:
            username: Username to test (ignored for VNC as it only uses password)
            password: Password to test
            
        Returns:
            Tuple containing (success_bool, optional_message)
                success_bool: True if authentication succeeded, False otherwise
                optional_message: Additional information or error message
        """
        # VNC only uses password for authentication, username is ignored
        
        if self.prefer_ssh_tunnel and PARAMIKO_AVAILABLE:
            return self._test_via_ssh_tunnel(password)
        elif VNC_AVAILABLE:
            return self._test_with_vncdotool(password)
        else:
            return False, "No supported VNC libraries available"
    
    def _test_with_vncdotool(self, password: str) -> Tuple[bool, Optional[str]]:
        """Test VNC authentication using vncdotool library.
        
        Args:
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            # Create VNC server address
            server = f"{self.host}::{self.port}"
            
            # Set authentication timeout
            socket.setdefaulttimeout(self.connection_timeout)
            
            # Attempt connection with password
            # vncdotool uses a callback-based API
            client = api.connect(server, password=password)
            
            # If we got here, authentication succeeded
            # Disconnect immediately
            client.disconnect()
            
            self.logger.info(f"VNC authentication successful on {self.host}:{self.port}")
            return True, None
            
        except api.VNCAuthError:
            # Authentication failed
            return False, "VNC authentication failed: Invalid password"
            
        except (socket.timeout, socket.error, ConnectionError) as e:
            # Network error
            error_msg = f"VNC connection error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            # Unexpected error
            error_msg = f"VNC unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _test_via_ssh_tunnel(self, password: str) -> Tuple[bool, Optional[str]]:
        """Test VNC authentication by first creating an SSH tunnel, then port forwarding to VNC.
        This is useful when VNC is only accessible via SSH.
        
        Args:
            password: VNC password to test
            
        Returns:
            Success status and optional message
        """
        if not PARAMIKO_AVAILABLE:
            return False, "Paramiko library is not available for SSH tunneling"
            
        ssh_client = None
        local_port = self.port + 10000  # Use a high port number to avoid conflicts
        
        try:
            import paramiko
            
            # Create SSH client and connect
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to SSH server
            connect_kwargs = {
                'hostname': self.ssh_host,
                'port': self.ssh_port,
                'timeout': self.connection_timeout
            }
            
            if self.ssh_username:
                connect_kwargs['username'] = self.ssh_username
                
            if self.ssh_password:
                connect_kwargs['password'] = self.ssh_password
                
            if self.ssh_key_file:
                connect_kwargs['key_filename'] = self.ssh_key_file
                
            ssh_client.connect(**connect_kwargs)
            
            # Create the tunnel
            # Forward a local port to the VNC port on the remote host
            ssh_client.get_transport().request_port_forward('', local_port, self.host, self.port)
            
            # Now test VNC connection through the tunnel
            # Create temporary VNC configuration
            tunnel_config = {
                'host': 'localhost',
                'port': local_port,
                'timeout': self.authentication_timeout
            }
            
            # Create a temporary VNC instance that connects through the tunnel
            temp_vnc = VNC(tunnel_config)
            
            # Test connection 
            if VNC_AVAILABLE:
                result, message = temp_vnc._test_with_vncdotool(password)
            else:
                result, message = False, "VNC library not available for testing through tunnel"
                
            if result:
                self.logger.info(f"VNC authentication via SSH tunnel successful on {self.host}:{self.port}")
            
            return result, message
            
        except paramiko.AuthenticationException:
            # SSH authentication failed
            return False, "SSH authentication failed: Cannot create tunnel to VNC"
            
        except paramiko.SSHException as e:
            # SSH connection error
            error_msg = f"SSH connection error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            # Unexpected error
            error_msg = f"SSH tunnel error: {str(e)}"
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
        """Return the configuration schema for VNC protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        schema = {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "VNC Server",
                    "description": "Hostname or IP address of the VNC server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for VNC service (default: 5900)",
                    "default": 5900
                },
                "display": {
                    "type": "integer",
                    "title": "Display",
                    "description": "VNC display number (alternative to port, e.g. 1 for port 5901)"
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
                }
            },
            "required": ["host"]
        }
        
        # Add SSH tunnel options if paramiko is available
        if PARAMIKO_AVAILABLE:
            ssh_props = {
                "prefer_ssh_tunnel": {
                    "type": "boolean",
                    "title": "Use SSH Tunnel",
                    "description": "Access VNC through an SSH tunnel",
                    "default": False
                },
                "ssh_host": {
                    "type": "string",
                    "title": "SSH Server",
                    "description": "Hostname or IP address of the SSH server (defaults to VNC host)"
                },
                "ssh_port": {
                    "type": "integer",
                    "title": "SSH Port",
                    "description": "Port number for SSH service",
                    "default": 22
                },
                "ssh_username": {
                    "type": "string",
                    "title": "SSH Username",
                    "description": "Username for SSH authentication"
                },
                "ssh_password": {
                    "type": "string",
                    "title": "SSH Password",
                    "description": "Password for SSH authentication"
                },
                "ssh_key_file": {
                    "type": "string",
                    "title": "SSH Key File",
                    "description": "Path to private key file for SSH authentication"
                }
            }
            
            schema["properties"].update(ssh_props)
        
        return schema
    
    @property
    def default_port(self) -> int:
        """Return the default port for VNC.
        
        Returns:
            Default port number
        """
        return 5900
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "VNC"


# Register protocol
from src.protocols import protocol_registry
protocol_registry.register_protocol("vnc", VNC)
