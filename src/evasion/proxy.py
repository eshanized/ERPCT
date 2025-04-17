#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT proxy manager module.
This module implements proxy management for password cracking.
"""

import os
import time
import random
import json
import requests
from typing import Dict, Any, Optional, List, Union, Tuple, Set, Callable

from src.evasion.base import EvasionBase
from src.utils.logging import get_logger


class ProxyManager(EvasionBase):
    """
    Proxy manager for handling proxy connections.
    
    This class manages proxies for authentication attempts, including:
    - Proxy testing and validation
    - Proxy rotation
    - Country/region-specific proxies
    - Anonymous proxies
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the proxy manager.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Proxy configuration
        self.proxies = []  # List of proxy dicts
        self.current_proxy_index = 0
        self.rotation_strategy = self.config.get("rotation_strategy", "round_robin")  # round_robin, random, sequential, performance
        self.test_timeout = self.config.get("test_timeout", 5.0)  # Timeout for proxy testing
        self.max_failures = self.config.get("max_failures", 3)  # Max failures before blacklisting
        self.prefer_country = self.config.get("prefer_country", "")  # Country code for preferred proxies
        self.require_anonymous = self.config.get("require_anonymous", False)  # Require anonymous proxies
        
        # Load proxies from configuration
        proxy_list = self.config.get("proxy_list", [])
        for proxy in proxy_list:
            self.add_proxy(proxy)
        
        # Load proxies from file if specified
        proxy_file = self.config.get("proxy_file", "")
        if proxy_file and os.path.exists(proxy_file):
            self.load_proxies_from_file(proxy_file)
        
        # Proxy state
        self.working_proxies = set()  # Set of working proxies (by id)
        self.blacklisted_proxies = set()  # Set of blacklisted proxies (by id)
        self.proxy_failures = {}  # proxy_id -> failure count
        self.proxy_performance = {}  # proxy_id -> {"success": count, "failure": count, "avg_time": time}
        
        # Test proxies if auto_test is enabled
        self.auto_test = self.config.get("auto_test", False)
        if self.auto_test and self.proxies:
            self.test_proxies()
        
        self.logger.debug(f"ProxyManager initialized with {len(self.proxies)} proxies, "
                          f"strategy={self.rotation_strategy}")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply proxy configuration before authentication attempt.
        
        Args:
            target: Optional target information
        """
        super().pre_auth(target)
        
        if not self.enabled or not target or not self.proxies:
            return
        
        # Get proxy for this request
        proxy = self.get_proxy()
        if not proxy:
            return
        
        # Apply proxy to target
        if "request_params" not in target:
            target["request_params"] = {}
        
        proxy_url = self._get_proxy_url(proxy)
        target["request_params"]["proxy"] = proxy_url
        target["request_params"]["proxy_id"] = proxy.get("id")
        
        self.logger.debug(f"Applied proxy: {proxy_url} to target")
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Update proxy state after authentication attempt.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        super().post_auth(success, response, target)
        
        if not self.enabled or not target:
            return
        
        # Get the proxy that was used
        if "request_params" not in target or "proxy_id" not in target["request_params"]:
            return
        
        proxy_id = target["request_params"]["proxy_id"]
        
        # Update proxy performance
        if proxy_id not in self.proxy_performance:
            self.proxy_performance[proxy_id] = {"success": 0, "failure": 0, "avg_time": 0.0, "total_time": 0.0}
        
        if success:
            self.proxy_performance[proxy_id]["success"] += 1
            
            # Reset failure count on success
            self.proxy_failures[proxy_id] = 0
            
            # Add to working proxies
            self.working_proxies.add(proxy_id)
        else:
            self.proxy_performance[proxy_id]["failure"] += 1
            
            # Update failures
            if proxy_id not in self.proxy_failures:
                self.proxy_failures[proxy_id] = 0
            
            self.proxy_failures[proxy_id] += 1
            
            # Check if we should blacklist
            if self.proxy_failures[proxy_id] >= self.max_failures:
                self.blacklist_proxy(proxy_id)
    
    def get_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Get a proxy according to the rotation strategy.
        
        Returns:
            Proxy dictionary or None if no proxies available
        """
        # Get available proxies (excluding blacklisted)
        available_proxies = [p for p in self.proxies 
                            if p.get("id") not in self.blacklisted_proxies]
        
        if not available_proxies:
            self.logger.warning("No available proxies")
            return None
        
        # Apply rotation strategy
        if self.rotation_strategy == "round_robin":
            # Move to the next proxy
            proxy = available_proxies[self.current_proxy_index % len(available_proxies)]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(available_proxies)
            
        elif self.rotation_strategy == "random":
            # Pick a random proxy
            proxy = random.choice(available_proxies)
            
        elif self.rotation_strategy == "sequential":
            # Use the first proxy until it fails
            proxy = available_proxies[0]
            
        elif self.rotation_strategy == "performance":
            # Use the best performing proxy (highest success rate)
            if not self.proxy_performance:
                # No performance data yet, fall back to round robin
                proxy = available_proxies[self.current_proxy_index % len(available_proxies)]
                self.current_proxy_index = (self.current_proxy_index + 1) % len(available_proxies)
            else:
                # Calculate success rate for each proxy
                best_proxy = None
                best_rate = -1
                
                for p in available_proxies:
                    proxy_id = p.get("id")
                    
                    if proxy_id in self.proxy_performance:
                        perf = self.proxy_performance[proxy_id]
                        success = perf["success"]
                        failure = perf["failure"]
                        
                        # Calculate success rate
                        total_attempts = success + failure
                        if total_attempts > 0:
                            rate = success / total_attempts
                            
                            if rate > best_rate:
                                best_rate = rate
                                best_proxy = p
                
                proxy = best_proxy if best_proxy else available_proxies[0]
        else:
            # Default to round robin
            proxy = available_proxies[self.current_proxy_index % len(available_proxies)]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(available_proxies)
        
        return proxy
    
    def add_proxy(self, proxy: Union[Dict[str, Any], str]) -> str:
        """
        Add a proxy to the proxy list.
        
        Args:
            proxy: Proxy dictionary or URL string
            
        Returns:
            Proxy ID
        """
        # Convert string to dict if needed
        if isinstance(proxy, str):
            proxy = self._parse_proxy_url(proxy)
        
        # Ensure proxy has an ID
        if "id" not in proxy:
            proxy["id"] = str(len(self.proxies))
        
        # Add to list
        self.proxies.append(proxy)
        self.logger.debug(f"Added proxy: {self._get_proxy_url(proxy)}")
        
        return proxy["id"]
    
    def blacklist_proxy(self, proxy_id: str) -> None:
        """
        Blacklist a proxy.
        
        Args:
            proxy_id: Proxy ID
        """
        if proxy_id not in self.blacklisted_proxies:
            self.blacklisted_proxies.add(proxy_id)
            self.working_proxies.discard(proxy_id)
            self.logger.info(f"Blacklisted proxy {proxy_id}")
    
    def test_proxies(self, test_url: str = "https://api.ipify.org?format=json") -> Dict[str, Any]:
        """
        Test all proxies and update their status.
        
        Args:
            test_url: URL to test proxies against
            
        Returns:
            Dictionary with test results
        """
        results = {
            "total": len(self.proxies),
            "working": 0,
            "blacklisted": len(self.blacklisted_proxies),
            "tested": 0,
            "country_matches": 0,
            "anonymous": 0
        }
        
        # Clear working proxies
        self.working_proxies = set()
        
        # Test each proxy
        for proxy in self.proxies:
            proxy_id = proxy.get("id")
            
            # Skip blacklisted proxies
            if proxy_id in self.blacklisted_proxies:
                continue
            
            # Test the proxy
            test_result = self._test_proxy(proxy, test_url)
            results["tested"] += 1
            
            if test_result["working"]:
                self.working_proxies.add(proxy_id)
                results["working"] += 1
                
                # Check country match if prefer_country is set
                if self.prefer_country and test_result.get("country", "").lower() == self.prefer_country.lower():
                    results["country_matches"] += 1
                
                # Check if anonymous
                if test_result.get("anonymous", False):
                    results["anonymous"] += 1
            else:
                # Update failures
                if proxy_id not in self.proxy_failures:
                    self.proxy_failures[proxy_id] = 0
                
                self.proxy_failures[proxy_id] += 1
                
                # Check if we should blacklist
                if self.proxy_failures[proxy_id] >= self.max_failures:
                    self.blacklist_proxy(proxy_id)
        
        self.logger.info(f"Tested {results['tested']} proxies, {results['working']} working, "
                         f"{results['blacklisted']} blacklisted")
        return results
    
    def _test_proxy(self, proxy: Dict[str, Any], test_url: str) -> Dict[str, Any]:
        """
        Test a single proxy.
        
        Args:
            proxy: Proxy dictionary
            test_url: URL to test against
            
        Returns:
            Dictionary with test results
        """
        result = {
            "proxy_id": proxy.get("id"),
            "working": False,
            "response_time": None,
            "error": None,
            "ip": None,
            "country": None,
            "anonymous": False
        }
        
        proxy_url = self._get_proxy_url(proxy)
        proxies = {"http": proxy_url, "https": proxy_url}
        
        try:
            # Start timing
            start_time = time.time()
            
            # Make request
            response = requests.get(test_url, proxies=proxies, timeout=self.test_timeout)
            
            # End timing
            end_time = time.time()
            response_time = end_time - start_time
            
            # Check if successful
            if response.status_code == 200:
                result["working"] = True
                result["response_time"] = response_time
                
                # Try to get IP and country information
                try:
                    data = response.json()
                    if "ip" in data:
                        result["ip"] = data["ip"]
                    
                    # Additional info might be available depending on the test URL
                    if "country" in data:
                        result["country"] = data["country"]
                    if "anonymous" in data:
                        result["anonymous"] = data["anonymous"]
                except (json.JSONDecodeError, ValueError):
                    pass
                
                # Update proxy performance
                proxy_id = proxy.get("id")
                if proxy_id not in self.proxy_performance:
                    self.proxy_performance[proxy_id] = {
                        "success": 0, "failure": 0, "avg_time": 0.0, "total_time": 0.0}
                
                perf = self.proxy_performance[proxy_id]
                perf["success"] += 1
                perf["total_time"] += response_time
                perf["avg_time"] = perf["total_time"] / perf["success"]
                
                self.logger.debug(f"Proxy {proxy_id} working ({response_time:.2f}s)")
            else:
                result["error"] = f"HTTP {response.status_code}"
                self.logger.debug(f"Proxy {proxy_id} returned {response.status_code}")
        
        except Exception as e:
            result["error"] = str(e)
            self.logger.debug(f"Proxy {proxy_id} error: {str(e)}")
        
        return result
    
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
                # Try to parse as JSON first
                try:
                    data = json.load(f)
                    
                    # Check if it's a list of proxies
                    if isinstance(data, list):
                        for proxy in data:
                            if isinstance(proxy, dict):
                                self.add_proxy(proxy)
                                count += 1
                            elif isinstance(proxy, str):
                                self.add_proxy(proxy)
                                count += 1
                    
                    # Or a dict with a proxies list
                    elif isinstance(data, dict) and "proxies" in data:
                        for proxy in data["proxies"]:
                            if isinstance(proxy, dict):
                                self.add_proxy(proxy)
                                count += 1
                            elif isinstance(proxy, str):
                                self.add_proxy(proxy)
                                count += 1
                    
                except json.JSONDecodeError:
                    # Not JSON, try line-by-line
                    f.seek(0)
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        self.add_proxy(line)
                        count += 1
            
            self.logger.info(f"Loaded {count} proxies from {filename}")
            return count
            
        except Exception as e:
            self.logger.error(f"Error loading proxies from {filename}: {str(e)}")
            return 0
    
    def _parse_proxy_url(self, url: str) -> Dict[str, Any]:
        """
        Parse a proxy URL into a proxy dictionary.
        
        Args:
            url: Proxy URL
            
        Returns:
            Proxy dictionary
        """
        proxy = {
            "type": "http",
            "host": "",
            "port": 80,
            "username": "",
            "password": ""
        }
        
        try:
            # Parse various formats
            # Format 1: host:port
            # Format 2: protocol://host:port
            # Format 3: protocol://username:password@host:port
            
            if "://" in url:
                # Format 2 or 3
                protocol, rest = url.split("://", 1)
                proxy["type"] = protocol.lower()
                
                if "@" in rest:
                    # Format 3
                    auth, hostport = rest.rsplit("@", 1)
                    if ":" in auth:
                        proxy["username"], proxy["password"] = auth.split(":", 1)
                else:
                    # Format 2
                    hostport = rest
                
                if ":" in hostport:
                    proxy["host"], port = hostport.split(":", 1)
                    proxy["port"] = int(port)
                else:
                    proxy["host"] = hostport
            
            else:
                # Format 1
                if ":" in url:
                    proxy["host"], port = url.split(":", 1)
                    proxy["port"] = int(port)
                else:
                    proxy["host"] = url
            
            return proxy
            
        except Exception as e:
            self.logger.warning(f"Error parsing proxy URL: {url} - {str(e)}")
            return proxy
    
    def _get_proxy_url(self, proxy: Dict[str, Any]) -> str:
        """
        Get the URL representation of a proxy.
        
        Args:
            proxy: Proxy dictionary
            
        Returns:
            Proxy URL
        """
        proxy_type = proxy.get("type", "http")
        host = proxy.get("host", "")
        port = proxy.get("port", 80)
        username = proxy.get("username", "")
        password = proxy.get("password", "")
        
        if not host:
            return ""
        
        auth = ""
        if username:
            auth = username
            if password:
                auth += f":{password}"
            auth += "@"
        
        return f"{proxy_type}://{auth}{host}:{port}"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the proxy manager.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_stats()
        
        avg_latency = 0.0
        success_rate = 0.0
        
        # Calculate overall performance
        total_success = 0
        total_failure = 0
        total_time = 0.0
        
        for proxy_id, perf in self.proxy_performance.items():
            total_success += perf["success"]
            total_failure += perf["failure"]
            total_time += perf["total_time"]
        
        total_requests = total_success + total_failure
        if total_requests > 0:
            success_rate = (total_success / total_requests) * 100
        
        if total_success > 0:
            avg_latency = total_time / total_success
        
        stats.update({
            "total_proxies": len(self.proxies),
            "working_proxies": len(self.working_proxies),
            "blacklisted_proxies": len(self.blacklisted_proxies),
            "rotation_strategy": self.rotation_strategy,
            "success_rate": success_rate,
            "avg_latency": avg_latency,
            "total_requests": total_requests
        })
        
        return stats
