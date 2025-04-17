#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SMB protocol implementation for ERPCT.
This module provides support for SMB/CIFS authentication attacks.
"""

import socket
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

try:
    from impacket.smbconnection import SMBConnection
    from impacket.smb3structs import SMB2Error
    from impacket.nmb import NetBIOSError
    IMPACKET_AVAILABLE = True
except ImportError:
    try:
        from smb.SMBConnection import SMBConnection
        PYSMB_AVAILABLE = True
        IMPACKET_AVAILABLE = False
    except ImportError:
        PYSMB_AVAILABLE = False
        IMPACKET_AVAILABLE = False


class SMB(ProtocolBase):
    """SMB/CIFS protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the SMB protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        if not IMPACKET_AVAILABLE and not PYSMB_AVAILABLE:
            self.logger.error("Either impacket or pysmb package is required but not installed")
            raise ImportError("Either impacket or pysmb package is required for SMB support")
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.domain = config.get("domain", "")
        self.timeout = config.get("timeout", 5)
        self.smb_version = config.get("smb_version", "auto").lower()  # auto, smb1, smb2
        self.use_kerberos = config.get("use_kerberos", False)
        self.share_name = config.get("share_name", "IPC$")
        self.local_name = config.get("local_name", socket.gethostname())
        self.remote_name = config.get("remote_name", "*SMBSERVER")
        
        if not self.host:
            raise ValueError("SMB host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test SMB authentication with the given credentials.
        
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
            
        # Use the appropriate library based on availability
        if IMPACKET_AVAILABLE:
            return self._test_with_impacket(username, password)
        else:
            return self._test_with_pysmb(username, password)
    
    def _test_with_impacket(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test SMB authentication using impacket.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            domain = self.domain
            
            # If domain is in username (DOMAIN\\user), extract it
            if '\\' in username and not domain:
                domain, username = username.split('\\', 1)
            
            # Create connection object
            connection = SMBConnection(
                remoteName=self.remote_name,
                remoteHost=self.host
            )
            
            # Set SMB version preferences
            if self.smb_version == "smb1":
                connection.preferredDialect = SMBConnection.SMB_DIALECT
            elif self.smb_version == "smb2":
                connection.preferredDialect = SMBConnection.SMB2_DIALECT_002
            
            # Attempt login
            connection.login(
                user=username,
                password=password,
                domain=domain,
                lmhash='',
                nthash='',
                useKerberos=self.use_kerberos
            )
            
            # If we got here, authentication succeeded
            # Try to connect to a share as an extra validation
            try:
                connection.connectTree(self.share_name)
            except:
                # Ignore errors connecting to share
                pass
                
            # Close connection
            connection.close()
            
            self.logger.info(f"SMB authentication successful for user {username}")
            return True, None
            
        except SMB2Error as e:
            # SMB specific authentication error
            return False, f"SMB authentication error: {str(e)}"
            
        except NetBIOSError as e:
            # NetBIOS error (typically connection issues)
            error_msg = f"NetBIOS error: {str(e)}"
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
    
    def _test_with_pysmb(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test SMB authentication using pysmb.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            domain = self.domain
            
            # If domain is in username (DOMAIN\\user), extract it
            if '\\' in username and not domain:
                domain, username = username.split('\\', 1)
            
            # Create connection object
            connection = SMBConnection(
                username=username,
                password=password,
                my_name=self.local_name,
                remote_name=self.remote_name,
                domain=domain,
                use_ntlm_v2=True,
                is_direct_tcp=True
            )
            
            # Set timeout
            socket.setdefaulttimeout(self.timeout)
            
            # Attempt connection
            if connection.connect(self.host, self.port):
                # Connection successful
                connection.close()
                self.logger.info(f"SMB authentication successful for user {username}")
                return True, None
            else:
                # Connection failed
                return False, "SMB authentication failed"
                
        except Exception as e:
            # Authentication failed or other error
            error_msg = str(e)
            
            # Check if it's an authentication error
            if "authentication failure" in error_msg.lower() or "access denied" in error_msg.lower():
                return False, error_msg
            else:
                # Other error
                self.logger.error(f"SMB error: {error_msg}")
                return False, error_msg
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for SMB protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "SMB Server",
                    "description": "Hostname or IP address of the SMB server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for SMB service (default: 445)",
                    "default": 445
                },
                "domain": {
                    "type": "string",
                    "title": "Domain",
                    "description": "Domain name for authentication"
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 5
                },
                "smb_version": {
                    "type": "string",
                    "title": "SMB Version",
                    "description": "SMB protocol version to use",
                    "enum": ["auto", "smb1", "smb2"],
                    "default": "auto"
                },
                "use_kerberos": {
                    "type": "boolean",
                    "title": "Use Kerberos",
                    "description": "Use Kerberos authentication (requires impacket)",
                    "default": False
                },
                "share_name": {
                    "type": "string",
                    "title": "Share Name",
                    "description": "Share name to connect to for validation",
                    "default": "IPC$"
                },
                "local_name": {
                    "type": "string",
                    "title": "Local Name",
                    "description": "Local machine name (for NetBIOS)",
                    "default": socket.gethostname()
                },
                "remote_name": {
                    "type": "string",
                    "title": "Remote Name",
                    "description": "Remote machine name (for NetBIOS)",
                    "default": "*SMBSERVER"
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for SMB.
        
        Returns:
            Default port number
        """
        return 445
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "SMB"
    
    @property
    def supports_username_enumeration(self) -> bool:
        """Whether SMB supports username enumeration.
        
        Returns:
            True as SMB can enumerate usernames in some cases
        """
        return True

    def get_options(self) -> Dict[str, Dict[str, Any]]:
        """Return configurable options for this protocol.
        
        Returns:
            Dictionary of configuration options
        """
        return {
            "host": {
                "type": "string",
                "default": "",
                "description": "Host"
            },
            "port": {
                "type": "string",
                "default": "self.",
                "description": "Port"
            }
        }
    



# Register protocol



def register_protocol():
    """Register this protocol with the protocol registry."""
    from src.protocols import register_protocol
    register_protocol("smb", SMB)
