#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Dashboard.
This module provides a unified dashboard view for monitoring and metrics.
"""

import gi
import time
import random
from datetime import datetime, timedelta
import cairo
import os
import csv
import logging

gi.require_version('Gtk', '3.0')
# Linter may report these as unknown, but they are valid when GTK is properly installed
from gi.repository import Gtk, GLib, Gdk, Pango

from src.utils.logging import get_logger
from src.core.attack import AttackController
from src.utils.system_monitor import SystemMonitor
from src.core.data_manager import DataManager


class Dashboard(Gtk.Box):
    """Dashboard widget with overview metrics and monitoring."""
    
    def __init__(self):
        """Initialize the dashboard widget."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Data sources
        self.attack_source = None
        self.results_source = None
        self.system_monitor = None
        self.data_manager = None
        self.attack_controller = None
        
        # Recent attacks
        self.attack_history = []
        
        # Discovered credentials
        self.discovered_credentials = []
        
        # UI elements we need to update
        self.summary_labels = {}
        self.system_status_widgets = {}
        self.attack_store = None
        self.credentials_store = None
        self.success_rate_data = []
        
        # Create a 2x2 grid layout for dashboard panels
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.pack_start(grid, True, True, 0)
        
        # Add dashboard panels
        grid.attach(self._create_summary_panel(), 0, 0, 1, 1)
        grid.attach(self._create_recent_attacks_panel(), 1, 0, 1, 1)
        grid.attach(self._create_system_status_panel(), 0, 1, 1, 1)
        grid.attach(self._create_discovered_credentials_panel(), 1, 1, 1, 1)
    
    def connect_to_data_sources(self, attack_source=None, results_source=None, system_monitor=None):
        """Connect to data sources for live updates.
        
        Args:
            attack_source: Attack status source
            results_source: Results data source
            system_monitor: System monitoring source
        """
        self.attack_source = attack_source
        self.results_source = results_source
        self.system_monitor = system_monitor
        
        try:
            from src.core.data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except ImportError:
            self.logger.error("Failed to import DataManager")
            self.data_manager = None
            
        try:
            from src.core.attack import AttackController
            self.attack_controller = AttackController.get_instance()
        except ImportError:
            self.logger.error("Failed to import AttackController")
            self.attack_controller = None
        
        # Initialize metrics with real values if sources are available
        self._initialize_metrics()
        
        # Start update timer
        GLib.timeout_add(5000, self._update_metrics)
        
        self.logger.info("Dashboard connected to data sources")
    
    def _initialize_metrics(self):
        """Initialize metrics with real values from data sources."""
        # Initialize system metrics if monitor is available
        if self.system_monitor:
            self._update_system_metrics()
        
        # Initialize attack metrics if sources are available
        if self.results_source:
            # Get attack history
            self.attack_history = self.results_source.get_recent_attacks(10)
            self._update_attack_store()
            
            # Get discovered credentials
            self.discovered_credentials = self.results_source.get_recent_credentials(10)
            self._update_credentials_store()
            
            # Update summary metrics
            self._update_summary_metrics()
    
    def _create_summary_panel(self):
        """Create the summary metrics panel.
        
        Returns:
            Gtk.Frame: The summary panel
        """
        frame = Gtk.Frame(label="Attack Summary")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Create a grid for metrics
        metrics_grid = Gtk.Grid()
        metrics_grid.set_column_spacing(12)
        metrics_grid.set_row_spacing(6)
        box.pack_start(metrics_grid, True, True, 0)
        
        # Total attacks
        label = Gtk.Label(label="Total Attacks:", xalign=0)
        metrics_grid.attach(label, 0, 0, 1, 1)
        
        self.total_attacks_label = Gtk.Label(label="0", xalign=1)
        metrics_grid.attach(self.total_attacks_label, 1, 0, 1, 1)
        
        # Successful attacks
        label = Gtk.Label(label="Successful:", xalign=0)
        metrics_grid.attach(label, 0, 1, 1, 1)
        
        self.successful_attacks_label = Gtk.Label(label="0", xalign=1)
        metrics_grid.attach(self.successful_attacks_label, 1, 1, 1, 1)
        
        # Success rate
        label = Gtk.Label(label="Success Rate:", xalign=0)
        metrics_grid.attach(label, 0, 2, 1, 1)
        
        self.success_rate_label = Gtk.Label(label="0.0%", xalign=1)
        metrics_grid.attach(self.success_rate_label, 1, 2, 1, 1)
        
        # Total credentials found
        label = Gtk.Label(label="Credentials Found:", xalign=0)
        metrics_grid.attach(label, 0, 3, 1, 1)
        
        self.total_creds_label = Gtk.Label(label="0", xalign=1)
        metrics_grid.attach(self.total_creds_label, 1, 3, 1, 1)
        
        # Total targets
        label = Gtk.Label(label="Targets:", xalign=0)
        metrics_grid.attach(label, 0, 4, 1, 1)
        
        self.total_targets_label = Gtk.Label(label="0", xalign=1)
        metrics_grid.attach(self.total_targets_label, 1, 4, 1, 1)
        
        # Active scans
        label = Gtk.Label(label="Active Scans:", xalign=0)
        metrics_grid.attach(label, 0, 5, 1, 1)
        
        self.active_scans_label = Gtk.Label(label="0", xalign=1)
        metrics_grid.attach(self.active_scans_label, 1, 5, 1, 1)
        
        # Create chart placeholder
        chart_label = Gtk.Label(label="Success Rate Over Time")
        box.pack_start(chart_label, False, False, 6)
        
        # Real chart implementation using Cairo
        chart_frame = Gtk.Frame()
        chart_frame.set_size_request(-1, 150)
        
        chart_drawing_area = Gtk.DrawingArea()
        chart_drawing_area.connect("draw", self._on_draw_chart)
        chart_frame.add(chart_drawing_area)
        
        box.pack_start(chart_frame, True, True, 0)
        
        return frame
    
    def _on_draw_chart(self, widget, cr):
        """Draw a chart with real success rate data.
        
        Args:
            widget: The drawing area widget
            cr: Cairo context
        """
        # Get widget dimensions
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        
        # Draw background
        cr.set_source_rgb(0.95, 0.95, 0.95)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        
        # Draw border
        cr.set_source_rgb(0.8, 0.8, 0.8)
        cr.rectangle(0, 0, width, height)
        cr.stroke()
        
        # Draw axes
        cr.set_source_rgb(0.5, 0.5, 0.5)
        cr.set_line_width(1)
        
        # X-axis
        cr.move_to(10, height - 10)
        cr.line_to(width - 10, height - 10)
        cr.stroke()
        
        # Y-axis
        cr.move_to(10, 10)
        cr.line_to(10, height - 10)
        cr.stroke()
        
        # Get success rate data if available
        if self.results_source:
            success_data = self.results_source.get_success_rate_over_time(7)
            if success_data and len(success_data) > 0:
                # Calculate scale factors
                x_scale = (width - 20) / (len(success_data) - 1) if len(success_data) > 1 else width - 20
                y_scale = (height - 20) / 100  # Percentage scale
                
                # Draw line
                cr.set_source_rgb(0.2, 0.4, 0.8)
                cr.set_line_width(2)
                
                # First point
                x_value = 0
                y_value = success_data[0]
                cr.move_to(10 + x_value * x_scale, height - 10 - y_value * y_scale)
                
                # Remaining points
                for i in range(1, len(success_data)):
                    x_value = i
                    y_value = success_data[i]
                    cr.line_to(10 + x_value * x_scale, height - 10 - y_value * y_scale)
                
                cr.stroke()
                
                # Draw points
                for i in range(len(success_data)):
                    x_value = i
                    y_value = success_data[i]
                    cr.arc(10 + x_value * x_scale, height - 10 - y_value * y_scale, 3, 0, 2 * 3.14159)
                    cr.fill()
        
        return True
    
    def _create_recent_attacks_panel(self):
        """Create the recent attacks panel.
        
        Returns:
            Gtk.Frame: The recent attacks panel
        """
        frame = Gtk.Frame(label="Recent Attacks")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Create scrolled window for attack list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        box.pack_start(scrolled, True, True, 0)
        
        # List store for recent attacks
        # Time, Target, Protocol, Status, Success Rate
        self.attack_store = Gtk.ListStore(str, str, str, str, float)
        
        # Tree view
        attack_view = Gtk.TreeView(model=self.attack_store)
        attack_view.set_headers_visible(True)
        scrolled.add(attack_view)
        
        # Columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Time", renderer, text=0)
        column.set_sort_column_id(0)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Target", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Protocol", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Status", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        renderer = Gtk.CellRendererProgress()
        column = Gtk.TreeViewColumn("Success", renderer, value=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        return frame
    
    def _create_system_status_panel(self):
        """Create the system status panel.
        
        Returns:
            Gtk.Frame: The system status panel
        """
        frame = Gtk.Frame(label="System Status")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # CPU usage
        cpu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cpu_label = Gtk.Label(label="CPU Usage:", xalign=0)
        cpu_box.pack_start(cpu_label, False, False, 0)
        
        self.cpu_progress = Gtk.ProgressBar()
        self.cpu_progress.set_show_text(True)
        self.cpu_progress.set_text("0.0%")
        self.cpu_progress.set_fraction(0.0)
        cpu_box.pack_start(self.cpu_progress, True, True, 0)
        
        box.pack_start(cpu_box, False, False, 0)
        
        # Memory usage
        mem_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mem_label = Gtk.Label(label="Memory:", xalign=0)
        mem_box.pack_start(mem_label, False, False, 0)
        
        self.mem_progress = Gtk.ProgressBar()
        self.mem_progress.set_show_text(True)
        self.mem_progress.set_text("0.0%")
        self.mem_progress.set_fraction(0.0)
        mem_box.pack_start(self.mem_progress, True, True, 0)
        
        box.pack_start(mem_box, False, False, 0)
        
        # Disk usage
        disk_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        disk_label = Gtk.Label(label="Disk Space:", xalign=0)
        disk_box.pack_start(disk_label, False, False, 0)
        
        self.disk_progress = Gtk.ProgressBar()
        self.disk_progress.set_show_text(True)
        self.disk_progress.set_text("0.0%")
        self.disk_progress.set_fraction(0.0)
        disk_box.pack_start(self.disk_progress, True, True, 0)
        
        box.pack_start(disk_box, False, False, 0)
        
        # Network usage
        net_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        net_label = Gtk.Label(label="Network:", xalign=0)
        net_box.pack_start(net_label, False, False, 0)
        
        self.net_progress = Gtk.ProgressBar()
        self.net_progress.set_show_text(True)
        self.net_progress.set_text("0.0%")
        self.net_progress.set_fraction(0.0)
        net_box.pack_start(self.net_progress, True, True, 0)
        
        box.pack_start(net_box, False, False, 0)
        
        # System info
        info_frame = Gtk.Frame(label="System Information")
        box.pack_start(info_frame, True, True, 6)
        
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info_box.set_border_width(6)
        info_frame.add(info_box)
        
        # Hostname
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Hostname:", xalign=0)
        host_box.pack_start(host_label, False, False, 0)
        
        self.hostname_label = Gtk.Label(label="", xalign=0)
        host_box.pack_start(self.hostname_label, True, True, 0)
        
        info_box.pack_start(host_box, False, False, 0)
        
        # IP Address
        ip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ip_label = Gtk.Label(label="IP Address:", xalign=0)
        ip_box.pack_start(ip_label, False, False, 0)
        
        self.ip_addr_label = Gtk.Label(label="", xalign=0)
        ip_box.pack_start(self.ip_addr_label, True, True, 0)
        
        info_box.pack_start(ip_box, False, False, 0)
        
        # System uptime
        uptime_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        uptime_label = Gtk.Label(label="Uptime:", xalign=0)
        uptime_box.pack_start(uptime_label, False, False, 0)
        
        self.uptime_label = Gtk.Label(label="0d 0h 0m", xalign=0)
        uptime_box.pack_start(self.uptime_label, True, True, 0)
        
        info_box.pack_start(uptime_box, False, False, 0)
        
        # ERPCT version
        version_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        version_label = Gtk.Label(label="ERPCT Version:", xalign=0)
        version_box.pack_start(version_label, False, False, 0)
        
        self.version_label = Gtk.Label(label="", xalign=0)
        version_box.pack_start(self.version_label, True, True, 0)
        
        info_box.pack_start(version_box, False, False, 0)
        
        return frame
    
    def _create_discovered_credentials_panel(self):
        """Create the discovered credentials panel.
        
        Returns:
            Gtk.Frame: The discovered credentials panel
        """
        frame = Gtk.Frame(label="Recently Discovered Credentials")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Create scrolled window for credentials list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        box.pack_start(scrolled, True, True, 0)
        
        # List store for credentials
        # Time, Target, Username, Password, Protocol
        self.creds_store = Gtk.ListStore(str, str, str, str, str)
        
        # Tree view
        creds_view = Gtk.TreeView(model=self.creds_store)
        creds_view.set_headers_visible(True)
        scrolled.add(creds_view)
        
        # Columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Time", renderer, text=0)
        column.set_sort_column_id(0)
        column.set_resizable(True)
        creds_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Target", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        creds_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Username", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        creds_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Password", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        creds_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Protocol", renderer, text=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        creds_view.append_column(column)
        
        # Search and export box
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(action_box, False, False, 6)
        
        # Search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search credentials...")
        self.search_entry.connect("search-changed", self._on_search_changed)
        action_box.pack_start(self.search_entry, True, True, 0)
        
        # Export button
        export_button = Gtk.Button(label="Export Credentials")
        export_button.connect("clicked", self._on_export_clicked)
        action_box.pack_start(export_button, False, False, 0)
        
        return frame
    
    def _on_search_changed(self, entry):
        """Handle credential search.
        
        Args:
            entry: The search entry widget
        """
        search_text = entry.get_text().lower()
        
        # Pass search to results source if available
        if self.results_source and search_text:
            search_results = self.results_source.search_credentials(search_text)
            
            # Update store with search results
            self.creds_store.clear()
            for cred in search_results:
                self.creds_store.append([
                    cred.get('timestamp', ''),
                    cred.get('target', ''),
                    cred.get('username', ''),
                    cred.get('password', ''),
                    cred.get('protocol', '')
                ])
        elif self.results_source:
            # Reset to recent credentials
            self.discovered_credentials = self.results_source.get_recent_credentials(10)
            self._update_credentials_store()
    
    def _on_export_clicked(self, button):
        """Handle export credentials button click."""
        if not self.results_source:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Export Error"
            )
            dialog.format_secondary_text("No results data source available.")
            dialog.run()
            dialog.destroy()
            return
        
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Export Credentials",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        # Default filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dialog.set_current_name(f"credentials-{timestamp}.csv")
        
        # CSV filter
        csv_filter = Gtk.FileFilter()
        csv_filter.set_name("CSV files")
        csv_filter.add_mime_type("text/csv")
        csv_filter.add_pattern("*.csv")
        dialog.add_filter(csv_filter)
        
        response = dialog.run()
        filename = dialog.get_filename()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and filename:
            try:
                # Export credentials through the results source
                self.results_source.export_credentials(filename)
                
                # Show success message
                success_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Export Successful"
                )
                success_dialog.format_secondary_text(f"Credentials have been exported to:\n{filename}")
                success_dialog.run()
                success_dialog.destroy()
                
                self.logger.info(f"Exported credentials to {filename}")
            except Exception as e:
                # Show error message
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Export Error"
                )
                error_dialog.format_secondary_text(f"Failed to export credentials: {str(e)}")
                error_dialog.run()
                error_dialog.destroy()
                
                self.logger.error(f"Error exporting credentials: {str(e)}")
    
    def _update_system_metrics(self):
        """Update system metrics from system monitor."""
        if not self.system_monitor:
            return
            
        try:
            # Get formatted metrics
            metrics = self.system_monitor.get_formatted_metrics()
            
            # Update UI with real system metrics
            self.cpu_progress.set_text(metrics['cpu'])
            self.cpu_progress.set_fraction(float(metrics['cpu'].rstrip('%')) / 100.0)
            
            self.mem_progress.set_text(metrics['memory'])
            self.mem_progress.set_fraction(float(metrics['memory'].rstrip('%')) / 100.0)
            
            self.disk_progress.set_text(metrics['disk'])
            self.disk_progress.set_fraction(float(metrics['disk'].rstrip('%')) / 100.0)
            
            self.net_progress.set_text(metrics['network'])
            self.net_progress.set_fraction(float(metrics['network'].rstrip('%')) / 100.0)
            
            # Update system info
            self.hostname_label.set_text(metrics['hostname'])
            self.ip_addr_label.set_text(metrics['ip_address'])
            self.uptime_label.set_text(metrics['uptime'])
            self.version_label.set_text(metrics['version'])
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {str(e)}")
    
    def _update_attack_store(self):
        """Update the attack store with real attack data."""
        # Clear existing data
        if self.attack_store is None:
            self.logger.error("Attack store is not initialized")
            return
            
        self.attack_store.clear()
        
        # Get recent attacks from data manager
        if self.data_manager is None:
            self.logger.warning("Data manager is not available")
            # Add a placeholder row to show no data is available
            self.attack_store.append([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "No Data Available",
                "N/A",
                "No active attacks",
                0.0  # Use float instead of string for success rate
            ])
            return
            
        recent_attacks = self.data_manager.get_recent_attacks(limit=10)
        
        # Get active attacks
        if self.attack_controller is None:
            self.logger.warning("Attack controller is not available")
            # Add a placeholder row to show no data is available
            self.attack_store.append([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "No Data Available",
                "N/A",
                "No active attacks",
                0.0  # Use float instead of string for success rate
            ])
            return
            
        active_attacks = self.attack_controller.get_active_attacks()
        
        # Check if we have any active or recent attacks
        if not active_attacks and not recent_attacks:
            # Add a placeholder row to show no data is available
            self.attack_store.append([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "No Data Available",
                "N/A",
                "No attack history",
                0.0  # Use float instead of string for success rate
            ])
            return
            
        # Add active attacks to the list
        for attack_id, attack in active_attacks.items():
            status = attack.get_status()
            target = attack.config.get('target', 'Unknown')
            protocol = attack.config.get('protocol', 'Unknown')
            
            # Calculate success rate
            completed = status.get('completed_attempts', 0)
            successful = status.get('successful_attempts', 0)
            success_rate = (successful / completed * 100) if completed > 0 else 0
            
            # Add to store
            self.attack_store.append([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                target,
                protocol,
                "Running" if status.get('running', False) else "Complete",
                success_rate  # Already a float, don't format as string
            ])
        
        # Add completed attacks
        for attack in recent_attacks:
            success_rate = float(attack.get('success_rate', 0))  # Ensure it's a float
            self.attack_store.append([
                attack.get('timestamp', 'Unknown'),
                attack.get('target', 'Unknown'),
                attack.get('protocol', 'Unknown'),
                attack.get('status', 'Unknown'),
                success_rate  # Use float instead of formatted string
            ])
    
    def _update_credentials_store(self):
        """Update the credentials store with real credentials data."""
        # Clear existing data
        if self.creds_store is None:
            self.logger.error("Credentials store is not initialized")
            return
            
        self.creds_store.clear()
        
        # Get recent credentials from data manager
        if self.data_manager is None:
            self.logger.warning("Data manager is not available")
            # Add a placeholder row to show no data is available
            self.creds_store.append([
                "No Data Available",
                "Run an attack to find credentials",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "N/A",
                "N/A"
            ])
            return
            
        recent_credentials = self.data_manager.get_recent_credentials(limit=50)
        
        # Get active attacks and their credentials
        if self.attack_controller is None:
            self.logger.warning("Attack controller is not available")
            # Add a placeholder row to show no data is available
            self.creds_store.append([
                "No Data Available",
                "Run an attack to find credentials",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "N/A",
                "N/A"
            ])
            return
            
        active_attacks = self.attack_controller.get_active_attacks()
        active_credentials = []
        for attack_id, attack in active_attacks.items():
            status = attack.get_status()
            for username, password in attack.get_successful_credentials():
                active_credentials.append({
                    'username': username,
                    'password': password,
                    'target': attack.config.get('target', 'Unknown'),
                    'protocol': attack.config.get('protocol', 'Unknown'),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # Check if we have any active or recent credentials
        if not active_credentials and not recent_credentials:
            # Add a placeholder row to show no data is available
            self.creds_store.append([
                "No Credentials Found",
                "Run an attack to find credentials",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "N/A",
                "N/A"
            ])
            return
        
        # Add active credentials first
        for cred in active_credentials:
            self.creds_store.append([
                cred.get('timestamp', 'Unknown'),
                cred.get('target', 'Unknown'),
                cred.get('protocol', 'Unknown'),
                cred.get('username', 'Unknown'),
                cred.get('password', 'Unknown')
            ])
        
        # Add stored credentials
        for cred in recent_credentials:
            self.creds_store.append([
                cred.get('timestamp', 'Unknown'),
                cred.get('target', 'Unknown'),
                cred.get('protocol', 'Unknown'),
                cred.get('username', 'Unknown'),
                cred.get('password', 'Unknown')
            ])
    
    def _update_summary_metrics(self):
        """Update summary metrics from results source."""
        if not self.results_source:
            # Show default values with clear messages
            self.total_attacks_label.set_text("0 (No Data)")
            self.successful_attacks_label.set_text("0 (No Data)")
            self.total_creds_label.set_text("0 (No Data)")
            self.total_targets_label.set_text("0 (No Data)")
            self.active_scans_label.set_text("0 (No Active Scans)")
            self.success_rate_label.set_text("0.0% (No Data)")
            return
            
        try:
            # Get summary metrics
            metrics = self.results_source.get_summary_metrics()
            
            # Update UI with real metrics or default values with clear messages
            if metrics.get('total_attacks', 0) > 0:
                self.total_attacks_label.set_text(str(metrics.get('total_attacks', 0)))
                self.successful_attacks_label.set_text(str(metrics.get('successful_attacks', 0)))
                self.total_creds_label.set_text(str(metrics.get('total_credentials', 0)))
                self.total_targets_label.set_text(str(metrics.get('total_targets', 0)))
                
                # Calculate success rate
                success_rate = (metrics.get('successful_attacks', 0) / metrics.get('total_attacks', 0)) * 100
                self.success_rate_label.set_text(f"{success_rate:.1f}%")
            else:
                self.total_attacks_label.set_text("0 (No Attacks Run)")
                self.successful_attacks_label.set_text("0 (No Data)")
                self.total_creds_label.set_text("0 (No Credentials Found)")
                self.total_targets_label.set_text("0 (No Targets)")
                self.success_rate_label.set_text("0.0% (No Data)")
            
            # Active scans are updated separately
            active_scans = metrics.get('active_scans', 0)
            if active_scans > 0:
                self.active_scans_label.set_text(str(active_scans))
            else:
                self.active_scans_label.set_text("0 (No Active Scans)")
            
            # Update success rate data for chart
            success_rates = metrics.get('success_rate_history', [])
            if success_rates:
                self.success_rate_data = success_rates
        except Exception as e:
            self.logger.error(f"Error updating summary metrics: {str(e)}")
            # Show error message in labels
            self.total_attacks_label.set_text("Error")
            self.successful_attacks_label.set_text("Error")
            self.total_creds_label.set_text("Error")
            self.total_targets_label.set_text("Error")
            self.active_scans_label.set_text("Error")
            self.success_rate_label.set_text("Error")
    
    def _update_metrics(self):
        """Update all dashboard metrics with real data."""
        try:
            # Update system metrics
            if self.system_monitor:
                self._update_system_metrics()
            
            # Update attack metrics if sources are available
            if self.results_source:
                # Check for new attacks
                new_history = self.results_source.get_recent_attacks(10)
                if new_history != self.attack_history:
                    self.attack_history = new_history
                    self._update_attack_store()
                
                # Check for new credentials
                new_creds = self.results_source.get_recent_credentials(10)
                if new_creds != self.discovered_credentials:
                    self.discovered_credentials = new_creds
                    self._update_credentials_store()
                
                # Update summary metrics
                self._update_summary_metrics()
            
            # Check active scans
            if self.attack_source:
                active_scans = len(self.attack_source.get_active_attacks())
                self.active_scans_label.set_text(str(active_scans))
        except Exception as e:
            self.logger.error(f"Error in metrics update: {str(e)}")
        
        return True  # Continue the timer 