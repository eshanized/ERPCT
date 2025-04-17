#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IMAP protocol implementation for ERPCT.
This module provides support for IMAP authentication attacks.
"""

import imaplib
import socket
import ssl
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger


class IMAP(ProtocolBase):
    """IMAP protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the IMAP protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.use_ssl = config.get("use_ssl", True)
        self.timeout = config.get("timeout", 10)
        self.verify_cert = config.get("verify_cert", True)
        self.auth_method = config.get("auth_method", "").upper()  # LOGIN, CRAM-MD5, etc.
        
        # If not using SSL, change default port
        if not self.use_ssl and self.port == 993:
            self.port = 143
            
        if not self.host:
            raise ValueError("IMAP host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test IMAP authentication with the given credentials.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Tuple containing (success_bool, optional_message)
                success_bool: True if authentication succeeded, False otherwise
                optional_message: Additional information or error message
        """
        if not username or not password:
            return False, "Username and password must not be empty"
            
        imap_client = None
        
        try:
            # Create IMAP client with appropriate SSL settings
            if self.use_ssl:
                # Create SSL context if needed
                if not self.verify_cert:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    imap_client = imaplib.IMAP4_SSL(
                        host=self.host, 
                        port=self.port,
                        ssl_context=context
                    )
                else:
                    imap_client = imaplib.IMAP4_SSL(
                        host=self.host, 
                        port=self.port
                    )
            else:
                imap_client = imaplib.IMAP4(
                    host=self.host, 
                    port=self.port
                )
            
            # Set timeout
            imap_client.socket().settimeout(self.timeout)
            
            # Login using specified auth method or default
            if self.auth_method == "CRAM-MD5":
                imap_client.login_cram_md5(username, password)
            else:  # Default to standard login
                imap_client.login(username, password)
                
            # Try to select INBOX as an extra validation
            try:
                imap_client.select('INBOX')
            except:
                # Ignore errors selecting inbox
                pass
                
            # If we got here, authentication succeeded
            self.logger.info(f"IMAP authentication successful for user {username}")
            return True, None
            
        except imaplib.IMAP4.error as e:
            # IMAP specific error (likely authentication failure)
            error_msg = str(e)
            
            # Check if it's an authentication error
            if "authentication failed" in error_msg.lower() or "login failed" in error_msg.lower():
                return False, f"IMAP authentication failed: {error_msg}"
            else:
                # Other IMAP error
                self.logger.error(f"IMAP error: {error_msg}")
                return False, error_msg
                
        except (socket.timeout, socket.error, ConnectionError, ssl.SSLError) as e:
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
            # Always log out and close IMAP client if it exists
            if imap_client:
                try:
                    imap_client.logout()
                except:
                    # Ignore errors during logout
                    pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for IMAP protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "IMAP Server",
                    "description": "Hostname or IP address of the IMAP server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for IMAP service (default: 993 for SSL, 143 for non-SSL)",
                    "default": 993
                },
                "use_ssl": {
                    "type": "boolean",
                    "title": "Use SSL",
                    "description": "Connect using SSL (IMAPS)",
                    "default": True
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 10
                },
                "verify_cert": {
                    "type": "boolean",
                    "title": "Verify Certificate",
                    "description": "Verify SSL certificate when using SSL",
                    "default": True
                },
                "auth_method": {
                    "type": "string",
                    "title": "Authentication Method",
                    "description": "IMAP authentication method to use",
                    "enum": ["", "CRAM-MD5"],
                    "default": ""
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for IMAP.
        
        Returns:
            Default port number
        """
        return 993 if self.use_ssl else 143
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "IMAP"

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
from src.protocols import protocol_registry
protocol_registry.register_protocol("imap", IMAP)
