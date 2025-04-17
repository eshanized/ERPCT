#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MySQL protocol implementation for ERPCT.
This module provides support for MySQL authentication attacks.
"""

import socket
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


class MySQL(ProtocolBase):
    """MySQL protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the MySQL protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        if not MYSQL_AVAILABLE:
            self.logger.error("mysql-connector-python package is required but not installed")
            raise ImportError("mysql-connector-python package is required for MySQL support")
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.database = config.get("database", "")
        self.connect_timeout = int(config.get("timeout", 5))
        self.use_ssl = config.get("use_ssl", False)
        
        # SSL options
        if self.use_ssl:
            self.ssl_ca = config.get("ssl_ca", None)
            self.ssl_cert = config.get("ssl_cert", None)
            self.ssl_key = config.get("ssl_key", None)
        
        # Connection pooling
        self._connection = None
        self._conn_last_used = 0
        self._conn_max_idle = 30  # Seconds to keep connection open
        
        if not self.host:
            raise ValueError("MySQL host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test MySQL authentication with the given credentials.
        
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
            
        # None password is valid in MySQL if configured that way, so don't check that
        
        try:
            # Create connection config
            conn_config = {
                'user': username,
                'password': password,
                'host': self.host,
                'port': self.port,
                'connection_timeout': self.connect_timeout,
                'raise_on_warnings': True
            }
            
            # Add database if specified
            if self.database:
                conn_config['database'] = self.database
                
            # Add SSL config if enabled
            if self.use_ssl:
                ssl_config = {}
                if self.ssl_ca:
                    ssl_config['ca'] = self.ssl_ca
                if self.ssl_cert:
                    ssl_config['cert'] = self.ssl_cert
                if self.ssl_key:
                    ssl_config['key'] = self.ssl_key
                
                if ssl_config:
                    conn_config['ssl_ca'] = ssl_config.get('ca')
                    conn_config['ssl_cert'] = ssl_config.get('cert')
                    conn_config['ssl_key'] = ssl_config.get('key')
            
            # Attempt connection
            connection = mysql.connector.connect(**conn_config)
            
            # If we got here, authentication succeeded
            # Close connection immediately
            connection.close()
            
            self.logger.info(f"MySQL authentication successful for user {username}")
            return True, None
            
        except mysql.connector.Error as e:
            # Authentication failed or database error
            error_code = e.errno if hasattr(e, 'errno') else None
            
            # Check if it's an authentication error
            if error_code == 1045:  # Access denied for user
                return False, str(e)
            else:
                # Other database error
                error_msg = f"MySQL error ({error_code}): {str(e)}"
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
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for MySQL protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "MySQL Server",
                    "description": "Hostname or IP address of the MySQL server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for MySQL service (default: 3306)",
                    "default": 3306
                },
                "database": {
                    "type": "string",
                    "title": "Database",
                    "description": "Optional database name to connect to"
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout",
                    "description": "Connection timeout in seconds",
                    "default": 5
                },
                "use_ssl": {
                    "type": "boolean",
                    "title": "Use SSL",
                    "description": "Use SSL for connection encryption",
                    "default": False
                },
                "ssl_ca": {
                    "type": "string",
                    "title": "SSL CA Certificate",
                    "description": "Path to CA certificate file for SSL"
                },
                "ssl_cert": {
                    "type": "string",
                    "title": "SSL Client Certificate",
                    "description": "Path to client certificate file for SSL"
                },
                "ssl_key": {
                    "type": "string",
                    "title": "SSL Client Key",
                    "description": "Path to client key file for SSL"
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for MySQL.
        
        Returns:
            Default port number
        """
        return 3306
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "MySQL"


# Register protocol
from src.protocols import protocol_registry
protocol_registry.register_protocol("mysql", MySQL)
