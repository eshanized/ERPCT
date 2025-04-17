#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTTP protocol implementation for ERPCT.
This module provides support for HTTP Basic/Digest authentication attacks.
"""

import socket
import ssl
import time
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

try:
    import requests
    from requests.auth import HTTPBasicAuth, HTTPDigestAuth
    # Disable SSL warnings
    try:
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    except:
        pass
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class HTTP(ProtocolBase):
    """HTTP protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the HTTP protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        if not REQUESTS_AVAILABLE:
            self.logger.error("requests package is required but not installed")
            raise ImportError("requests package is required for HTTP support")
        
        # Extract configuration
        self.url = config.get("url", "")
        self.method = config.get("method", "GET").upper()
        self.auth_type = config.get("auth_type", "basic").lower()  # basic, digest
        self.timeout = config.get("timeout", 10)
        self.verify_ssl = config.get("verify_ssl", True)
        self.follow_redirects = config.get("follow_redirects", True)
        self.headers = config.get("headers", {})
        self.proxy = config.get("proxy", None)
        self.success_codes = config.get("success_codes", [200, 201, 202, 203, 204, 205, 206, 207, 208, 226])
        self.failure_codes = config.get("failure_codes", [401, 403])
        
        # Check and parse URL
        if not self.url:
            raise ValueError("HTTP URL must be specified")
            
        # Parse URL to extract components
        parsed_url = urllib.parse.urlparse(self.url)
        self.scheme = parsed_url.scheme.lower()
        self.host = parsed_url.netloc
        
        # Set default port based on scheme
        if ':' in self.host:
            self.host, port_str = self.host.split(':', 1)
            self.port = int(port_str)
        else:
            self.port = 443 if self.scheme == 'https' else 80
        
        # Session for connection reuse
        self._session = None
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test HTTP authentication with the given credentials.
        
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
            
        try:
            # Get session
            session = self._get_session()
            
            # Create auth object based on auth type
            if self.auth_type == "digest":
                auth = HTTPDigestAuth(username, password)
            else:  # Default to basic
                auth = HTTPBasicAuth(username, password)
            
            # Prepare request
            request_kwargs = {
                'auth': auth,
                'timeout': self.timeout,
                'verify': self.verify_ssl,
                'allow_redirects': self.follow_redirects,
                'headers': self.headers
            }
            
            # Add proxy if configured
            if self.proxy:
                request_kwargs['proxies'] = {
                    'http': self.proxy,
                    'https': self.proxy
                }
            
            # Make request based on method
            if self.method == "GET":
                response = session.get(self.url, **request_kwargs)
            elif self.method == "POST":
                # Add empty data for POST
                request_kwargs['data'] = {}
                response = session.post(self.url, **request_kwargs)
            elif self.method == "HEAD":
                response = session.head(self.url, **request_kwargs)
            else:
                return False, f"Unsupported HTTP method: {self.method}"
            
            # Check response status code
            status_code = response.status_code
            
            # Success if status code is in success_codes but not in failure_codes
            if status_code in self.success_codes and status_code not in self.failure_codes:
                self.logger.info(f"HTTP authentication successful for user {username}")
                return True, None
            elif status_code in self.failure_codes:
                # Authentication failed with specific failure code
                return False, f"Authentication failed with status code {status_code}"
            else:
                # Unexpected status code
                error_msg = f"Unexpected status code: {status_code}"
                self.logger.warning(error_msg)
                return False, error_msg
                
        except requests.exceptions.RequestException as e:
            # Request-specific error
            error_msg = f"HTTP request error: {str(e)}"
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
    
    def _get_session(self) -> requests.Session:
        """Get a requests session, creating if necessary.
        
        Returns:
            Requests session object
        """
        if self._session is None:
            self._session = requests.Session()
            
            # Set reasonable defaults
            adapter = requests.adapters.HTTPAdapter(
                max_retries=1,
                pool_connections=10,
                pool_maxsize=10
            )
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)
        
        return self._session
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for HTTP protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "title": "URL",
                    "description": "URL to test (including http:// or https://)"
                },
                "method": {
                    "type": "string",
                    "title": "HTTP Method",
                    "description": "HTTP method to use",
                    "enum": ["GET", "POST", "HEAD"],
                    "default": "GET"
                },
                "auth_type": {
                    "type": "string",
                    "title": "Authentication Type",
                    "description": "HTTP authentication type",
                    "enum": ["basic", "digest"],
                    "default": "basic"
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout",
                    "description": "Request timeout in seconds",
                    "default": 10
                },
                "verify_ssl": {
                    "type": "boolean",
                    "title": "Verify SSL",
                    "description": "Verify SSL certificates",
                    "default": True
                },
                "follow_redirects": {
                    "type": "boolean",
                    "title": "Follow Redirects",
                    "description": "Follow HTTP redirects",
                    "default": True
                },
                "headers": {
                    "type": "object",
                    "title": "Headers",
                    "description": "Custom HTTP headers to include in requests"
                },
                "proxy": {
                    "type": "string",
                    "title": "Proxy",
                    "description": "Proxy URL (e.g., http://proxy.example.com:8080)"
                },
                "success_codes": {
                    "type": "array",
                    "title": "Success Codes",
                    "description": "HTTP status codes that indicate successful authentication",
                    "items": {
                        "type": "integer"
                    },
                    "default": [200, 201, 202, 203, 204, 205, 206, 207, 208, 226]
                },
                "failure_codes": {
                    "type": "array",
                    "title": "Failure Codes",
                    "description": "HTTP status codes that indicate failed authentication",
                    "items": {
                        "type": "integer"
                    },
                    "default": [401, 403]
                }
            },
            "required": ["url"]
        }
    
    @property
    def default_port(self) -> int:
        """Return the default port for HTTP.
        
        Returns:
            Default port number
        """
        return 80
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "HTTP"
    
    def get_options(self) -> Dict[str, Dict[str, Any]]:
        """Return configurable options for this protocol.
        
        Returns:
            Dictionary of configuration options
        """
        return {
            "url": {
                "type": "string",
                "default": "",
                "description": "Url"
            },
            "method": {
                "type": "string",
                "default": "GET",
                "description": "Method"
            },
            "auth_type": {
                "type": "string",
                "default": "basic",
                "description": "Auth Type"
            },
            "timeout": {
                "type": "integer",
                "default": 10,
                "description": "Timeout"
            },
            "verify_ssl": {
                "type": "boolean",
                "default": True,
                "description": "Verify Ssl"
            },
            "follow_redirects": {
                "type": "boolean",
                "default": True,
                "description": "Follow Redirects"
            },
            "headers": {
                "type": "string",
                "default": "{}",
                "description": "Headers"
            },
            "proxy": {
                "type": "string",
                "default": "None",
                "description": "Proxy"
            },
            "success_codes": {
                "type": "string",
                "default": "[200, 201, 202, 203, 204, 205, 206, 207, 208, 226]",
                "description": "Success Codes"
            },
            "failure_codes": {
                "type": "string",
                "default": "[401, 403]",
                "description": "Failure Codes"
            }
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._session:
            try:
                self._session.close()
            except:
                pass
            
            self._session = None


def register_protocol():
    """Register this protocol with the protocol registry."""
    from src.protocols import register_protocol
    register_protocol("http", HTTP)
