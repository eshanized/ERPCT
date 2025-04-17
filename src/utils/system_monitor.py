#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT System Monitor.
This module provides system resource monitoring capabilities.
"""

import os
import socket
import platform
import threading
import time
import psutil
from datetime import datetime

from src.utils.logging import get_logger


class SystemMonitor:
    """System monitoring class for resource usage and system info."""
    
    def __init__(self):
        """Initialize the system monitor."""
        self.logger = get_logger(__name__)
        self.lock = threading.Lock()
        self._metrics = {
            'cpu': 0.0,
            'memory': 0.0,
            'disk': 0.0,
            'network': 0.0,
            'timestamp': datetime.now(),
            'hostname': socket.gethostname(),
            'ip_address': self._get_ip_address(),
            'uptime': self._get_uptime(),
            'system_info': self._get_system_info()
        }
        self._version = self._get_version()
        self._monitoring = False
        self._update_thread = None
        
        # Start monitoring thread
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start monitoring system resources."""
        if not self._monitoring:
            self._monitoring = True
            self._update_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._update_thread.start()
            self.logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring system resources."""
        self._monitoring = False
        if self._update_thread:
            self._update_thread.join(timeout=1.0)
            self._update_thread = None
        self.logger.info("System monitoring stopped")
    
    def _monitor_loop(self):
        """Background thread to update system metrics."""
        while self._monitoring:
            try:
                self._update_metrics()
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                self.logger.error(f"Error updating system metrics: {str(e)}")
                time.sleep(5)  # Longer delay on error
    
    def _update_metrics(self):
        """Update system resource metrics."""
        with self.lock:
            # CPU usage
            self._metrics['cpu'] = psutil.cpu_percent()
            
            # Memory usage
            memory = psutil.virtual_memory()
            self._metrics['memory'] = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self._metrics['disk'] = disk.percent
            
            # Network usage (as percentage of max observed throughput)
            net_io = psutil.net_io_counters()
            if not hasattr(self, '_last_net_io'):
                self._last_net_io = net_io
                self._max_net_throughput = 1000000  # 1 MB/s initial estimate
                self._metrics['network'] = 0.0
            else:
                # Calculate current throughput
                bytes_sent = net_io.bytes_sent - self._last_net_io.bytes_sent
                bytes_recv = net_io.bytes_recv - self._last_net_io.bytes_recv
                throughput = (bytes_sent + bytes_recv) / 2.0
                
                # Update max throughput if needed
                if throughput > self._max_net_throughput:
                    self._max_net_throughput = throughput
                
                # Calculate network usage percentage
                if self._max_net_throughput > 0:
                    self._metrics['network'] = min(100.0, (throughput / self._max_net_throughput) * 100.0)
                
                self._last_net_io = net_io
            
            # Update timestamp and uptime
            self._metrics['timestamp'] = datetime.now()
            self._metrics['uptime'] = self._get_uptime()
    
    def get_metrics(self):
        """Get current system metrics.
        
        Returns:
            dict: Dictionary with system metrics
        """
        with self.lock:
            return self._metrics.copy()
    
    def get_formatted_metrics(self):
        """Get formatted system metrics for display.
        
        Returns:
            dict: Dictionary with formatted system metrics
        """
        metrics = self.get_metrics()
        return {
            'cpu': f"{metrics['cpu']:.1f}%",
            'memory': f"{metrics['memory']:.1f}%",
            'disk': f"{metrics['disk']:.1f}%",
            'network': f"{metrics['network']:.1f}%",
            'hostname': metrics['hostname'],
            'ip_address': metrics['ip_address'],
            'uptime': metrics['uptime'],
            'version': self._version,
            'system_info': metrics['system_info']
        }
    
    def _get_ip_address(self):
        """Get the primary IP address of the system.
        
        Returns:
            str: IP address
        """
        try:
            # Create a socket to determine the outgoing IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            self.logger.error(f"Error determining IP address: {str(e)}")
            return "127.0.0.1"
    
    def _get_uptime(self):
        """Get system uptime in a formatted string.
        
        Returns:
            str: Uptime string in the format "Xd Yh Zm"
        """
        try:
            uptime_seconds = int(time.time() - psutil.boot_time())
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)
            
            return f"{days}d {hours}h {minutes}m"
        except Exception as e:
            self.logger.error(f"Error determining uptime: {str(e)}")
            return "0d 0h 0m"
    
    def _get_system_info(self):
        """Get basic system information.
        
        Returns:
            dict: Dictionary with system information
        """
        try:
            return {
                'os': platform.system(),
                'os_version': platform.version(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            }
        except Exception as e:
            self.logger.error(f"Error determining system info: {str(e)}")
            return {
                'os': 'Unknown',
                'os_version': 'Unknown',
                'processor': 'Unknown',
                'python_version': 'Unknown'
            }
    
    def _get_version(self):
        """Get the ERPCT version from version file.
        
        Returns:
            str: Version string
        """
        try:
            version_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'VERSION'
            )
            
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    return f.read().strip()
            
            return "1.0.0"  # Default version if file not found
        except Exception as e:
            self.logger.error(f"Error reading version file: {str(e)}")
            return "1.0.0" 