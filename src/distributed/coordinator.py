#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT distributed coordinator module.
This module implements the coordinator for distributed password cracking.
"""

import os
import json
import time
import threading
import socket
import queue
from typing import Dict, List, Optional, Tuple, Any, Set
import uuid

from src.core.distributed import DistributedAttackController, NodeStatus
from src.utils.logging import get_logger


class Coordinator:
    """
    Coordinator for distributed password cracking.
    
    The Coordinator manages workers, distributes tasks, and collects results.
    It is designed to be run as a standalone process or embedded in a larger application.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the coordinator.
        
        Returns:
            Coordinator instance
        """
        if cls._instance is None:
            cls._instance = Coordinator()
        return cls._instance
    
    def __init__(self):
        """Initialize the coordinator."""
        self.logger = get_logger(__name__)
        self.controller = DistributedAttackController.get_instance()
        
        # Configuration
        self.bind_address = "0.0.0.0"
        self.bind_port = 5555
        self.node_timeout = 30.0  # seconds
        
        # Task management
        self.tasks = {}  # task_id -> task_dict
        self.results = {}  # task_id -> result_dict
        
        # Status tracking
        self.is_running = False
        self.start_time = 0
        
        # Synchronization
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
    
    def start(self, bind_address: str = "0.0.0.0", bind_port: int = 5555):
        """Start the coordinator.
        
        Args:
            bind_address: Address to bind to
            bind_port: Port to bind to
        """
        with self.lock:
            if self.is_running:
                self.logger.warning("Coordinator is already running")
                return
            
            # Update configuration
            self.bind_address = bind_address
            self.bind_port = bind_port
            
            # Configure and start the controller
            self.controller.configure_as_master(bind_address, bind_port)
            self.controller.start()
            
            # Update status
            self.is_running = True
            self.start_time = time.time()
            self.stop_event.clear()
            
            self.logger.info(f"Coordinator started on {bind_address}:{bind_port}")
    
    def stop(self):
        """Stop the coordinator."""
        with self.lock:
            if not self.is_running:
                self.logger.warning("Coordinator is not running")
                return
            
            # Stop the controller
            self.controller.stop()
            
            # Update status
            self.is_running = False
            self.stop_event.set()
            
            self.logger.info("Coordinator stopped")
    
    def add_task(self, config: Dict[str, Any]) -> str:
        """Add a task to the queue.
        
        Args:
            config: Task configuration
        
        Returns:
            Task ID
        """
        if not self.is_running:
            raise RuntimeError("Coordinator is not running")
        
        # Add task to the controller
        task_id = self.controller.add_task(config)
        
        # Store task locally
        with self.lock:
            self.tasks[task_id] = {
                "id": task_id,
                "config": config,
                "created": time.time(),
                "status": "queued"
            }
        
        self.logger.info(f"Added task {task_id} to queue")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task.
        
        Args:
            task_id: Task ID
        
        Returns:
            Task status dictionary or None if not found
        """
        # Check local tasks first
        with self.lock:
            if task_id in self.tasks:
                return self.tasks[task_id]
            
            if task_id in self.results:
                return self.results[task_id]
        
        # Check controller
        return self.controller.get_task_status(task_id)
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get a list of connected worker nodes.
        
        Returns:
            List of node status dictionaries
        """
        return self.controller.get_nodes()
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get a list of active tasks.
        
        Returns:
            List of task dictionaries
        """
        with self.lock:
            return [task for task in self.tasks.values() 
                    if task["status"] in ["queued", "assigned", "running"]]
    
    def get_completed_tasks(self) -> List[Dict[str, Any]]:
        """Get a list of completed tasks.
        
        Returns:
            List of task dictionaries
        """
        with self.lock:
            return list(self.results.values())
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the coordinator.
        
        Returns:
            Status dictionary
        """
        nodes = self.get_nodes()
        
        with self.lock:
            active_tasks = self.get_active_tasks()
            completed_tasks = self.get_completed_tasks()
            
            return {
                "is_running": self.is_running,
                "start_time": self.start_time,
                "uptime": time.time() - self.start_time if self.is_running else 0,
                "address": f"{self.bind_address}:{self.bind_port}",
                "node_count": len(nodes),
                "active_nodes": sum(1 for node in nodes if node["connected"] and node["active"]),
                "active_tasks": len(active_tasks),
                "completed_tasks": len(completed_tasks),
                "success_rate": self._calculate_success_rate()
            }
    
    def _calculate_success_rate(self) -> float:
        """Calculate the success rate of completed tasks.
        
        Returns:
            Success rate as a percentage
        """
        with self.lock:
            completed_tasks = self.get_completed_tasks()
            
            if not completed_tasks:
                return 0.0
                
            successful_tasks = sum(1 for task in completed_tasks 
                                 if task.get("result", {}).get("success", False))
                                 
            return (successful_tasks / len(completed_tasks)) * 100 if completed_tasks else 0
