#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT distributed attack module.
This module implements distributed password cracking functionality.
"""

import os
import json
import sys
import time
import socket
import threading
import queue
from typing import Dict, List, Optional, Tuple, Any, Callable, Set
import uuid

from src.core.attack import Attack, AttackResult, AttackStatus
from src.utils.logging import get_logger

try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False


class NodeStatus:
    """Class representing the status of a worker node."""
    
    def __init__(self, node_id: str, address: str):
        """Initialize node status.
        
        Args:
            node_id: Unique ID of the node
            address: Network address of the node (host:port)
        """
        self.node_id = node_id
        self.address = address
        self.connected = False
        self.active = False
        self.last_heartbeat = 0
        self.current_task = None
        self.total_tasks_completed = 0
        self.successful_tasks = 0
        self.stats = {}
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = time.time()
    
    def is_alive(self, timeout: float = 30.0) -> bool:
        """Check if the node is alive based on heartbeat.
        
        Args:
            timeout: Maximum time in seconds since last heartbeat
            
        Returns:
            True if node is considered alive, False otherwise
        """
        return (time.time() - self.last_heartbeat) < timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node status to dictionary.
        
        Returns:
            Dictionary representation of node status
        """
        return {
            "id": self.node_id,
            "address": self.address,
            "connected": self.connected,
            "active": self.active,
            "last_heartbeat": self.last_heartbeat,
            "current_task": self.current_task,
            "total_tasks_completed": self.total_tasks_completed,
            "successful_tasks": self.successful_tasks,
            "stats": self.stats
        }


class DistributedAttackController:
    """Controller for distributed password cracking attacks.
    
    This class manages the coordination of attacks across multiple worker nodes.
    It can operate in both master and worker modes.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of the controller.
        
        Returns:
            DistributedAttackController instance
        """
        if cls._instance is None:
            cls._instance = DistributedAttackController()
        return cls._instance
    
    def __init__(self):
        """Initialize the distributed attack controller."""
        self.logger = get_logger(__name__)
        
        if not ZMQ_AVAILABLE:
            self.logger.warning("ZeroMQ is not available. Distributed mode will not work properly.")
        
        # Mode configuration
        self.is_master = False
        self.is_worker = False
        
        # Network configuration
        self.bind_address = "0.0.0.0"
        self.bind_port = 5555
        self.master_address = None
        
        # Node identification
        self.node_id = str(uuid.uuid4())
        self.node_name = socket.gethostname()
        
        # Worker nodes (only used in master mode)
        self.nodes = {}  # node_id -> NodeStatus
        
        # Task management
        self.task_queue = queue.Queue()
        self.active_tasks = {}  # task_id -> task_dict
        self.completed_tasks = []
        
        # ZeroMQ context and sockets
        if ZMQ_AVAILABLE:
            self.context = zmq.Context()
            self.master_socket = None
            self.worker_socket = None
        
        # Threading
        self.stop_event = threading.Event()
        self.threads = []
    
    def configure_as_master(self, bind_address: str = "0.0.0.0", bind_port: int = 5555):
        """Configure this instance as a master node.
        
        Args:
            bind_address: Address to bind to
            bind_port: Port to bind to
        """
        if not ZMQ_AVAILABLE:
            raise RuntimeError("ZeroMQ is required for distributed mode")
            
        self.is_master = True
        self.is_worker = False
        self.bind_address = bind_address
        self.bind_port = bind_port
        
        # Set up master socket
        self.master_socket = self.context.socket(zmq.ROUTER)
        self.master_socket.bind(f"tcp://{bind_address}:{bind_port}")
        
        self.logger.info(f"Configured as master node on {bind_address}:{bind_port}")
    
    def configure_as_worker(self, master_address: str):
        """Configure this instance as a worker node.
        
        Args:
            master_address: Address of the master node (host:port)
        """
        if not ZMQ_AVAILABLE:
            raise RuntimeError("ZeroMQ is required for distributed mode")
            
        self.is_master = False
        self.is_worker = True
        self.master_address = master_address
        
        # Set up worker socket
        self.worker_socket = self.context.socket(zmq.DEALER)
        self.worker_socket.setsockopt_string(zmq.IDENTITY, self.node_id)
        self.worker_socket.connect(f"tcp://{master_address}")
        
        self.logger.info(f"Configured as worker node connecting to {master_address}")
    
    def start(self):
        """Start the distributed attack controller."""
        if not ZMQ_AVAILABLE:
            raise RuntimeError("ZeroMQ is required for distributed mode")
            
        self.stop_event.clear()
        
        if self.is_master:
            # Start master threads
            self.threads.append(threading.Thread(target=self._master_receive_loop))
            self.threads.append(threading.Thread(target=self._master_heartbeat_loop))
            self.threads.append(threading.Thread(target=self._master_task_distribution_loop))
        
        if self.is_worker:
            # Start worker threads
            self.threads.append(threading.Thread(target=self._worker_receive_loop))
            self.threads.append(threading.Thread(target=self._worker_heartbeat_loop))
        
        # Start all threads
        for thread in self.threads:
            thread.daemon = True
            thread.start()
        
        self.logger.info("Distributed attack controller started")
    
    def stop(self):
        """Stop the distributed attack controller."""
        self.stop_event.set()
        
        # Wait for threads to terminate
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        # Close sockets
        if self.master_socket:
            self.master_socket.close()
            
        if self.worker_socket:
            self.worker_socket.close()
        
        self.logger.info("Distributed attack controller stopped")
    
    def add_task(self, task_config: Dict[str, Any]) -> str:
        """Add a new task to the queue.
        
        Args:
            task_config: Task configuration dictionary
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "config": task_config,
            "created": time.time(),
            "status": "queued",
            "assigned_node": None,
            "result": None
        }
        
        self.task_queue.put(task)
        self.active_tasks[task_id] = task
        
        self.logger.info(f"Added task {task_id} to queue")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task status dictionary or None if not found
        """
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
            
        for task in self.completed_tasks:
            if task["id"] == task_id:
                return task
                
        return None
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get a list of all connected nodes.
        
        Returns:
            List of node status dictionaries
        """
        return [node.to_dict() for node in self.nodes.values()]
    
    # Private methods for master node
    def _master_receive_loop(self):
        """Main receive loop for the master node."""
        while not self.stop_event.is_set():
            try:
                if self.master_socket.poll(1000):
                    node_id, message = self.master_socket.recv_multipart()
                    node_id = node_id.decode('utf-8')
                    self._handle_worker_message(node_id, message)
            except Exception as e:
                self.logger.error(f"Error in master receive loop: {str(e)}")
    
    def _master_heartbeat_loop(self):
        """Heartbeat loop for the master node."""
        while not self.stop_event.is_set():
            try:
                # Send heartbeat to all nodes
                for node_id, node in list(self.nodes.items()):
                    try:
                        if not node.is_alive():
                            self.logger.warning(f"Node {node_id} timed out")
                            # Handle node disconnect
                            node.connected = False
                            if node.current_task:
                                # Re-queue the task
                                task_id = node.current_task
                                if task_id in self.active_tasks:
                                    task = self.active_tasks[task_id]
                                    task["status"] = "queued"
                                    task["assigned_node"] = None
                                    self.task_queue.put(task)
                                    self.logger.info(f"Re-queued task {task_id} from disconnected node")
                        else:
                            # Send heartbeat
                            message = {"type": "heartbeat", "timestamp": time.time()}
                            self.master_socket.send_multipart([
                                node_id.encode('utf-8'),
                                json.dumps(message).encode('utf-8')
                            ])
                    except Exception as e:
                        self.logger.error(f"Error sending heartbeat to node {node_id}: {str(e)}")
                
                # Sleep for a short time
                time.sleep(5.0)
            except Exception as e:
                self.logger.error(f"Error in master heartbeat loop: {str(e)}")
    
    def _master_task_distribution_loop(self):
        """Task distribution loop for the master node."""
        while not self.stop_event.is_set():
            try:
                # Find available nodes
                available_nodes = [
                    node_id for node_id, node in self.nodes.items()
                    if node.connected and node.active and not node.current_task
                ]
                
                if available_nodes and not self.task_queue.empty():
                    # Get next task and assign to a node
                    task = self.task_queue.get(block=False)
                    node_id = available_nodes[0]  # Simple round-robin for now
                    
                    # Update task status
                    task["status"] = "assigned"
                    task["assigned_node"] = node_id
                    
                    # Update node status
                    self.nodes[node_id].current_task = task["id"]
                    
                    # Send task to node
                    message = {
                        "type": "task",
                        "task_id": task["id"],
                        "config": task["config"]
                    }
                    self.master_socket.send_multipart([
                        node_id.encode('utf-8'),
                        json.dumps(message).encode('utf-8')
                    ])
                    
                    self.logger.info(f"Assigned task {task['id']} to node {node_id}")
                
                # Sleep for a short time
                time.sleep(0.1)
            except queue.Empty:
                # No tasks available, just continue
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Error in master task distribution loop: {str(e)}")
    
    def _handle_worker_message(self, node_id: str, message_data: bytes):
        """Handle a message from a worker node.
        
        Args:
            node_id: ID of the worker node
            message_data: Message data as bytes
        """
        try:
            message = json.loads(message_data.decode('utf-8'))
            message_type = message.get("type")
            
            # Update or create node status
            if node_id not in self.nodes:
                address = message.get("address", "unknown")
                self.nodes[node_id] = NodeStatus(node_id, address)
                self.logger.info(f"New node connected: {node_id} from {address}")
            
            node = self.nodes[node_id]
            node.update_heartbeat()
            
            if message_type == "register":
                # Node registration
                node.connected = True
                node.active = True
                node.stats = message.get("stats", {})
                
                # Send acknowledgement
                response = {"type": "register_ack", "node_id": node_id}
                self.master_socket.send_multipart([
                    node_id.encode('utf-8'),
                    json.dumps(response).encode('utf-8')
                ])
                
                self.logger.info(f"Node {node_id} registered")
                
            elif message_type == "heartbeat":
                # Heartbeat from node
                pass
                
            elif message_type == "task_result":
                # Task result from node
                task_id = message.get("task_id")
                success = message.get("success", False)
                result = message.get("result", {})
                
                if task_id in self.active_tasks:
                    task = self.active_tasks[task_id]
                    task["status"] = "completed"
                    task["completed"] = time.time()
                    task["result"] = result
                    
                    # Update node status
                    node.current_task = None
                    node.total_tasks_completed += 1
                    if success:
                        node.successful_tasks += 1
                    
                    # Move to completed tasks
                    self.completed_tasks.append(task)
                    del self.active_tasks[task_id]
                    
                    self.logger.info(f"Task {task_id} completed by node {node_id}, success: {success}")
                else:
                    self.logger.warning(f"Received result for unknown task {task_id} from node {node_id}")
                
            elif message_type == "status_update":
                # Status update from node
                node.stats = message.get("stats", {})
                
            else:
                self.logger.warning(f"Unknown message type {message_type} from node {node_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing message from node {node_id}: {str(e)}")
    
    # Private methods for worker node
    def _worker_receive_loop(self):
        """Main receive loop for the worker node."""
        while not self.stop_event.is_set():
            try:
                if self.worker_socket.poll(1000):
                    message = self.worker_socket.recv()
                    self._handle_master_message(message)
            except Exception as e:
                self.logger.error(f"Error in worker receive loop: {str(e)}")
    
    def _worker_heartbeat_loop(self):
        """Heartbeat loop for the worker node."""
        # Register with master first
        self._send_registration()
        
        while not self.stop_event.is_set():
            try:
                # Send heartbeat
                message = {
                    "type": "heartbeat",
                    "node_id": self.node_id,
                    "timestamp": time.time()
                }
                self.worker_socket.send(json.dumps(message).encode('utf-8'))
                
                # Sleep for a short time
                time.sleep(10.0)
            except Exception as e:
                self.logger.error(f"Error in worker heartbeat loop: {str(e)}")
    
    def _send_registration(self):
        """Send registration message to the master."""
        try:
            # Get system stats
            import psutil
            stats = {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "hostname": socket.gethostname(),
                "platform": sys.platform
            }
        except ImportError:
            stats = {}
        
        message = {
            "type": "register",
            "node_id": self.node_id,
            "name": self.node_name,
            "address": socket.gethostbyname(socket.gethostname()),
            "timestamp": time.time(),
            "stats": stats
        }
        
        self.worker_socket.send(json.dumps(message).encode('utf-8'))
        self.logger.info(f"Sent registration to master")
    
    def _handle_master_message(self, message_data: bytes):
        """Handle a message from the master node.
        
        Args:
            message_data: Message data as bytes
        """
        try:
            message = json.loads(message_data.decode('utf-8'))
            message_type = message.get("type")
            
            if message_type == "register_ack":
                # Registration acknowledgement
                self.logger.info("Registration acknowledged by master")
                
            elif message_type == "heartbeat":
                # Heartbeat from master
                pass
                
            elif message_type == "task":
                # New task from master
                task_id = message.get("task_id")
                config = message.get("config", {})
                
                self.logger.info(f"Received task {task_id} from master")
                
                # Execute task in a separate thread to avoid blocking the receive loop
                threading.Thread(
                    target=self._execute_task,
                    args=(task_id, config),
                    daemon=True
                ).start()
                
            else:
                self.logger.warning(f"Unknown message type {message_type} from master")
                
        except Exception as e:
            self.logger.error(f"Error processing message from master: {str(e)}")
    
    def _execute_task(self, task_id: str, config: Dict[str, Any]):
        """Execute a task.
        
        Args:
            task_id: ID of the task
            config: Task configuration
        """
        try:
            self.logger.info(f"Executing task {task_id}")
            
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
            
            # Send result to master
            success = len(results) > 0
            message = {
                "type": "task_result",
                "task_id": task_id,
                "success": success,
                "result": {
                    "credentials": results,
                    "stats": attack.get_status()
                }
            }
            
            self.worker_socket.send(json.dumps(message).encode('utf-8'))
            self.logger.info(f"Task {task_id} completed, success: {success}")
            
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {str(e)}")
            
            # Send error to master
            message = {
                "type": "task_result",
                "task_id": task_id,
                "success": False,
                "result": {
                    "error": str(e)
                }
            }
            
            self.worker_socket.send(json.dumps(message).encode('utf-8')) 