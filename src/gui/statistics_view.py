#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Statistics View component.
This module provides the GUI panel for viewing attack statistics and performance metrics.
"""

import os
import time
import datetime
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango

from src.utils.logging import get_logger


class StatisticsView(Gtk.Box):
    """Statistics view panel for displaying attack metrics."""
    
    def __init__(self):
        """Initialize the statistics view panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Default stats directory
        self.stats_dir = os.path.join(os.path.expanduser("~"), ".erpct", "stats")
        os.makedirs(self.stats_dir, exist_ok=True)
        
        # Create UI components
        self._create_summary_section()
        self._create_history_section()
        self._create_performance_section()
        self._create_export_button()
        
        # Load statistics
        self.load_statistics()
        
        # Update timer (every 10 seconds)
        self.update_timer_id = GLib.timeout_add(10000, self._update_statistics)
    
    def _create_summary_section(self):
        """Create statistics summary section."""
        frame = Gtk.Frame(label="Summary Statistics")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Grid for statistics
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(6)
        box.pack_start(grid, True, True, 0)
        
        # Column headers
        headers = ["Metric", "All-time", "Past Month", "Past Week", "Today"]
        for col, header in enumerate(headers):
            label = Gtk.Label(label=header)
            label.set_markup(f"<b>{header}</b>")
            grid.attach(label, col, 0, 1, 1)
        
        # Row labels and values
        metrics = [
            "Total Attacks",
            "Successful Attacks",
            "Passwords Found",
            "Success Rate",
            "Avg. Time per Attack",
            "Avg. Attempts per Second"
        ]
        
        self.summary_values = {}
        for row, metric in enumerate(metrics, 1):
            # Label
            label = Gtk.Label(label=metric)
            label.set_xalign(0)
            grid.attach(label, 0, row, 1, 1)
            
            # Value fields
            self.summary_values[metric] = []
            for col in range(1, 5):  # All-time, Month, Week, Today
                value_label = Gtk.Label(label="--")
                value_label.set_xalign(0.5)
                grid.attach(value_label, col, row, 1, 1)
                self.summary_values[metric].append(value_label)
    
    def _create_history_section(self):
        """Create attack history section."""
        frame = Gtk.Frame(label="Attack History")
        self.pack_start(frame, True, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Create a scrollable tree view for history
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Attack history store and view
        self.history_store = Gtk.ListStore(str, str, str, str, int, int, float, str)
        # Date, Time, Target, Protocol, Attempts, Found, Duration, Result
        
        self.history_view = Gtk.TreeView(model=self.history_store)
        
        # Add columns
        columns = [
            ("Date", 0, 100),
            ("Time", 1, 80),
            ("Target", 2, 150),
            ("Protocol", 3, 100),
            ("Attempts", 4, 80),
            ("Found", 5, 60),
            ("Duration", 6, 80),
            ("Result", 7, 100)
        ]
        
        for i, (title, col_id, width) in enumerate(columns):
            if col_id in (4, 5):  # Numeric columns
                renderer = Gtk.CellRendererText()
                renderer.set_property("xalign", 1.0)
                column = Gtk.TreeViewColumn(title, renderer, text=col_id)
            elif col_id == 6:  # Duration (format as time)
                renderer = Gtk.CellRendererText()
                renderer.set_property("xalign", 1.0)
                column = Gtk.TreeViewColumn(title, renderer)
                column.set_cell_data_func(renderer, self._format_duration)
            else:
                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(title, renderer, text=col_id)
            
            column.set_resizable(True)
            column.set_min_width(width)
            column.set_sort_column_id(col_id)
            self.history_view.append_column(column)
        
        scrolled.add(self.history_view)
        box.pack_start(scrolled, True, True, 0)
    
    def _create_performance_section(self):
        """Create performance metrics section."""
        frame = Gtk.Frame(label="Performance Metrics")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_border_width(10)
        frame.add(box)
        
        # Create metric boxes
        metrics = [
            ("Peak Attempts/s", "0", "Highest recorded attempts per second"),
            ("Avg. Success Time", "00:00:00", "Average time to find a valid credential"),
            ("Total Credentials", "0", "Total unique credentials discovered"),
            ("Most Common Protocol", "--", "Most frequently used protocol")
        ]
        
        self.performance_values = {}
        for title, default, tooltip in metrics:
            metric_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            metric_box.set_border_width(5)
            
            # Title
            title_label = Gtk.Label()
            title_label.set_markup(f"<b>{title}</b>")
            title_label.set_xalign(0.5)
            metric_box.pack_start(title_label, False, False, 0)
            
            # Value
            value_label = Gtk.Label(label=default)
            value_label.set_xalign(0.5)
            metric_box.pack_start(value_label, False, False, 0)
            
            # Add tooltip
            metric_box.set_tooltip_text(tooltip)
            
            # Add to container
            box.pack_start(metric_box, True, True, 0)
            
            # Store reference
            self.performance_values[title] = value_label
    
    def _create_export_button(self):
        """Create export button section."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_start(button_box, False, False, 0)
        
        # Add spacer
        button_box.pack_start(Gtk.Label(), True, True, 0)
        
        # Export button
        self.export_button = Gtk.Button.new_with_label("Export Statistics")
        self.export_button.connect("clicked", self._on_export_clicked)
        button_box.pack_start(self.export_button, False, False, 0)
    
    def _format_duration(self, column, cell, model, iter, data):
        """Format duration as HH:MM:SS.
        
        Args:
            column: TreeViewColumn
            cell: CellRenderer
            model: TreeModel
            iter: TreeIter
            data: User data
        """
        duration = model.get_value(iter, 6)  # Duration in seconds
        formatted = time.strftime("%H:%M:%S", time.gmtime(duration))
        cell.set_property("text", formatted)
    
    def _on_export_clicked(self, button):
        """Handle export button click.
        
        Args:
            button: Button that was clicked
        """
        dialog = Gtk.FileChooserDialog(
            title="Export Statistics",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK
            )
        )
        
        # Set default filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dialog.set_current_name(f"erpct_statistics_{timestamp}.csv")
        
        # Add filters
        csv_filter = Gtk.FileFilter()
        csv_filter.set_name("CSV files")
        csv_filter.add_pattern("*.csv")
        dialog.add_filter(csv_filter)
        
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self._export_statistics(filename)
        
        dialog.destroy()
    
    def _export_statistics(self, filename):
        """Export statistics to a CSV file.
        
        Args:
            filename: Path to the output file
        """
        try:
            with open(filename, 'w') as f:
                # Write header
                f.write("Date,Time,Target,Protocol,Attempts,Found,Duration,Result\n")
                
                # Write data
                for row in self.history_store:
                    date = row[0]
                    time_str = row[1]
                    target = row[2]
                    protocol = row[3]
                    attempts = row[4]
                    found = row[5]
                    duration = row[6]
                    result = row[7]
                    
                    # Format duration
                    duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
                    
                    # Write row
                    f.write(f"{date},{time_str},{target},{protocol},{attempts},{found},{duration_str},{result}\n")
            
            # Show success message
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Export Successful"
            )
            dialog.format_secondary_text(f"Statistics have been exported to:\n{filename}")
            dialog.run()
            dialog.destroy()
            
        except Exception as e:
            self.logger.error(f"Error exporting statistics: {str(e)}")
            
            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Export Failed"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def load_statistics(self):
        """Load and display statistics data."""
        # Clear existing data
        self.history_store.clear()
        
        try:
            # Load stats directory
            if not os.path.exists(self.stats_dir):
                return
            
            # Load attack history files
            stats_files = [os.path.join(self.stats_dir, f) for f in os.listdir(self.stats_dir)
                          if f.endswith('.json')]
            
            # Process stats files
            all_stats = []
            for file_path in stats_files:
                try:
                    with open(file_path, 'r') as f:
                        stats = json.load(f)
                        all_stats.append(stats)
                except Exception as e:
                    self.logger.error(f"Error loading stats file {file_path}: {str(e)}")
            
            # Process data for display
            self._process_statistics(all_stats)
            
        except Exception as e:
            self.logger.error(f"Error loading statistics: {str(e)}")
    
    def _process_statistics(self, all_stats):
        """Process statistics data for display.
        
        Args:
            all_stats: List of statistics data dictionaries
        """
        if not all_stats:
            return
        
        # Sort by timestamp (newest first)
        all_stats.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Populate history view
        for stats in all_stats:
            timestamp = stats.get('timestamp', 0)
            date_str = time.strftime("%Y-%m-%d", time.localtime(timestamp))
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            
            target = stats.get('target', '--')
            protocol = stats.get('protocol', '--')
            total_attempts = stats.get('total_attempts', 0)
            completed_attempts = stats.get('completed_attempts', 0)
            successful_attempts = stats.get('successful_attempts', 0)
            duration = stats.get('duration', 0)
            
            # Determine result
            if successful_attempts > 0:
                result = "Success"
            elif completed_attempts == total_attempts:
                result = "Completed"
            else:
                result = "Stopped"
            
            # Add to history store
            self.history_store.append([
                date_str,
                time_str,
                target,
                protocol,
                completed_attempts,
                successful_attempts,
                duration,
                result
            ])
        
        # Update summary statistics
        self._update_summary_statistics(all_stats)
        
        # Update performance metrics
        self._update_performance_metrics(all_stats)
    
    def _update_summary_statistics(self, all_stats):
        """Update summary statistics.
        
        Args:
            all_stats: List of statistics data dictionaries
        """
        # Get current time for filtering
        current_time = time.time()
        day_ago = current_time - (24 * 60 * 60)
        week_ago = current_time - (7 * 24 * 60 * 60)
        month_ago = current_time - (30 * 24 * 60 * 60)
        
        # Filter by time period
        today_stats = [s for s in all_stats if s.get('timestamp', 0) >= day_ago]
        week_stats = [s for s in all_stats if s.get('timestamp', 0) >= week_ago]
        month_stats = [s for s in all_stats if s.get('timestamp', 0) >= month_ago]
        
        # Time periods for display
        periods = [all_stats, month_stats, week_stats, today_stats]
        
        # Calculate summary statistics
        for period_idx, period_stats in enumerate(periods):
            # Total attacks
            total_attacks = len(period_stats)
            self.summary_values["Total Attacks"][period_idx].set_text(str(total_attacks))
            
            # Successful attacks (those with at least one success)
            successful_attacks = sum(1 for s in period_stats if s.get('successful_attempts', 0) > 0)
            self.summary_values["Successful Attacks"][period_idx].set_text(str(successful_attacks))
            
            # Passwords found
            passwords_found = sum(s.get('successful_attempts', 0) for s in period_stats)
            self.summary_values["Passwords Found"][period_idx].set_text(str(passwords_found))
            
            # Success rate
            if total_attacks > 0:
                success_rate = (successful_attacks / total_attacks) * 100
                self.summary_values["Success Rate"][period_idx].set_text(f"{success_rate:.1f}%")
            else:
                self.summary_values["Success Rate"][period_idx].set_text("--")
            
            # Average time per attack
            if total_attacks > 0:
                avg_time = sum(s.get('duration', 0) for s in period_stats) / total_attacks
                avg_time_str = time.strftime("%H:%M:%S", time.gmtime(avg_time))
                self.summary_values["Avg. Time per Attack"][period_idx].set_text(avg_time_str)
            else:
                self.summary_values["Avg. Time per Attack"][period_idx].set_text("--")
            
            # Average attempts per second
            total_duration = sum(s.get('duration', 0) for s in period_stats)
            total_attempts = sum(s.get('completed_attempts', 0) for s in period_stats)
            if total_duration > 0:
                avg_attempts = total_attempts / total_duration
                self.summary_values["Avg. Attempts per Second"][period_idx].set_text(f"{avg_attempts:.1f}")
            else:
                self.summary_values["Avg. Attempts per Second"][period_idx].set_text("--")
    
    def _update_performance_metrics(self, all_stats):
        """Update performance metrics.
        
        Args:
            all_stats: List of statistics data dictionaries
        """
        if not all_stats:
            return
        
        # Peak attempts per second
        peak_attempts = max((s.get('attempts_per_second', 0) for s in all_stats), default=0)
        self.performance_values["Peak Attempts/s"].set_text(f"{peak_attempts:.1f}")
        
        # Average success time
        successful_times = []
        for stat in all_stats:
            if stat.get('successful_attempts', 0) > 0 and stat.get('duration', 0) > 0:
                successful_times.append(stat.get('duration', 0) / max(1, stat.get('successful_attempts', 1)))
        
        if successful_times:
            avg_success_time = sum(successful_times) / len(successful_times)
            time_str = time.strftime("%H:%M:%S", time.gmtime(avg_success_time))
            self.performance_values["Avg. Success Time"].set_text(time_str)
        else:
            self.performance_values["Avg. Success Time"].set_text("--")
        
        # Total unique credentials
        total_creds = sum(s.get('successful_attempts', 0) for s in all_stats)
        self.performance_values["Total Credentials"].set_text(str(total_creds))
        
        # Most common protocol
        protocols = {}
        for stat in all_stats:
            protocol = stat.get('protocol', '--')
            protocols[protocol] = protocols.get(protocol, 0) + 1
        
        if protocols:
            most_common = max(protocols.items(), key=lambda x: x[1])[0]
            self.performance_values["Most Common Protocol"].set_text(most_common)
    
    def _update_statistics(self):
        """Update statistics periodically.
        
        Returns:
            True to continue timer, False to stop
        """
        self.load_statistics()
        return True
    
    def add_attack_statistics(self, stats):
        """Add new attack statistics.
        
        Args:
            stats: Dictionary with attack statistics
        """
        # Generate unique filename
        timestamp = int(time.time())
        filename = f"attack_{timestamp}.json"
        file_path = os.path.join(self.stats_dir, filename)
        
        try:
            # Ensure stats directory exists
            os.makedirs(self.stats_dir, exist_ok=True)
            
            # Add timestamp if not present
            if 'timestamp' not in stats:
                stats['timestamp'] = timestamp
            
            # Save stats to file
            with open(file_path, 'w') as f:
                json.dump(stats, f, indent=2)
            
            # Reload statistics
            self.load_statistics()
            
        except Exception as e:
            self.logger.error(f"Error saving attack statistics: {str(e)}")
    
    def get_statistics_summary(self):
        """Get a summary of the statistics.
        
        Returns:
            Dictionary with statistics summary
        """
        summary = {}
        
        # Extract values from UI elements
        for metric, labels in self.summary_values.items():
            # Get all-time value (first column)
            all_time_value = labels[0].get_text()
            summary[metric] = all_time_value
        
        # Extract performance metrics
        for metric, label in self.performance_values.items():
            summary[metric] = label.get_text()
        
        return summary
