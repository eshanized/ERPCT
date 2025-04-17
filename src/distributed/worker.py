#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT distributed worker module.
This module implements the worker for distributed password cracking.
"""

import os
import sys
import json
import time
import threading
import socket
import platform
from typing import Dict, List, Optional, Tuple, Any

from src.core.distributed import DistributedAttackController
from src.core.attack import Attack, AttackResult
from src.utils.logging import get_logger
from src.utils.system_monitor import SystemMonitor


class Worker:
    """
    Worker for distributed password cracking.
    
    The Worker connects to a coordinator, receives tasks, executes them,
    and reports results back.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the worker.
        
        Returns:
            Worker instance
        """
        if cls._instance is None:
            cls._instance = Worker()
        return cls._instance
    
    def __init__(self):
        """Initialize the worker."""
        self.logger = get_logger(__name__)
        self.controller = DistributedAttackController.get_instance()
        
        # Configuration
        self.master_address = ""
        self.name = socket.gethostname()
        self.max_tasks = 1  # Maximum number of concurrent tasks
        
        # Status tracking
        self.is_running = False
        self.start_time = 0
        self.current_task = None
        self.completed_tasks = []
        
        # System monitoring
        try:
            self.system_monitor = SystemMonitor()
        except Exception as e:
            self.logger.warning(f"Failed to initialize system monitor: {str(e)}")
            self.system_monitor = None
        
        # Synchronization
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
    
    def start(self, master_address: str):
        """Start the worker.
        
        Args:
            master_address: Address of the coordinator (host:port)
        """
        with self.lock:
            if self.is_running:
                self.logger.warning("Worker is already running")
                return
            
            # Update configuration
            self.master_address = master_address
            
            # Configure and start the controller
            self.controller.configure_as_worker(master_address)
            self.controller.start()
            
            # Start system monitor if available
            if self.system_monitor:
                self.system_monitor.start()
            
            # Update status
            self.is_running = True
            self.start_time = time.time()
            self.stop_event.clear()
            
            # Start status update thread
            self.status_thread = threading.Thread(target=self._status_update_loop, daemon=True)
            self.status_thread.start()
            
            self.logger.info(f"Worker started, connected to {master_address}")
    
    def stop(self):
        """Stop the worker."""
        with self.lock:
            if not self.is_running:
                self.logger.warning("Worker is not running")
                return
            
            # Stop the controller
            self.controller.stop()
            
            # Stop system monitor if available
            if self.system_monitor:
                self.system_monitor.stop()
            
            # Update status
            self.is_running = False
            self.stop_event.set()
            
            # Wait for status thread to terminate
            if hasattr(self, 'status_thread') and self.status_thread.is_alive():
                self.status_thread.join(timeout=2.0)
            
            self.logger.info("Worker stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the worker.
        
        Returns:
            Status dictionary
        """
        system_stats = {}
        if self.system_monitor:
            system_stats = self.system_monitor.get_stats()
        
        with self.lock:
            return {
                "is_running": self.is_running,
                "name": self.name,
                "master_address": self.master_address,
                "start_time": self.start_time,
                "uptime": time.time() - self.start_time if self.is_running else 0,
                "current_task": self.current_task,
                "completed_tasks": len(self.completed_tasks),
                "system": {
                    "hostname": socket.gethostname(),
                    "platform": platform.platform(),
                    "processor": platform.processor(),
                    "python_version": platform.python_version(),
                    **system_stats
                }
            }
    
    def _status_update_loop(self):
        """Periodically send status updates to the coordinator."""
        while not self.stop_event.is_set():
            try:
                # Get current status
                status = self.get_status()
                
                # Send status update message
                # Note: This is handled internally by the controller
                # We don't need to do anything here
                
                # Sleep for a while
                time.sleep(10.0)
            except Exception as e:
                self.logger.error(f"Error in status update loop: {str(e)}")
                time.sleep(30.0)  # Longer delay on error
    
    def execute_task(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task.
        
        This method is called by the controller when a task is received.
        It is not meant to be called directly.
        
        Args:
            task_id: Task ID
            config: Task configuration
            
        Returns:
            Task result dictionary
        """
        with self.lock:
            self.current_task = task_id
        
        self.logger.info(f"Executing task {task_id}")
        
        try:
            # Create Attack instance
            attack = Attack(config)
            results = []
            
            # Define success callback
            def on_success(result: AttackResult):
                """Handle successful authentication."""
                results.append({
                    "username": result.username,
                    "password": result.password,
                    "timestamp": result.timestamp,
                    "message": result.message
                })
            
            # Set callback
            attack.set_on_success_callback(on_success)
            
            # Start attack
            attack.start()
            
            # Wait for attack to finish
            while attack.status.running and not self.stop_event.is_set():
                time.sleep(0.1)
            
            # If we're stopping, stop the attack too
            if self.stop_event.is_set() and attack.status.running:
                attack.stop()
            
            # Construct result
            status = attack.get_status()
            success = len(results) > 0
            result = {
                "task_id": task_id,
                "success": success,
                "credentials": results,
                "stats": status,
                "completed": time.time()
            }
            
            # Store completed task
            with self.lock:
                self.completed_tasks.append({
                    "task_id": task_id,
                    "success": success,
                    "completed": time.time()
                })
                self.current_task = None
            
            self.logger.info(f"Task {task_id} completed, success: {success}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {str(e)}")
            
            # Construct error result
            result = {
                "task_id": task_id,
                "success": False,
                "error": str(e),
                "completed": time.time()
            }
            
            # Update status
            with self.lock:
                self.completed_tasks.append({
                    "task_id": task_id,
                    "success": False,
                    "error": str(e),
                    "completed": time.time()
                })
                self.current_task = None
            
            return result
