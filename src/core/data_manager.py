#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Data Manager.
This module provides data management for attack results and credentials.
"""

import os
import json
import time
import threading
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

from src.utils.logging import get_logger
from src.core.attack import AttackController


class DataManager:
    """Singleton class for managing ERPCT data and results."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance.
        
        Returns:
            DataManager: The singleton instance
        """
        if cls._instance is None:
            cls._instance = DataManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the data manager."""
        if DataManager._instance is not None:
            raise RuntimeError("DataManager is a singleton - use get_instance()")
        
        self.logger = get_logger(__name__)
        self.lock = threading.RLock()
        
        # Default results directory
        self.results_dir = os.path.join(os.path.expanduser("~"), ".erpct", "results")
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Load saved results
        self.results = {}
        self._load_results()
        
        # Success rate history (for charts)
        self.success_rate_history = []
        self._update_success_rate_history()
    
    def _load_results(self):
        """Load saved results from disk."""
        try:
            if os.path.exists(self.results_dir):
                for filename in os.listdir(self.results_dir):
                    if filename.endswith(".json"):
                        filepath = os.path.join(self.results_dir, filename)
                        if os.path.isfile(filepath):
                            try:
                                with open(filepath, 'r') as f:
                                    result_data = json.load(f)
                                    result_id = result_data.get("id", os.path.splitext(filename)[0])
                                    self.results[result_id] = result_data
                            except Exception as e:
                                self.logger.error(f"Error loading result file {filepath}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error loading results: {str(e)}")
    
    def save_result(self, result_data: Dict[str, Any]) -> str:
        """Save an attack result.
        
        Args:
            result_data: Dictionary with result data
            
        Returns:
            str: Result ID
        """
        with self.lock:
            # Generate ID and filename
            result_id = str(int(time.time()))
            result_data["id"] = result_id
            
            if "timestamp" not in result_data:
                result_data["timestamp"] = time.time()
                
            if "name" not in result_data:
                target = result_data.get("target", "unknown")
                protocol = result_data.get("protocol", "unknown")
                result_data["name"] = f"{protocol}_{target}_{result_id}"
            
            # Save result file
            filename = f"{result_id}.json"
            filepath = os.path.join(self.results_dir, filename)
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(result_data, f, indent=2)
                
                # Add to in-memory results
                self.results[result_id] = result_data
                
                # Update success rate history
                self._update_success_rate_history()
                
                return result_id
                    
            except Exception as e:
                self.logger.error(f"Error saving result: {str(e)}")
                return ""
    
    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Get a result by ID.
        
        Args:
            result_id: Result ID
            
        Returns:
            Result data dictionary or None if not found
        """
        with self.lock:
            return self.results.get(result_id)
    
    def delete_result(self, result_id: str) -> bool:
        """Delete a result.
        
        Args:
            result_id: Result ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.lock:
            if result_id in self.results:
                filepath = os.path.join(self.results_dir, f"{result_id}.json")
                try:
                    # Remove file
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    
                    # Remove from in-memory results
                    del self.results[result_id]
                    
                    # Update success rate history
                    self._update_success_rate_history()
                    
                    return True
                except Exception as e:
                    self.logger.error(f"Error deleting result {result_id}: {str(e)}")
            
            return False
    
    def get_recent_attacks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent attacks.
        
        Args:
            limit: Maximum number of attacks to return
            
        Returns:
            list: List of attack dictionaries
        """
        with self.lock:
            # Return most recent attacks from results data
            attacks = []
            
            # Get attacks sorted by timestamp (most recent first)
            for result_id, result in sorted(
                self.results.items(),
                key=lambda x: x[1].get('timestamp', 0),
                reverse=True
            ):
                # Format attack data
                attack = {
                    'id': result_id,
                    'timestamp': self._format_timestamp(result.get('timestamp')),
                    'target': result.get('target', 'Unknown'),
                    'protocol': result.get('protocol', 'Unknown'),
                    'status': 'Completed',
                    'success_rate': self._calculate_success_rate(result)
                }
                attacks.append(attack)
                
                # Stop after reaching limit
                if len(attacks) >= limit:
                    break
            
            return attacks
    
    def get_recent_credentials(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently discovered credentials.
        
        Args:
            limit: Maximum number of credentials to return
            
        Returns:
            list: List of credential dictionaries
        """
        with self.lock:
            credentials = []
            
            # Get all credentials from all results, sorted by timestamp
            all_creds = []
            for result_id, result in self.results.items():
                for cred in result.get('credentials', []):
                    all_creds.append({
                        'timestamp': self._format_timestamp(cred.get('timestamp', 0)),
                        'target': result.get('target', 'Unknown'),
                        'username': cred.get('username', 'Unknown'),
                        'password': cred.get('password', 'Unknown'),
                        'protocol': result.get('protocol', 'Unknown')
                    })
            
            # Sort by timestamp (most recent first)
            all_creds.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Return up to the limit
            return all_creds[:limit]
    
    def search_credentials(self, search_text: str) -> List[Dict[str, Any]]:
        """Search for credentials.
        
        Args:
            search_text: Text to search for
            
        Returns:
            list: List of matching credential dictionaries
        """
        with self.lock:
            search_text = search_text.lower()
            matching_creds = []
            
            # Search all credentials from all results
            for result_id, result in self.results.items():
                target = result.get('target', '').lower()
                protocol = result.get('protocol', '').lower()
                
                for cred in result.get('credentials', []):
                    username = cred.get('username', '').lower()
                    password = cred.get('password', '').lower()
                    
                    # Check if any field matches search text
                    if (search_text in target or 
                        search_text in protocol or 
                        search_text in username or 
                        search_text in password):
                        
                        matching_creds.append({
                            'timestamp': self._format_timestamp(cred.get('timestamp', 0)),
                            'target': result.get('target', 'Unknown'),
                            'username': cred.get('username', 'Unknown'),
                            'password': cred.get('password', 'Unknown'),
                            'protocol': result.get('protocol', 'Unknown')
                        })
            
            # Sort by timestamp (most recent first)
            matching_creds.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return matching_creds
    
    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get summary metrics.
        
        Returns:
            dict: Dictionary with summary metrics
        """
        with self.lock:
            # Calculate summary metrics
            total_attacks = len(self.results)
            successful_attacks = 0
            total_credentials = 0
            targets = set()
            
            for result in self.results.values():
                # Count successful attacks (any credentials found)
                if result.get('credentials', []):
                    successful_attacks += 1
                
                # Count total credentials
                total_credentials += len(result.get('credentials', []))
                
                # Add target to set
                if result.get('target'):
                    targets.add(result.get('target'))
            
            # Get active scans from attack controller
            attack_controller = AttackController.get_instance()
            active_scans = attack_controller.get_active_attack_count()
            
            return {
                'total_attacks': total_attacks,
                'successful_attacks': successful_attacks,
                'total_credentials': total_credentials,
                'total_targets': len(targets),
                'active_scans': active_scans,
                'success_rate_history': self.success_rate_history
            }
    
    def export_credentials(self, filename: str) -> None:
        """Export credentials to a CSV file.
        
        Args:
            filename: Path to the output file
            
        Raises:
            Exception: If export fails
        """
        with self.lock:
            try:
                # Get all credentials
                all_creds = []
                for result_id, result in self.results.items():
                    for cred in result.get('credentials', []):
                        all_creds.append({
                            'timestamp': self._format_timestamp(cred.get('timestamp', 0)),
                            'target': result.get('target', 'Unknown'),
                            'protocol': result.get('protocol', 'Unknown'),
                            'username': cred.get('username', 'Unknown'),
                            'password': cred.get('password', 'Unknown'),
                            'result_id': result_id
                        })
                
                # Write to CSV file
                with open(filename, 'w', newline='') as csvfile:
                    fieldnames = ['timestamp', 'target', 'protocol', 'username', 'password', 'result_id']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for cred in all_creds:
                        writer.writerow(cred)
                
                self.logger.info(f"Exported {len(all_creds)} credentials to {filename}")
            except Exception as e:
                self.logger.error(f"Error exporting credentials: {str(e)}")
                raise
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format a timestamp.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            str: Formatted timestamp
        """
        if not timestamp:
            return ""
        
        # Convert to datetime and format
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def _calculate_success_rate(self, result: Dict[str, Any]) -> float:
        """Calculate success rate for an attack.
        
        Args:
            result: Attack result dictionary
            
        Returns:
            float: Success rate as a percentage
        """
        total_attempts = result.get('total_attempts', 0)
        successful_attempts = result.get('successful_attempts', 0)
        
        if total_attempts > 0:
            return (successful_attempts / total_attempts) * 100
        else:
            return 0.0
    
    def _update_success_rate_history(self, days: int = 7) -> None:
        """Update success rate history for charts.
        
        Args:
            days: Number of days to include
        """
        # Calculate start time
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        start_timestamp = time.mktime(start_time.timetuple())
        
        # Divide into periods (one per day)
        period_seconds = 86400  # Seconds in a day
        periods = []
        for i in range(days):
            period_start = start_timestamp + (i * period_seconds)
            period_end = period_start + period_seconds
            periods.append((period_start, period_end))
        
        # Calculate success rate for each period
        success_rates = []
        for period_start, period_end in periods:
            # Get attacks in this period
            period_attacks = 0
            period_successes = 0
            
            for result in self.results.values():
                timestamp = result.get('timestamp', 0)
                if period_start <= timestamp < period_end:
                    period_attacks += 1
                    if result.get('credentials', []):
                        period_successes += 1
            
            # Calculate success rate
            if period_attacks > 0:
                success_rate = (period_successes / period_attacks) * 100
            else:
                success_rate = 0
            
            success_rates.append(success_rate)
        
        self.success_rate_history = success_rates 