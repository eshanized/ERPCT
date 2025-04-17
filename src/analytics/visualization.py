#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Visualization module for ERPCT.
This module provides visualization functions for attack data and performance metrics.
"""

import os
import time
import datetime
import io
from typing import Dict, List, Tuple, Any, Optional, Union
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from src.utils.logging import get_logger


# Define consistent color schemes
COLORS = {
    "primary": "#2C3E50",
    "success": "#27AE60",
    "failure": "#E74C3C",
    "warning": "#F39C12",
    "info": "#3498DB",
    "neutral": "#95A5A6",
    "accent1": "#9B59B6",
    "accent2": "#16A085",
}

# Chart types
CHART_TYPES = [
    "timeline",
    "success_rate",
    "attempt_distribution",
    "performance",
    "resource_usage",
    "protocol_comparison"
]


def create_attack_timeline(timestamps: List[float], 
                         successes: List[int], 
                         failures: List[int],
                         title: str = "Attack Timeline",
                         output_path: Optional[str] = None) -> Optional[Figure]:
    """Create a timeline visualization of attack attempts.
    
    Args:
        timestamps: List of timestamps
        successes: Cumulative successful attempts at each timestamp
        failures: Cumulative failed attempts at each timestamp
        title: Chart title
        output_path: Optional path to save the figure
        
    Returns:
        Matplotlib Figure object if output_path is None, else None
    """
    logger = get_logger(__name__)
    
    if not timestamps or len(timestamps) != len(successes) or len(timestamps) != len(failures):
        logger.warning("Invalid data for timeline visualization")
        return None
    
    try:
        # Convert timestamps to datetime
        dates = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot data
        ax.plot(dates, successes, label="Successful Attempts", color=COLORS["success"], linewidth=2)
        ax.plot(dates, failures, label="Failed Attempts", color=COLORS["failure"], linewidth=2)
        ax.plot(dates, [s + f for s, f in zip(successes, failures)], 
                label="Total Attempts", color=COLORS["primary"], linewidth=1, linestyle='--')
        
        # Configure plot
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Cumulative Attempts", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend(loc="upper left")
        
        # Format date axis
        if max(timestamps) - min(timestamps) > 86400:  # > 1 day
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Tight layout
        plt.tight_layout()
        
        # Save or return
        if output_path:
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return None
        else:
            return fig
            
    except Exception as e:
        logger.error(f"Error creating attack timeline: {str(e)}")
        return None


def create_success_rate_chart(categories: List[str], 
                            success_rates: List[float],
                            title: str = "Success Rates by Category",
                            output_path: Optional[str] = None) -> Optional[Figure]:
    """Create a bar chart of success rates by category.
    
    Args:
        categories: List of category names (e.g., protocols, usernames)
        success_rates: List of success rates as percentages
        title: Chart title
        output_path: Optional path to save the figure
        
    Returns:
        Matplotlib Figure object if output_path is None, else None
    """
    logger = get_logger(__name__)
    
    if not categories or not success_rates or len(categories) != len(success_rates):
        logger.warning("Invalid data for success rate visualization")
        return None
    
    try:
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot data
        bars = ax.bar(categories, success_rates, color=COLORS["primary"], alpha=0.8)
        
        # Add data labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
        
        # Configure plot
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Category", fontsize=12)
        ax.set_ylabel("Success Rate (%)", fontsize=12)
        ax.set_ylim(0, max(success_rates) * 1.15 if success_rates else 100)  # Add headroom for labels
        ax.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        # Rotate x labels if there are many categories
        if len(categories) > 5:
            plt.xticks(rotation=45, ha='right')
        
        # Tight layout
        plt.tight_layout()
        
        # Save or return
        if output_path:
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return None
        else:
            return fig
            
    except Exception as e:
        logger.error(f"Error creating success rate chart: {str(e)}")
        return None


def create_attempt_distribution(time_periods: List[str],
                              attempts: List[int],
                              success_counts: Optional[List[int]] = None,
                              title: str = "Attempt Distribution",
                              output_path: Optional[str] = None) -> Optional[Figure]:
    """Create a distribution chart of attempts over time periods.
    
    Args:
        time_periods: List of time period labels (e.g., hours of day)
        attempts: List of attempt counts for each period
        success_counts: Optional list of successful attempt counts
        title: Chart title
        output_path: Optional path to save the figure
        
    Returns:
        Matplotlib Figure object if output_path is None, else None
    """
    logger = get_logger(__name__)
    
    if not time_periods or not attempts or len(time_periods) != len(attempts):
        logger.warning("Invalid data for attempt distribution visualization")
        return None
    
    try:
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(time_periods))
        bar_width = 0.35
        
        # Plot attempts
        bars1 = ax.bar(x, attempts, bar_width, label='Total Attempts', color=COLORS["primary"])
        
        # Plot successes if provided
        if success_counts and len(success_counts) == len(attempts):
            bars2 = ax.bar(x + bar_width, success_counts, bar_width, 
                         label='Successful Attempts', color=COLORS["success"])
        
        # Configure plot
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Time Period", fontsize=12)
        ax.set_ylabel("Number of Attempts", fontsize=12)
        ax.set_xticks(x + bar_width / 2)
        ax.set_xticklabels(time_periods)
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        # Rotate x labels if there are many periods
        if len(time_periods) > 8:
            plt.xticks(rotation=45, ha='right')
        
        # Tight layout
        plt.tight_layout()
        
        # Save or return
        if output_path:
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return None
        else:
            return fig
            
    except Exception as e:
        logger.error(f"Error creating attempt distribution chart: {str(e)}")
        return None


def create_performance_graph(timestamps: List[float],
                           metrics: Dict[str, List[float]],
                           title: str = "Performance Metrics",
                           output_path: Optional[str] = None) -> Optional[Figure]:
    """Create a multi-line graph of performance metrics over time.
    
    Args:
        timestamps: List of timestamps
        metrics: Dictionary mapping metric names to lists of values
        title: Chart title
        output_path: Optional path to save the figure
        
    Returns:
        Matplotlib Figure object if output_path is None, else None
    """
    logger = get_logger(__name__)
    
    if not timestamps or not metrics:
        logger.warning("Invalid data for performance graph visualization")
        return None
    
    # Check that at least one metric has the same length as timestamps
    valid_metric = False
    for values in metrics.values():
        if len(values) == len(timestamps):
            valid_metric = True
            break
    
    if not valid_metric:
        logger.warning("No valid metrics with matching timestamp length")
        return None
    
    try:
        # Convert timestamps to datetime
        dates = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]
        
        # Create figure with subplots based on metric count
        metric_count = len(metrics)
        fig, axes = plt.subplots(metric_count, 1, figsize=(12, 3 * metric_count), sharex=True)
        
        # Handle case of single metric (axes not in array)
        if metric_count == 1:
            axes = [axes]
        
        # Available colors for cycling
        colors = list(COLORS.values())
        
        # Plot each metric in its own subplot
        for i, (metric_name, values) in enumerate(metrics.items()):
            if len(values) != len(timestamps):
                logger.warning(f"Skipping metric {metric_name} due to length mismatch")
                continue
                
            ax = axes[i]
            ax.plot(dates, values, label=metric_name, color=colors[i % len(colors)], linewidth=2)
            
            # Configure subplot
            ax.set_ylabel(metric_name, fontsize=10)
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Add moving average if there are enough points
            if len(values) > 10:
                window_size = min(10, len(values) // 5)
                moving_avg = np.convolve(values, np.ones(window_size)/window_size, mode='valid')
                moving_avg_dates = dates[window_size-1:]
                ax.plot(moving_avg_dates, moving_avg, 
                       label=f"{metric_name} (MA)", 
                       color=colors[i % len(colors)], 
                       linewidth=1, 
                       linestyle='--')
            
            ax.legend(loc="upper right")
        
        # Set title for the entire figure
        fig.suptitle(title, fontsize=14)
        
        # Format date axis on bottom subplot
        if max(timestamps) - min(timestamps) > 86400:  # > 1 day
            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()
        else:
            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        axes[-1].set_xlabel("Time", fontsize=12)
        
        # Tight layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)  # Make room for the suptitle
        
        # Save or return
        if output_path:
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return None
        else:
            return fig
            
    except Exception as e:
        logger.error(f"Error creating performance graph: {str(e)}")
        return None


def create_resource_usage_charts(cpu_data: List[float],
                               memory_data: List[float],
                               timestamps: List[float],
                               title: str = "Resource Usage",
                               output_path: Optional[str] = None) -> Optional[Figure]:
    """Create resource usage charts (CPU and memory).
    
    Args:
        cpu_data: List of CPU usage percentages
        memory_data: List of memory usage values (MB)
        timestamps: List of timestamps
        title: Chart title
        output_path: Optional path to save the figure
        
    Returns:
        Matplotlib Figure object if output_path is None, else None
    """
    logger = get_logger(__name__)
    
    if not cpu_data or not memory_data or not timestamps:
        logger.warning("Invalid data for resource usage visualization")
        return None
    
    if len(cpu_data) != len(timestamps) or len(memory_data) != len(timestamps):
        logger.warning("Data length mismatch for resource usage visualization")
        return None
    
    try:
        # Convert timestamps to datetime
        dates = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Plot CPU usage
        ax1.plot(dates, cpu_data, label="CPU Usage", color=COLORS["primary"], linewidth=2)
        ax1.set_ylabel("CPU Usage (%)", fontsize=10)
        ax1.set_ylim(0, max(100, max(cpu_data) * 1.1))
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.legend(loc="upper right")
        
        # Plot memory usage
        ax2.plot(dates, memory_data, label="Memory Usage", color=COLORS["accent1"], linewidth=2)
        ax2.set_ylabel("Memory Usage (MB)", fontsize=10)
        ax2.set_ylim(0, max(memory_data) * 1.1)
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.legend(loc="upper right")
        
        # Format date axis
        if max(timestamps) - min(timestamps) > 86400:  # > 1 day
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()
        else:
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Set common title and x label
        fig.suptitle(title, fontsize=14)
        ax2.set_xlabel("Time", fontsize=12)
        
        # Tight layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)  # Make room for the suptitle
        
        # Save or return
        if output_path:
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return None
        else:
            return fig
            
    except Exception as e:
        logger.error(f"Error creating resource usage charts: {str(e)}")
        return None


def create_protocol_comparison(protocols: List[str],
                             metrics: Dict[str, List[float]],
                             title: str = "Protocol Comparison",
                             output_path: Optional[str] = None) -> Optional[Figure]:
    """Create a comparison chart between different protocols.
    
    Args:
        protocols: List of protocol names
        metrics: Dictionary mapping metric names to lists of values (one per protocol)
        title: Chart title
        output_path: Optional path to save the figure
        
    Returns:
        Matplotlib Figure object if output_path is None, else None
    """
    logger = get_logger(__name__)
    
    if not protocols or not metrics:
        logger.warning("Invalid data for protocol comparison visualization")
        return None
    
    # Check that all metrics have same length as protocols list
    for metric_name, values in metrics.items():
        if len(values) != len(protocols):
            logger.warning(f"Metric {metric_name} has length mismatch with protocols list")
            return None
    
    try:
        # Create figure
        fig, ax = plt.subplots(figsize=(max(8, len(protocols) * 1.2), 7))
        
        # Set up bar positions
        x = np.arange(len(protocols))
        bar_width = 0.8 / len(metrics)
        
        # Plot each metric as a group of bars
        for i, (metric_name, values) in enumerate(metrics.items()):
            positions = x - 0.4 + (i + 0.5) * bar_width
            bars = ax.bar(positions, values, bar_width, 
                        label=metric_name, 
                        color=list(COLORS.values())[i % len(COLORS)])
            
            # Add data labels
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                           f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        
        # Configure plot
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Protocol", fontsize=12)
        ax.set_ylabel("Value", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(protocols)
        ax.legend(loc="upper right")
        ax.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        # Rotate x labels if there are many protocols
        if len(protocols) > 5:
            plt.xticks(rotation=45, ha='right')
        
        # Tight layout
        plt.tight_layout()
        
        # Save or return
        if output_path:
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return None
        else:
            return fig
            
    except Exception as e:
        logger.error(f"Error creating protocol comparison chart: {str(e)}")
        return None


def export_visualization(fig: Figure, 
                       format: str = "png", 
                       output_path: Optional[str] = None,
                       dpi: int = 100) -> Optional[bytes]:
    """Export a visualization to a file or bytes.
    
    Args:
        fig: Matplotlib Figure object
        format: Output format (png, pdf, svg, etc.)
        output_path: Optional path to save the figure
        dpi: Resolution for raster formats
        
    Returns:
        Bytes object if output_path is None, else None
    """
    logger = get_logger(__name__)
    
    if not fig:
        logger.warning("No figure provided for export")
        return None
    
    try:
        # If output path is provided, save directly
        if output_path:
            fig.savefig(output_path, format=format, dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            return None
        
        # Otherwise, convert to bytes
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        with io.BytesIO() as buffer:
            canvas.print_figure(buffer, format=format, dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            return buffer.getvalue()
            
    except Exception as e:
        logger.error(f"Error exporting visualization: {str(e)}")
        return None
