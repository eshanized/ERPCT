#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTTPS protocol implementation for ERPCT.
This module provides support for HTTPS Basic/Digest authentication attacks.
This is a thin wrapper around the HTTP protocol module.
"""

from typing import Dict, List, Optional, Tuple, Any

from src.protocols.http import HTTP, REQUESTS_AVAILABLE
from src.utils.logging import get_logger


class HTTPS(HTTP):
    """HTTPS protocol implementation for password attacks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the HTTPS protocol handler.
        
        Args:
            config: Dictionary containing protocol configuration
        """
        # Make sure URL uses HTTPS scheme
        url = config.get("url", "")
        if url and not url.lower().startswith("https://"):
            # If the URL doesn't start with https://, add it
            if "://" in url:
                # Replace existing scheme with https
                parts = url.split("://", 1)
                url = f"https://{parts[1]}"
            else:
                # No scheme at all, add https://
                url = f"https://{url}"
            
            config["url"] = url
        
        # Set verify_ssl to False by default for HTTPS
        if "verify_ssl" not in config:
            config["verify_ssl"] = True
            
        # Call parent constructor
        super().__init__(config)
    
    @property
    def default_port(self) -> int:
        """Return the default port for HTTPS.
        
        Returns:
            Default port number
        """
        return 443
    
    @property
    def name(self) -> str:
        """Return the name of the protocol.
        
        Returns:
            Protocol name
        """
        return "HTTPS"
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for HTTPS protocol.
        
        Returns:
            JSON schema for protocol configuration
        """
        # Get schema from parent class
        schema = super().get_config_schema()
        
        # Update schema properties specific to HTTPS
        schema["properties"]["url"]["description"] = "URL to test (including https://)"
        
        # Set default verify_ssl to True
        schema["properties"]["verify_ssl"]["default"] = True
        
        return schema


# Register protocol
from src.protocols import protocol_registry
protocol_registry.register_protocol("https", HTTPS)
