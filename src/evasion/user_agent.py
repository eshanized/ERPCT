#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT user agent manager module.
This module implements user agent management for password cracking.
"""

import os
import json
import random
import time
from typing import Dict, Any, Optional, List, Union, Callable

from src.evasion.base import EvasionBase
from src.utils.logging import get_logger


class UserAgentManager(EvasionBase):
    """
    User Agent manager for handling user agent rotation.
    
    This class manages user agents for authentication attempts, including:
    - Randomization of user agents
    - Platform-specific user agents
    - Browser-specific user agents
    - Common user agent patterns
    """
    
    # Default user agents by browser type
    DEFAULT_USER_AGENTS = {
        "chrome": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36"
        ],
        "firefox": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ],
        "safari": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        ],
        "edge": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
        ],
        "mobile": [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36"
        ],
        "bot": [
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)"
        ]
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the user agent manager.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # User agent configuration
        self.strategy = self.config.get("strategy", "random")  # random, sequential, browser_specific, platform_specific
        self.preferred_browsers = self.config.get("preferred_browsers", ["chrome", "firefox"])
        self.preferred_platforms = self.config.get("preferred_platforms", ["windows", "mac", "linux"])
        self.rotate_every = self.config.get("rotate_every", 10)  # How many requests before rotation
        self.consistent_per_target = self.config.get("consistent_per_target", False)  # Use same UA for same target
        
        # User agent sources
        self.user_agents = []  # All available user agents
        self.user_agent_by_type = {}  # Type -> list of user agents
        
        # Load default user agents
        for browser, agents in self.DEFAULT_USER_AGENTS.items():
            self.user_agent_by_type[browser] = agents.copy()
            self.user_agents.extend(agents)
        
        # Load user agents from configuration
        user_agent_list = self.config.get("user_agent_list", [])
        for ua in user_agent_list:
            self.add_user_agent(ua)
        
        # Load user agents from file if specified
        user_agent_file = self.config.get("user_agent_file", "")
        if user_agent_file and os.path.exists(user_agent_file):
            self.load_user_agents_from_file(user_agent_file)
        
        # User agent state
        self.current_index = 0
        self.request_count = 0
        self.target_user_agents = {}  # Target -> user agent
        self.current_user_agent = self._choose_initial_user_agent()
        
        self.logger.debug(f"UserAgentManager initialized with {len(self.user_agents)} user agents, "
                         f"strategy={self.strategy}")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply user agent configuration before authentication attempt.
        
        Args:
            target: Optional target information
        """
        super().pre_auth(target)
        
        if not self.enabled or not target:
            return
        
        # Check if we need to rotate
        if self.request_count >= self.rotate_every:
            self._rotate_user_agent()
            self.request_count = 0
        
        # Get user agent for this request
        user_agent = self._get_user_agent_for_target(target)
        
        # Apply user agent to target
        if "request_params" not in target:
            target["request_params"] = {}
        
        if "headers" not in target["request_params"]:
            target["request_params"]["headers"] = {}
        
        target["request_params"]["headers"]["User-Agent"] = user_agent
        self.logger.debug(f"Applied User-Agent: {user_agent[:40]}... to target")
        
        # Increment request count
        self.request_count += 1
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Update user agent state after authentication attempt.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        super().post_auth(success, response, target)
    
    def _get_user_agent_for_target(self, target: Dict[str, Any]) -> str:
        """
        Get the user agent for a specific target.
        
        Args:
            target: Target information
            
        Returns:
            User agent string
        """
        if not self.consistent_per_target:
            return self.current_user_agent
        
        # Get target identifier
        target_id = target.get("id", "")
        target_host = target.get("host", "")
        
        # Use target ID or host as key
        target_key = target_id or target_host
        
        if not target_key:
            return self.current_user_agent
        
        # Get or set user agent for this target
        if target_key not in self.target_user_agents:
            if self.strategy == "browser_specific":
                browser = random.choice(self.preferred_browsers)
                if browser in self.user_agent_by_type and self.user_agent_by_type[browser]:
                    self.target_user_agents[target_key] = random.choice(self.user_agent_by_type[browser])
                else:
                    self.target_user_agents[target_key] = self.current_user_agent
            else:
                self.target_user_agents[target_key] = self.current_user_agent
        
        return self.target_user_agents[target_key]
    
    def _choose_initial_user_agent(self) -> str:
        """
        Choose the initial user agent based on the strategy.
        
        Returns:
            User agent string
        """
        if not self.user_agents:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        if self.strategy == "browser_specific":
            browser = random.choice(self.preferred_browsers)
            if browser in self.user_agent_by_type and self.user_agent_by_type[browser]:
                return random.choice(self.user_agent_by_type[browser])
            
        elif self.strategy == "platform_specific":
            # Filter user agents by platform
            platform_agents = []
            for ua in self.user_agents:
                for platform in self.preferred_platforms:
                    if self._is_platform(ua, platform):
                        platform_agents.append(ua)
            
            if platform_agents:
                return random.choice(platform_agents)
        
        # Default to random selection
        return random.choice(self.user_agents)
    
    def _rotate_user_agent(self) -> None:
        """
        Rotate to a new user agent based on the strategy.
        """
        if not self.user_agents:
            return
        
        if self.strategy == "random":
            self.current_user_agent = random.choice(self.user_agents)
            
        elif self.strategy == "sequential":
            self.current_index = (self.current_index + 1) % len(self.user_agents)
            self.current_user_agent = self.user_agents[self.current_index]
            
        elif self.strategy == "browser_specific":
            browser = random.choice(self.preferred_browsers)
            if browser in self.user_agent_by_type and self.user_agent_by_type[browser]:
                self.current_user_agent = random.choice(self.user_agent_by_type[browser])
            else:
                self.current_user_agent = random.choice(self.user_agents)
                
        elif self.strategy == "platform_specific":
            platform = random.choice(self.preferred_platforms)
            platform_agents = [ua for ua in self.user_agents if self._is_platform(ua, platform)]
            
            if platform_agents:
                self.current_user_agent = random.choice(platform_agents)
            else:
                self.current_user_agent = random.choice(self.user_agents)
        
        self.logger.debug(f"Rotated user agent to: {self.current_user_agent[:40]}...")
    
    def add_user_agent(self, user_agent: Union[Dict[str, Any], str]) -> None:
        """
        Add a user agent to the list.
        
        Args:
            user_agent: User agent string or dictionary
        """
        ua_string = user_agent
        ua_type = None
        
        # Handle dictionary format
        if isinstance(user_agent, dict):
            ua_string = user_agent.get("user_agent", "")
            ua_type = user_agent.get("type", "")
        
        if not ua_string:
            return
        
        # Add to list if not already present
        if ua_string not in self.user_agents:
            self.user_agents.append(ua_string)
            
            # Determine type if not provided
            if not ua_type:
                ua_type = self._detect_browser_type(ua_string)
            
            # Add to type dictionary
            if ua_type:
                if ua_type not in self.user_agent_by_type:
                    self.user_agent_by_type[ua_type] = []
                
                if ua_string not in self.user_agent_by_type[ua_type]:
                    self.user_agent_by_type[ua_type].append(ua_string)
            
            self.logger.debug(f"Added user agent of type {ua_type}: {ua_string[:40]}...")
    
    def load_user_agents_from_file(self, filename: str) -> int:
        """
        Load user agents from a file.
        
        Args:
            filename: Path to user agent list file
            
        Returns:
            Number of user agents loaded
        """
        count = 0
        try:
            with open(filename, 'r') as f:
                # Try to parse as JSON first
                try:
                    data = json.load(f)
                    
                    # Check if it's a list of user agents
                    if isinstance(data, list):
                        for ua in data:
                            if isinstance(ua, dict):
                                self.add_user_agent(ua)
                                count += 1
                            elif isinstance(ua, str):
                                self.add_user_agent(ua)
                                count += 1
                    
                    # Or a dict with a user_agents list
                    elif isinstance(data, dict) and "user_agents" in data:
                        for ua in data["user_agents"]:
                            if isinstance(ua, dict):
                                self.add_user_agent(ua)
                                count += 1
                            elif isinstance(ua, str):
                                self.add_user_agent(ua)
                                count += 1
                    
                except json.JSONDecodeError:
                    # Not JSON, try line-by-line
                    f.seek(0)
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        self.add_user_agent(line)
                        count += 1
            
            self.logger.info(f"Loaded {count} user agents from {filename}")
            return count
            
        except Exception as e:
            self.logger.error(f"Error loading user agents from {filename}: {str(e)}")
            return 0
    
    def _detect_browser_type(self, user_agent: str) -> Optional[str]:
        """
        Detect the browser type from a user agent string.
        
        Args:
            user_agent: User agent string
            
        Returns:
            Browser type or None if not detected
        """
        ua_lower = user_agent.lower()
        
        if "chrome" in ua_lower and "edg" not in ua_lower:
            return "chrome"
        elif "firefox" in ua_lower:
            return "firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            return "safari"
        elif "edg" in ua_lower or "edge" in ua_lower:
            return "edge"
        elif "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            return "mobile"
        elif "bot" in ua_lower or "spider" in ua_lower or "crawler" in ua_lower:
            return "bot"
        
        return None
    
    def _is_platform(self, user_agent: str, platform: str) -> bool:
        """
        Check if a user agent matches a platform.
        
        Args:
            user_agent: User agent string
            platform: Platform to check ("windows", "mac", "linux", "android", "ios")
            
        Returns:
            True if the user agent matches the platform
        """
        ua_lower = user_agent.lower()
        
        if platform == "windows" and ("windows" in ua_lower or "win64" in ua_lower or "win32" in ua_lower):
            return True
        elif platform == "mac" and ("macintosh" in ua_lower or "mac os" in ua_lower) and "iphone" not in ua_lower and "ipad" not in ua_lower:
            return True
        elif platform == "linux" and "linux" in ua_lower and "android" not in ua_lower:
            return True
        elif platform == "android" and "android" in ua_lower:
            return True
        elif platform == "ios" and ("iphone" in ua_lower or "ipad" in ua_lower or "ios" in ua_lower):
            return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the user agent manager.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_stats()
        
        stats.update({
            "total_user_agents": len(self.user_agents),
            "by_type": {k: len(v) for k, v in self.user_agent_by_type.items()},
            "strategy": self.strategy,
            "rotation_interval": self.rotate_every,
            "consistent_per_target": self.consistent_per_target,
            "request_count": self.request_count
        })
        
        return stats 