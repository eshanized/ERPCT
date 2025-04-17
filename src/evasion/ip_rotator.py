#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT IP rotator module.
This module implements IP rotation strategies for evading detection.
"""

import time
import random
import socket
import ipaddress
import subprocess
from typing import Dict, Any, Optional, List, Union, Tuple, Set

from src.evasion.base import EvasionBase
from src.utils.logging import get_logger


class IPRotator(EvasionBase):
    """
    IP rotator for evading detection.
    
    This class implements IP rotation strategies, including:
    - Proxy rotation
    - Local IP rotation (for multi-homed systems)
    - VPN rotation (if supported)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the IP rotator.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Rotation strategy
        self.strategy = self.config.get("strategy", "round_robin")  # round_robin, random, sequential
        
        # IP sources
        self.proxy_list = self.config.get("proxy_list", [])
        self.source_ips = self.config.get("source_ips", [])
        self.vpn_providers = self.config.get("vpn_providers", [])
        
        # Local network interfaces
        self.use_local_interfaces = self.config.get("use_local_interfaces", False)
        if self.use_local_interfaces:
            self._discover_local_interfaces()
        
        # Rotation settings
        self.rotation_interval = self.config.get("rotation_interval", 10)  # Number of attempts before rotation
        self.failed_threshold = self.config.get("failed_threshold", 3)  # Number of failures before blacklisting
        
        # Proxy format: {"host": "1.2.3.4", "port": 8080, "username": "user", "password": "pass", "type": "http"}
        
        # State
        self.current_ip_index = 0
        self.attempt_count = 0
        self.ip_history = []  # List of (ip, timestamp) tuples
        self.blacklisted_ips = set()  # Set of blacklisted IPs
        self.ip_failures = {}  # IP -> failure count
        
        # Check if we have valid sources
        if not self.proxy_list and not self.source_ips and not self.vpn_providers and not self.use_local_interfaces:
            self.logger.warning("No IP rotation sources configured")
        
        # Initialize rotation state
        self._update_current_ip()
        
        self.logger.debug(f"IPRotator initialized with strategy={self.strategy}, "
                         f"sources={len(self.proxy_list)} proxies, {len(self.source_ips)} source IPs, "
                         f"{len(self.vpn_providers)} VPN providers")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply IP rotation before authentication attempt.
        
        Args:
            target: Optional target information
        """
        super().pre_auth(target)
        
        if not self.enabled or not target:
            return
        
        # Check if we need to rotate based on attempt count
        self.attempt_count += 1
        if self.attempt_count >= self.rotation_interval:
            self.rotate_ip()
            self.attempt_count = 0
        
        # Apply current IP to target
        self._apply_ip_to_target(target)
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Handle results after authentication attempt.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        super().post_auth(success, response, target)
        
        if not self.enabled or not target:
            return
        
        # Get the IP that was used
        used_ip = self._get_current_ip_representation()
        
        # Update failure count
        if not success:
            if used_ip not in self.ip_failures:
                self.ip_failures[used_ip] = 0
            
            self.ip_failures[used_ip] += 1
            
            # Check if we should blacklist this IP
            if self.ip_failures[used_ip] >= self.failed_threshold:
                self.blacklist_ip(used_ip)
                self.rotate_ip()  # Force an IP rotation
    
    def rotate_ip(self) -> bool:
        """
        Rotate to the next IP based on strategy.
        
        Returns:
            True if rotated successfully, False otherwise
        """
        if not self.enabled:
            return False
            
        # Get all available IPs (excluding blacklisted ones)
        available_ips = self._get_available_sources()
        
        if not available_ips:
            self.logger.warning("No available IPs for rotation")
            return False
        
        # Apply strategy
        if self.strategy == "round_robin":
            self.current_ip_index = (self.current_ip_index + 1) % len(available_ips)
        elif self.strategy == "random":
            self.current_ip_index = random.randint(0, len(available_ips) - 1)
        elif self.strategy == "sequential":
            self.current_ip_index = (self.current_ip_index + 1) % len(available_ips)
        
        # Update current IP
        success = self._update_current_ip()
        
        if success:
            # Record in history
            current_ip = self._get_current_ip_representation()
            self.ip_history.append((current_ip, time.time()))
            
            # Keep history manageable
            if len(self.ip_history) > 100:
                self.ip_history = self.ip_history[-100:]
            
            self.logger.info(f"Rotated to IP: {current_ip}")
        
        return success
    
    def blacklist_ip(self, ip: str) -> None:
        """
        Blacklist an IP from future use.
        
        Args:
            ip: IP address to blacklist
        """
        self.blacklisted_ips.add(ip)
        self.logger.info(f"Blacklisted IP: {ip}")
    
    def _get_available_sources(self) -> List[Union[Dict[str, Any], str]]:
        """
        Get all available IP sources, excluding blacklisted ones.
        
        Returns:
            List of available sources (proxies, IPs, etc.)
        """
        sources = []
        
        # Add proxies
        for proxy in self.proxy_list:
            proxy_str = self._proxy_to_string(proxy)
            if proxy_str not in self.blacklisted_ips:
                sources.append(proxy)
        
        # Add source IPs
        for ip in self.source_ips:
            if ip not in self.blacklisted_ips:
                sources.append(ip)
        
        # Add VPN providers
        for vpn in self.vpn_providers:
            vpn_str = vpn.get("name", "")
            if vpn_str and vpn_str not in self.blacklisted_ips:
                sources.append(vpn)
        
        # Add local interfaces
        if self.use_local_interfaces:
            for iface in self.local_interfaces:
                if iface.get("ip") not in self.blacklisted_ips:
                    sources.append(iface)
        
        return sources
    
    def _update_current_ip(self) -> bool:
        """
        Update the current IP based on the selected index.
        
        Returns:
            True if updated successfully, False otherwise
        """
        available_sources = self._get_available_sources()
        
        if not available_sources:
            self.logger.warning("No available IP sources")
            return False
        
        if self.current_ip_index >= len(available_sources):
            self.current_ip_index = 0
        
        current_source = available_sources[self.current_ip_index]
        
        # Handle different source types
        if isinstance(current_source, dict) and "type" in current_source:
            # Proxy
            if current_source.get("type", "").lower() in ["http", "https", "socks4", "socks5"]:
                self.current_source = current_source
                return True
            
            # VPN
            elif "name" in current_source:
                # Try to connect to VPN
                vpn_name = current_source.get("name", "")
                vpn_config = current_source.get("config", "")
                
                if vpn_name and vpn_config:
                    success = self._connect_to_vpn(vpn_name, vpn_config)
                    if success:
                        self.current_source = current_source
                        return True
                    else:
                        self.blacklist_ip(vpn_name)
                        return False
            
            # Local interface
            elif "interface" in current_source:
                self.current_source = current_source
                return True
        
        # Direct IP
        elif isinstance(current_source, str):
            try:
                # Validate IP
                ipaddress.ip_address(current_source)
                self.current_source = {"ip": current_source}
                return True
            except ValueError:
                self.logger.warning(f"Invalid IP address: {current_source}")
                self.blacklist_ip(current_source)
                return False
        
        self.logger.warning(f"Unknown source type: {current_source}")
        return False
    
    def _apply_ip_to_target(self, target: Dict[str, Any]) -> None:
        """
        Apply the current IP to the target configuration.
        
        Args:
            target: Target configuration
        """
        if not hasattr(self, "current_source") or not self.current_source:
            return
        
        source = self.current_source
        
        # Handle proxy
        if isinstance(source, dict) and "type" in source and source.get("type", "").lower() in ["http", "https", "socks4", "socks5"]:
            # Set proxy in target
            if "request_params" not in target:
                target["request_params"] = {}
            
            proxy_url = self._get_proxy_url(source)
            target["request_params"]["proxy"] = proxy_url
            self.logger.debug(f"Applied proxy: {proxy_url}")
        
        # Handle direct IP
        elif isinstance(source, dict) and "ip" in source:
            # Set source IP in target
            if "connection_params" not in target:
                target["connection_params"] = {}
            
            target["connection_params"]["source_ip"] = source["ip"]
            self.logger.debug(f"Applied source IP: {source['ip']}")
        
        # Handle local interface
        elif isinstance(source, dict) and "interface" in source and "ip" in source:
            # Set source interface in target
            if "connection_params" not in target:
                target["connection_params"] = {}
            
            target["connection_params"]["source_ip"] = source["ip"]
            target["connection_params"]["source_interface"] = source["interface"]
            self.logger.debug(f"Applied source interface: {source['interface']} ({source['ip']})")
    
    def _get_current_ip_representation(self) -> str:
        """
        Get a string representation of the current IP.
        
        Returns:
            String representation of the current IP
        """
        if not hasattr(self, "current_source") or not self.current_source:
            return "unknown"
        
        source = self.current_source
        
        # Proxy
        if isinstance(source, dict) and "type" in source and source.get("type", "").lower() in ["http", "https", "socks4", "socks5"]:
            return self._proxy_to_string(source)
        
        # Direct IP
        elif isinstance(source, dict) and "ip" in source:
            return source["ip"]
        
        # VPN
        elif isinstance(source, dict) and "name" in source:
            return source["name"]
        
        # Local interface
        elif isinstance(source, dict) and "interface" in source and "ip" in source:
            return f"{source['interface']}({source['ip']})"
        
        return str(source)
    
    def _proxy_to_string(self, proxy: Dict[str, Any]) -> str:
        """
        Convert a proxy dict to a string representation.
        
        Args:
            proxy: Proxy dictionary
            
        Returns:
            String representation of the proxy
        """
        host = proxy.get("host", "")
        port = proxy.get("port", "")
        
        if host and port:
            return f"{host}:{port}"
        return str(proxy)
    
    def _get_proxy_url(self, proxy: Dict[str, Any]) -> str:
        """
        Convert a proxy dict to a URL format.
        
        Args:
            proxy: Proxy dictionary
            
        Returns:
            Proxy URL
        """
        proxy_type = proxy.get("type", "http").lower()
        host = proxy.get("host", "")
        port = proxy.get("port", "")
        username = proxy.get("username", "")
        password = proxy.get("password", "")
        
        if not host or not port:
            return ""
        
        # Build auth string if credentials are provided
        auth = ""
        if username:
            auth = username
            if password:
                auth += f":{password}"
            auth += "@"
        
        return f"{proxy_type}://{auth}{host}:{port}"
    
    def _discover_local_interfaces(self) -> None:
        """Discover local network interfaces with IP addresses."""
        self.local_interfaces = []
        
        try:
            # Get all interfaces
            import netifaces
            
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                
                # Get IPv4 addresses
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr.get("addr")
                        if ip and not ip.startswith("127."):
                            self.local_interfaces.append({
                                "interface": iface,
                                "ip": ip,
                                "netmask": addr.get("netmask", ""),
                                "broadcast": addr.get("broadcast", "")
                            })
            
            self.logger.debug(f"Discovered {len(self.local_interfaces)} local interfaces")
            
        except ImportError:
            self.logger.warning("netifaces module not available, cannot discover interfaces")
            self.use_local_interfaces = False
    
    def _connect_to_vpn(self, vpn_name: str, vpn_config: str) -> bool:
        """
        Connect to a VPN provider.
        
        Args:
            vpn_name: VPN provider name
            vpn_config: VPN configuration
            
        Returns:
            True if connected successfully, False otherwise
        """
        # This is a placeholder - actual implementation would depend on the VPN solution
        self.logger.warning(f"VPN rotation not fully implemented: {vpn_name}")
        return False
    
    def add_proxy(self, host: str, port: int, 
                  proxy_type: str = "http", 
                  username: str = "", 
                  password: str = "") -> None:
        """
        Add a proxy to the proxy list.
        
        Args:
            host: Proxy host
            port: Proxy port
            proxy_type: Proxy type (http, https, socks4, socks5)
            username: Optional username for authentication
            password: Optional password for authentication
        """
        proxy = {
            "host": host,
            "port": port,
            "type": proxy_type.lower(),
            "username": username,
            "password": password
        }
        self.proxy_list.append(proxy)
        self.logger.debug(f"Added proxy: {host}:{port} ({proxy_type})")
    
    def add_source_ip(self, ip: str) -> None:
        """
        Add a source IP to the source IP list.
        
        Args:
            ip: IP address
        """
        try:
            # Validate IP
            ipaddress.ip_address(ip)
            self.source_ips.append(ip)
            self.logger.debug(f"Added source IP: {ip}")
        except ValueError:
            self.logger.warning(f"Invalid IP address: {ip}")
    
    def load_proxies_from_file(self, filename: str) -> int:
        """
        Load proxies from a file.
        
        Args:
            filename: Path to proxy list file
            
        Returns:
            Number of proxies loaded
        """
        count = 0
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse proxy format (various formats supported)
                    # Format 1: host:port
                    # Format 2: type://host:port
                    # Format 3: type://username:password@host:port
                    # Format 4: host:port:username:password:type
                    
                    proxy_type = "http"
                    username = ""
                    password = ""
                    
                    if '://' in line:
                        # Format 2 or 3
                        parts = line.split('://', 1)
                        proxy_type = parts[0].lower()
                        
                        if '@' in parts[1]:
                            # Format 3
                            auth, hostport = parts[1].rsplit('@', 1)
                            if ':' in auth:
                                username, password = auth.split(':', 1)
                        else:
                            # Format 2
                            hostport = parts[1]
                        
                        if ':' in hostport:
                            host, port = hostport.split(':', 1)
                            try:
                                port = int(port)
                                self.add_proxy(host, port, proxy_type, username, password)
                                count += 1
                            except ValueError:
                                self.logger.warning(f"Invalid port in line: {line}")
                        
                    elif line.count(':') >= 1:
                        parts = line.split(':')
                        
                        if len(parts) >= 2:
                            # Format 1
                            host = parts[0]
                            try:
                                port = int(parts[1])
                                
                                # Check for Format 4
                                if len(parts) >= 5:
                                    username = parts[2]
                                    password = parts[3]
                                    proxy_type = parts[4].lower()
                                elif len(parts) >= 3:
                                    # Format with just type at the end
                                    proxy_type = parts[2].lower()
                                
                                self.add_proxy(host, port, proxy_type, username, password)
                                count += 1
                            except ValueError:
                                self.logger.warning(f"Invalid port in line: {line}")
            
            self.logger.info(f"Loaded {count} proxies from {filename}")
            return count
            
        except Exception as e:
            self.logger.error(f"Error loading proxies from {filename}: {str(e)}")
            return 0
    
    def is_ip_blacklisted(self, ip: str) -> bool:
        """
        Check if an IP is blacklisted.
        
        Args:
            ip: IP to check
            
        Returns:
            True if blacklisted, False otherwise
        """
        return ip in self.blacklisted_ips
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the IP rotator.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_stats()
        
        stats.update({
            "strategy": self.strategy,
            "available_sources": len(self._get_available_sources()),
            "blacklisted_sources": len(self.blacklisted_ips),
            "proxy_count": len(self.proxy_list),
            "source_ip_count": len(self.source_ips),
            "vpn_count": len(self.vpn_providers),
            "local_interface_count": len(getattr(self, "local_interfaces", [])),
            "rotation_interval": self.rotation_interval,
            "current_attempt": self.attempt_count,
            "ip_history_count": len(self.ip_history),
            "current_ip": self._get_current_ip_representation() if hasattr(self, "current_source") else None
        })
        
        return stats
