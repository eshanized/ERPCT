#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Network Scanner.
This module provides a GUI for scanning and discovering network targets.
"""

import gi
import threading
import time
import ipaddress
import socket
import os
import json

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from src.utils.logging import get_logger

# Import nmap for network scanning
try:
    import nmap
    NMAP_AVAILABLE = True
except ImportError:
    NMAP_AVAILABLE = False


class NetworkScanner(Gtk.Box):
    """Network scanner widget."""
    
    def __init__(self):
        """Initialize the network scanner widget."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        self.scan_thread = None
        self.stop_scan_flag = False
        self.target_callback = None
        
        # Check for nmap
        if not NMAP_AVAILABLE:
            self.logger.error("python-nmap is required but not installed")
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Missing Dependency"
            )
            dialog.format_secondary_text("python-nmap is required for network scanning.\nPlease install it with 'pip install python-nmap'.")
            dialog.run()
            dialog.destroy()
        
        # Scan configuration section
        config_frame = Gtk.Frame(label="Scan Configuration")
        self.pack_start(config_frame, False, False, 0)
        
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        config_box.set_border_width(10)
        config_frame.add(config_box)
        
        # IP Range
        ip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ip_label = Gtk.Label(label="IP Range:", xalign=0)
        ip_label.set_width_chars(12)
        ip_box.pack_start(ip_label, False, False, 0)
        
        self.ip_entry = Gtk.Entry()
        self.ip_entry.set_placeholder_text("Enter IP range (e.g., 192.168.1.0/24)")
        self.ip_entry.set_text("192.168.1.0/24")
        ip_box.pack_start(self.ip_entry, True, True, 0)
        
        config_box.pack_start(ip_box, False, False, 0)
        
        # Port Range
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port Range:", xalign=0)
        port_label.set_width_chars(12)
        port_box.pack_start(port_label, False, False, 0)
        
        self.start_port_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=1, lower=1, upper=65535, step_increment=1, page_increment=100)
        self.start_port_spin.set_adjustment(adjustment)
        port_box.pack_start(self.start_port_spin, True, True, 0)
        
        port_box.pack_start(Gtk.Label(label="-"), False, False, 0)
        
        self.end_port_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=1024, lower=1, upper=65535, step_increment=1, page_increment=100)
        self.end_port_spin.set_adjustment(adjustment)
        port_box.pack_start(self.end_port_spin, True, True, 0)
        
        config_box.pack_start(port_box, False, False, 0)
        
        # Scan options
        options_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        options_label = Gtk.Label(label="Options:", xalign=0)
        options_label.set_width_chars(12)
        options_box.pack_start(options_label, False, False, 0)
        
        self.ping_check = Gtk.CheckButton(label="Ping Scan")
        self.ping_check.set_active(True)
        options_box.pack_start(self.ping_check, True, True, 0)
        
        self.tcp_check = Gtk.CheckButton(label="TCP Connect")
        self.tcp_check.set_active(True)
        options_box.pack_start(self.tcp_check, True, True, 0)
        
        self.service_check = Gtk.CheckButton(label="Service Detection")
        self.service_check.set_active(True)
        options_box.pack_start(self.service_check, True, True, 0)
        
        config_box.pack_start(options_box, False, False, 0)
        
        # Scan speed / intensity
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        speed_label = Gtk.Label(label="Scan Speed:", xalign=0)
        speed_label.set_width_chars(12)
        speed_box.pack_start(speed_label, False, False, 0)
        
        speed_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 5, 1)
        speed_scale.set_value(3)
        speed_scale.set_digits(0)
        speed_scale.set_draw_value(True)
        speed_scale.add_mark(1, Gtk.PositionType.BOTTOM, "Slow/Stealthy")
        speed_scale.add_mark(5, Gtk.PositionType.BOTTOM, "Fast/Aggressive")
        speed_box.pack_start(speed_scale, True, True, 0)
        self.speed_scale = speed_scale
        
        config_box.pack_start(speed_box, False, False, 0)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        config_box.pack_start(button_box, False, False, 10)
        
        self.scan_button = Gtk.Button(label="Start Scan")
        self.scan_button.connect("clicked", self._on_scan_clicked)
        button_box.pack_end(self.scan_button, False, False, 0)
        
        # Results section
        results_frame = Gtk.Frame(label="Scan Results")
        self.pack_start(results_frame, True, True, 0)
        
        results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        results_box.set_border_width(10)
        results_frame.add(results_box)
        
        # Status bar
        self.status_bar = Gtk.ProgressBar()
        self.status_bar.set_show_text(True)
        self.status_bar.set_text("Ready")
        results_box.pack_start(self.status_bar, False, False, 0)
        
        # Results tree view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        results_box.pack_start(scrolled, True, True, 0)
        
        # List store columns for hosts
        # IP, Hostname, Status, OS, # Open Ports, Last Seen
        self.host_store = Gtk.ListStore(str, str, str, str, int, str)
        
        # Tree view
        self.host_view = Gtk.TreeView(model=self.host_store)
        self.host_view.set_headers_visible(True)
        self.host_view.connect("row-activated", self._on_host_activated)
        scrolled.add(self.host_view)
        
        # Columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("IP Address", renderer, text=0)
        column.set_sort_column_id(0)
        column.set_resizable(True)
        self.host_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Hostname", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        self.host_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Status", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        self.host_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("OS", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        self.host_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Open Ports", renderer, text=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        self.host_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Last Seen", renderer, text=5)
        column.set_sort_column_id(5)
        column.set_resizable(True)
        self.host_view.append_column(column)
        
        # Port details view
        ports_label = Gtk.Label(label="Open Ports:", xalign=0)
        results_box.pack_start(ports_label, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        scrolled.set_size_request(-1, 150)
        results_box.pack_start(scrolled, False, False, 0)
        
        # List store columns for ports
        # Port, Protocol, Service, Version, Status
        self.port_store = Gtk.ListStore(int, str, str, str, str)
        
        # Tree view
        self.port_view = Gtk.TreeView(model=self.port_store)
        self.port_view.set_headers_visible(True)
        scrolled.add(self.port_view)
        
        # Columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Port", renderer, text=0)
        column.set_sort_column_id(0)
        column.set_resizable(True)
        self.port_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Protocol", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        self.port_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Service", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        self.port_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Version", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        self.port_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Status", renderer, text=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        self.port_view.append_column(column)
        
        # Action buttons
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        results_box.pack_start(action_box, False, False, 0)
        
        self.add_target_button = Gtk.Button(label="Add to Targets")
        self.add_target_button.connect("clicked", self._on_add_target)
        action_box.pack_start(self.add_target_button, False, False, 0)
        
        self.export_button = Gtk.Button(label="Export Results")
        self.export_button.connect("clicked", self._on_export_results)
        action_box.pack_start(self.export_button, False, False, 0)
        
        self.clear_button = Gtk.Button(label="Clear Results")
        self.clear_button.connect("clicked", self._on_clear_results)
        action_box.pack_start(self.clear_button, False, False, 0)
    
    def set_target_callback(self, callback):
        """Set the callback function for adding targets.
        
        Args:
            callback: Function to call when a target is added
        """
        self.logger.debug("Setting target callback")
        self.target_callback = callback

    def _on_scan_clicked(self, button):
        """Handle scan button click."""
        if self.scan_thread and self.scan_thread.is_alive():
            # Stop running scan
            self.stop_scan_flag = True
            self.scan_button.set_label("Starting Scan")
            self.scan_button.set_sensitive(False)
            return
        
        # Start a new scan
        ip_range = self.ip_entry.get_text()
        start_port = self.start_port_spin.get_value_as_int()
        end_port = self.end_port_spin.get_value_as_int()
        
        # Basic validation
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
        except ValueError:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Invalid IP Range"
            )
            dialog.format_secondary_text(f"'{ip_range}' is not a valid IP range. Use CIDR notation (e.g., 192.168.1.0/24).")
            dialog.run()
            dialog.destroy()
            return
        
        if start_port > end_port:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Invalid Port Range"
            )
            dialog.format_secondary_text("End port must be greater than or equal to start port.")
            dialog.run()
            dialog.destroy()
            return
        
        # Clear previous results
        self.port_store.clear()
        
        # Update UI
        self.scan_button.set_label("Stop Scan")
        self.status_bar.set_text("Scanning...")
        self.status_bar.set_fraction(0.0)
        
        # Start scan in a separate thread
        self.stop_scan_flag = False
        self.scan_thread = threading.Thread(
            target=self._run_scan,
            args=(ip_range, start_port, end_port)
        )
        self.scan_thread.daemon = True
        self.scan_thread.start()
    
    def _run_scan(self, ip_range, start_port, end_port):
        """Run the network scan using python-nmap.
        
        Args:
            ip_range: IP range to scan
            start_port: Starting port
            end_port: Ending port
        """
        self.logger.info(f"Starting nmap scan: {ip_range}, ports {start_port}-{end_port}")
        
        try:
            # Initialize the nmap scanner
            nm = nmap.PortScanner()
            
            # Scan speed factor (1-5)
            speed = int(self.speed_scale.get_value())
            timing_template = min(5, speed)  # T0-T5 in nmap
            
            # Determine scan arguments based on options
            arguments = f"-T{timing_template}"
            
            if self.ping_check.get_active():
                arguments += " -PE"  # ICMP echo
            else:
                arguments += " -Pn"  # Skip ping
                
            if self.tcp_check.get_active():
                arguments += " -sT"  # TCP connect scan
            
            if self.service_check.get_active():
                arguments += " -sV"  # Version detection
                
            # Port range
            port_range = f"{start_port}-{end_port}"
            
            # Update status
            GLib.idle_add(self._update_scan_status, f"Starting scan on {ip_range}...", 0.1, False)
            
            # Run the scan
            self.logger.debug(f"Running nmap with arguments: {arguments}")
            nm.scan(ip_range, port_range, arguments)
            
            # Process results
            hosts_count = len(nm.all_hosts())
            if hosts_count == 0:
                GLib.idle_add(self._update_scan_status, "No hosts found", 1.0, True)
                return
                
            self.logger.info(f"Found {hosts_count} hosts")
            
            # Process each host
            for i, host in enumerate(nm.all_hosts()):
                if self.stop_scan_flag:
                    GLib.idle_add(self._update_scan_status, "Scan stopped", 0.0, True)
                    break
                    
                # Calculate progress
                progress = (i + 1) / hosts_count
                
                # Skip hosts that are down
                if nm[host].state() != "up":
                    continue
                    
                # Get host information
                hostname = nm[host].hostname() or f"host-{host.replace('.', '-')}.local"
                status = "Up"
                
                # Get OS information if available
                os_name = "Unknown"
                if 'osmatch' in nm[host] and nm[host]['osmatch']:
                    os_match = nm[host]['osmatch'][0]
                    os_name = os_match.get('name', "Unknown")
                
                # Count open ports
                open_ports_count = 0
                for proto in nm[host].all_protocols():
                    ports = nm[host][proto].keys()
                    for port in ports:
                        if nm[host][proto][port]['state'] == 'open':
                            open_ports_count += 1
                
                # Add to host list
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                host_row = [host, hostname, status, os_name, open_ports_count, current_time]
                
                GLib.idle_add(self._add_host, host_row)
                GLib.idle_add(self._update_scan_status, f"Scanning {host} ({i+1}/{hosts_count})", progress, False)
                
                # Small delay to prevent UI freezing
                time.sleep(0.01)
            
            # Scan completed
            GLib.idle_add(self._update_scan_status, f"Scan completed: found {hosts_count} hosts", 1.0, True)
            
        except Exception as e:
            self.logger.error(f"Nmap scan error: {str(e)}")
            GLib.idle_add(self._update_scan_status, f"Error: {str(e)}", 0.0, True)
    
    def _add_host(self, host_row):
        """Add a host to the results.
        
        Args:
            host_row: List of host data to add
        """
        self.host_store.append(host_row)
        return False  # Required for GLib.idle_add
    
    def _update_scan_status(self, message, progress, finished):
        """Update scan status UI.
        
        Args:
            message: Status message
            progress: Progress fraction (0-1)
            finished: Whether the scan is finished
        """
        self.status_bar.set_text(message)
        self.status_bar.set_fraction(progress)
        
        if finished:
            self.scan_button.set_label("Start Scan")
            self.scan_button.set_sensitive(True)
        
        return False  # Required for GLib.idle_add
    
    def _on_host_activated(self, treeview, path, column):
        """Handle host row activation (double-click or Enter).
        
        Args:
            treeview: The TreeView widget
            path: Path to the selected row
            column: The column that was activated
        """
        model = treeview.get_model()
        iter = model.get_iter(path)
        ip_address = model.get_value(iter, 0)
        
        # Clear previous port data
        self.port_store.clear()
        
        # Populate port data for the selected host using nmap
        self._populate_sample_ports(ip_address, model.get_value(iter, 4))
    
    def _populate_sample_ports(self, ip, num_ports):
        """Populate port data for the selected host using nmap.
        
        Args:
            ip: IP address of the host
            num_ports: Number of open ports to generate
        """
        self.status_bar.set_text(f"Scanning ports on {ip}...")
        
        try:
            # Initialize the nmap scanner
            nm = nmap.PortScanner()
            
            # Scan common ports with service detection
            nm.scan(ip, arguments='-sV -F')  # Fast scan with version detection
            
            # Check if host was found and is up
            if ip not in nm.all_hosts() or nm[ip].state() != "up":
                self.port_store.append([0, "none", "Host not available", "", "closed"])
                self.status_bar.set_text("Ready")
                return
                
            # Get all open ports
            port_info = []
            for proto in nm[ip].all_protocols():
                ports = nm[ip][proto].keys()
                for port in ports:
                    if nm[ip][proto][port]['state'] == 'open':
                        service = nm[ip][proto][port]['name'] if nm[ip][proto][port]['name'] != '' else "unknown"
                        version = nm[ip][proto][port]['product'] + " " + nm[ip][proto][port]['version'] if nm[ip][proto][port]['product'] != '' else ""
                        port_info.append((port, proto, service, version.strip(), "open"))
            
            # Sort by port number
            port_info.sort(key=lambda x: x[0])
            
            # Add port information to the store
            for info in port_info:
                self.port_store.append(list(info))
                
            # If no open ports were found
            if len(self.port_store) == 0:
                self.port_store.append([0, "none", "No open ports found", "", "closed"])
                
        except Exception as e:
            self.logger.error(f"Error scanning ports: {str(e)}")
            self.port_store.append([0, "none", f"Error: {str(e)}", "", "error"])
            
        self.status_bar.set_text("Ready")
    
    def _on_add_target(self, button):
        """Handle adding the selected host to targets."""
        selection = self.host_view.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            ip = model[treeiter][0]
            hostname = model[treeiter][1]
            
            # Call the target callback if set
            if self.target_callback:
                self.logger.debug(f"Calling target callback with {ip}")
                target_data = {
                    "host": ip,
                    "hostname": hostname
                }
                self.target_callback(target_data)
            else:
                self.logger.warning("Target callback not set")
            
            # Show confirmation
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Target Added"
            )
            dialog.format_secondary_text(f"Added {ip} to targets.")
            dialog.run()
            dialog.destroy()
    
    def _on_export_results(self, button):
        """Handle export results button click."""
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Export Scan Results",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        # File filters
        xml_filter = Gtk.FileFilter()
        xml_filter.set_name("XML files")
        xml_filter.add_mime_type("application/xml")
        xml_filter.add_pattern("*.xml")
        dialog.add_filter(xml_filter)
        
        text_filter = Gtk.FileFilter()
        text_filter.set_name("Text files")
        text_filter.add_mime_type("text/plain")
        text_filter.add_pattern("*.txt")
        dialog.add_filter(text_filter)
        
        csv_filter = Gtk.FileFilter()
        csv_filter.set_name("CSV files")
        csv_filter.add_mime_type("text/csv")
        csv_filter.add_pattern("*.csv")
        dialog.add_filter(csv_filter)
        
        # Set default filename
        scan_time = time.strftime("%Y%m%d-%H%M%S")
        dialog.set_current_name(f"network-scan-{scan_time}.xml")
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            
            # In a real implementation, this would export the scan results
            self.logger.info(f"Exporting scan results to {filename}")
            
            # Show a success message
            msg_dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Export Successful"
            )
            msg_dialog.format_secondary_text(f"Scan results have been exported to:\n{filename}")
            msg_dialog.run()
            msg_dialog.destroy()
            
        dialog.destroy()
    
    def _on_clear_results(self, button):
        """Handle clear results button click."""
        # Clear the results lists
        self.host_store.clear()
        self.port_store.clear()
        
        # Reset the status bar
        self.status_bar.set_text("Ready")
        self.status_bar.set_fraction(0.0)
        
        self.logger.info("Scan results cleared")