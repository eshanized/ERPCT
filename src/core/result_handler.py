#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Result handler module for ERPCT.
This module handles the processing and storage of password attack results.
"""

import os
import json
import csv
import time
import threading
from typing import Dict, List, Any, Optional, Set, Tuple

from src.utils.logging import get_logger


class ResultHandler:
    """Result handler class for processing and storing attack results.
    
    The ResultHandler is responsible for:
    1. Processing successful/failed password attempts
    2. Storing results in various formats (text, CSV, JSON)
    3. Providing statistics and reporting
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the result handler with configuration.
        
        Args:
            config: Dictionary containing result handler configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Extract configuration
        self.output_dir = config.get("output_dir", "results")
        self.save_successful = config.get("save_successful", True)
        self.save_failed = config.get("save_failed", False)
        self.output_format = config.get("output_format", "text").lower()
        self.append_timestamp = config.get("append_timestamp", True)
        
        # Result storage
        self.successful_results = []
        self.failed_results = []
        self.unique_credentials: Set[Tuple[str, str]] = set()
        
        # Locking for thread safety
        self.results_lock = threading.RLock()
        
        # Ensure output directory exists
        self._ensure_output_directory()
    
    def initialize(self) -> None:
        """Initialize the result handler."""
        self.logger.info("Initializing result handler")
        
        # Prepare output files if needed
        if self.output_format != "memory":
            self._prepare_output_files()
    
    def _ensure_output_directory(self) -> None:
        """Ensure the output directory exists."""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                self.logger.info(f"Created output directory: {self.output_dir}")
        except Exception as e:
            self.logger.error(f"Error creating output directory: {str(e)}")
            # Fall back to current directory
            self.output_dir = "."
    
    def _prepare_output_files(self) -> None:
        """Prepare output files based on configuration."""
        timestamp = ""
        if self.append_timestamp:
            timestamp = f"_{int(time.time())}"
        
        # Base filename
        base_filename = self.config.get("output_base", "erpct_results")
        
        # Create filenames
        if self.save_successful:
            self.successful_file = os.path.join(
                self.output_dir, f"{base_filename}_successful{timestamp}"
            )
            
            # Create file with headers based on format
            if self.output_format == "csv":
                self.successful_file += ".csv"
                with open(self.successful_file, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Timestamp", "Username", "Password", "Target", "Protocol"])
                    
            elif self.output_format == "json":
                self.successful_file += ".json"
                with open(self.successful_file, 'w') as jsonfile:
                    jsonfile.write("[\n")  # Start JSON array
                    
            else:  # Default to text
                self.successful_file += ".txt"
                with open(self.successful_file, 'w') as txtfile:
                    txtfile.write("# ERPCT Successful Results\n")
                    txtfile.write("# Timestamp, Username, Password, Target, Protocol\n")
        
        if self.save_failed:
            self.failed_file = os.path.join(
                self.output_dir, f"{base_filename}_failed{timestamp}"
            )
            
            # Create file with headers based on format
            if self.output_format == "csv":
                self.failed_file += ".csv"
                with open(self.failed_file, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Timestamp", "Username", "Password", "Target", "Protocol", "Error"])
                    
            elif self.output_format == "json":
                self.failed_file += ".json"
                with open(self.failed_file, 'w') as jsonfile:
                    jsonfile.write("[\n")  # Start JSON array
                    
            else:  # Default to text
                self.failed_file += ".txt"
                with open(self.failed_file, 'w') as txtfile:
                    txtfile.write("# ERPCT Failed Results\n")
                    txtfile.write("# Timestamp, Username, Password, Target, Protocol, Error\n")
    
    def handle_result(self, result: Dict[str, Any]) -> None:
        """Handle a general authentication result.
        
        Args:
            result: Dictionary containing result information
        """
        # Extract basic information
        username = result.get("username", "")
        password = result.get("password", "")
        success = result.get("success", False)
        
        with self.results_lock:
            if success:
                self.handle_success(result)
            else:
                # Add to failed results
                self.failed_results.append(result)
                
                # Write to file if configured
                if self.save_failed and self.output_format != "memory":
                    self._write_result_to_file(result, self.failed_file, is_success=False)
    
    def handle_success(self, result: Dict[str, Any]) -> None:
        """Handle a successful authentication result.
        
        Args:
            result: Dictionary containing result information
        """
        # Extract information
        username = result.get("username", "")
        password = result.get("password", "")
        
        with self.results_lock:
            # Check if this is a new credential
            credential = (username, password)
            is_new = credential not in self.unique_credentials
            
            if is_new:
                # Add to unique credentials
                self.unique_credentials.add(credential)
                
                # Add to successful results
                self.successful_results.append(result)
                
                # Log the success
                target = result.get("target", "")
                protocol = result.get("protocol", "")
                self.logger.info(
                    f"Successful authentication: username='{username}', "
                    f"password='{password}', target='{target}', protocol='{protocol}'"
                )
                
                # Write to file if configured
                if self.save_successful and self.output_format != "memory":
                    self._write_result_to_file(result, self.successful_file, is_success=True)
    
    def _write_result_to_file(self, result: Dict[str, Any], 
                             filename: str, is_success: bool) -> None:
        """Write a result to the appropriate output file.
        
        Args:
            result: Result dictionary
            filename: Output filename
            is_success: Whether this is a successful result
        """
        try:
            timestamp = result.get("timestamp", time.time())
            formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            username = result.get("username", "")
            password = result.get("password", "")
            target = result.get("target", "")
            protocol = result.get("protocol", "")
            error = result.get("error", "") if not is_success else ""
            
            if self.output_format == "csv":
                with open(filename, 'a', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    if is_success:
                        writer.writerow([formatted_time, username, password, target, protocol])
                    else:
                        writer.writerow([formatted_time, username, password, target, protocol, error])
                        
            elif self.output_format == "json":
                with open(filename, 'a') as jsonfile:
                    # Check if we need a comma (not first entry)
                    if (is_success and len(self.successful_results) > 1) or \
                       (not is_success and len(self.failed_results) > 1):
                        jsonfile.write(",\n")
                    
                    # Write the entry
                    json_entry = {
                        "timestamp": timestamp,
                        "formatted_time": formatted_time,
                        "username": username,
                        "password": password,
                        "target": target,
                        "protocol": protocol
                    }
                    
                    if not is_success:
                        json_entry["error"] = error
                        
                    json.dump(json_entry, jsonfile, indent=2)
                    
            else:  # Default to text
                with open(filename, 'a') as txtfile:
                    if is_success:
                        txtfile.write(f"{formatted_time},{username},{password},{target},{protocol}\n")
                    else:
                        txtfile.write(f"{formatted_time},{username},{password},{target},{protocol},{error}\n")
                        
        except Exception as e:
            self.logger.error(f"Error writing result to file: {str(e)}")
    
    def get_successful_credentials(self) -> List[Tuple[str, str]]:
        """Get list of unique successful credentials.
        
        Returns:
            List of (username, password) tuples
        """
        with self.results_lock:
            return list(self.unique_credentials)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get result statistics.
        
        Returns:
            Dictionary with result statistics
        """
        with self.results_lock:
            return {
                "successful_count": len(self.successful_results),
                "failed_count": len(self.failed_results),
                "unique_credentials_count": len(self.unique_credentials)
            }
    
    def save_final_results(self) -> None:
        """Save final results and close files if needed."""
        if self.output_format == "json":
            # Close JSON arrays
            if self.save_successful:
                try:
                    with open(self.successful_file, 'a') as jsonfile:
                        jsonfile.write("\n]")
                except Exception as e:
                    self.logger.error(f"Error finalizing successful results file: {str(e)}")
                    
            if self.save_failed:
                try:
                    with open(self.failed_file, 'a') as jsonfile:
                        jsonfile.write("\n]")
                except Exception as e:
                    self.logger.error(f"Error finalizing failed results file: {str(e)}")
        
        # Generate summary file
        self._generate_summary()
    
    def _generate_summary(self) -> None:
        """Generate a summary file with overall statistics."""
        try:
            timestamp = ""
            if self.append_timestamp:
                timestamp = f"_{int(time.time())}"
                
            # Base filename
            base_filename = self.config.get("output_base", "erpct_results")
            summary_file = os.path.join(self.output_dir, f"{base_filename}_summary{timestamp}.txt")
            
            with open(summary_file, 'w') as sumfile:
                sumfile.write("# ERPCT Attack Summary\n")
                sumfile.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Basic statistics
                sumfile.write("## Statistics\n")
                stats = self.get_stats()
                sumfile.write(f"Total successful attempts: {stats['successful_count']}\n")
                sumfile.write(f"Total failed attempts: {stats['failed_count']}\n")
                sumfile.write(f"Unique credentials found: {stats['unique_credentials_count']}\n\n")
                
                # Write successful credentials
                if len(self.unique_credentials) > 0:
                    sumfile.write("## Successful Credentials\n")
                    sumfile.write("Username,Password\n")
                    
                    for username, password in sorted(self.unique_credentials):
                        sumfile.write(f"{username},{password}\n")
                
                # Additional attack information
                sumfile.write("\n## Attack Information\n")
                target = self.config.get("target", "N/A")
                protocol = self.config.get("protocol", "N/A")
                sumfile.write(f"Target: {target}\n")
                sumfile.write(f"Protocol: {protocol}\n")
                
                # References to other files
                sumfile.write("\n## Result Files\n")
                if self.save_successful:
                    sumfile.write(f"Successful results: {os.path.basename(self.successful_file)}\n")
                if self.save_failed:
                    sumfile.write(f"Failed results: {os.path.basename(self.failed_file)}\n")
                
        except Exception as e:
            self.logger.error(f"Error generating summary file: {str(e)}")
            
    def clear(self) -> None:
        """Clear all stored results."""
        with self.results_lock:
            self.successful_results = []
            self.failed_results = []
            self.unique_credentials = set()
