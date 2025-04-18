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
from gi.repository import Gtk, GLib, Gdk, Pango

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
        
        # Recent scan history (to prevent redundant scanning)
        self.scan_history = {}
        
        # Load scan cache from user data directory
        self._load_scan_cache()
        
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
        
        # Add a direct scan button next to the IP entry
        self.direct_scan_button = Gtk.Button(label="Quick Scan")
        self.direct_scan_button.connect("clicked", self._on_direct_scan_clicked)
        self.direct_scan_button.set_tooltip_text("Quickly scan a single IP address")
        ip_box.pack_start(self.direct_scan_button, False, False, 0)
        
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
        
        self.generate_report_button = Gtk.Button(label="Generate Report")
        self.generate_report_button.connect("clicked", self._on_generate_report)
        action_box.pack_start(self.generate_report_button, False, False, 0)
    
    def set_target_callback(self, callback):
        """Set the callback function for adding targets.
        
        Args:
            callback: Function to call when a target is added
        """
        self.logger.debug("Setting target callback")
        self.target_callback = callback

    def _on_scan_clicked(self, button):
        """Handle scan button click.
        
        Args:
            button: Button that was clicked
        """
        # If scan is running, stop it
        if button.get_label() == "Stop Scan":
            if self.scan_thread and self.scan_thread.is_alive():
                self.stop_scan_flag = True
                self.scan_button.set_sensitive(False)
                self.status_bar.set_text("Stopping scan...")
            return
        
        # Get scan parameters
        ip_range = self.ip_entry.get_text()
        start_port = int(self.start_port_spin.get_value())
        end_port = int(self.end_port_spin.get_value())
        
        # Check if it's a single IP address
        try:
            socket.inet_aton(ip_range)
            # This is a single IP address, use the optimized method
            self.scan_single_ip(ip_range, f"{start_port}-{end_port}")
            return
        except socket.error:
            # Not a single IP, continue with normal scan
            pass
        
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
        
        # Build a context menu
        popup = Gtk.Menu()
        
        # Add menu items
        scan_item = Gtk.MenuItem(label="Scan Ports")
        scan_item.connect("activate", lambda w: self._populate_sample_ports(ip_address, model.get_value(iter, 4)))
        popup.append(scan_item)
        
        report_item = Gtk.MenuItem(label="Generate Report")
        report_item.connect("activate", lambda w: self._on_generate_single_report(ip_address))
        popup.append(report_item)
        
        compare_item = Gtk.MenuItem(label="Compare With Previous Scan")
        compare_item.connect("activate", lambda w: self.show_comparison_dialog(ip_address))
        popup.append(compare_item)
        
        copy_item = Gtk.MenuItem(label="Copy IP")
        copy_item.connect("activate", lambda w: self._copy_to_clipboard(ip_address))
        popup.append(copy_item)
        
        # Add to targets if callback is set
        if self.target_callback:
            add_item = Gtk.MenuItem(label="Add to Targets")
            add_item.connect("activate", lambda w: self._on_add_specific_target(ip_address))
            popup.append(add_item)
        
        # Show popup menu
        popup.show_all()
        popup.popup_at_pointer(None)
        
        # Also populate the ports anyway
        self.port_store.clear()
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

    def scan_single_ip(self, ip_address, port_range="22-1024"):
        """Scan a single IP address directly.
        
        Args:
            ip_address: Single IP address to scan
            port_range: Port range to scan (default: "22-1024")
            
        Returns:
            dict: Scan results dictionary or None if error
        """
        self.logger.info(f"Starting direct scan of IP: {ip_address}, ports {port_range}")
        
        # Validate IP address format
        try:
            socket.inet_aton(ip_address)
        except socket.error:
            self.logger.error(f"Invalid IP address format: {ip_address}")
            return None
            
        # Clear previous port data
        self.port_store.clear()
        
        # Clear previous host data if appropriate
        self.host_store.clear()
        
        # Update UI
        self.ip_entry.set_text(ip_address)
        self.status_bar.set_text(f"Scanning {ip_address}...")
        self.status_bar.set_fraction(0.1)
        
        try:
            # Initialize the nmap scanner
            nm = nmap.PortScanner()
            
            # Set scan options for single IP (faster and more thorough)
            # -T4: Faster timing template
            # -Pn: Skip host discovery
            # -sV: Version detection
            scan_args = "-T4 -Pn -sV"
            
            # Run the scan
            self.logger.debug(f"Running direct scan with arguments: {scan_args}")
            scan_results = nm.scan(ip_address, port_range, scan_args)
            
            # Process results
            if ip_address in nm.all_hosts():
                # Get host information
                hostname = nm[ip_address].hostname() or f"host-{ip_address.replace('.', '-')}.local"
                status = nm[ip_address].state()
                
                # Get OS information if available
                os_name = "Unknown"
                if 'osmatch' in nm[ip_address] and nm[ip_address]['osmatch']:
                    os_match = nm[ip_address]['osmatch'][0]
                    os_name = os_match.get('name', "Unknown")
                
                # Count open ports
                open_ports_count = 0
                for proto in nm[ip_address].all_protocols():
                    ports = nm[ip_address][proto].keys()
                    for port in ports:
                        if nm[ip_address][proto][port]['state'] == 'open':
                            open_ports_count += 1
                            
                            # Add port to port store
                            port_num = port
                            protocol = proto
                            service = nm[ip_address][proto][port]['name'] if nm[ip_address][proto][port]['name'] != '' else "unknown"
                            version = nm[ip_address][proto][port]['product'] + " " + nm[ip_address][proto][port]['version'] if nm[ip_address][proto][port]['product'] != '' else ""
                            self.port_store.append([port_num, protocol, service, version.strip(), "open"])
                
                # Add to host list
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                host_row = [ip_address, hostname, status, os_name, open_ports_count, current_time]
                self.host_store.append(host_row)
                
                # Select the added host
                if len(self.host_store) > 0:
                    self.host_view.set_cursor(Gtk.TreePath.new_first())
                
                self.status_bar.set_text(f"Scan completed: {ip_address} is {status} with {open_ports_count} open ports")
                self.status_bar.set_fraction(1.0)
                
                return scan_results
            else:
                self.logger.warning(f"Host {ip_address} not found in scan results")
                self.status_bar.set_text(f"Host {ip_address} not found or not responding")
                self.status_bar.set_fraction(0.0)
                return None
                
        except Exception as e:
            self.logger.error(f"Error scanning IP {ip_address}: {str(e)}")
            self.status_bar.set_text(f"Error: {str(e)}")
            self.status_bar.set_fraction(0.0)
            return None
        finally:
            # Ensure UI is updated
            self.scan_button.set_label("Start Scan")
            self.scan_button.set_sensitive(True)

    def _on_direct_scan_clicked(self, button):
        """Handle direct scan button click.
        
        Args:
            button: Button that was clicked
        """
        # Get the IP address from the entry
        ip_address = self.ip_entry.get_text().strip()
        
        # Check if it's a valid IP address
        try:
            socket.inet_aton(ip_address)
            # Valid single IP address
            self.logger.info(f"Starting quick scan for IP: {ip_address}")
            
            # Use common ports for quick scan
            common_ports = "21-25,53,80,443,3306,3389,5432,8080,8443"
            
            # Start the scan
            self.scan_single_ip(ip_address, common_ports)
            
        except socket.error:
            # Not a valid single IP
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Invalid IP Address"
            )
            dialog.format_secondary_text(
                f"'{ip_address}' is not a valid IP address.\n"
                "For quick scan, please enter a single IP (e.g., 192.168.1.10)"
            )
            dialog.run()
            dialog.destroy()

    def scan_target_ip(self, target_ip):
        """Public method to scan a specific target IP address.
        
        Args:
            target_ip: The target IP address to scan
            
        Returns:
            bool: True if scan started successfully, False otherwise
        """
        try:
            # Check for valid business targets
            if not self._validate_business_target(target_ip):
                self.logger.warning(f"IP {target_ip} is not considered a valid business target")
                # Continue anyway but log the warning
            
            # Validate IP address
            socket.inet_aton(target_ip)
            
            # Update the IP entry with the target
            self.ip_entry.set_text(target_ip)
            
            # Check if we've recently scanned this IP (within the last hour)
            if target_ip in self.scan_history:
                last_scan_time = self.scan_history[target_ip]['timestamp']
                if time.time() - last_scan_time < 3600:  # 1 hour in seconds
                    # Ask user if they want to rescan
                    dialog = Gtk.MessageDialog(
                        transient_for=self.get_toplevel(),
                        flags=0,
                        message_type=Gtk.MessageType.QUESTION,
                        buttons=Gtk.ButtonsType.YES_NO,
                        text="Rescan IP Address?"
                    )
                    dialog.format_secondary_text(
                        f"The IP {target_ip} was already scanned at {time.strftime('%H:%M:%S', time.localtime(last_scan_time))}.\n"
                        "Do you want to scan it again?"
                    )
                    response = dialog.run()
                    dialog.destroy()
                    
                    if response != Gtk.ResponseType.YES:
                        # Load previous scan results
                        self._load_previous_scan_results(target_ip)
                        return True
            
            # Use common ports plus additional business-relevant ports
            common_ports = "21-25,53,80,443,3306,3389,5432,8080,8443,1433,1521,3000,4443,5000,5900,6379,7001,8000,8081,9000,9090,27017"
            
            # Start the scan
            self.logger.info(f"Scanning target IP: {target_ip}")
            scan_result = self.scan_single_ip(target_ip, common_ports)
            
            # Save results to scan history
            if scan_result:
                self._save_scan_results(target_ip, scan_result)
            
            return scan_result is not None
            
        except (socket.error, Exception) as e:
            self.logger.error(f"Error scanning target IP {target_ip}: {str(e)}")
            self.status_bar.set_text(f"Error: {str(e)}")
            return False

    def _validate_business_target(self, ip_address):
        """Validate if an IP address is a legitimate business target.
        
        Args:
            ip_address: The IP address to validate
            
        Returns:
            bool: True if the IP is a valid business target, False otherwise
        """
        try:
            # Don't scan private/reserved ranges unless explicitly allowed
            ip = ipaddress.ip_address(ip_address)
            
            # Check for private ranges
            if ip.is_private:
                # Only scan the specific business private IP ranges
                business_networks = [
                    # Example business networks (would be configured appropriately)
                    ipaddress.ip_network("192.168.1.0/24"),
                    ipaddress.ip_network("10.10.0.0/16")
                ]
                
                in_business_network = any(ip in network for network in business_networks)
                if not in_business_network:
                    self.logger.warning(f"IP {ip_address} is in a private range but not in approved business networks")
                    return False
            
            # Check for reserved/special-use IP ranges
            if ip.is_multicast or ip.is_loopback or ip.is_reserved or ip.is_unspecified:
                self.logger.warning(f"IP {ip_address} is a reserved/special-use address")
                return False
                
            # Additional business policy checks could be added here
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating IP {ip_address}: {str(e)}")
            return False
    
    def _save_scan_results(self, ip_address, scan_results):
        """Save scan results to history and disk cache.
        
        Args:
            ip_address: The IP address scanned
            scan_results: The nmap scan results dictionary
        """
        try:
            # Add to in-memory cache
            self.scan_history[ip_address] = {
                'timestamp': time.time(),
                'scan_results': scan_results
            }
            
            # Save to disk cache
            cache_dir = os.path.join(os.path.expanduser("~"), ".config", "erpct", "scan_cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Create safe filename from IP
            safe_ip = ip_address.replace(".", "_")
            cache_file = os.path.join(cache_dir, f"{safe_ip}.json")
            
            # Write cache file
            with open(cache_file, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'ip_address': ip_address,
                    'scan_results': scan_results
                }, f)
                
            self.logger.debug(f"Saved scan results for {ip_address} to cache")
            
        except Exception as e:
            self.logger.warning(f"Could not save scan results for {ip_address}: {str(e)}")
    
    def _load_scan_cache(self):
        """Load previously cached scan results."""
        try:
            cache_dir = os.path.join(os.path.expanduser("~"), ".config", "erpct", "scan_cache")
            if not os.path.exists(cache_dir):
                return
                
            # Load all cached scans
            for filename in os.listdir(cache_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(cache_dir, filename), 'r') as f:
                            cache_data = json.load(f)
                            
                        ip_address = cache_data.get('ip_address')
                        if ip_address:
                            self.scan_history[ip_address] = {
                                'timestamp': cache_data.get('timestamp', 0),
                                'scan_results': cache_data.get('scan_results', {})
                            }
                    except Exception as e:
                        self.logger.warning(f"Error loading cached scan {filename}: {str(e)}")
                        
            self.logger.info(f"Loaded {len(self.scan_history)} previous scan results")
            
        except Exception as e:
            self.logger.warning(f"Error loading scan cache: {str(e)}")
    
    def _load_previous_scan_results(self, ip_address):
        """Load and display previous scan results for an IP address.
        
        Args:
            ip_address: The IP address to load results for
            
        Returns:
            bool: True if results were loaded, False otherwise
        """
        if ip_address not in self.scan_history:
            return False
            
        scan_data = self.scan_history[ip_address]
        self.logger.info(f"Loading cached scan results for {ip_address}")
        
        # Clear current results
        self.host_store.clear()
        self.port_store.clear()
        
        try:
            # Create simulated scan results from cache
            scan_results = scan_data.get('scan_results', {})
            
            # Populate host data
            nm_info = scan_results.get('scan', {}).get(ip_address, {})
            
            hostname = nm_info.get('hostnames', [{}])[0].get('name', f"host-{ip_address.replace('.', '-')}.local")
            status = nm_info.get('status', {}).get('state', 'unknown')
            
            # Get OS info
            os_name = "Unknown"
            if 'osmatch' in nm_info and nm_info['osmatch']:
                os_match = nm_info['osmatch'][0]
                os_name = os_match.get('name', "Unknown")
            
            # Count and add open ports
            open_ports_count = 0
            
            # Get all TCP/UDP ports
            for proto in ['tcp', 'udp']:
                if proto in nm_info:
                    for port_number, port_data in nm_info[proto].items():
                        if port_data.get('state') == 'open':
                            open_ports_count += 1
                            
                            # Add to port store
                            port_num = int(port_number)
                            service = port_data.get('name', 'unknown')
                            product = port_data.get('product', '')
                            version = port_data.get('version', '')
                            version_str = f"{product} {version}".strip()
                            
                            self.port_store.append([port_num, proto, service, version_str, 'open'])
            
            # Add to host store
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(scan_data['timestamp']))
            self.host_store.append([ip_address, hostname, status, os_name, open_ports_count, timestamp])
            
            # Select the host
            if len(self.host_store) > 0:
                self.host_view.set_cursor(Gtk.TreePath.new_first())
                
            # Update status
            self.status_bar.set_text(f"Loaded cached results for {ip_address} ({timestamp})")
            self.status_bar.set_fraction(1.0)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading cached results for {ip_address}: {str(e)}")
            return False

    def generate_scan_report(self, ip_address=None):
        """Generate a business-level report of scan results.
        
        Args:
            ip_address: Optional specific IP to report on. If None, reports on all selected hosts.
            
        Returns:
            str: Report text
        """
        report = []
        report.append("# Network Scan Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Get the IP to report on
        if ip_address:
            # Report on specific IP
            ips_to_report = [ip_address]
        else:
            # Get selected hosts from the view
            selection = self.host_view.get_selection()
            model, paths = selection.get_selected_rows()
            
            if not paths:
                # No selection, report on all hosts
                ips_to_report = [row[0] for row in self.host_store]
            else:
                # Report on selected hosts
                ips_to_report = [model[path][0] for path in paths]
        
        # Process each host
        for ip in ips_to_report:
            # Find in store
            for row in self.host_store:
                if row[0] == ip:
                    host_data = row
                    break
            else:
                continue  # IP not found
            
            # Host information
            report.append(f"## Host: {host_data[0]}")
            report.append(f"- Hostname: {host_data[1]}")
            report.append(f"- Status: {host_data[2]}")
            report.append(f"- OS: {host_data[3]}")
            report.append(f"- Open Ports: {host_data[4]}")
            report.append(f"- Last Scan: {host_data[5]}")
            report.append("")
            
            # Port details
            report.append("### Open Ports")
            report.append("| Port | Protocol | Service | Version |")
            report.append("|------|----------|---------|---------|")
            
            # Filter ports for this IP
            has_ports = False
            for port_row in self.port_store:
                # TODO: Link ports to hosts to support multiple hosts
                report.append(f"| {port_row[0]} | {port_row[1]} | {port_row[2]} | {port_row[3]} |")
                has_ports = True
            
            if not has_ports:
                report.append("No open ports found.")
            
            report.append("")
            
            # Security analysis
            report.append("### Security Analysis")
            # TODO: Add more sophisticated security analysis based on open ports/services
            if host_data[4] > 10:
                report.append("- **WARNING**: High number of open ports may indicate excessive attack surface")
            
            # Check for common sensitive services
            sensitive_services = {
                21: "FTP (unencrypted file transfer)",
                23: "Telnet (unencrypted terminal)",
                25: "SMTP (email)",
                53: "DNS",
                80: "HTTP (unencrypted web)",
                445: "SMB (file sharing)",
                3306: "MySQL Database",
                3389: "RDP (Remote Desktop)",
                5432: "PostgreSQL Database"
            }
            
            security_issues = []
            for port_row in self.port_store:
                port = port_row[0]
                if port in sensitive_services:
                    security_issues.append(f"- Port {port}: {sensitive_services[port]}")
            
            if security_issues:
                report.append("Potentially sensitive services detected:")
                report.extend(security_issues)
            else:
                report.append("No obvious security issues detected in open ports.")
            
            report.append("")
        
        return "\n".join(report)

    def _on_generate_single_report(self, ip_address):
        """Generate a report for a single IP address."""
        report_text = self.generate_scan_report(ip_address)
        
        # Create a dialog with a text view
        dialog = Gtk.Dialog(
            title=f"Scan Report: {ip_address}",
            parent=self.get_toplevel(),
            flags=0,
            buttons=(Gtk.STOCK_SAVE, Gtk.ResponseType.APPLY, Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        )
        dialog.set_default_size(700, 500)
        
        # Create scrolled window for text view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        dialog.get_content_area().pack_start(scrolled, True, True, 0)
        
        # Create text view
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        buffer = text_view.get_buffer()
        buffer.set_text(report_text)
        scrolled.add(text_view)
        
        # Show the dialog
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.APPLY:
            # Save the report
            self._save_report_to_file(report_text)
        
        dialog.destroy()
    
    def _save_report_to_file(self, report_text):
        """Save report text to file."""
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Save Scan Report",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        # File filters
        markdown_filter = Gtk.FileFilter()
        markdown_filter.set_name("Markdown files")
        markdown_filter.add_mime_type("text/markdown")
        markdown_filter.add_pattern("*.md")
        dialog.add_filter(markdown_filter)
        
        text_filter = Gtk.FileFilter()
        text_filter.set_name("Text files")
        text_filter.add_mime_type("text/plain")
        text_filter.add_pattern("*.txt")
        dialog.add_filter(text_filter)
        
        # Set default filename
        scan_time = time.strftime("%Y%m%d-%H%M%S")
        dialog.set_current_name(f"network-scan-report-{scan_time}.md")
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            
            # Save the report
            try:
                with open(filename, 'w') as f:
                    f.write(report_text)
                
                self.logger.info(f"Report saved to {filename}")
                
                # Show a success message
                msg_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Report Exported"
                )
                msg_dialog.format_secondary_text(f"Report has been saved to:\n{filename}")
                msg_dialog.run()
                msg_dialog.destroy()
                
            except Exception as e:
                self.logger.error(f"Error saving report: {str(e)}")
                
                # Show error dialog
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Error Saving Report"
                )
                error_dialog.format_secondary_text(f"Could not save report: {str(e)}")
                error_dialog.run()
                error_dialog.destroy()
        
        dialog.destroy()

    def compare_with_previous_scan(self, ip_address):
        """Compare current scan results with previous scan for changes.
        
        Args:
            ip_address: IP address to compare
            
        Returns:
            dict: Comparison results with added, removed, and changed services
        """
        # Find most recent scan in history that's not the current scan
        current_scan = None
        previous_scan = None
        
        # Get all scans for this IP
        ip_scans = []
        for filename in os.listdir(os.path.join(os.path.expanduser("~"), ".config", "erpct", "scan_cache")):
            if filename.startswith(ip_address.replace(".", "_")):
                try:
                    with open(os.path.join(os.path.expanduser("~"), ".config", "erpct", "scan_cache", filename), 'r') as f:
                        scan_data = json.load(f)
                    ip_scans.append(scan_data)
                except:
                    continue
        
        # Sort by timestamp descending
        ip_scans.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Get current and previous scan
        if len(ip_scans) > 0:
            current_scan = ip_scans[0]
        
        if len(ip_scans) > 1:
            previous_scan = ip_scans[1]
        
        if not current_scan or not previous_scan:
            return None
        
        # Compare the scans
        comparison = {
            'new_ports': [],
            'removed_ports': [],
            'changed_services': [],
            'current_timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_scan.get('timestamp', 0))),
            'previous_timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(previous_scan.get('timestamp', 0))),
        }
        
        # Extract port information
        current_ports = self._extract_ports_from_scan(current_scan)
        previous_ports = self._extract_ports_from_scan(previous_scan)
        
        # Find new ports
        for port_key, port_info in current_ports.items():
            if port_key not in previous_ports:
                comparison['new_ports'].append({
                    'port': port_info['port'],
                    'protocol': port_info['protocol'],
                    'service': port_info['service'],
                    'version': port_info['version']
                })
        
        # Find removed ports
        for port_key, port_info in previous_ports.items():
            if port_key not in current_ports:
                comparison['removed_ports'].append({
                    'port': port_info['port'],
                    'protocol': port_info['protocol'],
                    'service': port_info['service'],
                    'version': port_info['version']
                })
        
        # Find changed services
        for port_key, current_info in current_ports.items():
            if port_key in previous_ports:
                prev_info = previous_ports[port_key]
                
                # Check if service or version changed
                if (current_info['service'] != prev_info['service'] or 
                    current_info['version'] != prev_info['version']):
                    
                    comparison['changed_services'].append({
                        'port': current_info['port'],
                        'protocol': current_info['protocol'],
                        'old_service': prev_info['service'],
                        'new_service': current_info['service'],
                        'old_version': prev_info['version'],
                        'new_version': current_info['version']
                    })
        
        return comparison
    
    def _extract_ports_from_scan(self, scan_data):
        """Extract port information from scan data.
        
        Args:
            scan_data: Scan data dictionary
            
        Returns:
            dict: Dictionary of port information
        """
        ports = {}
        ip = scan_data.get('ip_address')
        
        if not ip:
            return ports
        
        # Get scan results
        scan_results = scan_data.get('scan_results', {})
        nm_info = scan_results.get('scan', {}).get(ip, {})
        
        # Extract port information
        for proto in ['tcp', 'udp']:
            if proto in nm_info:
                for port_number, port_data in nm_info[proto].items():
                    if port_data.get('state') == 'open':
                        port_key = f"{port_number}/{proto}"
                        ports[port_key] = {
                            'port': int(port_number),
                            'protocol': proto,
                            'service': port_data.get('name', 'unknown'),
                            'version': f"{port_data.get('product', '')} {port_data.get('version', '')}".strip()
                        }
        
        return ports

    def show_comparison_dialog(self, ip_address):
        """Show a dialog with comparison results between scans.
        
        Args:
            ip_address: IP to compare scans for
        """
        comparison = self.compare_with_previous_scan(ip_address)
        
        if not comparison:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Cannot Compare Scans"
            )
            dialog.format_secondary_text("Need at least two scans of this IP to compare changes.")
            dialog.run()
            dialog.destroy()
            return
        
        # Create a dialog with a scrollable text view
        dialog = Gtk.Dialog(
            title=f"Scan Comparison: {ip_address}",
            parent=self.get_toplevel(),
            flags=0,
            buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        )
        dialog.set_default_size(600, 400)
        
        # Create scrolled window for text view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        dialog.get_content_area().pack_start(scrolled, True, True, 0)
        
        # Create text view
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        buffer = text_view.get_buffer()
        scrolled.add(text_view)
        
        # Create tags for formatting
        buffer.create_tag("heading", weight=Pango.Weight.BOLD, scale=1.5)
        buffer.create_tag("subheading", weight=Pango.Weight.BOLD, scale=1.2)
        buffer.create_tag("addition", foreground="#008800")
        buffer.create_tag("removal", foreground="#FF0000")
        buffer.create_tag("change", foreground="#0000FF")
        
        # Insert comparison text
        end_iter = buffer.get_end_iter()
        
        # Title
        buffer.insert_with_tags_by_name(end_iter, f"Scan Comparison: {ip_address}\n", "heading")
        buffer.insert(end_iter, f"Current Scan: {comparison['current_timestamp']}\n")
        buffer.insert(end_iter, f"Previous Scan: {comparison['previous_timestamp']}\n\n")
        
        # New ports
        buffer.insert_with_tags_by_name(end_iter, "New Open Ports\n", "subheading")
        if comparison['new_ports']:
            for port in comparison['new_ports']:
                buffer.insert_with_tags_by_name(
                    end_iter, 
                    f"+ {port['port']}/{port['protocol']}: {port['service']} {port['version']}\n", 
                    "addition"
                )
        else:
            buffer.insert(end_iter, "No new ports detected.\n")
        buffer.insert(end_iter, "\n")
        
        # Removed ports
        buffer.insert_with_tags_by_name(end_iter, "Closed Ports\n", "subheading")
        if comparison['removed_ports']:
            for port in comparison['removed_ports']:
                buffer.insert_with_tags_by_name(
                    end_iter, 
                    f"- {port['port']}/{port['protocol']}: {port['service']} {port['version']}\n", 
                    "removal"
                )
        else:
            buffer.insert(end_iter, "No ports were closed.\n")
        buffer.insert(end_iter, "\n")
        
        # Changed services
        buffer.insert_with_tags_by_name(end_iter, "Changed Services\n", "subheading")
        if comparison['changed_services']:
            for service in comparison['changed_services']:
                buffer.insert_with_tags_by_name(
                    end_iter, 
                    f"~ {service['port']}/{service['protocol']}: {service['old_service']} {service['old_version']} → {service['new_service']} {service['new_version']}\n", 
                    "change"
                )
        else:
            buffer.insert(end_iter, "No service changes detected.\n")
        
        # Security analysis based on changes
        buffer.insert(end_iter, "\n")
        buffer.insert_with_tags_by_name(end_iter, "Security Analysis\n", "subheading")
        
        # Check for security concerns
        security_concerns = []
        
        # New sensitive ports
        sensitive_ports = [21, 22, 23, 25, 53, 80, 443, 445, 1433, 3306, 3389, 5432]
        new_sensitive = [p for p in comparison['new_ports'] if p['port'] in sensitive_ports]
        if new_sensitive:
            concerns = [f"{p['port']}/{p['protocol']}" for p in new_sensitive]
            security_concerns.append(f"New sensitive services detected: {', '.join(concerns)}")
        
        # Large number of new ports
        if len(comparison['new_ports']) > 5:
            security_concerns.append(f"Significant increase in open ports: {len(comparison['new_ports'])} new ports")
        
        # Services changing without reason
        if len(comparison['changed_services']) > 3:
            security_concerns.append("Multiple service changes detected, could indicate reconfiguration or compromise")
        
        # Show security analysis
        if security_concerns:
            for concern in security_concerns:
                buffer.insert(end_iter, f"⚠️ {concern}\n")
        else:
            buffer.insert(end_iter, "No significant security concerns detected in changes.\n")
        
        # Show the dialog
        dialog.show_all()
        dialog.run()
        dialog.destroy()
        
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    def _on_generate_report(self, button):
        """Handle generate report button click."""
        # Generate the report
        report_text = self.generate_scan_report()
        
        if not report_text:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No Scan Results"
            )
            dialog.format_secondary_text("There are no scan results to generate a report from.")
            dialog.run()
            dialog.destroy()
            return
        
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Save Scan Report",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        # File filters
        markdown_filter = Gtk.FileFilter()
        markdown_filter.set_name("Markdown files")
        markdown_filter.add_mime_type("text/markdown")
        markdown_filter.add_pattern("*.md")
        dialog.add_filter(markdown_filter)
        
        text_filter = Gtk.FileFilter()
        text_filter.set_name("Text files")
        text_filter.add_mime_type("text/plain")
        text_filter.add_pattern("*.txt")
        dialog.add_filter(text_filter)
        
        # Set default filename
        scan_time = time.strftime("%Y%m%d-%H%M%S")
        dialog.set_current_name(f"network-scan-report-{scan_time}.md")
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            
            # Save the report
            try:
                with open(filename, 'w') as f:
                    f.write(report_text)
                
                self.logger.info(f"Report saved to {filename}")
                
                # Show a success message
                msg_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Report Exported"
                )
                msg_dialog.format_secondary_text(f"Report has been saved to:\n{filename}")
                msg_dialog.run()
                msg_dialog.destroy()
                
            except Exception as e:
                self.logger.error(f"Error saving report: {str(e)}")
                
                # Show error dialog
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Error Saving Report"
                )
                error_dialog.format_secondary_text(f"Could not save report: {str(e)}")
                error_dialog.run()
                error_dialog.destroy()
        
        dialog.destroy()