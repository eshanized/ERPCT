#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LDAP protocol implementation for ERPCT.
This module provides support for LDAP authentication attacks.
"""

import socket
import ssl
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

try:
    import ldap3
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False


class LDAP(ProtocolBase):
    """LDAP protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the LDAP protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        if not LDAP_AVAILABLE:
            self.logger.error("ldap3 package is required but not installed")
            raise ImportError("ldap3 package is required for LDAP support")
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.use_ssl = config.get("use_ssl", False)
        self.timeout = config.get("timeout", 5)
        self.base_dn = config.get("base_dn", "")
        self.user_dn_format = config.get("user_dn_format", "cn={},dc=example,dc=com")
        self.auth_method = config.get("auth_method", "simple").lower()
        self.verify_cert = config.get("verify_cert", True)
        
        # Connection pooling
        self._server = None
        
        if not self.host:
            raise ValueError("LDAP host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test LDAP authentication with the given credentials.
        
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
            
        # Get LDAP server object
        server = self._get_server()
        
        # Determine user DN
        user_dn = self._get_user_dn(username)
        
        try:
            # Attempt authentication
            connection = ldap3.Connection(
                server,
                user=user_dn,
                password=password,
                authentication=self._get_auth_method(),
                read_only=True,
                auto_bind=False,
                receive_timeout=self.timeout
            )
            
            # Try to bind
            if connection.bind():
                # Authentication successful
                connection.unbind()
                self.logger.info(f"LDAP authentication successful for user {username}")
                return True, None
            else:
                # Authentication failed
                return False, connection.result.get('message', 'Unknown authentication error')
                
        except ldap3.core.exceptions.LDAPBindError as e:
            # Authentication failed
            return False, str(e)
            
        except ldap3.core.exceptions.LDAPException as e:
            # LDAP error
            error_msg = f"LDAP error: {str(e)}"
            self.logger.error(error_msg)
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
    
    def _get_server(self) -> ldap3.Server:
        """Get LDAP server object.
        
        Returns:
            LDAP server object
        """
        if self._server is None:
            # Create new server
            self._server = ldap3.Server(
                host=self.host,
                port=self.port,
                use_ssl=self.use_ssl,
                connect_timeout=self.timeout,
                get_info=ldap3.NONE,
                tls=self._get_tls_config() if self.use_ssl else None
            )
        
        return self._server
    
    def _get_tls_config(self) -> Optional[ldap3.Tls]:
        """Get TLS configuration for LDAP connection.
        
        Returns:
            TLS configuration object
        """
        if not self.use_ssl:
            return None
            
        tls_config = {}
        
        # Validate certificate?
        if not self.verify_cert:
            tls_config['validate'] = ssl.CERT_NONE
        
        # CA certificates path
        ca_certs_file = self.config.get("ca_certs_file")
        if ca_certs_file:
            tls_config['ca_certs_file'] = ca_certs_file
            
        return ldap3.Tls(**tls_config) if tls_config else None
    
    def _get_auth_method(self) -> str:
        """Get LDAP authentication method.
        
        Returns:
            Authentication method string
        """
        method = self.auth_method.lower()
        
        if method == "ntlm":
            return ldap3.NTLM
        elif method == "sasl":
            return ldap3.SASL
        else:
            return ldap3.SIMPLE
    
    def _get_user_dn(self, username: str) -> str:
        """Format username into distinguished name (DN).
        
        Args:
            username: Username to format
            
        Returns:
            Distinguished name string
        """
        if "{" not in self.user_dn_format:
            # If no format placeholder, just use as-is
            return self.user_dn_format
            
        try:
            # Try to format with the username
            return self.user_dn_format.format(username)
        except Exception as e:
            self.logger.error(f"Error formatting user DN: {str(e)}")
            # Fall back to a basic format
            return f"cn={username},{self.base_dn}" if self.base_dn else f"cn={username}"
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for LDAP protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "LDAP Server",
                    "description": "Hostname or IP address of the LDAP server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for LDAP service (default: 389)",
                    "default": 389
                },
                "use_ssl": {
                    "type": "boolean",
                    "title": "Use SSL/TLS",
                    "description": "Use SSL/TLS for connection (LDAPS)",
                    "default": False
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 5
                },
                "base_dn": {
                    "type": "string",
                    "title": "Base DN",
                    "description": "Base Distinguished Name"
                },
                "user_dn_format": {
                    "type": "string",
                    "title": "User DN Format",
                    "description": "Format string for user DN (e.g., cn={},dc=example,dc=com)",
                    "default": "cn={},dc=example,dc=com"
                },
                "auth_method": {
                    "type": "string",
                    "title": "Authentication Method",
                    "description": "LDAP authentication method",
                    "enum": ["simple", "ntlm", "sasl"],
                    "default": "simple"
                },
                "verify_cert": {
                    "type": "boolean",
                    "title": "Verify Certificate",
                    "description": "Verify SSL certificate when using SSL/TLS",
                    "default": True
                },
                "ca_certs_file": {
                    "type": "string",
                    "title": "CA Certificates File",
                    "description": "Path to CA certificates file for SSL verification"
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for LDAP.
        
        Returns:
            Default port number
        """
        return 389 if not self.use_ssl else 636
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "LDAP"
    
    @property
    def supports_username_enumeration(self) -> bool:
        """Whether LDAP supports username enumeration.
        
        Returns:
            True as LDAP can enumerate usernames
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
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._server = None


# Register protocol
from src.protocols import protocol_registry
protocol_registry.register_protocol("ldap", LDAP)
