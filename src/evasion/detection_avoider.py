#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT detection avoider module.
This module implements detection and adaptation to defense mechanisms.
"""

import time
import re
import random
from typing import Dict, Any, Optional, List, Callable, Set, Union

from src.evasion.base import EvasionBase


class DetectionAvoider(EvasionBase):
    """
    Detection avoider for adapting to defense mechanisms.
    
    This class implements mechanisms to detect and adapt to various
    defense systems, including account lockout detection, blacklisting
    detection, and IDS/IPS evasion.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the detection avoider.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Detection flags
        self.detect_lockout = self.config.get("detect_lockout", True)
        self.detect_blacklist = self.config.get("detect_blacklist", True)
        self.detect_ids = self.config.get("detect_ids", True)
        
        # Detection thresholds
        self.lockout_threshold = self.config.get("lockout_threshold", 3)
        self.blacklist_threshold = self.config.get("blacklist_threshold", 3)
        self.ids_threshold = self.config.get("ids_threshold", 3)
        
        # Response actions
        self.lockout_action = self.config.get("lockout_action", "pause")  # pause, stop, alert
        self.blacklist_action = self.config.get("blacklist_action", "rotate_ip")  # rotate_ip, pause, stop, alert
        self.ids_action = self.config.get("ids_action", "slow_down")  # slow_down, rotate_ip, pause, stop, alert
        
        # Timing settings
        self.pause_duration = self.config.get("pause_duration", 300.0)  # 5 minutes
        self.slow_down_factor = self.config.get("slow_down_factor", 2.0)
        
        # Detection patterns
        self.lockout_patterns = [
            "account locked", "too many failed attempts", 
            "temporarily disabled", "account disabled",
            "try again later", "locked out", "suspended"
        ]
        self.blacklist_patterns = [
            "access denied", "forbidden", "ip blocked", "blacklisted",
            "banned", "403", "ip address has been blocked"
        ]
        self.ids_patterns = [
            "unusual activity", "suspicious activity", "security alert",
            "detected automated access", "captcha required", "prove you are human"
        ]
        
        # Add custom patterns if specified
        if "lockout_patterns" in self.config:
            self.lockout_patterns.extend(self.config["lockout_patterns"])
        if "blacklist_patterns" in self.config:
            self.blacklist_patterns.extend(self.config["blacklist_patterns"])
        if "ids_patterns" in self.config:
            self.ids_patterns.extend(self.config["ids_patterns"])
        
        # Convert patterns to lowercase for case-insensitive matching
        self.lockout_patterns = [p.lower() for p in self.lockout_patterns]
        self.blacklist_patterns = [p.lower() for p in self.blacklist_patterns]
        self.ids_patterns = [p.lower() for p in self.ids_patterns]
        
        # Detection state
        self.consecutive_lockout_indicators = 0
        self.consecutive_blacklist_indicators = 0
        self.consecutive_ids_indicators = 0
        self.detected_lockout = False
        self.detected_blacklist = False
        self.detected_ids = False
        self.pause_until = 0.0  # Time to pause until (epoch time)
        self.slow_down_until = 0.0  # Time to apply slowdown until (epoch time)
        self.current_delay_factor = 1.0
        
        # Canary accounts for lockout detection
        self.canary_accounts = self.config.get("canary_accounts", [])
        self.canary_results = {}  # username -> last result
        
        # Tracking
        self.target_history = {}  # target_id -> list of response patterns
        
        self.logger.debug(f"DetectionAvoider initialized with lockout_detection={self.detect_lockout}, "
                          f"blacklist_detection={self.detect_blacklist}, ids_detection={self.detect_ids}")
    
    def pre_auth(self, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Check for detection measures before authentication attempt.
        
        Args:
            target: Optional target information
        """
        super().pre_auth(target)
        
        if not self.enabled or not target:
            return
        
        # Check if we should pause
        current_time = time.time()
        if current_time < self.pause_until:
            remaining = self.pause_until - current_time
            self.logger.debug(f"Pausing for {remaining:.2f}s due to detection")
            time.sleep(remaining)
            self.pause_until = 0.0  # Reset after waiting
        
        # Apply slow down
        if current_time < self.slow_down_until:
            delay = random.uniform(1.0, 3.0) * self.current_delay_factor
            self.logger.debug(f"Adding {delay:.2f}s delay due to IDS detection")
            time.sleep(delay)
    
    def post_auth(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Check for signs of detection after authentication attempt.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        super().post_auth(success, response, target)
        
        if not self.enabled or not target:
            return
        
        # Analyze response for detection signs
        self._analyze_response(success, response, target)
        
        # Check canary accounts if lockout detection is enabled
        if self.detect_lockout and self.canary_accounts and random.random() < 0.1:  # 10% chance
            self._check_canary_account()
    
    def _analyze_response(self, success: bool, response: Any = None, target: Optional[Dict[str, Any]] = None) -> None:
        """
        Analyze response for signs of detection.
        
        Args:
            success: Whether the authentication was successful
            response: The response from the authentication attempt
            target: Optional target information
        """
        if not response:
            return
        
        # Get response message
        response_str = str(response).lower()
        
        # Add to target history
        target_id = self._get_target_id(target)
        if target_id not in self.target_history:
            self.target_history[target_id] = []
        self.target_history[target_id].append(response_str)
        
        # Keep only the last 10 responses
        if len(self.target_history[target_id]) > 10:
            self.target_history[target_id] = self.target_history[target_id][-10:]
        
        # Check for lockout indicators
        if self.detect_lockout and not self.detected_lockout:
            if any(pattern in response_str for pattern in self.lockout_patterns):
                self.consecutive_lockout_indicators += 1
                self.logger.warning(f"Lockout indicator detected: {response_str[:100]}")
                
                if self.consecutive_lockout_indicators >= self.lockout_threshold:
                    self._handle_detected_lockout(target)
            else:
                self.consecutive_lockout_indicators = 0
        
        # Check for blacklist indicators
        if self.detect_blacklist and not self.detected_blacklist:
            if any(pattern in response_str for pattern in self.blacklist_patterns):
                self.consecutive_blacklist_indicators += 1
                self.logger.warning(f"Blacklist indicator detected: {response_str[:100]}")
                
                if self.consecutive_blacklist_indicators >= self.blacklist_threshold:
                    self._handle_detected_blacklist(target)
            else:
                self.consecutive_blacklist_indicators = 0
        
        # Check for IDS indicators
        if self.detect_ids and not self.detected_ids:
            if any(pattern in response_str for pattern in self.ids_patterns):
                self.consecutive_ids_indicators += 1
                self.logger.warning(f"IDS indicator detected: {response_str[:100]}")
                
                if self.consecutive_ids_indicators >= self.ids_threshold:
                    self._handle_detected_ids(target)
            else:
                self.consecutive_ids_indicators = 0
    
    def _check_canary_account(self) -> None:
        """Check canary account to detect lockout policies."""
        if not self.canary_accounts:
            return
        
        # Select a random canary account
        canary = random.choice(self.canary_accounts)
        
        # Call the callback to test the canary account
        if self._on_canary_check:
            username = canary.get("username", "")
            password = canary.get("password", "")
            
            # Call the canary check callback
            self._on_canary_check(username, password, self._handle_canary_result)
    
    def _handle_canary_result(self, username: str, success: bool, response: Any = None) -> None:
        """
        Handle result from canary account check.
        
        Args:
            username: Canary account username
            success: Whether authentication was successful
            response: Response from authentication attempt
        """
        # Record result
        self.canary_results[username] = {
            "success": success,
            "response": response,
            "time": time.time()
        }
        
        # If a previously working account now fails, it may indicate lockout
        if not success:
            # Check if we've seen this account before
            for result in self.target_history.values():
                if username in str(result):
                    self.logger.warning(f"Canary account {username} is now failing, possible lockout detected")
                    self._handle_detected_lockout(None)
                    break
    
    def _handle_detected_lockout(self, target: Optional[Dict[str, Any]]) -> None:
        """
        Handle detected account lockout.
        
        Args:
            target: Target information
        """
        self.detected_lockout = True
        self.logger.warning("Account lockout detected")
        
        # Trigger lockout callback
        reason = f"Account lockout detected after {self.consecutive_lockout_indicators} indicators"
        self._trigger_lockout_callback(reason, target)
        
        # Take action based on configuration
        if self.lockout_action == "pause":
            self.pause_until = time.time() + self.pause_duration
            self.logger.info(f"Pausing for {self.pause_duration}s due to account lockout")
        elif self.lockout_action == "stop":
            self.enabled = False
            self.logger.info("Stopping due to account lockout")
    
    def _handle_detected_blacklist(self, target: Optional[Dict[str, Any]]) -> None:
        """
        Handle detected IP blacklisting.
        
        Args:
            target: Target information
        """
        self.detected_blacklist = True
        self.logger.warning("IP blacklisting detected")
        
        # Trigger detection callback
        reason = f"IP blacklisting detected after {self.consecutive_blacklist_indicators} indicators"
        self._trigger_detection_callback(reason, target)
        
        # Take action based on configuration
        if self.blacklist_action == "rotate_ip":
            # Trigger IP rotation via callback
            if self._on_ip_rotation:
                self._on_ip_rotation(target)
                self.logger.info("Requesting IP rotation due to blacklist detection")
            else:
                self.logger.warning("No IP rotation callback set")
        elif self.blacklist_action == "pause":
            self.pause_until = time.time() + self.pause_duration
            self.logger.info(f"Pausing for {self.pause_duration}s due to blacklist detection")
        elif self.blacklist_action == "stop":
            self.enabled = False
            self.logger.info("Stopping due to blacklist detection")
    
    def _handle_detected_ids(self, target: Optional[Dict[str, Any]]) -> None:
        """
        Handle detected IDS/IPS.
        
        Args:
            target: Target information
        """
        self.detected_ids = True
        self.logger.warning("IDS/IPS detection detected")
        
        # Trigger detection callback
        reason = f"IDS detection detected after {self.consecutive_ids_indicators} indicators"
        self._trigger_detection_callback(reason, target)
        
        # Take action based on configuration
        if self.ids_action == "slow_down":
            self.slow_down_until = time.time() + self.pause_duration
            self.current_delay_factor = self.slow_down_factor
            self.logger.info(f"Slowing down by factor {self.slow_down_factor} for {self.pause_duration}s")
        elif self.ids_action == "rotate_ip":
            # Trigger IP rotation via callback
            if self._on_ip_rotation:
                self._on_ip_rotation(target)
                self.logger.info("Requesting IP rotation due to IDS detection")
            else:
                self.logger.warning("No IP rotation callback set")
        elif self.ids_action == "pause":
            self.pause_until = time.time() + self.pause_duration
            self.logger.info(f"Pausing for {self.pause_duration}s due to IDS detection")
        elif self.ids_action == "stop":
            self.enabled = False
            self.logger.info("Stopping due to IDS detection")
    
    def _get_target_id(self, target: Dict[str, Any]) -> str:
        """
        Generate a unique identifier for a target.
        
        Args:
            target: Target information
            
        Returns:
            Target identifier string
        """
        # Prefer the target's explicit ID if available
        if "id" in target:
            return str(target["id"])
        
        # Otherwise, create a composite ID from host and username
        host = target.get("host", "")
        username = target.get("username", "")
        
        return f"{host}:{username}"
    
    def add_lockout_patterns(self, patterns: List[str]) -> None:
        """
        Add custom lockout detection patterns.
        
        Args:
            patterns: List of regex patterns to match
        """
        self.lockout_patterns.extend([p.lower() for p in patterns])
        self.logger.debug(f"Added {len(patterns)} lockout patterns")
    
    def add_blacklist_patterns(self, patterns: List[str]) -> None:
        """
        Add custom blacklist detection patterns.
        
        Args:
            patterns: List of regex patterns to match
        """
        self.blacklist_patterns.extend([p.lower() for p in patterns])
        self.logger.debug(f"Added {len(patterns)} blacklist patterns")
    
    def add_ids_patterns(self, patterns: List[str]) -> None:
        """
        Add custom IDS detection patterns.
        
        Args:
            patterns: List of regex patterns to match
        """
        self.ids_patterns.extend([p.lower() for p in patterns])
        self.logger.debug(f"Added {len(patterns)} IDS patterns")
    
    def set_canary_accounts(self, accounts: List[Dict[str, str]]) -> None:
        """
        Set canary accounts for lockout detection.
        
        Args:
            accounts: List of dicts with username/password pairs
        """
        self.canary_accounts = accounts
        self.logger.debug(f"Set {len(accounts)} canary accounts")
    
    def set_on_canary_check(self, callback: Callable[[str, str, Callable], None]) -> None:
        """
        Set callback for checking canary accounts.
        
        Args:
            callback: Function that performs authentication with a canary account
                     and calls a result handler
        """
        self._on_canary_check = callback
        self.logger.debug("Set canary check callback")
    
    def set_on_ip_rotation(self, callback: Callable[[Optional[Dict[str, Any]]], None]) -> None:
        """
        Set callback for IP rotation.
        
        Args:
            callback: Function to call when IP rotation is needed
        """
        self._on_ip_rotation = callback
        self.logger.debug("Set IP rotation callback")
    
    def reset_detection_state(self) -> None:
        """Reset all detection state."""
        self.consecutive_lockout_indicators = 0
        self.consecutive_blacklist_indicators = 0
        self.consecutive_ids_indicators = 0
        self.detected_lockout = False
        self.detected_blacklist = False
        self.detected_ids = False
        self.pause_until = 0.0
        self.slow_down_until = 0.0
        self.current_delay_factor = 1.0
        self.logger.debug("Reset detection state")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the detection avoider.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_stats()
        
        stats.update({
            "lockout_detected": self.detected_lockout,
            "blacklist_detected": self.detected_blacklist,
            "ids_detected": self.detected_ids,
            "consecutive_lockout_indicators": self.consecutive_lockout_indicators,
            "consecutive_blacklist_indicators": self.consecutive_blacklist_indicators,
            "consecutive_ids_indicators": self.consecutive_ids_indicators,
            "paused_until": self.pause_until,
            "slow_down_until": self.slow_down_until,
            "current_delay_factor": self.current_delay_factor,
            "canary_accounts_count": len(self.canary_accounts),
            "targets_tracked": len(self.target_history)
        })
        
        return stats
