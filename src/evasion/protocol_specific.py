#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT protocol-specific evasion module.
This module implements protocol-specific evasion techniques.
"""

import time
import random
import json
import os
from typing import Dict, Any, Optional, List, Set, Union

from src.evasion.base import EvasionBase
from src.core.protocols import Protocol


class ProtocolSpecificEvasion(EvasionBase):
    """
    Protocol-specific evasion techniques.
    
    This class implements evasion techniques specific to different
    protocols (HTTP, SSH, FTP, etc.) to avoid detection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize protocol-specific evasion.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Protocol to apply evasion for
        self.protocol = self.config.get("protocol", "http")
        
        # Load evasion configuration for the specific protocol
        protocol_config = self.config.get(self.protocol, {})
        
        # HTTP specific settings
        if self.protocol == "http" or self.protocol == "https":
            self.user_agent_rotation = protocol_config.get("user_agent_rotation", False)
            self.header_randomization = protocol_config.get("header_randomization", False)
            self.random_url_params = protocol_config.get("random_url_params", False)
            self.cookie_handling = protocol_config.get("cookie_handling", "session_based")
            self.referrer_spoofing = protocol_config.get("referrer_spoofing", False)
            
            # Load user agents if rotation is enabled
            self.user_agents = []
            if self.user_agent_rotation:
                self._load_user_agents()
            
            # Load headers if randomization is enabled
            self.headers = {}
            if self.header_randomization:
                self._load_headers()
            
            # Load referrers if spoofing is enabled
            self.referrers = []
            if self.referrer_spoofing:
                self._load_referrers()
        
        # SSH specific settings
        elif self.protocol == "ssh":
            self.client_version_rotation = protocol_config.get("client_version_rotation", False)
            self.kex_rotation = protocol_config.get("kex_rotation", False)
            self.cipher_rotation = protocol_config.get("cipher_rotation", False)
            self.banner_delay = protocol_config.get("banner_delay", [0, 0])
            self.connection_pattern = protocol_config.get("connection_pattern", "default")
            
            # Load SSH client versions if rotation is enabled
            self.ssh_client_versions = []
            if self.client_version_rotation:
                self._load_ssh_client_versions()
            
            # Load key exchange algorithms if rotation is enabled
            self.kex_algorithms = []
            if self.kex_rotation:
                self._load_kex_algorithms()
            
            # Load ciphers if rotation is enabled
            self.ciphers = []
            if self.cipher_rotation:
                self._load_ciphers()
        
        # FTP specific settings
        elif self.protocol == "ftp":
            self.mode_switching = protocol_config.get("mode_switching", False)
            self.command_pacing = protocol_config.get("command_pacing", [0, 0])
            self.welcome_delay = protocol_config.get("welcome_delay", [0, 0])
        
        # SMTP specific settings
        elif self.protocol == "smtp":
            self.greeting_rotation = protocol_config.get("greeting_rotation", False)
            self.extended_hello = protocol_config.get("extended_hello", True)
            self.domain_rotation = protocol_config.get("domain_rotation", False)
            
            # Load greeting domains if rotation is enabled
            self.domains = []
            if self.domain_rotation:
                self._load_domains()
        
        self.logger.debug(f"Initialized protocol-specific evasion for {self.protocol}")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply protocol-specific evasion before authentication.
        
        Args:
            target: Optional target information
        """
        super().pre_auth(target)
        
        if not self.enabled:
            return
        
        # Apply protocol-specific pre-auth evasion
        if self.protocol == "http" or self.protocol == "https":
            self._apply_http_pre_auth(target)
        elif self.protocol == "ssh":
            self._apply_ssh_pre_auth(target)
        elif self.protocol == "ftp":
            self._apply_ftp_pre_auth(target)
        elif self.protocol == "smtp":
            self._apply_smtp_pre_auth(target)
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply protocol-specific evasion after authentication.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        super().post_auth(success, response, target)
        
        if not self.enabled:
            return
        
        # Apply protocol-specific post-auth evasion
        if self.protocol == "http" or self.protocol == "https":
            self._apply_http_post_auth(success, response, target)
        elif self.protocol == "ssh":
            self._apply_ssh_post_auth(success, response, target)
        elif self.protocol == "ftp":
            self._apply_ftp_post_auth(success, response, target)
        elif self.protocol == "smtp":
            self._apply_smtp_post_auth(success, response, target)
    
    def _apply_http_pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply HTTP-specific evasion before authentication.
        
        Args:
            target: Optional target information
        """
        # Modify the target connection parameters if present
        if not target:
            return
        
        request_params = target.get("request_params", {})
        
        # Apply user agent rotation
        if self.user_agent_rotation and self.user_agents:
            user_agent = random.choice(self.user_agents)
            headers = request_params.get("headers", {})
            headers["User-Agent"] = user_agent
            request_params["headers"] = headers
            self.logger.debug(f"Set User-Agent: {user_agent}")
        
        # Apply header randomization
        if self.header_randomization and self.headers:
            headers = request_params.get("headers", {})
            for header, values in self.headers.items():
                if random.random() < 0.7:  # 70% chance to include each header
                    headers[header] = random.choice(values)
            request_params["headers"] = headers
            self.logger.debug(f"Applied header randomization")
        
        # Apply referrer spoofing
        if self.referrer_spoofing and self.referrers:
            referrer = random.choice(self.referrers)
            headers = request_params.get("headers", {})
            headers["Referer"] = referrer
            request_params["headers"] = headers
            self.logger.debug(f"Set Referer: {referrer}")
        
        # Apply random URL parameters
        if self.random_url_params:
            url = request_params.get("url", "")
            if url:
                # Add random parameters
                param_count = random.randint(1, 3)
                random_params = []
                for _ in range(param_count):
                    param_name = f"r{random.randint(1000, 9999)}"
                    param_value = f"{random.randint(1000, 9999)}"
                    random_params.append(f"{param_name}={param_value}")
                
                # Add to URL
                if "?" in url:
                    url += "&" + "&".join(random_params)
                else:
                    url += "?" + "&".join(random_params)
                
                request_params["url"] = url
                self.logger.debug(f"Added random URL parameters")
        
        # Update target with modified parameters
        target["request_params"] = request_params
    
    def _apply_http_post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply HTTP-specific evasion after authentication.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        # Process cookies if cookie handling is enabled
        if self.cookie_handling != "none" and response:
            self._process_cookies(response, target)
    
    def _process_cookies(self, response: Any, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Process cookies from HTTP response.
        
        Args:
            response: The response object
            target: Optional target information
        """
        if not target:
            return
        
        # Extract cookies from response
        cookies = getattr(response, "cookies", None)
        if not cookies:
            return
        
        # Update cookies in target
        request_params = target.get("request_params", {})
        headers = request_params.get("headers", {})
        
        # Combine existing cookies with new ones
        if "Cookie" in headers:
            existing_cookies = headers["Cookie"]
            for cookie_name, cookie_value in cookies.items():
                if cookie_name not in existing_cookies:
                    existing_cookies += f"; {cookie_name}={cookie_value}"
            headers["Cookie"] = existing_cookies
        else:
            cookie_str = "; ".join([f"{name}={value}" for name, value in cookies.items()])
            headers["Cookie"] = cookie_str
        
        request_params["headers"] = headers
        target["request_params"] = request_params
        self.logger.debug(f"Updated cookies from response")
    
    def _apply_ssh_pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply SSH-specific evasion before authentication.
        
        Args:
            target: Optional target information
        """
        if not target:
            return
        
        ssh_params = target.get("ssh_params", {})
        
        # Apply client version rotation
        if self.client_version_rotation and self.ssh_client_versions:
            client_version = random.choice(self.ssh_client_versions)
            ssh_params["client_version"] = client_version
            self.logger.debug(f"Set SSH client version: {client_version}")
        
        # Apply key exchange algorithm rotation
        if self.kex_rotation and self.kex_algorithms:
            kex_algo = random.choice(self.kex_algorithms)
            ssh_params["kex_algorithm"] = kex_algo
            self.logger.debug(f"Set SSH key exchange algorithm: {kex_algo}")
        
        # Apply cipher rotation
        if self.cipher_rotation and self.ciphers:
            cipher = random.choice(self.ciphers)
            ssh_params["cipher"] = cipher
            self.logger.debug(f"Set SSH cipher: {cipher}")
        
        # Apply banner delay
        if self.banner_delay and self.banner_delay[1] > 0:
            min_delay, max_delay = self.banner_delay
            delay = random.uniform(min_delay, max_delay)
            ssh_params["banner_delay"] = delay
            self.logger.debug(f"Set SSH banner delay: {delay:.2f}s")
        
        # Update target with modified parameters
        target["ssh_params"] = ssh_params
    
    def _apply_ssh_post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply SSH-specific evasion after authentication.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        pass  # No specific post-auth evasion for SSH currently
    
    def _apply_ftp_pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply FTP-specific evasion before authentication.
        
        Args:
            target: Optional target information
        """
        if not target:
            return
        
        ftp_params = target.get("ftp_params", {})
        
        # Apply passive/active mode switching
        if self.mode_switching:
            # Randomly switch between passive and active mode
            passive = random.choice([True, False])
            ftp_params["passive"] = passive
            self.logger.debug(f"Set FTP {'passive' if passive else 'active'} mode")
        
        # Apply welcome delay
        if self.welcome_delay and self.welcome_delay[1] > 0:
            min_delay, max_delay = self.welcome_delay
            delay = random.uniform(min_delay, max_delay)
            ftp_params["welcome_delay"] = delay
            self.logger.debug(f"Set FTP welcome delay: {delay:.2f}s")
        
        # Update target with modified parameters
        target["ftp_params"] = ftp_params
    
    def _apply_ftp_post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply FTP-specific evasion after authentication.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        pass  # No specific post-auth evasion for FTP currently
    
    def _apply_smtp_pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply SMTP-specific evasion before authentication.
        
        Args:
            target: Optional target information
        """
        if not target:
            return
        
        smtp_params = target.get("smtp_params", {})
        
        # Apply greeting rotation
        if self.greeting_rotation:
            # Switch between HELO and EHLO
            use_ehlo = self.extended_hello and random.choice([True, False])
            smtp_params["extended_hello"] = use_ehlo
            self.logger.debug(f"Using {'EHLO' if use_ehlo else 'HELO'} for SMTP greeting")
        
        # Apply domain rotation
        if self.domain_rotation and self.domains:
            domain = random.choice(self.domains)
            smtp_params["local_hostname"] = domain
            self.logger.debug(f"Set SMTP local hostname: {domain}")
        
        # Update target with modified parameters
        target["smtp_params"] = smtp_params
    
    def _apply_smtp_post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply SMTP-specific evasion after authentication.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        pass  # No specific post-auth evasion for SMTP currently
    
    def _load_user_agents(self) -> None:
        """Load a list of user agents."""
        # Common user agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.254"
        ]
        
        # Try to load from file if specified
        user_agents_file = self.config.get("user_agents_file")
        if user_agents_file and os.path.exists(user_agents_file):
            try:
                with open(user_agents_file, 'r') as f:
                    agents = [line.strip() for line in f if line.strip()]
                    if agents:
                        self.user_agents = agents
                        self.logger.debug(f"Loaded {len(agents)} user agents from {user_agents_file}")
            except Exception as e:
                self.logger.error(f"Error loading user agents from {user_agents_file}: {str(e)}")
    
    def _load_headers(self) -> None:
        """Load HTTP headers for randomization."""
        # Common headers and values
        self.headers = {
            "Accept": [
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            ],
            "Accept-Language": [
                "en-US,en;q=0.9",
                "en-US,en;q=0.8,fr;q=0.5",
                "en-GB,en;q=0.9,en-US;q=0.8",
                "en-CA,en-US;q=0.9,en;q=0.8",
                "en-AU,en;q=0.9,en-US;q=0.8"
            ],
            "Accept-Encoding": [
                "gzip, deflate, br",
                "gzip, deflate",
                "br;q=1.0, gzip;q=0.8, *;q=0.1"
            ],
            "Connection": [
                "keep-alive",
                "close"
            ],
            "DNT": [
                "1",
                "0"
            ],
            "Upgrade-Insecure-Requests": [
                "1"
            ],
            "Cache-Control": [
                "max-age=0",
                "no-cache",
                "no-store"
            ]
        }
        
        # Try to load from file if specified
        headers_file = self.config.get("headers_file")
        if headers_file and os.path.exists(headers_file):
            try:
                with open(headers_file, 'r') as f:
                    custom_headers = json.load(f)
                    if isinstance(custom_headers, dict):
                        self.headers.update(custom_headers)
                        self.logger.debug(f"Loaded headers from {headers_file}")
            except Exception as e:
                self.logger.error(f"Error loading headers from {headers_file}: {str(e)}")
    
    def _load_referrers(self) -> None:
        """Load referrers for spoofing."""
        # Common referrers
        self.referrers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://search.yahoo.com/",
            "https://duckduckgo.com/",
            "https://www.facebook.com/",
            "https://www.twitter.com/",
            "https://www.linkedin.com/",
            "https://www.reddit.com/"
        ]
        
        # Try to load from file if specified
        referrers_file = self.config.get("referrers_file")
        if referrers_file and os.path.exists(referrers_file):
            try:
                with open(referrers_file, 'r') as f:
                    refs = [line.strip() for line in f if line.strip()]
                    if refs:
                        self.referrers = refs
                        self.logger.debug(f"Loaded {len(refs)} referrers from {referrers_file}")
            except Exception as e:
                self.logger.error(f"Error loading referrers from {referrers_file}: {str(e)}")
    
    def _load_ssh_client_versions(self) -> None:
        """Load SSH client versions for rotation."""
        # Common SSH client versions
        self.ssh_client_versions = [
            "SSH-2.0-OpenSSH_8.4",
            "SSH-2.0-OpenSSH_7.9",
            "SSH-2.0-OpenSSH_8.2",
            "SSH-2.0-PuTTY_0.74",
            "SSH-2.0-paramiko_2.7.1"
        ]
        
        # Try to load from file if specified
        versions_file = self.config.get("ssh_versions_file")
        if versions_file and os.path.exists(versions_file):
            try:
                with open(versions_file, 'r') as f:
                    versions = [line.strip() for line in f if line.strip()]
                    if versions:
                        self.ssh_client_versions = versions
                        self.logger.debug(f"Loaded {len(versions)} SSH client versions from {versions_file}")
            except Exception as e:
                self.logger.error(f"Error loading SSH client versions from {versions_file}: {str(e)}")
    
    def _load_kex_algorithms(self) -> None:
        """Load SSH key exchange algorithms for rotation."""
        # Common key exchange algorithms
        self.kex_algorithms = [
            "curve25519-sha256",
            "diffie-hellman-group-exchange-sha256",
            "diffie-hellman-group14-sha256",
            "diffie-hellman-group16-sha512"
        ]
        
        # Try to load from file if specified
        kex_file = self.config.get("kex_file")
        if kex_file and os.path.exists(kex_file):
            try:
                with open(kex_file, 'r') as f:
                    algorithms = [line.strip() for line in f if line.strip()]
                    if algorithms:
                        self.kex_algorithms = algorithms
                        self.logger.debug(f"Loaded {len(algorithms)} key exchange algorithms from {kex_file}")
            except Exception as e:
                self.logger.error(f"Error loading key exchange algorithms from {kex_file}: {str(e)}")
    
    def _load_ciphers(self) -> None:
        """Load SSH ciphers for rotation."""
        # Common SSH ciphers
        self.ciphers = [
            "aes128-ctr",
            "aes192-ctr",
            "aes256-ctr",
            "chacha20-poly1305@openssh.com"
        ]
        
        # Try to load from file if specified
        ciphers_file = self.config.get("ciphers_file")
        if ciphers_file and os.path.exists(ciphers_file):
            try:
                with open(ciphers_file, 'r') as f:
                    ciphers = [line.strip() for line in f if line.strip()]
                    if ciphers:
                        self.ciphers = ciphers
                        self.logger.debug(f"Loaded {len(ciphers)} SSH ciphers from {ciphers_file}")
            except Exception as e:
                self.logger.error(f"Error loading SSH ciphers from {ciphers_file}: {str(e)}")
    
    def _load_domains(self) -> None:
        """Load domains for SMTP rotation."""
        # Common domains
        self.domains = [
            "localhost",
            "client.example.com",
            "mail-client.example.net",
            "smtp-client.local"
        ]
        
        # Try to load from file if specified
        domains_file = self.config.get("domains_file")
        if domains_file and os.path.exists(domains_file):
            try:
                with open(domains_file, 'r') as f:
                    domains = [line.strip() for line in f if line.strip()]
                    if domains:
                        self.domains = domains
                        self.logger.debug(f"Loaded {len(domains)} domains from {domains_file}")
            except Exception as e:
                self.logger.error(f"Error loading domains from {domains_file}: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about protocol-specific evasion.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_stats()
        
        # Add protocol-specific stats
        protocol_stats = {
            "protocol": self.protocol
        }
        
        # HTTP/HTTPS specific stats
        if self.protocol == "http" or self.protocol == "https":
            protocol_stats.update({
                "user_agent_rotation": self.user_agent_rotation,
                "user_agents_count": len(self.user_agents) if self.user_agent_rotation else 0,
                "header_randomization": self.header_randomization,
                "random_url_params": self.random_url_params,
                "referrer_spoofing": self.referrer_spoofing
            })
        
        # SSH specific stats
        elif self.protocol == "ssh":
            protocol_stats.update({
                "client_version_rotation": self.client_version_rotation,
                "kex_rotation": self.kex_rotation,
                "cipher_rotation": self.cipher_rotation,
                "banner_delay": self.banner_delay
            })
        
        # FTP specific stats
        elif self.protocol == "ftp":
            protocol_stats.update({
                "mode_switching": self.mode_switching,
                "command_pacing": self.command_pacing,
                "welcome_delay": self.welcome_delay
            })
        
        # SMTP specific stats
        elif self.protocol == "smtp":
            protocol_stats.update({
                "greeting_rotation": self.greeting_rotation,
                "extended_hello": self.extended_hello,
                "domain_rotation": self.domain_rotation
            })
        
        stats["protocol_specific"] = protocol_stats
        return stats
