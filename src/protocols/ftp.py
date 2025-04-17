#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FTP protocol implementation for ERPCT.
This module provides FTP authentication capabilities for password testing.
"""

import socket
import time
import ftplib
from typing import Dict, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger


class FTPProtocol(ProtocolBase):
    """FTP protocol implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the FTP protocol.
        
        Args:
            config: Dictionary containing FTP configuration options
        """
        self.logger = get_logger(__name__)
        
        # Accept either 'host' or 'target' for compatibility
        self.host = config.get("host") or config.get("target")
        if not self.host:
            self.logger.error(f"Host/target not specified in config: {config}")
            raise ValueError("Host must be specified for FTP protocol")
            
        self.port = int(config.get("port", self.default_port))
        self.timeout = int(config.get("timeout", 10))
        self.use_ssl = bool(config.get("use_ssl", False))
        self.passive_mode = bool(config.get("passive_mode", True))
        
        # Default command after login
        self.test_command = config.get("test_command", "PWD")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test FTP credentials.
        
        Args:
            username: FTP username
            password: FTP password
            
        Returns:
            Tuple containing (success_bool, optional_message)
        """
        self.logger.debug(f"Testing FTP credentials {username}:{password} on {self.host}:{self.port}")
        
        # Choose the appropriate FTP class based on SSL setting
        ftp_class = ftplib.FTP_TLS if self.use_ssl else ftplib.FTP
        
        try:
            # Create FTP connection
            ftp = ftp_class(timeout=self.timeout)
            
            # Connect to server
            ftp.connect(self.host, self.port)
            
            # Login with credentials
            ftp.login(username, password)
            
            # Set passive mode if configured
            if self.passive_mode:
                ftp.set_pasv(True)
                
            # If using SSL, secure the data connection
            if self.use_ssl and hasattr(ftp, 'prot_p'):
                ftp.prot_p()
            
            # Execute test command to verify successful login
            response = ftp.sendcmd(self.test_command)
            
            # Quit the session
            ftp.quit()
            
            # If we reach here, authentication was successful
            self.logger.info(f"FTP authentication successful for {username} on {self.host}:{self.port}")
            return True, f"Authentication successful: {response}"
            
        except ftplib.error_perm as e:
            # Authentication failed - permission error
            error_str = str(e)
            if "530" in error_str:  # 530 = Authentication failed
                self.logger.debug(f"FTP authentication failed for {username} on {self.host}:{self.port}")
                return False, None
            else:
                # Other permission errors
                self.logger.error(f"FTP permission error: {error_str}")
                return False, f"Permission error: {error_str}"
                
        except (socket.error, socket.timeout, ftplib.Error) as e:
            # Connection error
            error_msg = f"FTP connection error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
        finally:
            # Ensure the connection is closed in case of an exception
            try:
                if 'ftp' in locals() and ftp:
                    ftp.close()
            except:
                pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema for FTP protocol.
        
        Returns:
            JSON schema object for FTP configuration
        """
        return {
            "type": "object",
            "required": ["host"],
            "properties": {
                "host": {
                    "type": "string",
                    "title": "Host",
                    "description": "FTP server hostname or IP address"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "FTP server port",
                    "default": self.default_port
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 10
                },
                "use_ssl": {
                    "type": "boolean",
                    "title": "Use SSL/TLS",
                    "description": "Use FTPS (FTP over SSL/TLS)",
                    "default": False
                },
                "passive_mode": {
                    "type": "boolean",
                    "title": "Passive Mode",
                    "description": "Use passive mode for data transfers",
                    "default": True
                },
                "test_command": {
                    "type": "string",
                    "title": "Test Command",
                    "description": "FTP command to verify successful login",
                    "default": "PWD"
                }
            }
        }
    
    @property
    def default_port(self) -> int:
        """Return the default FTP port.
        
        Returns:
            Default FTP port (21)
        """
        return 21
    
    @property
    def name(self) -> str:
        """Return the protocol name.
        
        Returns:
            Protocol name 'ftp'
        """
        return "ftp"
    
    def cleanup(self) -> None:
        """Clean up any resources.
        
        For FTP protocol, no cleanup is necessary as connections
        are closed after each test.
        """
        pass


# Register this protocol with the registry
def register_protocol():
    """Register this protocol in the registry."""
    from src.protocols import protocol_registry
    protocol_registry.register_protocol("ftp", FTPProtocol)
