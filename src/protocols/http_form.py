#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTTP Form protocol implementation for ERPCT.
This module provides HTTP Form-based authentication capabilities for password testing.
"""

import re
import time
import random
from typing import Dict, Optional, Tuple, Any, List

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger


class HTTPFormProtocol(ProtocolBase):
    """HTTP Form authentication protocol implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the HTTP Form protocol.
        
        Args:
            config: Dictionary containing HTTP Form configuration options
        """
        self.logger = get_logger(__name__)
        
        # Target URL is required
        self.url = config.get("url")
        if not self.url:
            raise ValueError("URL must be specified for HTTP Form protocol")
            
        # Extract hostname and port from URL for consistency with other protocols
        parsed_url = urlparse(self.url)
        self.host = parsed_url.netloc
        self.port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        
        # Method and form data
        self.method = config.get("method", "POST").upper()
        self.form_data = config.get("form_data", "")
        if not self.form_data:
            raise ValueError("Form data must be specified for HTTP Form protocol")
            
        # Success and failure patterns
        self.success_match = config.get("success_match")
        self.failure_match = config.get("failure_match")
        if not self.success_match and not self.failure_match:
            raise ValueError("Either success_match or failure_match must be specified")
        
        # CSRF token handling
        self.csrf_token_field = config.get("csrf_token_field")
        self.csrf_token_url = config.get("csrf_token_url", self.url)
        self.csrf_token_regex = config.get("csrf_token_regex")
        
        # Optional settings
        self.timeout = int(config.get("timeout", 10))
        self.verify_ssl = bool(config.get("verify_ssl", True))
        self.follow_redirects = bool(config.get("follow_redirects", True))
        self.user_agent = config.get("user_agent", "ERPCT HTTP Form Authentication")
        self.captcha_detection = config.get("captcha_detection")
        
        # Headers
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": self.url,
            "Connection": "keep-alive"
        }
        
        # Additional headers from config
        if "headers" in config:
            self.headers.update(config["headers"])
        
        # Session for maintaining cookies
        self.session = requests.Session()
    
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test HTTP Form credentials.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Tuple containing (success_bool, optional_message)
        """
        self.logger.debug(f"Testing HTTP Form credentials {username}:{password} on {self.url}")
        
        try:
            # Process the form data, replacing username and password markers
            form_data = self._prepare_form_data(username, password)
            
            # Get CSRF token if needed
            if self.csrf_token_field:
                csrf_token = self._get_csrf_token()
                if csrf_token:
                    # Add CSRF token to form data
                    if self.method == "POST":
                        form_data[self.csrf_token_field] = csrf_token
                    else:  # GET
                        if "?" in self.url:
                            url = f"{self.url}&{self.csrf_token_field}={csrf_token}"
                        else:
                            url = f"{self.url}?{self.csrf_token_field}={csrf_token}"
            
            # Send the request
            if self.method == "POST":
                response = self.session.post(
                    self.url,
                    data=form_data,
                    headers=self.headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    allow_redirects=self.follow_redirects
                )
            else:  # GET
                response = self.session.get(
                    self.url,
                    params=form_data,
                    headers=self.headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    allow_redirects=self.follow_redirects
                )
            
            # Check response
            content = response.text
            
            # Check for captcha if configured
            if self.captcha_detection and re.search(self.captcha_detection, content, re.IGNORECASE):
                return False, "CAPTCHA detected"
            
            # Check for success or failure patterns
            if self.success_match and re.search(self.success_match, content, re.IGNORECASE):
                self.logger.info(f"HTTP Form authentication successful for {username} on {self.url}")
                return True, "Authentication successful"
                
            if self.failure_match and re.search(self.failure_match, content, re.IGNORECASE):
                self.logger.debug(f"HTTP Form authentication failed for {username} on {self.url}")
                return False, None
                
            # If we only have success_match and it wasn't found, authentication failed
            if self.success_match and not self.failure_match:
                self.logger.debug(f"HTTP Form authentication failed for {username} on {self.url} (success pattern not found)")
                return False, None
                
            # If we only have failure_match and it wasn't found, authentication succeeded
            if self.failure_match and not self.success_match:
                self.logger.info(f"HTTP Form authentication successful for {username} on {self.url} (failure pattern not found)")
                return True, "Authentication successful (failure pattern not found)"
            
            # If we reach here, we're not sure about the result
            self.logger.warning(f"HTTP Form authentication result unclear for {username} on {self.url}")
            return False, "Authentication result unclear"
            
        except requests.RequestException as e:
            # Connection error
            error_msg = f"HTTP Form connection error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _prepare_form_data(self, username: str, password: str) -> Dict[str, str]:
        """Prepare form data by replacing username and password markers.
        
        Args:
            username: Username to insert
            password: Password to insert
            
        Returns:
            Dictionary with form data
        """
        # For GET method, we need to parse the form data string into a dictionary
        if self.method == "GET":
            params = {}
            for param in self.form_data.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value
                else:
                    params[param] = ""
            form_data = params
        else:  # POST
            if "{" in self.form_data:  # JSON format
                import json
                form_data = json.loads(self.form_data)
            else:  # URL-encoded format
                form_data = {}
                for param in self.form_data.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        form_data[key] = value
                    else:
                        form_data[param] = ""
        
        # Replace username and password markers in all fields
        for key in form_data:
            if isinstance(form_data[key], str):
                form_data[key] = form_data[key].replace("^USER^", username).replace("^PASS^", password)
        
        return form_data
    
    def _get_csrf_token(self) -> Optional[str]:
        """Get CSRF token from the page.
        
        Returns:
            CSRF token string if found, None otherwise
        """
        try:
            response = self.session.get(
                self.csrf_token_url,
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            content = response.text
            
            # If a regex is provided, use it to find the token
            if self.csrf_token_regex:
                match = re.search(self.csrf_token_regex, content)
                if match and match.group(1):
                    return match.group(1)
            
            # Otherwise, try to find the token in a form input field
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for input field with the specified name
            input_field = soup.find('input', {'name': self.csrf_token_field})
            if input_field and input_field.get('value'):
                return input_field.get('value')
            
            # Look for meta tag with the token
            meta_field = soup.find('meta', {'name': self.csrf_token_field})
            if meta_field and meta_field.get('content'):
                return meta_field.get('content')
            
            # No token found
            self.logger.warning(f"CSRF token not found for field {self.csrf_token_field}")
            return None
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching CSRF token: {str(e)}")
            return None
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema for HTTP Form protocol.
        
        Returns:
            JSON schema object for HTTP Form configuration
        """
        return {
            "type": "object",
            "required": ["url", "form_data"],
            "properties": {
                "url": {
                    "type": "string",
                    "title": "URL",
                    "description": "Full URL of the login form"
                },
                "method": {
                    "type": "string",
                    "title": "Method",
                    "description": "HTTP method (GET/POST)",
                    "enum": ["GET", "POST"],
                    "default": "POST"
                },
                "form_data": {
                    "type": "string",
                    "title": "Form Data",
                    "description": "Form data template with ^USER^ and ^PASS^ markers"
                },
                "success_match": {
                    "type": "string",
                    "title": "Success Pattern",
                    "description": "Text pattern indicating successful login"
                },
                "failure_match": {
                    "type": "string",
                    "title": "Failure Pattern",
                    "description": "Text pattern indicating failed login"
                },
                "csrf_token_field": {
                    "type": "string",
                    "title": "CSRF Token Field",
                    "description": "Name of CSRF token field, if any"
                },
                "csrf_token_url": {
                    "type": "string",
                    "title": "CSRF Token URL",
                    "description": "URL to fetch CSRF token from (defaults to form URL)"
                },
                "csrf_token_regex": {
                    "type": "string",
                    "title": "CSRF Token Regex",
                    "description": "Regular expression to extract CSRF token"
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
                    "description": "Verify SSL certificate",
                    "default": True
                },
                "follow_redirects": {
                    "type": "boolean",
                    "title": "Follow Redirects",
                    "description": "Follow HTTP redirects",
                    "default": True
                },
                "user_agent": {
                    "type": "string",
                    "title": "User Agent",
                    "description": "User-Agent header value"
                },
                "captcha_detection": {
                    "type": "string",
                    "title": "CAPTCHA Detection",
                    "description": "Pattern to detect CAPTCHA presence"
                }
            }
        }
    
    @property
    def default_port(self) -> int:
        """Return the default HTTP port.
        
        Returns:
            Default HTTP port (80)
        """
        return 80
    
    @property
    def name(self) -> str:
        """Return the protocol name.
        
        Returns:
            Protocol name 'http-form'
        """
        return "http-form"
    
    def get_options(self) -> Dict[str, Dict[str, Any]]:
        """Return configurable options for HTTP Form protocol.
        
        Returns:
            Dictionary of configuration options
        """
        return {
            "url": {
                "type": "string",
                "default": "",
                "description": "URL of the login form"
            },
            "method": {
                "type": "select",
                "default": "POST",
                "choices": ["POST", "GET"],
                "description": "HTTP method to use"
            },
            "form_data": {
                "type": "string",
                "default": "username=^USER^&password=^PASS^",
                "description": "Form data (use ^USER^ and ^PASS^ as placeholders)"
            },
            "success_match": {
                "type": "string",
                "default": "",
                "description": "Regex pattern for successful login"
            },
            "failure_match": {
                "type": "string",
                "default": "",
                "description": "Regex pattern for failed login"
            },
            "csrf_token_field": {
                "type": "string",
                "default": "",
                "description": "Name of CSRF token field (if required)"
            },
            "csrf_token_regex": {
                "type": "string",
                "default": "",
                "description": "Regex to extract CSRF token"
            },
            "timeout": {
                "type": "integer",
                "default": 10,
                "description": "Connection timeout in seconds"
            },
            "verify_ssl": {
                "type": "boolean",
                "default": True,
                "description": "Verify SSL certificates"
            },
            "follow_redirects": {
                "type": "boolean",
                "default": True,
                "description": "Follow HTTP redirects"
            },
            "user_agent": {
                "type": "string",
                "default": "ERPCT HTTP Form Authentication",
                "description": "User-Agent header to use"
            }
        }
    
    def cleanup(self) -> None:
        """Clean up resources.
        
        Closes the HTTP session.
        """
        if hasattr(self, 'session'):
            self.session.close() 