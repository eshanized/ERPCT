#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Performance metrics module for ERPCT.
This module provides tools for tracking and analyzing performance of password cracking operations.
"""

import os
import time
import threading
import psutil
import statistics
from typing import Dict, List, Tuple, Any, Optional, Callable, Union
from collections import deque, defaultdict

from src.utils.logging import get_logger


class PerformanceTracker:
    """Track performance metrics during attack operations."""
    
    def __init__(self, attack_id: Optional[str] = None, 
                window_size: int = 60, sample_interval: float = 1.0):
        """Initialize performance tracker.
        
        Args:
            attack_id: Optional attack identifier
            window_size: Size of the sliding window for metrics (in samples)
            sample_interval: Time between samples in seconds
        """
        self.logger = get_logger(__name__)
        self.attack_id = attack_id
        self.window_size = window_size
        self.sample_interval = sample_interval
        
        # Metrics storage
        self.timestamps = deque(maxlen=window_size)
        self.attempts = deque(maxlen=window_size)
        self.attempt_rates = deque(maxlen=window_size)
        self.successes = deque(maxlen=window_size)
        self.cpu_usage = deque(maxlen=window_size)
        self.memory_usage = deque(maxlen=window_size)
        self.network_usage = deque(maxlen=window_size)
        
        # Tracking state
        self.running = False
        self.tracking_thread = None
        self.last_sampled = 0
        self.total_attempts = 0
        self.total_successes = 0
        self.failed_attempts = 0
        self.error_attempts = 0
        
        # Protocol specific metrics
        self.protocol = None
        self.protocol_metrics = defaultdict(list)
        
        # Resource usage
        self.process = psutil.Process(os.getpid())
        
        # Custom tracking callbacks
        self.custom_metrics = {}
        self.custom_callbacks = {}
    
    def start(self, protocol: Optional[str] = None) -> None:
        """Start tracking performance metrics.
        
        Args:
            protocol: Optional protocol name for protocol-specific metrics
        """
        if self.running:
            return
            
        self.protocol = protocol
        self.running = True
        self.last_sampled = time.time()
        
        # Start tracking thread
        self.tracking_thread = threading.Thread(
            target=self._tracking_loop,
            daemon=True
        )
        self.tracking_thread.start()
        self.logger.debug(f"Performance tracking started for attack ID: {self.attack_id}")
    
    def stop(self) -> None:
        """Stop tracking performance metrics."""
        self.running = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=2.0)
            self.tracking_thread = None
        self.logger.debug(f"Performance tracking stopped for attack ID: {self.attack_id}")
    
    def _tracking_loop(self) -> None:
        """Main tracking loop to sample metrics."""
        while self.running:
            now = time.time()
            
            # Sample at regular intervals
            if now - self.last_sampled >= self.sample_interval:
                self._take_sample()
                self.last_sampled = now
                
            # Sleep to avoid consuming CPU
            time.sleep(min(0.1, self.sample_interval / 10))
    
    def _take_sample(self) -> None:
        """Take a sample of current performance metrics."""
        now = time.time()
        
        # Record timestamp
        self.timestamps.append(now)
        
        # Resource usage
        try:
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            
            # Store metrics
            self.cpu_usage.append(cpu_percent)
            self.memory_usage.append(memory_mb)
            
            # Network usage is more complex, simplified version here
            net_io = psutil.net_io_counters()
            if hasattr(self, '_last_net_io'):
                sent_delta = net_io.bytes_sent - self._last_net_io.bytes_sent
                recv_delta = net_io.bytes_recv - self._last_net_io.bytes_recv
                self.network_usage.append((sent_delta, recv_delta))
            else:
                self.network_usage.append((0, 0))
            self._last_net_io = net_io
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
            self.logger.error(f"Error sampling system metrics: {str(e)}")
        
        # Sample custom metrics if defined
        for metric_name, callback in self.custom_callbacks.items():
            try:
                value = callback()
                if metric_name not in self.custom_metrics:
                    self.custom_metrics[metric_name] = deque(maxlen=self.window_size)
                self.custom_metrics[metric_name].append(value)
            except Exception as e:
                self.logger.error(f"Error sampling custom metric {metric_name}: {str(e)}")
    
    def record_attempt(self, success: bool, error: bool = False) -> None:
        """Record an attack attempt.
        
        Args:
            success: Whether the attempt was successful
            error: Whether the attempt resulted in an error
        """
        # Update counters
        self.total_attempts += 1
        
        if success:
            self.total_successes += 1
        elif error:
            self.error_attempts += 1
        else:
            self.failed_attempts += 1
            
        # Track attempts for rate calculation
        now = time.time()
        if self.timestamps and len(self.attempts) < self.window_size:
            # Fill in zeros for any missing points at the start
            self.attempts.append(self.total_attempts)
            self.successes.append(self.total_successes)
        elif self.timestamps:
            # Regular update
            self.attempts.append(self.total_attempts)
            self.successes.append(self.total_successes)
            
            # Calculate attempt rate over the last interval
            if len(self.timestamps) >= 2:
                time_diff = self.timestamps[-1] - self.timestamps[-2]
                attempt_diff = self.attempts[-1] - self.attempts[-2]
                if time_diff > 0:
                    rate = attempt_diff / time_diff
                    self.attempt_rates.append(rate)
    
    def record_protocol_metric(self, name: str, value: Any) -> None:
        """Record a protocol-specific metric.
        
        Args:
            name: Metric name
            value: Metric value
        """
        if self.protocol:
            metric_key = f"{self.protocol}_{name}"
            self.protocol_metrics[metric_key].append(value)
    
    def register_custom_metric(self, name: str, callback: Callable[[], Any]) -> None:
        """Register a custom metric with a callback function.
        
        Args:
            name: Metric name
            callback: Function that returns the metric value
        """
        self.custom_callbacks[name] = callback
    
    def get_current_rate(self) -> float:
        """Get the current attempt rate.
        
        Returns:
            Current attempts per second
        """
        if not self.attempt_rates:
            return 0.0
            
        # Return the most recent rate or an average of last few
        return self.attempt_rates[-1]
    
    def get_average_rate(self) -> float:
        """Get the average attempt rate.
        
        Returns:
            Average attempts per second
        """
        if not self.attempt_rates:
            return 0.0
            
        return statistics.mean(self.attempt_rates)
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage statistics.
        
        Returns:
            Dictionary with CPU, memory, and network usage
        """
        cpu_avg = statistics.mean(self.cpu_usage) if self.cpu_usage else 0
        mem_avg = statistics.mean(self.memory_usage) if self.memory_usage else 0
        
        # Calculate average network usage
        net_sent_avg = 0
        net_recv_avg = 0
        if self.network_usage:
            sent_values = [x[0] for x in self.network_usage]
            recv_values = [x[1] for x in self.network_usage]
            net_sent_avg = statistics.mean(sent_values)
            net_recv_avg = statistics.mean(recv_values)
        
        return {
            "cpu_percent": cpu_avg,
            "memory_mb": mem_avg,
            "network_sent_bytes_per_sec": net_sent_avg,
            "network_recv_bytes_per_sec": net_recv_avg
        }
    
    def get_protocol_metrics(self) -> Dict[str, List[Any]]:
        """Get protocol-specific metrics.
        
        Returns:
            Dictionary with protocol metrics
        """
        return dict(self.protocol_metrics)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary.
        
        Returns:
            Dictionary with performance summary
        """
        # Calculate time-based metrics
        elapsed = 0
        if self.timestamps:
            elapsed = self.timestamps[-1] - self.timestamps[0] if len(self.timestamps) > 1 else 0
            
        # Calculate rates
        overall_rate = self.total_attempts / elapsed if elapsed > 0 else 0
        success_rate = (self.total_successes / self.total_attempts * 100) if self.total_attempts > 0 else 0
        
        # Get resource usage
        resource_usage = self.get_resource_usage()
        
        return {
            "attack_id": self.attack_id,
            "protocol": self.protocol,
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "failed_attempts": self.failed_attempts,
            "error_attempts": self.error_attempts,
            "elapsed_seconds": elapsed,
            "overall_rate": overall_rate,
            "current_rate": self.get_current_rate(),
            "success_rate_percent": success_rate,
            "cpu_usage_percent": resource_usage["cpu_percent"],
            "memory_usage_mb": resource_usage["memory_mb"],
            "network_sent_bps": resource_usage["network_sent_bytes_per_sec"],
            "network_recv_bps": resource_usage["network_recv_bytes_per_sec"]
        }


def calculate_throughput(attempts: int, elapsed_time: float) -> Dict[str, float]:
    """Calculate throughput metrics for an attack.
    
    Args:
        attempts: Number of attempts
        elapsed_time: Elapsed time in seconds
        
    Returns:
        Dictionary with throughput metrics
    """
    if elapsed_time <= 0:
        return {
            "attempts_per_second": 0.0,
            "seconds_per_attempt": 0.0,
            "attempts_per_minute": 0.0,
            "attempts_per_hour": 0.0
        }
        
    attempts_per_second = attempts / elapsed_time
    seconds_per_attempt = elapsed_time / attempts if attempts > 0 else float('inf')
    
    return {
        "attempts_per_second": attempts_per_second,
        "seconds_per_attempt": seconds_per_attempt,
        "attempts_per_minute": attempts_per_second * 60,
        "attempts_per_hour": attempts_per_second * 3600
    }


def calculate_resource_usage(cpu_samples: List[float], memory_samples: List[float],
                           network_samples: List[Tuple[float, float]]) -> Dict[str, Any]:
    """Calculate resource usage statistics.
    
    Args:
        cpu_samples: List of CPU usage percentages
        memory_samples: List of memory usage values (MB)
        network_samples: List of (sent, received) network bytes
        
    Returns:
        Dictionary with resource usage statistics
    """
    if not cpu_samples or not memory_samples:
        return {
            "cpu": {
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "median": 0.0
            },
            "memory_mb": {
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "median": 0.0
            },
            "network": {
                "sent_avg_bps": 0.0,
                "recv_avg_bps": 0.0,
                "total_sent_mb": 0.0,
                "total_recv_mb": 0.0
            }
        }
        
    # CPU statistics
    cpu_stats = {
        "min": min(cpu_samples),
        "max": max(cpu_samples),
        "avg": statistics.mean(cpu_samples),
        "median": statistics.median(cpu_samples)
    }
    
    # Memory statistics
    memory_stats = {
        "min": min(memory_samples),
        "max": max(memory_samples),
        "avg": statistics.mean(memory_samples),
        "median": statistics.median(memory_samples)
    }
    
    # Network statistics
    network_stats = {
        "sent_avg_bps": 0.0,
        "recv_avg_bps": 0.0,
        "total_sent_mb": 0.0,
        "total_recv_mb": 0.0
    }
    
    if network_samples:
        sent_samples = [s[0] for s in network_samples]
        recv_samples = [s[1] for s in network_samples]
        
        network_stats["sent_avg_bps"] = statistics.mean(sent_samples)
        network_stats["recv_avg_bps"] = statistics.mean(recv_samples)
        network_stats["total_sent_mb"] = sum(sent_samples) / (1024 * 1024)
        network_stats["total_recv_mb"] = sum(recv_samples) / (1024 * 1024)
    
    return {
        "cpu": cpu_stats,
        "memory_mb": memory_stats,
        "network": network_stats
    }


def analyze_bottlenecks(performance_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze performance data to identify bottlenecks.
    
    Args:
        performance_data: Dictionary with performance metrics
        
    Returns:
        Dictionary with bottleneck analysis
    """
    bottlenecks = []
    limiting_factors = []
    recommendations = []
    
    # Check CPU usage
    cpu_usage = performance_data.get("cpu", {}).get("avg", 0)
    if cpu_usage > 90:
        bottlenecks.append("cpu")
        limiting_factors.append(f"High CPU usage ({cpu_usage:.1f}%)")
        recommendations.append("Reduce thread count or use distributed mode")
    
    # Check memory usage
    memory_usage = performance_data.get("memory_mb", {}).get("avg", 0)
    if memory_usage > 1024:  # >1GB
        bottlenecks.append("memory")
        limiting_factors.append(f"High memory usage ({memory_usage:.1f} MB)")
        recommendations.append("Optimize memory usage or use smaller wordlists")
    
    # Check network usage
    network = performance_data.get("network", {})
    network_usage = network.get("sent_avg_bps", 0) + network.get("recv_avg_bps", 0)
    if network_usage > 1_000_000:  # >1MB/s
        bottlenecks.append("network")
        limiting_factors.append(f"High network usage ({network_usage/1024/1024:.2f} MB/s)")
        recommendations.append("Reduce request rate or use more efficient protocols")
    
    # Check attempt rate vs expected
    attempts_per_second = performance_data.get("attempts_per_second", 0)
    if attempts_per_second < 1:
        bottlenecks.append("throughput")
        limiting_factors.append(f"Low attempt rate ({attempts_per_second:.2f}/s)")
        recommendations.append("Increase thread count or reduce timeout values")
    
    # Overall assessment
    if not bottlenecks:
        assessment = "No significant bottlenecks detected"
    else:
        assessment = f"Performance limited by: {', '.join(bottlenecks)}"
    
    return {
        "bottlenecks": bottlenecks,
        "limiting_factors": limiting_factors,
        "recommendations": recommendations,
        "assessment": assessment
    }


def get_protocol_performance(protocol: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Get protocol-specific performance metrics.
    
    Args:
        protocol: Protocol name
        metrics: Raw performance metrics
        
    Returns:
        Dictionary with protocol-specific metrics and insights
    """
    # Protocol-specific baseline expectations (attempts/second)
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
    
    attempts_per_second = metrics.get("attempts_per_second", 0)
    baseline = protocol_baselines.get(protocol.lower(), 10)
    
    # Calculate efficiency compared to baseline
    efficiency = (attempts_per_second / baseline) * 100 if baseline > 0 else 0
    
    # Protocol-specific insights
    insights = []
    if protocol.lower() == "http-form":
        # Check if network is the bottleneck
        network_recv = metrics.get("network", {}).get("recv_avg_bps", 0)
        if network_recv > 500000:  # 500KB/s
            insights.append("Large HTTP responses detected - consider filtering response size")
    elif protocol.lower() in ["ssh", "rdp", "vnc"]:
        # These protocols have high connection establishment overhead
        if attempts_per_second < baseline * 0.5:
            insights.append(f"Performance below expected baseline for {protocol} " +
                          "- consider increasing timeout values")
    
    # Overall protocol assessment
    if efficiency >= 90:
        assessment = f"{protocol} performance is excellent"
    elif efficiency >= 70:
        assessment = f"{protocol} performance is good"
    elif efficiency >= 40:
        assessment = f"{protocol} performance is average"
    else:
        assessment = f"{protocol} performance is below expectations"
    
    # Include any bottlenecks from the general analysis
    bottlenecks = metrics.get("bottlenecks", [])
    if bottlenecks:
        assessment += f" - limited by {', '.join(bottlenecks)}"
    
    return {
        "protocol": protocol,
        "attempts_per_second": attempts_per_second,
        "expected_baseline": baseline,
        "efficiency_percent": efficiency,
        "assessment": assessment,
        "insights": insights,
        "recommendations": metrics.get("recommendations", [])
    }
