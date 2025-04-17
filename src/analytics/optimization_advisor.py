#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Optimization Advisor module for ERPCT.
This module analyzes attack performance data and provides optimization recommendations.
"""

import os
import math
import psutil
from typing import Dict, List, Tuple, Any, Optional, Union, Set
from dataclasses import dataclass

from src.utils.logging import get_logger
from src.protocols import protocol_registry


@dataclass
class OptimizationRecommendation:
    """Class to represent an optimization recommendation."""
    
    title: str
    description: str
    impact: str  # "high", "medium", "low"
    category: str  # "performance", "success_rate", "resource_usage", etc.
    actions: List[str]
    
    @property
    def impact_score(self) -> int:
        """Convert impact string to numeric score.
        
        Returns:
            Impact score (3=high, 2=medium, 1=low)
        """
        impact_map = {"high": 3, "medium": 2, "low": 1}
        return impact_map.get(self.impact.lower(), 0)


class OptimizationAdvisor:
    """Analyzes attack data and provides optimization recommendations."""
    
    def __init__(self):
        """Initialize optimization advisor."""
        self.logger = get_logger(__name__)
        self.recommendations = []
        
        # System resource thresholds
        self.system_info = {
            "cpu_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "total_memory_gb": psutil.virtual_memory().total / (1024 * 1024 * 1024),
            "platform": os.name
        }
    
    def analyze_attack_data(self, attack_data: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Analyze attack data and generate optimization recommendations.
        
        Args:
            attack_data: Dictionary with attack statistics and performance data
            
        Returns:
            List of OptimizationRecommendation objects
        """
        self.recommendations = []
        
        # Extract key metrics
        protocol = attack_data.get("protocol", "unknown")
        threads = attack_data.get("threads", 1)
        success_rate = attack_data.get("success_rate", 0.0)
        attempts_per_second = attack_data.get("attempts_per_second", 0.0)
        cpu_usage = attack_data.get("cpu_usage_percent", 0.0)
        memory_usage_mb = attack_data.get("memory_usage_mb", 0.0)
        error_rate = attack_data.get("error_rate", 0.0)
        
        # Analyze key aspects of the attack
        self._analyze_thread_count(threads, cpu_usage, attempts_per_second, protocol)
        self._analyze_protocol_performance(protocol, attempts_per_second)
        self._analyze_resource_usage(cpu_usage, memory_usage_mb)
        self._analyze_error_rate(error_rate, protocol)
        self._analyze_success_rate(success_rate, protocol)
        
        # Sort recommendations by impact (highest first)
        self.recommendations.sort(key=lambda x: x.impact_score, reverse=True)
        
        return self.recommendations
    
    def _analyze_thread_count(self, threads: int, cpu_usage: float, 
                            attempts_per_second: float, protocol: str) -> None:
        """Analyze thread count and suggest optimal settings.
        
        Args:
            threads: Current thread count
            cpu_usage: CPU usage percentage
            attempts_per_second: Current attempts per second
            protocol: Protocol name
        """
        cpu_cores = self.system_info["cpu_cores"]
        
        # Get protocol-specific characteristics
        try:
            protocol_class = protocol_registry.get_protocol(protocol)
            protocol_instance = protocol_class({})
            is_io_bound = getattr(protocol_instance, "is_io_bound", True)  # Default to IO-bound
        except (ValueError, AttributeError):
            # If we can't determine, assume it's IO-bound (most network protocols are)
            is_io_bound = True
        
        # For IO-bound protocols, more threads can help even if CPU usage is high
        if is_io_bound:
            if threads < cpu_cores * 2 and attempts_per_second < 100:
                self.recommendations.append(OptimizationRecommendation(
                    title="Increase thread count for better throughput",
                    description=f"Current thread count ({threads}) is lower than optimal for IO-bound protocol.",
                    impact="medium",
                    category="performance",
                    actions=[f"Increase thread count to {min(cpu_cores * 2, 32)}",
                           "Monitor the system for resource constraints after increasing"]
                ))
        else:
            # For CPU-bound protocols, too many threads can hurt performance
            if threads > cpu_cores and cpu_usage > 90:
                self.recommendations.append(OptimizationRecommendation(
                    title="Reduce thread count to optimize CPU usage",
                    description="Too many threads for CPU-bound operation causing contention.",
                    impact="high",
                    category="performance",
                    actions=[f"Reduce thread count to match CPU core count ({cpu_cores})",
                           "Consider using distributed mode across multiple machines"]
                ))
                
        # If CPU usage is low but thread count is low, suggest increasing threads
        if cpu_usage < 50 and threads < cpu_cores:
            self.recommendations.append(OptimizationRecommendation(
                title="Increase thread count to utilize available CPU",
                description=f"CPU usage is only {cpu_usage:.1f}% with {threads} threads.",
                impact="medium",
                category="performance",
                actions=[f"Increase thread count to {cpu_cores}"]
            ))
    
    def _analyze_protocol_performance(self, protocol: str, attempts_per_second: float) -> None:
        """Analyze protocol-specific performance.
        
        Args:
            protocol: Protocol name
            attempts_per_second: Current attempts per second
        """
        # Protocol-specific baseline expectations
        protocol_baselines = {
            "ssh": 3,
            "ftp": 10,
            "http": 20,
            "http-form": 15,
            "smtp": 5,
            "pop3": 8,
            "imap": 5,
            "smb": 3,
            "rdp": 1,
            "vnc": 2,
            "telnet": 5,
            "mysql": 4,
            "postgres": 4,
            "ldap": 6
        }
        
        # Get baseline for this protocol
        baseline = protocol_baselines.get(protocol.lower(), 10)
        
        # Compare performance to baseline
        if attempts_per_second < baseline * 0.5:
            self.recommendations.append(OptimizationRecommendation(
                title=f"Improve {protocol} performance",
                description=f"Current rate ({attempts_per_second:.2f}/s) is below expected baseline for {protocol} ({baseline}/s).",
                impact="high" if attempts_per_second < baseline * 0.2 else "medium",
                category="performance",
                actions=[
                    "Check network latency to target",
                    "Adjust timeout settings for connection and operation",
                    "Consider protocol-specific optimizations",
                    "Use a machine closer to the target"
                ]
            ))
        
        # Protocol-specific recommendations
        if protocol.lower() == "http-form":
            self.recommendations.append(OptimizationRecommendation(
                title="Optimize HTTP form handling",
                description="HTTP form attacks can be optimized for better performance.",
                impact="medium",
                category="protocol",
                actions=[
                    "Use a more efficient success/failure detection method",
                    "Minimize payload size and unnecessary headers",
                    "Enable HTTP keep-alive for connection reuse",
                    "Consider using a custom HTTP client implementation"
                ]
            ))
        elif protocol.lower() in ["ssh", "rdp", "vnc"]:
            self.recommendations.append(OptimizationRecommendation(
                title=f"Optimize {protocol} connection handling",
                description=f"{protocol} has high connection establishment overhead.",
                impact="medium",
                category="protocol",
                actions=[
                    "Increase connection timeout value slightly",
                    "Allocate more threads specifically for this protocol",
                    "For SSH, disable strict key checking and compression"
                ]
            ))
    
    def _analyze_resource_usage(self, cpu_usage: float, memory_usage_mb: float) -> None:
        """Analyze resource usage and provide recommendations.
        
        Args:
            cpu_usage: CPU usage percentage
            memory_usage_mb: Memory usage in MB
        """
        total_memory_gb = self.system_info["total_memory_gb"]
        
        # Check for memory constraints
        memory_usage_percent = (memory_usage_mb / (total_memory_gb * 1024)) * 100
        
        if memory_usage_percent > 80:
            self.recommendations.append(OptimizationRecommendation(
                title="Reduce memory usage",
                description=f"Memory usage is high ({memory_usage_mb:.1f} MB, {memory_usage_percent:.1f}% of system memory).",
                impact="high",
                category="resource_usage",
                actions=[
                    "Use smaller wordlists or split into multiple runs",
                    "Optimize data structures for memory efficiency",
                    "Enable memory-efficient mode (if available in configuration)",
                    "Consider using streaming processing for large datasets"
                ]
            ))
        
        # Check for CPU constraints
        if cpu_usage > 90:
            self.recommendations.append(OptimizationRecommendation(
                title="Reduce CPU usage",
                description=f"CPU usage is very high ({cpu_usage:.1f}%).",
                impact="high",
                category="resource_usage",
                actions=[
                    "Reduce thread count",
                    "Avoid CPU-intensive operations like complex pattern matching",
                    "Check for other CPU-intensive applications running simultaneously",
                    "Consider distributed mode across multiple machines"
                ]
            ))
    
    def _analyze_error_rate(self, error_rate: float, protocol: str) -> None:
        """Analyze error rate and provide recommendations.
        
        Args:
            error_rate: Error rate percentage
            protocol: Protocol name
        """
        if error_rate > 20:
            self.recommendations.append(OptimizationRecommendation(
                title="Reduce error rate",
                description=f"High error rate detected ({error_rate:.1f}%).",
                impact="high",
                category="reliability",
                actions=[
                    "Increase connection timeout values",
                    "Implement more robust error handling and retries",
                    "Check network stability and target availability",
                    "Reduce attack rate to prevent overwhelming the target",
                    "Check logs for specific error messages"
                ]
            ))
        
        # Protocol-specific error handling
        if protocol.lower() in ["http", "http-form"] and error_rate > 10:
            self.recommendations.append(OptimizationRecommendation(
                title="Optimize HTTP error handling",
                description="HTTP protocol is experiencing errors that may indicate server-side limits.",
                impact="medium",
                category="protocol",
                actions=[
                    "Add delay between requests",
                    "Implement random User-Agent rotation",
                    "Use proxy rotation to distribute requests",
                    "Implement cookie handling for session management"
                ]
            ))
    
    def _analyze_success_rate(self, success_rate: float, protocol: str) -> None:
        """Analyze success rate and provide recommendations.
        
        Args:
            success_rate: Success rate percentage
            protocol: Protocol name
        """
        if success_rate < 0.01 and success_rate > 0:
            self.recommendations.append(OptimizationRecommendation(
                title="Improve wordlist selection",
                description=f"Very low success rate ({success_rate:.3f}%) suggests ineffective wordlist.",
                impact="high",
                category="success_rate",
                actions=[
                    "Use more targeted wordlists based on target characteristics",
                    "Implement password mutation rules specific to the target",
                    "Consider using organizational or industry-specific wordlists",
                    "Try different username lists if focusing on user enumeration"
                ]
            ))


def analyze_attack_efficiency(attack_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze attack efficiency based on performance data.
    
    Args:
        attack_data: Dictionary with attack statistics and performance data
        
    Returns:
        Dictionary with efficiency analysis
    """
    logger = get_logger(__name__)
    
    # Extract key metrics
    protocol = attack_data.get("protocol", "unknown")
    total_attempts = attack_data.get("total_attempts", 0)
    successful_attempts = attack_data.get("successful_attempts", 0)
    attempts_per_second = attack_data.get("attempts_per_second", 0)
    elapsed_seconds = attack_data.get("elapsed_seconds", 0)
    
    # Calculate basic efficiency metrics
    efficiency = {
        "success_rate": (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0,
        "attempts_per_second": attempts_per_second,
        "success_per_minute": (successful_attempts / (elapsed_seconds / 60)) if elapsed_seconds > 0 else 0,
        "work_per_success": (total_attempts / successful_attempts) if successful_attempts > 0 else float('inf')
    }
    
    # Calculate cost-benefit metrics
    if successful_attempts > 0:
        avg_time_to_success = elapsed_seconds / successful_attempts
    else:
        avg_time_to_success = float('inf')
    
    efficiency["avg_seconds_per_success"] = avg_time_to_success
    
    # Protocol-specific baselines for comparison
    baselines = {
        "ssh": {"attempts_per_second": 3, "success_rate": 0.1},
        "ftp": {"attempts_per_second": 10, "success_rate": 0.5},
        "http": {"attempts_per_second": 20, "success_rate": 0.05},
        "smtp": {"attempts_per_second": 5, "success_rate": 0.02},
        "smb": {"attempts_per_second": 3, "success_rate": 0.1},
    }
    
    # Compare against baseline if available
    baseline = baselines.get(protocol.lower(), {"attempts_per_second": 10, "success_rate": 0.1})
    
    efficiency["performance_vs_baseline"] = (attempts_per_second / baseline["attempts_per_second"]) * 100
    efficiency["success_rate_vs_baseline"] = (efficiency["success_rate"] / baseline["success_rate"]) if baseline["success_rate"] > 0 else 0
    
    # Overall efficiency score (0-100)
    # Weight performance and success rates
    performance_weight = 0.7  # 70% weight to performance
    success_weight = 0.3      # 30% weight to success rate
    
    perf_score = min(100, efficiency["performance_vs_baseline"])
    success_score = min(100, efficiency["success_rate_vs_baseline"])
    
    efficiency["overall_score"] = (perf_score * performance_weight) + (success_score * success_weight)
    
    # Categorize efficiency
    if efficiency["overall_score"] >= 80:
        efficiency["rating"] = "excellent"
    elif efficiency["overall_score"] >= 60:
        efficiency["rating"] = "good"
    elif efficiency["overall_score"] >= 40:
        efficiency["rating"] = "average"
    elif efficiency["overall_score"] >= 20:
        efficiency["rating"] = "poor"
    else:
        efficiency["rating"] = "very poor"
    
    return efficiency


def get_optimization_recommendations(attack_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get optimization recommendations based on attack data.
    
    Args:
        attack_data: Dictionary with attack statistics and performance data
        
    Returns:
        List of recommendation dictionaries
    """
    advisor = OptimizationAdvisor()
    recommendations = advisor.analyze_attack_data(attack_data)
    
    # Convert recommendations to dictionaries
    return [
        {
            "title": rec.title,
            "description": rec.description,
            "impact": rec.impact,
            "category": rec.category,
            "actions": rec.actions
        }
        for rec in recommendations
    ]


def calculate_optimal_thread_count(protocol: str, 
                                 cpu_cores: Optional[int] = None,
                                 memory_gb: Optional[float] = None,
                                 network_mbps: Optional[float] = None) -> Dict[str, Any]:
    """Calculate optimal thread count for a given protocol and system resources.
    
    Args:
        protocol: Protocol name
        cpu_cores: Number of CPU cores (detected automatically if None)
        memory_gb: Available memory in GB (detected automatically if None)
        network_mbps: Available network bandwidth in Mbps (estimated if None)
        
    Returns:
        Dictionary with thread count recommendations and rationale
    """
    logger = get_logger(__name__)
    
    # Auto-detect resources if not provided
    if cpu_cores is None:
        cpu_cores = psutil.cpu_count(logical=True)
    
    if memory_gb is None:
        memory_gb = psutil.virtual_memory().total / (1024 * 1024 * 1024)
    
    # Protocol-specific characteristics
    protocol_characteristics = {
        "ssh": {"io_bound": True, "memory_per_thread_mb": 10, "bandwidth_per_thread_kbps": 50},
        "ftp": {"io_bound": True, "memory_per_thread_mb": 8, "bandwidth_per_thread_kbps": 100},
        "http": {"io_bound": True, "memory_per_thread_mb": 15, "bandwidth_per_thread_kbps": 200},
        "http-form": {"io_bound": True, "memory_per_thread_mb": 20, "bandwidth_per_thread_kbps": 250},
        "smtp": {"io_bound": True, "memory_per_thread_mb": 8, "bandwidth_per_thread_kbps": 30},
        "pop3": {"io_bound": True, "memory_per_thread_mb": 8, "bandwidth_per_thread_kbps": 20},
        "imap": {"io_bound": True, "memory_per_thread_mb": 12, "bandwidth_per_thread_kbps": 25},
        "smb": {"io_bound": True, "memory_per_thread_mb": 15, "bandwidth_per_thread_kbps": 300},
        "rdp": {"io_bound": True, "memory_per_thread_mb": 25, "bandwidth_per_thread_kbps": 400},
        "vnc": {"io_bound": True, "memory_per_thread_mb": 20, "bandwidth_per_thread_kbps": 350},
        "mysql": {"io_bound": True, "memory_per_thread_mb": 12, "bandwidth_per_thread_kbps": 20},
        "postgres": {"io_bound": True, "memory_per_thread_mb": 12, "bandwidth_per_thread_kbps": 20},
        "ldap": {"io_bound": True, "memory_per_thread_mb": 10, "bandwidth_per_thread_kbps": 15},
    }
    
    # Get characteristics for the requested protocol, or use defaults
    char = protocol_characteristics.get(protocol.lower(), {
        "io_bound": True, 
        "memory_per_thread_mb": 15, 
        "bandwidth_per_thread_kbps": 100
    })
    
    # Calculate limits based on resources
    memory_limit = int((memory_gb * 1024 * 0.8) / char["memory_per_thread_mb"])  # Use 80% of available memory
    
    # For IO-bound protocols, we can use more threads than CPU cores
    if char["io_bound"]:
        cpu_limit = cpu_cores * 4  # Arbitrary multiplier for IO-bound operations
    else:
        cpu_limit = cpu_cores  # For CPU-bound, match thread count to cores
    
    # Calculate network limit if bandwidth is provided
    if network_mbps is not None:
        network_limit = int((network_mbps * 1000) / char["bandwidth_per_thread_kbps"])
    else:
        # Estimate based on typical home/office connection
        network_limit = 1000  # High value to indicate it's not the limiting factor
    
    # The limiting factor is the minimum of all limits
    limits = {
        "cpu_limit": cpu_limit,
        "memory_limit": memory_limit,
        "network_limit": network_limit
    }
    
    limiting_factor = min(limits, key=limits.get)
    optimal_threads = limits[limiting_factor]
    
    # Cap at a reasonable maximum to prevent DoS-like behavior
    max_reasonable_threads = 200
    if optimal_threads > max_reasonable_threads:
        optimal_threads = max_reasonable_threads
        limiting_factor = "system_safety"
    
    # Determine if distributed mode would be beneficial
    distributed_recommended = optimal_threads > 50 or cpu_cores > 8
    
    # Create the recommendation
    recommendation = {
        "protocol": protocol,
        "optimal_thread_count": optimal_threads,
        "limiting_factor": limiting_factor,
        "resource_limits": limits,
        "system_info": {
            "cpu_cores": cpu_cores,
            "memory_gb": memory_gb,
            "network_mbps": network_mbps if network_mbps is not None else "unknown"
        },
        "distributed_recommended": distributed_recommended,
        "rationale": f"Thread count limited by {limiting_factor} ({limits[limiting_factor]} threads)."
    }
    
    return recommendation
