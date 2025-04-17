#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PostgreSQL protocol implementation for ERPCT.
This module provides support for PostgreSQL authentication attacks.
"""

import socket
import time
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    try:
        import pg8000
        POSTGRES_AVAILABLE = True
        USING_PG8000 = True
    except ImportError:
        POSTGRES_AVAILABLE = False
        USING_PG8000 = False


class PostgreSQL(ProtocolBase):
    """PostgreSQL protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the PostgreSQL protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        if not POSTGRES_AVAILABLE:
            self.logger.error("Either psycopg2 or pg8000 package is required but not installed")
            raise ImportError("Either psycopg2 or pg8000 package is required for PostgreSQL support")
        
        # Extract configuration
        self.host = config.get("host", "")
        self.port = int(config.get("port", self.default_port))
        self.database = config.get("database", "postgres")  # Default to 'postgres' database
        self.connect_timeout = config.get("timeout", 5)
        self.use_ssl = config.get("use_ssl", False)
        
        # SSL options
        if self.use_ssl:
            self.ssl_mode = config.get("ssl_mode", "require")
            self.ssl_cert = config.get("ssl_cert", None)
            self.ssl_key = config.get("ssl_key", None)
            self.ssl_rootcert = config.get("ssl_rootcert", None)
        
        if not self.host:
            raise ValueError("PostgreSQL host must be specified")
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test PostgreSQL authentication with the given credentials.
        
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
            
        # Use the appropriate library
        if 'USING_PG8000' in globals() and USING_PG8000:
            return self._test_with_pg8000(username, password)
        else:
            return self._test_with_psycopg2(username, password)
    
    def _test_with_psycopg2(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test PostgreSQL authentication using psycopg2.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            # Create connection string
            conn_params = {
                'host': self.host,
                'port': self.port,
                'user': username,
                'password': password,
                'dbname': self.database,
                'connect_timeout': self.connect_timeout
            }
            
            # Add SSL parameters if enabled
            if self.use_ssl:
                conn_params['sslmode'] = self.ssl_mode
                if self.ssl_cert:
                    conn_params['sslcert'] = self.ssl_cert
                if self.ssl_key:
                    conn_params['sslkey'] = self.ssl_key
                if self.ssl_rootcert:
                    conn_params['sslrootcert'] = self.ssl_rootcert
            
            # Attempt connection
            connection = psycopg2.connect(**conn_params)
            
            # If we got here, authentication succeeded
            # Close connection immediately
            connection.close()
            
            self.logger.info(f"PostgreSQL authentication successful for user {username}")
            return True, None
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            
            # Check if it's an authentication error
            if "password authentication failed" in error_msg.lower() or "role" in error_msg.lower() and "does not exist" in error_msg.lower():
                return False, error_msg
            else:
                # Other database error
                self.logger.error(f"PostgreSQL operational error: {error_msg}")
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
    
    def _test_with_pg8000(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test PostgreSQL authentication using pg8000.
        
        Args:
            username: Username to test
            password: Password to test
            
        Returns:
            Success status and optional message
        """
        try:
            import pg8000
            
            # Create connection parameters
            conn_params = {
                'host': self.host,
                'port': self.port,
                'user': username,
                'password': password,
                'database': self.database,
                'timeout': self.connect_timeout
            }
            
            # SSL not directly supported in the same way as psycopg2
            # but pg8000 will use SSL if server requires it
            if self.use_ssl:
                conn_params['ssl'] = True
                # Other SSL parameters not directly supported by pg8000
            
            # Attempt connection
            connection = pg8000.connect(**conn_params)
            
            # If we got here, authentication succeeded
            # Close connection immediately
            connection.close()
            
            self.logger.info(f"PostgreSQL authentication successful for user {username}")
            return True, None
            
        except pg8000.exceptions.InterfaceError as e:
            error_msg = str(e)
            
            # Check if it's an authentication error
            if "authentication" in error_msg.lower():
                return False, error_msg
            else:
                # Other interface error
                self.logger.error(f"PostgreSQL interface error: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            # Any other error
            error_msg = f"PostgreSQL error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for PostgreSQL protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "title": "PostgreSQL Server",
                    "description": "Hostname or IP address of the PostgreSQL server"
                },
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "description": "Port number for PostgreSQL service (default: 5432)",
                    "default": 5432
                },
                "database": {
                    "type": "string",
                    "title": "Database",
                    "description": "Database name to connect to",
                    "default": "postgres"
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
                "ssl_mode": {
                    "type": "string",
                    "title": "SSL Mode",
                    "description": "PostgreSQL SSL mode (psycopg2 only)",
                    "enum": ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"],
                    "default": "require"
                },
                "ssl_cert": {
                    "type": "string",
                    "title": "SSL Client Certificate",
                    "description": "Path to client certificate file for SSL (psycopg2 only)"
                },
                "ssl_key": {
                    "type": "string",
                    "title": "SSL Client Key",
                    "description": "Path to client key file for SSL (psycopg2 only)"
                },
                "ssl_rootcert": {
                    "type": "string",
                    "title": "SSL Root Certificate",
                    "description": "Path to root certificate file for SSL (psycopg2 only)"
                }
            },
            "required": ["host"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for PostgreSQL.
        
        Returns:
            Default port number
        """
        return 5432
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "PostgreSQL"

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
    register_protocol("postgresql", PostgreSQL)
