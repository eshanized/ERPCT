#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SMTP protocol implementation for ERPCT.
This module provides support for SMTP authentication attacks.
"""

import socket
import ssl
import time
import smtplib
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger


class SMTP(ProtocolBase):
    """SMTP protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the SMTP protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.use_ssl = config.get("use_ssl", False)
        self.use_tls = config.get("use_tls", True)
        self.timeout = config.get("timeout", 10)
        self.domain = config.get("domain", "example.com")
        self.auth_method = config.get("auth_method", "auto").lower()  # auto, plain, login, cram-md5
        
        # Connection pooling
        self._connection = None
        self._conn_last_used = 0
        self._conn_max_idle = 30  # Seconds to keep connection open
        
        if not self.host:
            raise ValueError("SMTP host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test SMTP authentication with the given credentials.
        
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
            
        try:
            # Get connection
            smtp = self._get_connection()
            
            # Attempt login
            smtp.login(username, password)
            
            # If we got here, authentication succeeded
            self.logger.info(f"SMTP authentication successful for user {username}")
            return True, None
            
        except smtplib.SMTPAuthenticationError as e:
            # Authentication failed normally
            return False, str(e)
            
        except smtplib.SMTPException as e:
            # General SMTP error
            error_msg = str(e)
            self.logger.error(f"SMTP error: {error_msg}")
            
            # Connection might be in a bad state, reset it
            self._reset_connection()
            
            return False, error_msg
            
        except (socket.timeout, socket.error, ConnectionError, ssl.SSLError) as e:
            # Network error
            error_msg = f"Network error: {str(e)}"
            self.logger.error(error_msg)
            
            # Connection is definitely broken, reset it
            self._reset_connection()
            
            return False, error_msg
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            
            # Reset connection to be safe
            self._reset_connection()
            
            return False, error_msg
    
    def _get_connection(self) -> smtplib.SMTP:
        """Get an SMTP connection, reusing an existing one if possible.
        
        Returns:
            SMTP connection object
        """
        # Check if we have a connection and it's still fresh
        current_time = time.time()
        if (self._connection is not None and 
            current_time - self._conn_last_used < self._conn_max_idle):
            try:
                # Test connection with a NOOP
                self._connection.noop()
                self._conn_last_used = current_time
                return self._connection
            except:
                # Connection is dead, create a new one
                self._reset_connection()
        
        # Create new connection
        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(
                host=self.host,
                port=self.port,
                timeout=self.timeout
            )
        else:
            smtp = smtplib.SMTP(
                host=self.host,
                port=self.port,
                timeout=self.timeout
            )
            
            # Start TLS if requested
            if self.use_tls:
                try:
                    smtp.starttls()
                except (smtplib.SMTPException, ssl.SSLError) as e:
                    self.logger.warning(f"TLS failed, continuing without encryption: {str(e)}")
        
        # Say EHLO
        smtp.ehlo(self.domain)
        
        # Store and return connection
        self._connection = smtp
        self._conn_last_used = current_time
        return smtp
    
    def _reset_connection(self) -> None:
        """Close and reset the current connection."""
        if self._connection:
            try:
                self._connection.quit()
            except:
                # Ignore errors during quit
                pass
                
            self._connection = None
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for SMTP protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "SMTP Server",
                    "description": "Hostname or IP address of the SMTP server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for SMTP service (default: 25)",
                    "default": 25
                },
                "use_ssl": {
                    "type": "boolean",
                    "title": "Use SSL",
                    "description": "Connect using SSL (SMTPS)",
                    "default": False
                },
                "use_tls": {
                    "type": "boolean",
                    "title": "Use STARTTLS",
                    "description": "Use STARTTLS to encrypt connection",
                    "default": True
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
                    "description": "Domain name to use in EHLO command",
                    "default": "example.com"
                },
                "auth_method": {
                    "type": "string",
                    "title": "Authentication Method",
                    "description": "SMTP authentication method to use",
                    "enum": ["auto", "plain", "login", "cram-md5"],
                    "default": "auto"
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for SMTP.
        
        Returns:
            Default port number
        """
        return 25
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "SMTP"
    
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
        self._reset_connection()


# Register protocol



def register_protocol():
    """Register this protocol with the protocol registry."""
    from src.protocols import register_protocol
    register_protocol("smtp", SMTP)
