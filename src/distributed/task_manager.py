#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT distributed task manager module.
This module implements task management for distributed password cracking.
"""

import os
import json
import time
import threading
import queue
from typing import Dict, List, Optional, Tuple, Any, Set
import uuid

from src.utils.logging import get_logger


class Task:
    """Class representing a distributed task."""
    
    def __init__(self, task_id: str, config: Dict[str, Any]):
        """Initialize the task.
        
        Args:
            task_id: Unique task ID
            config: Task configuration dictionary
        """
        self.id = task_id
        self.config = config
        self.created = time.time()
        self.started = 0
        self.completed = 0
        self.status = "created"  # created, queued, assigned, running, completed, failed
        self.assigned_node = None
        self.result = None
        self.error = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary.
        
        Returns:
            Dictionary representation of the task
        """
        return {
            "id": self.id,
            "config": self.config,
            "created": self.created,
            "started": self.started,
            "completed": self.completed,
            "status": self.status,
            "assigned_node": self.assigned_node,
            "result": self.result,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a task from a dictionary.
        
        Args:
            data: Dictionary representation of a task
            
        Returns:
            Task instance
        """
        task = cls(data["id"], data["config"])
        task.created = data.get("created", 0)
        task.started = data.get("started", 0)
        task.completed = data.get("completed", 0)
        task.status = data.get("status", "created")
        task.assigned_node = data.get("assigned_node")
        task.result = data.get("result")
        task.error = data.get("error")
        return task


class TaskManager:
    """
    Task manager for distributed password cracking.
    
    The TaskManager handles task creation, queueing, distribution, and tracking.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the task manager.
        
        Returns:
            TaskManager instance
        """
        if cls._instance is None:
            cls._instance = TaskManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the task manager."""
        self.logger = get_logger(__name__)
        
        # Task queues
        self.task_queue = queue.PriorityQueue()  # (priority, task_id)
        self.tasks = {}  # task_id -> Task
        
        # Completed tasks
        self.completed_tasks = []  # List of completed tasks
        self.max_completed_tasks = 1000  # Maximum number of completed tasks to keep
        
        # Node assignment
        self.node_assignments = {}  # node_id -> set(task_id)
        
        # Task scheduling
        self.max_tasks_per_node = 1  # Maximum number of tasks per node
        
        # Persistence
        self.persistence_file = None  # Path to file for persisting tasks
        self.persistence_interval = 300  # Seconds between persistence operations
        
        # Synchronization
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
    
    def start(self, persistence_file: Optional[str] = None, persistence_interval: int = 300):
        """Start the task manager.
        
        Args:
            persistence_file: Path to file for persisting tasks
            persistence_interval: Seconds between persistence operations
        """
        with self.lock:
            self.persistence_file = persistence_file
            self.persistence_interval = persistence_interval
            self.stop_event.clear()
            
            # Start persistence thread if a file is specified
            if persistence_file:
                # Load tasks from file if it exists
                self._load_tasks()
                
                # Start persistence thread
                self.persistence_thread = threading.Thread(
                    target=self._persistence_loop, 
                    daemon=True
                )
                self.persistence_thread.start()
            
            self.logger.info("Task manager started")
    
    def stop(self):
        """Stop the task manager."""
        with self.lock:
            self.stop_event.set()
            
            # Persist tasks before stopping
            if self.persistence_file:
                self._persist_tasks()
            
            # Wait for persistence thread to terminate
            if hasattr(self, 'persistence_thread') and self.persistence_thread.is_alive():
                self.persistence_thread.join(timeout=2.0)
            
            self.logger.info("Task manager stopped")
    
    def create_task(self, config: Dict[str, Any], priority: int = 0) -> str:
        """Create a new task.
        
        Args:
            config: Task configuration dictionary
            priority: Task priority (lower values = higher priority)
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        with self.lock:
            # Create task
            task = Task(task_id, config)
            task.status = "queued"
            
            # Add to task store and queue
            self.tasks[task_id] = task
            self.task_queue.put((priority, task_id))
            
            self.logger.info(f"Created task {task_id} with priority {priority}")
            return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task dictionary or None if not found
        """
        with self.lock:
            if task_id in self.tasks:
                return self.tasks[task_id].to_dict()
                
            # Check completed tasks
            for task in self.completed_tasks:
                if task.id == task_id:
                    return task.to_dict()
                    
            return None
    
    def get_next_task(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get the next task for a node.
        
        Args:
            node_id: ID of the node requesting a task
            
        Returns:
            Task dictionary or None if no tasks are available
        """
        with self.lock:
            # Check if node has reached its maximum number of tasks
            node_tasks = self.node_assignments.get(node_id, set())
            if len(node_tasks) >= self.max_tasks_per_node:
                return None
            
            # Try to get a task from the queue
            try:
                _, task_id = self.task_queue.get(block=False)
                
                # Get the task
                task = self.tasks[task_id]
                
                # Update task status
                task.status = "assigned"
                task.assigned_node = node_id
                
                # Update node assignments
                if node_id not in self.node_assignments:
                    self.node_assignments[node_id] = set()
                self.node_assignments[node_id].add(task_id)
                
                self.logger.info(f"Assigned task {task_id} to node {node_id}")
                return task.to_dict()
                
            except queue.Empty:
                return None
    
    def task_started(self, task_id: str, node_id: str):
        """Mark a task as started.
        
        Args:
            task_id: Task ID
            node_id: ID of the node running the task
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Check if the task is assigned to this node
                if task.assigned_node != node_id:
                    self.logger.warning(f"Task {task_id} is not assigned to node {node_id}")
                    return
                
                # Update task status
                task.status = "running"
                task.started = time.time()
                
                self.logger.info(f"Task {task_id} started on node {node_id}")
    
    def task_completed(self, task_id: str, node_id: str, result: Dict[str, Any], error: Optional[str] = None):
        """Mark a task as completed.
        
        Args:
            task_id: Task ID
            node_id: ID of the node that ran the task
            result: Task result dictionary
            error: Error message, if any
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Check if the task is assigned to this node
                if task.assigned_node != node_id:
                    self.logger.warning(f"Task {task_id} is not assigned to node {node_id}")
                    return
                
                # Update task status
                task.status = "failed" if error else "completed"
                task.completed = time.time()
                task.result = result
                task.error = error
                
                # Remove from node assignments
                if node_id in self.node_assignments:
                    self.node_assignments[node_id].discard(task_id)
                
                # Move to completed tasks
                self.completed_tasks.append(task)
                del self.tasks[task_id]
                
                # Trim completed tasks if necessary
                if len(self.completed_tasks) > self.max_completed_tasks:
                    self.completed_tasks = self.completed_tasks[-self.max_completed_tasks:]
                
                self.logger.info(f"Task {task_id} {'failed' if error else 'completed'} on node {node_id}")
    
    def requeue_task(self, task_id: str, priority: int = 0):
        """Requeue a task for execution.
        
        Args:
            task_id: Task ID
            priority: Task priority (lower values = higher priority)
        """
        with self.lock:
            # Check active tasks
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Update task status
                task.status = "queued"
                task.assigned_node = None
                
                # Add to queue
                self.task_queue.put((priority, task_id))
                
                self.logger.info(f"Requeued task {task_id} with priority {priority}")
                return
                
            # Check completed tasks
            for i, task in enumerate(self.completed_tasks):
                if task.id == task_id:
                    # Remove from completed tasks
                    task = self.completed_tasks.pop(i)
                    
                    # Update task status
                    task.status = "queued"
                    task.assigned_node = None
                    task.started = 0
                    task.completed = 0
                    task.result = None
                    task.error = None
                    
                    # Add to active tasks and queue
                    self.tasks[task_id] = task
                    self.task_queue.put((priority, task_id))
                    
                    self.logger.info(f"Requeued completed task {task_id} with priority {priority}")
                    return
            
            self.logger.warning(f"Task {task_id} not found for requeuing")
    
    def clear_node_tasks(self, node_id: str):
        """Clear all tasks assigned to a node.
        
        Args:
            node_id: Node ID
        """
        with self.lock:
            # Get tasks assigned to the node
            node_tasks = self.node_assignments.get(node_id, set()).copy()
            
            # Requeue each task
            for task_id in node_tasks:
                self.requeue_task(task_id)
            
            # Clear node assignments
            self.node_assignments[node_id] = set()
            
            self.logger.info(f"Cleared {len(node_tasks)} tasks from node {node_id}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the task queue.
        
        Returns:
            Queue statistics dictionary
        """
        with self.lock:
            # Count tasks by status
            status_counts = {}
            for task in self.tasks.values():
                status = task.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count completed tasks
            completed_successful = sum(1 for task in self.completed_tasks 
                                      if task.status == "completed")
            completed_failed = sum(1 for task in self.completed_tasks 
                                  if task.status == "failed")
            
            return {
                "queue_size": self.task_queue.qsize(),
                "active_tasks": len(self.tasks),
                "completed_tasks": len(self.completed_tasks),
                "completed_successful": completed_successful,
                "completed_failed": completed_failed,
                "status_counts": status_counts,
                "node_assignments": {
                    node_id: len(tasks) 
                    for node_id, tasks in self.node_assignments.items()
                }
            }
    
    def _persistence_loop(self):
        """Periodically persist tasks to disk."""
        while not self.stop_event.is_set():
            try:
                # Sleep for the interval
                sleep_interval = min(10.0, self.persistence_interval)
                for _ in range(int(self.persistence_interval / sleep_interval)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(sleep_interval)
                
                # Persist tasks
                if not self.stop_event.is_set():
                    self._persist_tasks()
                    
            except Exception as e:
                self.logger.error(f"Error in persistence loop: {str(e)}")
                time.sleep(60.0)  # Longer delay on error
    
    def _persist_tasks(self):
        """Persist tasks to disk."""
        if not self.persistence_file:
            return
            
        with self.lock:
            try:
                # Create directory if needed
                os.makedirs(os.path.dirname(os.path.abspath(self.persistence_file)), exist_ok=True)
                
                # Prepare data for serialization
                data = {
                    "timestamp": time.time(),
                    "tasks": [task.to_dict() for task in self.tasks.values()],
                    "completed_tasks": [task.to_dict() for task in self.completed_tasks]
                }
                
                # Write to file
                with open(self.persistence_file, 'w') as f:
                    json.dump(data, f)
                    
                self.logger.info(f"Persisted {len(self.tasks)} active and {len(self.completed_tasks)} completed tasks")
                
            except Exception as e:
                self.logger.error(f"Error persisting tasks: {str(e)}")
    
    def _load_tasks(self):
        """Load tasks from disk."""
        if not self.persistence_file or not os.path.exists(self.persistence_file):
            return
            
        with self.lock:
            try:
                # Read from file
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                
                # Load tasks
                timestamp = data.get("timestamp", 0)
                
                # Check if the data is too old
                if time.time() - timestamp > 86400:  # 24 hours
                    self.logger.warning(f"Task data is too old, ignoring")
                    return
                
                # Load active tasks
                for task_data in data.get("tasks", []):
                    task = Task.from_dict(task_data)
                    self.tasks[task.id] = task
                    
                    # Add to queue if queued
                    if task.status == "queued":
                        self.task_queue.put((0, task.id))
                
                # Load completed tasks
                for task_data in data.get("completed_tasks", []):
                    task = Task.from_dict(task_data)
                    self.completed_tasks.append(task)
                
                # Trim completed tasks if necessary
                if len(self.completed_tasks) > self.max_completed_tasks:
                    self.completed_tasks = self.completed_tasks[-self.max_completed_tasks:]
                
                self.logger.info(f"Loaded {len(self.tasks)} active and {len(self.completed_tasks)} completed tasks")
            except Exception as e:
                self.logger.error(f"Error loading tasks: {str(e)}")
