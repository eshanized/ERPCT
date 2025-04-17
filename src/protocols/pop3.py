#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
POP3 protocol implementation for ERPCT.
This module provides support for POP3 authentication attacks.
"""

import poplib
import socket
import ssl
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger


class POP3(ProtocolBase):
    """POP3 protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the POP3 protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.use_ssl = config.get("use_ssl", True)
        self.use_tls = config.get("use_tls", False)
        self.timeout = config.get("timeout", 10)
        self.verify_cert = config.get("verify_cert", True)
        self.auth_method = config.get("auth_method", "").upper()  # APOP, etc.
        
        # If not using SSL, change default port
        if not self.use_ssl and self.port == 995:
            self.port = 110
            
        if not self.host:
            raise ValueError("POP3 host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test POP3 authentication with the given credentials.
        
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
            
        pop_client = None
        
        try:
            # Create POP3 client with appropriate SSL settings
            if self.use_ssl:
                # Create SSL context if verification is disabled
                if not self.verify_cert:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    pop_client = poplib.POP3_SSL(
                        host=self.host, 
                        port=self.port,
                        context=context
                    )
                else:
                    pop_client = poplib.POP3_SSL(
                        host=self.host, 
                        port=self.port
                    )
            else:
                pop_client = poplib.POP3(
                    host=self.host, 
                    port=self.port
                )
                
                # Use STLS/TLS if requested (non-SSL connections only)
                if self.use_tls:
                    # Set SSL context for STLS
                    context = None
                    if not self.verify_cert:
                        context = ssl.create_default_context()
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                    
                    try:
                        pop_client.stls(context=context)
                    except Exception as e:
                        self.logger.warning(f"Failed to start TLS: {str(e)}")
                
            # Set timeout
            pop_client.sock.settimeout(self.timeout)
            
            # Login using specified auth method or default
            if self.auth_method == "APOP" and hasattr(pop_client, 'apop'):
                pop_client.apop(username, password)
            else:
                # Default to standard USER/PASS login
                pop_client.user(username)
                pop_client.pass_(password)
                
            # Try to get mailbox stats as an extra validation
            try:
                pop_client.stat()
            except:
                # Ignore errors getting mailbox stats
                pass
                
            # If we got here, authentication succeeded
            self.logger.info(f"POP3 authentication successful for user {username}")
            return True, None
            
        except poplib.error_proto as e:
            # POP3 protocol error (likely authentication failure)
            error_msg = str(e)
            
            # Check if it's an authentication error
            if "-ERR" in error_msg:
                return False, f"POP3 authentication failed: {error_msg}"
            else:
                # Other POP3 error
                self.logger.error(f"POP3 protocol error: {error_msg}")
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
            # Always quit and close POP3 client if it exists
            if pop_client:
                try:
                    pop_client.quit()
                except:
                    # If quit fails, try to close the connection
                    try:
                        if hasattr(pop_client, 'close'):
                            pop_client.close()
                    except:
                        # Ignore errors during cleanup
                        pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for POP3 protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "POP3 Server",
                    "description": "Hostname or IP address of the POP3 server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for POP3 service (default: 995 for SSL, 110 for non-SSL)",
                    "default": 995
                },
                "use_ssl": {
                    "type": "boolean",
                    "title": "Use SSL",
                    "description": "Connect using SSL (POP3S)",
                    "default": True
                },
                "use_tls": {
                    "type": "boolean",
                    "title": "Use TLS",
                    "description": "Use STLS to encrypt connection (non-SSL only)",
                    "default": False
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
                    "description": "Verify SSL certificate when using SSL/TLS",
                    "default": True
                },
                "auth_method": {
                    "type": "string",
                    "title": "Authentication Method",
                    "description": "POP3 authentication method to use",
                    "enum": ["", "APOP"],
                    "default": ""
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for POP3.
        
        Returns:
            Default port number
        """
        return 995 if self.use_ssl else 110
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "POP3"


# Register protocol
from src.protocols import protocol_registry
protocol_registry.register_protocol("pop3", POP3)
