#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT result aggregator module.
This module implements the aggregation of results from distributed password cracking tasks.
"""

import os
import json
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.utils.logging import get_logger


class ResultAggregator:
    """
    Aggregates results from distributed password cracking tasks.
    
    This class is responsible for:
    - Collecting results from multiple worker nodes
    - Consolidating authentication successes
    - Tracking statistics across distributed tasks
    - Storing and exporting aggregated results
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, config: Optional[Dict[str, Any]] = None) -> 'ResultAggregator':
        """
        Get the singleton instance of ResultAggregator.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            The singleton instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = ResultAggregator(config or {})
            elif config is not None:
                cls._instance.update_config(config)
                
            return cls._instance
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the result aggregator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.export_dir = config.get("export_dir", "results")
        self.auto_export = config.get("auto_export", True)
        self.export_interval = config.get("export_interval", 300)  # 5 minutes
        
        # Result storage
        self.results = {}  # task_id -> results
        self.successes = {}  # task_id -> list of successful authentications
        self.statistics = {}  # task_id -> statistics
        self.aggregated_stats = {}  # Global statistics
        
        # Threading
        self.export_thread = None
        self.running = False
        self._export_lock = threading.Lock()
        
        # Ensure export directory exists
        if not os.path.exists(self.export_dir):
            try:
                os.makedirs(self.export_dir)
                self.logger.info(f"Created export directory: {self.export_dir}")
            except Exception as e:
                self.logger.error(f"Failed to create export directory: {str(e)}")
        
        self.logger.info("ResultAggregator initialized")
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Update the configuration.
        
        Args:
            config: New configuration dictionary
        """
        self.config.update(config)
        
        # Update settings based on new config
        self.export_dir = self.config.get("export_dir", self.export_dir)
        self.auto_export = self.config.get("auto_export", self.auto_export)
        self.export_interval = self.config.get("export_interval", self.export_interval)
        
        # Ensure export directory exists
        if not os.path.exists(self.export_dir):
            try:
                os.makedirs(self.export_dir)
                self.logger.info(f"Created export directory: {self.export_dir}")
            except Exception as e:
                self.logger.error(f"Failed to create export directory: {str(e)}")
    
    def start(self) -> None:
        """
        Start the result aggregator, including the auto-export thread if enabled.
        """
        if self.running:
            return
            
        self.running = True
        
        if self.auto_export and self.export_interval > 0:
            self.export_thread = threading.Thread(target=self._export_loop, daemon=True)
            self.export_thread.start()
            self.logger.info(f"Started auto-export thread with interval {self.export_interval}s")
    
    def stop(self) -> None:
        """
        Stop the result aggregator and export thread.
        """
        if not self.running:
            return
            
        self.running = False
        
        if self.export_thread and self.export_thread.is_alive():
            self.export_thread.join(timeout=2.0)
            self.logger.info("Stopped export thread")
        
        # Final export of results
        self.export_results()
    
    def add_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """
        Add a task result.
        
        Args:
            task_id: Task identifier
            result: Result dictionary
        """
        if not task_id:
            self.logger.warning("Attempted to add result with empty task_id")
            return
            
        with self._export_lock:
            # Initialize task result storage if needed
            if task_id not in self.results:
                self.results[task_id] = []
                self.successes[task_id] = []
                self.statistics[task_id] = {
                    "total_attempts": 0,
                    "successful_attempts": 0,
                    "start_time": time.time(),
                    "last_update": time.time(),
                    "nodes": set(),
                }
            
            # Add result to storage
            self.results[task_id].append(result)
            
            # Update statistics
            stats = self.statistics[task_id]
            stats["total_attempts"] += result.get("attempts", 1)
            stats["last_update"] = time.time()
            
            # Add node information
            if "node_id" in result:
                stats["nodes"].add(result["node_id"])
            
            # Handle successful authentication
            if result.get("success", False):
                stats["successful_attempts"] += 1
                self.successes[task_id].append(result)
                self.logger.info(f"Added successful authentication for task {task_id}")
            
            # Update aggregated statistics
            self._update_aggregated_stats()
    
    def get_results(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get results for a specific task or all tasks.
        
        Args:
            task_id: Optional task identifier
            
        Returns:
            Dictionary of results
        """
        with self._export_lock:
            if task_id:
                if task_id not in self.results:
                    return {"results": [], "successes": [], "statistics": {}}
                
                stats = self.statistics[task_id].copy()
                stats["nodes"] = list(stats["nodes"])  # Convert set to list for serialization
                
                return {
                    "results": self.results[task_id],
                    "successes": self.successes[task_id],
                    "statistics": stats
                }
            else:
                # Return all results
                all_stats = {}
                for tid, stats in self.statistics.items():
                    all_stats[tid] = stats.copy()
                    all_stats[tid]["nodes"] = list(stats["nodes"])
                
                return {
                    "tasks": list(self.results.keys()),
                    "statistics": all_stats,
                    "aggregated": self.aggregated_stats,
                    "success_count": sum(len(successes) for successes in self.successes.values())
                }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary containing task status
        """
        with self._export_lock:
            if task_id not in self.statistics:
                return {"status": "unknown", "task_id": task_id}
            
            stats = self.statistics[task_id].copy()
            stats["nodes"] = list(stats["nodes"])
            
            return {
                "task_id": task_id,
                "status": "running" if stats["last_update"] > time.time() - 60 else "idle",
                "statistics": stats,
                "success_count": len(self.successes[task_id])
            }
    
    def export_results(self, task_id: Optional[str] = None) -> Optional[str]:
        """
        Export results to a file.
        
        Args:
            task_id: Optional task identifier to export specific task
            
        Returns:
            Path to exported file or None if export failed
        """
        with self._export_lock:
            try:
                if not os.path.exists(self.export_dir):
                    os.makedirs(self.export_dir)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if task_id:
                    # Export specific task
                    if task_id not in self.results:
                        self.logger.warning(f"Cannot export task {task_id}: task not found")
                        return None
                    
                    filename = f"{self.export_dir}/task_{task_id}_{timestamp}.json"
                    results = self.get_results(task_id)
                else:
                    # Export all tasks
                    filename = f"{self.export_dir}/all_tasks_{timestamp}.json"
                    results = self.get_results()
                
                with open(filename, 'w') as f:
                    json.dump(results, f, indent=2)
                
                self.logger.info(f"Exported results to {filename}")
                return filename
                
            except Exception as e:
                self.logger.error(f"Failed to export results: {str(e)}")
                return None
    
    def clear_results(self, task_id: Optional[str] = None) -> None:
        """
        Clear stored results.
        
        Args:
            task_id: Optional task identifier to clear specific task
        """
        with self._export_lock:
            if task_id:
                # Clear specific task
                if task_id in self.results:
                    del self.results[task_id]
                if task_id in self.successes:
                    del self.successes[task_id]
                if task_id in self.statistics:
                    del self.statistics[task_id]
                self.logger.info(f"Cleared results for task {task_id}")
            else:
                # Clear all tasks
                self.results.clear()
                self.successes.clear()
                self.statistics.clear()
                self.logger.info("Cleared all results")
            
            # Update aggregated statistics
            self._update_aggregated_stats()
    
    def get_statistics(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific task or aggregated statistics.
        
        Args:
            task_id: Optional task identifier
            
        Returns:
            Dictionary of statistics
        """
        with self._export_lock:
            if task_id:
                if task_id not in self.statistics:
                    return {}
                
                stats = self.statistics[task_id].copy()
                stats["nodes"] = list(stats["nodes"])
                
                # Add success rate
                total = stats["total_attempts"]
                successes = stats["successful_attempts"]
                stats["success_rate"] = (successes / total) if total > 0 else 0
                
                # Add elapsed time
                stats["elapsed_time"] = time.time() - stats["start_time"]
                
                return stats
            else:
                # Return aggregated statistics
                return self.aggregated_stats
    
    def _update_aggregated_stats(self) -> None:
        """
        Update the aggregated statistics across all tasks.
        """
        total_attempts = 0
        successful_attempts = 0
        active_tasks = 0
        completed_tasks = 0
        all_nodes = set()
        earliest_start = float('inf')
        latest_update = 0
        
        # Aggregate from all tasks
        for task_id, stats in self.statistics.items():
            total_attempts += stats["total_attempts"]
            successful_attempts += stats["successful_attempts"]
            all_nodes.update(stats["nodes"])
            
            # Task timing
            earliest_start = min(earliest_start, stats["start_time"])
            latest_update = max(latest_update, stats["last_update"])
            
            # Task status
            if stats["last_update"] > time.time() - 60:
                active_tasks += 1
            
            # Determine completed tasks based on success
            if len(self.successes.get(task_id, [])) > 0:
                completed_tasks += 1
        
        # Create aggregated statistics
        self.aggregated_stats = {
            "total_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "success_rate": (successful_attempts / total_attempts) if total_attempts > 0 else 0,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "total_tasks": len(self.statistics),
            "node_count": len(all_nodes),
            "nodes": list(all_nodes),
        }
        
        # Add timing information
        if earliest_start != float('inf'):
            self.aggregated_stats["start_time"] = earliest_start
            self.aggregated_stats["elapsed_time"] = time.time() - earliest_start
        
        if latest_update > 0:
            self.aggregated_stats["last_update"] = latest_update
            self.aggregated_stats["idle_time"] = time.time() - latest_update
    
    def _export_loop(self) -> None:
        """
        Background thread for automatic export of results.
        """
        while self.running:
            time.sleep(self.export_interval)
            
            if not self.running:
                break
                
            try:
                self.export_results()
            except Exception as e:
                self.logger.error(f"Error in export thread: {str(e)}")
    
    def merge_task_results(self, task_ids: List[str], new_task_id: str) -> bool:
        """
        Merge results from multiple tasks into a new task.
        
        Args:
            task_ids: List of task identifiers to merge
            new_task_id: New task identifier for merged results
            
        Returns:
            True if merge was successful
        """
        with self._export_lock:
            # Verify all task IDs exist
            for task_id in task_ids:
                if task_id not in self.results:
                    self.logger.warning(f"Cannot merge task {task_id}: task not found")
                    return False
            
            # Create new task containers
            self.results[new_task_id] = []
            self.successes[new_task_id] = []
            self.statistics[new_task_id] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "start_time": float('inf'),
                "last_update": 0,
                "nodes": set(),
            }
            
            # Merge results and statistics
            for task_id in task_ids:
                # Merge results
                self.results[new_task_id].extend(self.results[task_id])
                
                # Merge successes
                self.successes[new_task_id].extend(self.successes[task_id])
                
                # Merge statistics
                stats = self.statistics[task_id]
                new_stats = self.statistics[new_task_id]
                
                new_stats["total_attempts"] += stats["total_attempts"]
                new_stats["successful_attempts"] += stats["successful_attempts"]
                new_stats["start_time"] = min(new_stats["start_time"], stats["start_time"])
                new_stats["last_update"] = max(new_stats["last_update"], stats["last_update"])
                new_stats["nodes"].update(stats["nodes"])
            
            # Fix start time if no tasks were merged
            if self.statistics[new_task_id]["start_time"] == float('inf'):
                self.statistics[new_task_id]["start_time"] = time.time()
            
            # Update aggregated statistics
            self._update_aggregated_stats()
            
            self.logger.info(f"Merged {len(task_ids)} tasks into new task {new_task_id}")
            return True
