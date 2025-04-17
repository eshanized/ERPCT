#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Network Scanner.
This module provides a GUI for scanning and discovering network targets.
"""

import gi
import random
import threading
import time
import ipaddress

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from src.utils.logging import get_logger


class NetworkScanner(Gtk.Box):
    """Network scanner widget."""
    
    def __init__(self):
        """Initialize the network scanner widget."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        self.scan_thread = None
        self.stop_scan_flag = False
        
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
        """Run the network scan.
        
        Args:
            ip_range: IP range to scan
            start_port: Starting port
            end_port: Ending port
        """
        self.logger.info(f"Starting scan: {ip_range}, ports {start_port}-{end_port}")
        
        # In a real implementation, this would use proper network scanning libraries
        # This is just a simulation for the UI
        
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            total_ips = network.num_addresses
            total_ports = end_port - start_port + 1
            
            # Total work units
            total_work = total_ips
            
            # For simulation purposes, we'll limit the number of hosts to display
            max_hosts = min(total_ips, 10)
            
            # Track progress
            current_work = 0
            
            # Scan speed factor (1-5)
            speed = self.speed_scale.get_value()
            delay = 6 - speed  # Higher speed means less delay
            
            # Sample services for common ports
            common_services = {
                21: ("FTP", "vsftpd 2.3.4"),
                22: ("SSH", "OpenSSH 7.4"),
                23: ("Telnet", "Linux telnetd"),
                25: ("SMTP", "Postfix 9.6.5"),
                53: ("DNS", "BIND 9.11.4"),
                80: ("HTTP", "Apache 2.4.6"),
                110: ("POP3", "Dovecot"),
                143: ("IMAP", "Courier IMAP 4.17.1"),
                443: ("HTTPS", "Apache 2.4.6 + OpenSSL"),
                3306: ("MySQL", "MySQL 5.7.32"),
                3389: ("RDP", "Xrdp 0.9.9"),
                8080: ("HTTP-Proxy", "Squid 3.5.20"),
            }
            
            # Sample operating systems
            os_options = [
                "Linux 5.4.0",
                "Windows Server 2019",
                "FreeBSD 13.0",
                "Cisco IOS 15.2",
                "VMware ESXi 7.0",
                "Ubuntu 20.04 LTS",
                "CentOS 8.3"
            ]
            
            # Scan each IP in the network
            host_count = 0
            for i, ip in enumerate(network):
                if self.stop_scan_flag:
                    GLib.idle_add(self._update_scan_status, "Scan stopped", 0.0, True)
                    break
                
                current_work = i + 1
                progress = current_work / total_work
                
                # For simulation, only add some random hosts as "up"
                if host_count < max_hosts and random.random() < 0.7:
                    # This IP is "up"
                    ip_str = str(ip)
                    hostname = f"host-{ip_str.replace('.', '-')}.local"
                    status = "Up"
                    os_name = random.choice(os_options)
                    
                    # Determine number of open ports (for sample data)
                    num_open_ports = random.randint(1, 8)
                    
                    # Add to host list
                    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    host_row = [ip_str, hostname, status, os_name, num_open_ports, current_time]
                    
                    GLib.idle_add(self._add_host, host_row)
                    host_count += 1
                    
                    # Simulate port scanning delay
                    time.sleep(delay / 10)
                
                # Update status
                status_msg = f"Scanning {ip} ({current_work}/{total_work})"
                GLib.idle_add(self._update_scan_status, status_msg, progress, False)
                
                # Small delay for simulation
                time.sleep(delay / 50)
            
            # Scan completed
            GLib.idle_add(self._update_scan_status, f"Scan completed: found {host_count} hosts", 1.0, True)
            
        except Exception as e:
            self.logger.error(f"Scan error: {str(e)}")
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
        
        # In a real implementation, this would load actual port data
        # For now, generate sample port data
        num_ports = model.get_value(iter, 4)
        self._populate_sample_ports(ip_address, num_ports)
    
    def _populate_sample_ports(self, ip, num_ports):
        """Populate sample port data for the selected host.
        
        Args:
            ip: IP address of the host
            num_ports: Number of open ports to generate
        """
        # Common services for sample data
        common_ports = {
            21: ("tcp", "FTP", "vsftpd 2.3.4"),
            22: ("tcp", "SSH", "OpenSSH 7.4"),
            23: ("tcp", "Telnet", "Linux telnetd"),
            25: ("tcp", "SMTP", "Postfix 9.6.5"),
            53: ("udp", "DNS", "BIND 9.11.4"),
            80: ("tcp", "HTTP", "Apache 2.4.6"),
            110: ("tcp", "POP3", "Dovecot"),
            143: ("tcp", "IMAP", "Courier IMAP 4.17.1"),
            443: ("tcp", "HTTPS", "Apache 2.4.6 + OpenSSL"),
            3306: ("tcp", "MySQL", "MySQL 5.7.32"),
            3389: ("tcp", "RDP", "Xrdp 0.9.9"),
            8080: ("tcp", "HTTP-Proxy", "Squid 3.5.20"),
        }
        
        # Pick random ports from the common list
        common_port_numbers = list(common_ports.keys())
        
        # If we need more ports than in our common list, add some random high ports
        all_ports = common_port_numbers.copy()
        for _ in range(max(0, num_ports - len(common_port_numbers))):
            all_ports.append(random.randint(1025, 49151))
        
        # Randomly select the required number of ports
        selected_ports = random.sample(all_ports, min(num_ports, len(all_ports)))
        
        # Add port data to the store
        for port in selected_ports:
            if port in common_ports:
                protocol, service, version = common_ports[port]
            else:
                protocol = "tcp" if random.random() < 0.8 else "udp"
                service = "unknown"
                version = ""
            
            status = "open"
            self.port_store.append([port, protocol, service, version, status])
    
    def _on_add_target(self, button):
        """Handle add to targets button click."""
        selection = self.host_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            ip = model.get_value(iter, 0)
            hostname = model.get_value(iter, 1)
            
            # In a real implementation, this would add the host to the target list
            self.logger.info(f"Adding target: {ip} ({hostname})")
            
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Target Added"
            )
            dialog.format_secondary_text(f"Added {ip} ({hostname}) to the target list.")
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