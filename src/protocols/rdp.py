#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RDP protocol implementation for ERPCT.
This module provides support for RDP (Remote Desktop Protocol) authentication attacks.
"""

import socket
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

try:
    import rdpy.core.log as rdpy_log  # type: ignore
    from rdpy.protocol.rdp import rdp  # type: ignore
    from rdpy.core.error import RDPSecurityNegoFail  # type: ignore
    # Disable rdpy logs
    rdpy_log.log._Logger__level = rdpy_log.Level.ERROR
    RDPY_AVAILABLE = True
except ImportError:
    try:
        import subprocess
        import sys
        import os
        import tempfile
        FREERDP_AVAILABLE = False
        # Check if xfreerdp is available
        try:
            subprocess.run(["xfreerdp", "--version"], capture_output=True)
            FREERDP_AVAILABLE = True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    except ImportError:
        FREERDP_AVAILABLE = False
    RDPY_AVAILABLE = False


class RDP(ProtocolBase):
    """RDP protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the RDP protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        if not RDPY_AVAILABLE and not FREERDP_AVAILABLE:
            self.logger.error("Either rdpy package or xfreerdp command is required but not available")
            raise ImportError("Either rdpy package or xfreerdp command is required for RDP support")
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.timeout = config.get("timeout", 10)
        self.domain = config.get("domain", "")
        self.use_nla = config.get("use_nla", True)
        self.use_tls = config.get("use_tls", True)
        self.prefer_freerdp = config.get("prefer_freerdp", False) and FREERDP_AVAILABLE
        self.freerdp_command = config.get("freerdp_command", "xfreerdp")
        
        # If using RDPY, check limitations
        if not self.prefer_freerdp and RDPY_AVAILABLE:
            # RDPY doesn't support NLA and CredSSP, warn if enabled
            if self.use_nla:
                self.logger.warning("RDPY does not support NLA authentication, use FreeRDP instead")
                if FREERDP_AVAILABLE:
                    self.logger.info("Switching to FreeRDP for RDP testing with NLA")
                    self.prefer_freerdp = True
                else:
                    self.use_nla = False
        
        if not self.host:
            raise ValueError("RDP host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test RDP authentication with the given credentials.
        
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
            
        # If domain is in username (DOMAIN\\user), extract it
        if '\\' in username and not self.domain:
            domain, username = username.split('\\', 1)
            self.domain = domain
            
        if self.prefer_freerdp and FREERDP_AVAILABLE:
            return self._test_with_freerdp(username, password)
        elif RDPY_AVAILABLE:
            return self._test_with_rdpy(username, password)
        else:
            return False, "No supported RDP libraries available"
    
    def _test_with_rdpy(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test RDP authentication using RDPY library.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            # Create RDP client options
            rdp_client = rdp.RDPClientObserver()
            rdp_client.setUsername(username)
            rdp_client.setPassword(password)
            rdp_client.setDomain(self.domain)
            rdp_client.setHostname(self.host)
            rdp_client.setPort(self.port)
            
            # Configure TLS and security
            rdp_client.setTLS(self.use_tls)
            rdp_client.setNegotiationProtocol(rdp.NegotiationProtocol.PROTOCOL_RDP if not self.use_nla else rdp.NegotiationProtocol.PROTOCOL_HYBRID)
            
            # Set timeout and connection params
            rdp_client.clientObserver.onReady = lambda: None
            
            # Connect to server with a timeout
            socket.setdefaulttimeout(self.timeout)
            
            # Attempt connection
            # RDPY uses a callback model, so we use a manual timeout
            start_time = time.time()
            rdp_client.connect()
            
            # Wait for timeout or connection result
            while not rdp_client.connected and time.time() - start_time < self.timeout:
                time.sleep(0.1)
            
            # Check if connected
            if rdp_client.connected:
                self.logger.info(f"RDP authentication successful for user {username}")
                return True, None
            else:
                # Connection failed
                return False, "RDP authentication failed or timed out"
            
        except RDPSecurityNegoFail:
            # Authentication failed (security negotiation failed)
            return False, "RDP authentication failed: Security negotiation failed"
            
        except (socket.timeout, socket.error, ConnectionError) as e:
            # Network error
            error_msg = f"RDP connection error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            # Unexpected error
            error_msg = f"RDP unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        finally:
            # Reset default timeout
            socket.setdefaulttimeout(None)
    
    def _test_with_freerdp(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test RDP authentication using FreeRDP command line tool.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            # Build FreeRDP command
            command = [
                self.freerdp_command,
                "/cert-ignore",  # Ignore certificate warnings
                f"/v:{self.host}:{self.port}",  # Host and port
                f"/u:{username}",  # Username
                f"/p:{password}",  # Password
                "/log-level:error",  # Only show errors
                "/timeout:{}".format(int(self.timeout * 1000)),  # Timeout in ms
                "+auth-only",  # Only authenticate, don't start a session
                "/rfx",  # Use RemoteFX codec (faster)
            ]
            
            # Add domain if specified
            if self.domain:
                command.append(f"/d:{self.domain}")
                
            # Add security options
            if self.use_nla:
                command.append("/sec:nla")
            elif self.use_tls:
                command.append("/sec:tls")
            else:
                command.append("/sec:rdp")
            
            # Create temporary files for stdout and stderr
            with tempfile.NamedTemporaryFile() as stdout_temp, tempfile.NamedTemporaryFile() as stderr_temp:
                # Run FreeRDP command
                process = subprocess.Popen(
                    command,
                    stdout=stdout_temp,
                    stderr=stderr_temp,
                    universal_newlines=True
                )
                
                # Wait for the process to complete with timeout
                try:
                    process.wait(timeout=self.timeout + 5)  # Add 5 seconds for overhead
                except subprocess.TimeoutExpired:
                    process.kill()
                    return False, "RDP connection timed out"
                
                # Get exit code
                exit_code = process.returncode
                
                # Read output
                stdout_temp.seek(0)
                stderr_temp.seek(0)
                stdout_content = stdout_temp.read().decode('utf-8', errors='ignore')
                stderr_content = stderr_temp.read().decode('utf-8', errors='ignore')
                
                # Check for success or failure
                if exit_code == 0:
                    self.logger.info(f"RDP authentication successful for user {username}")
                    return True, None
                else:
                    # Check for auth failures in stderr
                    if "AUTHENTICATION_FAILED" in stderr_content:
                        return False, "RDP authentication failed: Invalid credentials"
                    elif "CONNECTION_FAILED" in stderr_content:
                        return False, f"RDP connection failed: {stderr_content}"
                    else:
                        # Other error
                        error_msg = f"RDP error (code {exit_code}): {stderr_content}"
                        self.logger.error(error_msg)
                        return False, error_msg
            
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            # Command execution error
            error_msg = f"FreeRDP execution error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for RDP protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        schema = {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "RDP Server",
                    "description": "Hostname or IP address of the RDP server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for RDP service (default: 3389)",
                    "default": 3389
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 10
                },
                "domain": {
                    "type": "string",
                    "title": "Domain",
                    "description": "Windows domain for authentication"
                },
                "use_nla": {
                    "type": "boolean",
                    "title": "Use NLA",
                    "description": "Use Network Level Authentication",
                    "default": True
                },
                "use_tls": {
                    "type": "boolean",
                    "title": "Use TLS",
                    "description": "Use TLS for connection security",
                    "default": True
                }
            },
            "required": ["host"]
        }
        
        # Add FreeRDP options if available
        if FREERDP_AVAILABLE:
            freerdp_props = {
                "prefer_freerdp": {
                    "type": "boolean",
                    "title": "Prefer FreeRDP",
                    "description": "Use FreeRDP command line tool instead of RDPY library",
                    "default": False
                },
                "freerdp_command": {
                    "type": "string",
                    "title": "FreeRDP Command",
                    "description": "Path to FreeRDP command line tool (xfreerdp)",
                    "default": "xfreerdp"
                }
            }
            
            schema["properties"].update(freerdp_props)
        
        return schema
    
    @property
    def default_port(self) -> int:
        """Return the default port for RDP.
        
        Returns:
            Default port number
        """
        return 3389
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "RDP"


# Register protocol
from src.protocols import protocol_registry
protocol_registry.register_protocol("rdp", RDP)
