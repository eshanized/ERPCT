#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Results Explorer component.
This module provides the GUI panel for viewing and analyzing attack results.
"""

import os
import json
import time
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango

from src.utils.logging import get_logger


class ResultsExplorer(Gtk.Box):
    """Results explorer panel."""
    
    def __init__(self):
        """Initialize the results explorer panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Default results directory
        self.results_dir = os.path.join(os.path.expanduser("~"), ".erpct", "results")
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Initialize results dictionary
        self.results = {}
        
        # Create UI components
        self._create_results_browser()
        self._create_results_details()
        self._create_action_buttons()
        
        # Refresh the results list
        self.refresh_results()
    
    def _create_results_browser(self):
        """Create results browser section."""
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(paned, True, True, 0)
        
        # Results list on the left
        frame = Gtk.Frame(label="Results")
        frame.set_size_request(300, -1)
        paned.pack1(frame, True, False)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Scrollable results list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(300)
        
        # Results store and view
        self.results_store = Gtk.ListStore(str, str, str, int, str)  # ID, Name, Date, Success Count, Path
        self.results_view = Gtk.TreeView(model=self.results_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        column.set_resizable(True)
        column.set_min_width(150)
        self.results_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Date", renderer, text=2)
        column.set_resizable(True)
        column.set_min_width(150)
        self.results_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Success", renderer, text=3)
        column.set_resizable(True)
        column.set_min_width(80)
        self.results_view.append_column(column)
        
        scrolled.add(self.results_view)
        box.pack_start(scrolled, True, True, 0)
        
        # Selection handling
        self.selection = self.results_view.get_selection()
        self.selection.connect("changed", self._on_selection_changed)
        
        # Details pane on the right
        details_frame = Gtk.Frame(label="Credentials")
        paned.pack2(details_frame, True, False)
        
        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        details_box.set_border_width(10)
        details_frame.add(details_box)
        
        # Scrollable credentials view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Credentials store and view
        self.creds_store = Gtk.ListStore(str, str, str, str)  # Username, Password, Timestamp, Message
        self.creds_view = Gtk.TreeView(model=self.creds_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Username", renderer, text=0)
        column.set_resizable(True)
        column.set_min_width(150)
        self.creds_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Password", renderer, text=1)
        column.set_resizable(True)
        column.set_min_width(150)
        self.creds_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Timestamp", renderer, text=2)
        column.set_resizable(True)
        column.set_min_width(150)
        self.creds_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Message", renderer, text=3)
        column.set_resizable(True)
        column.set_min_width(150)
        self.creds_view.append_column(column)
        
        scrolled.add(self.creds_view)
        details_box.pack_start(scrolled, True, True, 0)
    
    def _create_results_details(self):
        """Create results details section."""
        frame = Gtk.Frame(label="Details")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Target and protocol info
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(6)
        
        grid.attach(Gtk.Label(label="Target:", xalign=1), 0, 0, 1, 1)
        self.target_label = Gtk.Label(label="", xalign=0)
        grid.attach(self.target_label, 1, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="Protocol:", xalign=1), 0, 1, 1, 1)
        self.protocol_label = Gtk.Label(label="", xalign=0)
        grid.attach(self.protocol_label, 1, 1, 1, 1)
        
        grid.attach(Gtk.Label(label="Duration:", xalign=1), 2, 0, 1, 1)
        self.duration_label = Gtk.Label(label="", xalign=0)
        grid.attach(self.duration_label, 3, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="Attempts:", xalign=1), 2, 1, 1, 1)
        self.attempts_label = Gtk.Label(label="", xalign=0)
        grid.attach(self.attempts_label, 3, 1, 1, 1)
        
        box.pack_start(grid, False, False, 0)
    
    def _create_action_buttons(self):
        """Create action buttons section."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_start(button_box, False, False, 0)
        
        # Export button
        self.export_button = Gtk.Button.new_with_label("Export Credentials")
        self.export_button.connect("clicked", self._on_export_clicked)
        self.export_button.set_sensitive(False)
        button_box.pack_start(self.export_button, True, True, 0)
        
        # Delete button
        self.delete_button = Gtk.Button.new_with_label("Delete Result")
        self.delete_button.connect("clicked", self._on_delete_clicked)
        self.delete_button.set_sensitive(False)
        button_box.pack_start(self.delete_button, True, True, 0)
        
        # Refresh button
        self.refresh_button = Gtk.Button.new_with_label("Refresh List")
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        button_box.pack_start(self.refresh_button, True, True, 0)
    
    def _on_selection_changed(self, selection):
        """Handle results selection change.
        
        Args:
            selection: TreeSelection that changed
        """
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            self.delete_button.set_sensitive(True)
            
            # Get result path
            result_path = model[treeiter][4]
            
            # Load and display credentials
            success_count = self._load_credentials(result_path)
            
            # Enable export if there are credentials
            self.export_button.set_sensitive(success_count > 0)
            
            # Load and display details
            self._load_result_details(result_path)
        else:
            self.delete_button.set_sensitive(False)
            self.export_button.set_sensitive(False)
            
            # Clear credentials and details
            self.creds_store.clear()
            self.target_label.set_text("")
            self.protocol_label.set_text("")
            self.duration_label.set_text("")
            self.attempts_label.set_text("")
    
    def _on_export_clicked(self, button):
        """Handle export button click.
        
        Args:
            button: Button that was clicked
        """
        model, treeiter = self.selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][1]
            result_path = model[treeiter][4]
            
            dialog = Gtk.FileChooserDialog(
                title="Export Credentials",
                parent=self.get_toplevel(),
                action=Gtk.FileChooserAction.SAVE
            )
            dialog.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK
            )
            
            # Add file filters
            filter_text = Gtk.FileFilter()
            filter_text.set_name("Text files")
            filter_text.add_mime_type("text/plain")
            dialog.add_filter(filter_text)
            
            filter_json = Gtk.FileFilter()
            filter_json.set_name("JSON files")
            filter_json.add_mime_type("application/json")
            dialog.add_filter(filter_json)
            
            # Suggest a filename
            dialog.set_current_name(f"{name}_export.txt")
            
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename()
                
                # Determine format based on extension
                json_format = filename.lower().endswith(".json")
                
                self._export_credentials(result_path, filename, json_format)
            
            dialog.destroy()
    
    def _on_delete_clicked(self, button):
        """Handle delete button click.
        
        Args:
            button: Button that was clicked
        """
        model, treeiter = self.selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][1]
            result_path = model[treeiter][4]
            
            # Confirm deletion
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Delete Result"
            )
            dialog.format_secondary_text(f"Are you sure you want to delete '{name}'?")
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                try:
                    # Remove the file
                    os.remove(result_path)
                    self.refresh_results()
                except Exception as e:
                    self.logger.error(f"Error deleting result: {str(e)}")
                    
                    # Show error dialog
                    error_dialog = Gtk.MessageDialog(
                        transient_for=self.get_toplevel(),
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Error Deleting Result"
                    )
                    error_dialog.format_secondary_text(str(e))
                    error_dialog.run()
                    error_dialog.destroy()
    
    def _on_refresh_clicked(self, button):
        """Handle refresh button click.
        
        Args:
            button: Button that was clicked
        """
        self.refresh_results()
    
    def _load_credentials(self, result_path):
        """Load credentials from a result file.
        
        Args:
            result_path: Path to result file
            
        Returns:
            Number of credentials loaded
        """
        self.creds_store.clear()
        
        try:
            with open(result_path, 'r') as f:
                result_data = json.load(f)
                
                # Check for results format
                credentials = result_data.get("credentials", [])
                
                # Add each credential to the store
                for cred in credentials:
                    username = cred.get("username", "")
                    password = cred.get("password", "")
                    timestamp = cred.get("timestamp", 0)
                    message = cred.get("message", "Success")
                    
                    # Format timestamp
                    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                    
                    self.creds_store.append([username, password, timestamp_str, message])
                
                return len(credentials)
                
        except Exception as e:
            self.logger.error(f"Error loading credentials: {str(e)}")
            return 0
    
    def _load_result_details(self, result_path):
        """Load and display result details.
        
        Args:
            result_path: Path to result file
        """
        try:
            with open(result_path, 'r') as f:
                result_data = json.load(f)
                
                # Update detail labels
                target = result_data.get("target", "")
                self.target_label.set_text(target)
                
                protocol = result_data.get("protocol", "")
                self.protocol_label.set_text(protocol)
                
                duration = result_data.get("duration", 0)
                duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
                self.duration_label.set_text(duration_str)
                
                total = result_data.get("total_attempts", 0)
                completed = result_data.get("completed_attempts", 0)
                self.attempts_label.set_text(f"{completed}/{total}")
                
        except Exception as e:
            self.logger.error(f"Error loading result details: {str(e)}")
            
            self.target_label.set_text("")
            self.protocol_label.set_text("")
            self.duration_label.set_text("")
            self.attempts_label.set_text("")
    
    def _export_credentials(self, result_path, export_path, json_format=False):
        """Export credentials to a file.
        
        Args:
            result_path: Path to source result file
            export_path: Path to export file
            json_format: Whether to export as JSON
        """
        try:
            with open(result_path, 'r') as f:
                result_data = json.load(f)
                
                # Get credentials
                credentials = result_data.get("credentials", [])
                
                if json_format:
                    # Export as JSON
                    with open(export_path, 'w') as out_f:
                        json.dump(credentials, out_f, indent=2)
                else:
                    # Export as text (username:password format)
                    with open(export_path, 'w') as out_f:
                        for cred in credentials:
                            username = cred.get("username", "")
                            password = cred.get("password", "")
                            out_f.write(f"{username}:{password}\n")
            
            # Show success message
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Credentials Exported"
            )
            dialog.format_secondary_text(f"Successfully exported to '{export_path}'")
            dialog.run()
            dialog.destroy()
            
        except Exception as e:
            self.logger.error(f"Error exporting credentials: {str(e)}")
            
            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Exporting Credentials"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def refresh_results(self):
        """Refresh the results list."""
        # Clear the store
        self.results_store.clear()
        
        # Add results from directory
        if os.path.exists(self.results_dir):
            for filename in os.listdir(self.results_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.results_dir, filename)
                    if os.path.isfile(filepath):
                        try:
                            with open(filepath, 'r') as f:
                                result_data = json.load(f)
                                
                                # Extract info
                                result_id = result_data.get("id", os.path.splitext(filename)[0])
                                name = result_data.get("name", os.path.splitext(filename)[0])
                                timestamp = result_data.get("timestamp", 0)
                                credentials = result_data.get("credentials", [])
                                
                                # Format timestamp
                                date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                                
                                # Add to store
                                self.results_store.append([
                                    result_id,
                                    name,
                                    date_str,
                                    len(credentials),
                                    filepath
                                ])
                        except:
                            pass
        
        # Sort by timestamp (newest first)
        self.results_store.set_sort_column_id(2, Gtk.SortType.DESCENDING)
    
    def add_result(self, result_data):
        """Add a new result.
        
        Args:
            result_data: Dictionary with result data
        """
        # Generate ID and filename
        result_id = str(int(time.time()))
        result_data["id"] = result_id
        
        if "timestamp" not in result_data:
            result_data["timestamp"] = time.time()
            
        if "name" not in result_data:
            target = result_data.get("target", "unknown")
            protocol = result_data.get("protocol", "unknown")
            result_data["name"] = f"{protocol}_{target}_{result_id}"
        
        # Save result file
        filename = f"{result_id}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(result_data, f, indent=2)
                
            # Refresh the list
            self.refresh_results()
            
        except Exception as e:
            self.logger.error(f"Error saving result: {str(e)}")
            
            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Saving Result"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def get_recent_attacks(self, limit=10):
        """Get recent attacks.
        
        Args:
            limit: Maximum number of attacks to return
            
        Returns:
            list: List of attack dictionaries
        """
        # Return most recent attacks from results data
        attacks = []
        
        # Get attacks sorted by timestamp (most recent first)
        for result_id, result in sorted(
            self.results.items(), 
            key=lambda x: x[1].get('timestamp', 0), 
            reverse=True
        ):
            # Format attack data
            attack = {
                'id': result_id,
                'timestamp': self._format_timestamp(result.get('timestamp')),
                'target': result.get('target', ''),
                'protocol': result.get('protocol', ''),
                'status': 'Completed',
                'success_rate': self._calculate_success_rate(result)
            }
            attacks.append(attack)
            
            # Stop after reaching limit
            if len(attacks) >= limit:
                break
        
        return attacks
    
    def get_recent_credentials(self, limit=10):
        """Get recently discovered credentials.
        
        Args:
            limit: Maximum number of credentials to return
            
        Returns:
            list: List of credential dictionaries
        """
        credentials = []
        
        # Get all credentials from all results, sorted by timestamp
        all_creds = []
        for result_id, result in self.results.items():
            for cred in result.get('credentials', []):
                all_creds.append({
                    'timestamp': self._format_timestamp(cred.get('timestamp', 0)),
                    'target': result.get('target', ''),
                    'username': cred.get('username', ''),
                    'password': cred.get('password', ''),
                    'protocol': result.get('protocol', '')
                })
        
        # Sort by timestamp (most recent first)
        all_creds.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Return up to the limit
        return all_creds[:limit]
    
    def search_credentials(self, search_text):
        """Search for credentials.
        
        Args:
            search_text: Text to search for
            
        Returns:
            list: List of matching credential dictionaries
        """
        search_text = search_text.lower()
        matching_creds = []
        
        # Search all credentials from all results
        for result_id, result in self.results.items():
            target = result.get('target', '').lower()
            protocol = result.get('protocol', '').lower()
            
            for cred in result.get('credentials', []):
                username = cred.get('username', '').lower()
                password = cred.get('password', '').lower()
                
                # Check if any field matches search text
                if (search_text in target or 
                    search_text in protocol or 
                    search_text in username or 
                    search_text in password):
                    
                    matching_creds.append({
                        'timestamp': self._format_timestamp(cred.get('timestamp', 0)),
                        'target': result.get('target', ''),
                        'username': cred.get('username', ''),
                        'password': cred.get('password', ''),
                        'protocol': result.get('protocol', '')
                    })
        
        # Sort by timestamp (most recent first)
        matching_creds.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return matching_creds
    
    def get_summary_metrics(self):
        """Get summary metrics.
        
        Returns:
            dict: Dictionary with summary metrics
        """
        # Calculate summary metrics
        total_attacks = len(self.results)
        successful_attacks = 0
        total_credentials = 0
        targets = set()
        
        for result in self.results.values():
            # Count successful attacks (any credentials found)
            if result.get('credentials', []):
                successful_attacks += 1
            
            # Count total credentials
            total_credentials += len(result.get('credentials', []))
            
            # Add target to set
            if result.get('target'):
                targets.add(result.get('target'))
        
        # Get active scans from attack controller
        from src.core.attack import AttackController
        active_scans = AttackController.get_instance().get_active_attack_count()
        
        return {
            'total_attacks': total_attacks,
            'successful_attacks': successful_attacks,
            'total_credentials': total_credentials,
            'total_targets': len(targets),
            'active_scans': active_scans
        }
    
    def get_success_rate_over_time(self, days=7):
        """Get success rate over time.
        
        Args:
            days: Number of days to include
            
        Returns:
            list: List of success rates
        """
        import time
        from datetime import datetime, timedelta
        
        # Calculate start time
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        start_timestamp = time.mktime(start_time.timetuple())
        
        # Divide into periods (one per day)
        period_seconds = 86400  # Seconds in a day
        periods = []
        for i in range(days):
            period_start = start_timestamp + (i * period_seconds)
            period_end = period_start + period_seconds
            periods.append((period_start, period_end))
        
        # Calculate success rate for each period
        success_rates = []
        for period_start, period_end in periods:
            # Get attacks in this period
            period_attacks = 0
            period_successes = 0
            
            for result in self.results.values():
                timestamp = result.get('timestamp', 0)
                if period_start <= timestamp < period_end:
                    period_attacks += 1
                    if result.get('credentials', []):
                        period_successes += 1
            
            # Calculate success rate
            if period_attacks > 0:
                success_rate = (period_successes / period_attacks) * 100
            else:
                success_rate = 0
            
            success_rates.append(success_rate)
        
        return success_rates
    
    def export_credentials(self, filename):
        """Export credentials to a CSV file.
        
        Args:
            filename: Path to the output file
            
        Raises:
            Exception: If export fails
        """
        import csv
        
        try:
            # Get all credentials
            all_creds = []
            for result_id, result in self.results.items():
                for cred in result.get('credentials', []):
                    all_creds.append({
                        'timestamp': self._format_timestamp(cred.get('timestamp', 0)),
                        'target': result.get('target', ''),
                        'protocol': result.get('protocol', ''),
                        'username': cred.get('username', ''),
                        'password': cred.get('password', ''),
                        'result_id': result_id
                    })
            
            # Write to CSV file
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'target', 'protocol', 'username', 'password', 'result_id']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for cred in all_creds:
                    writer.writerow(cred)
            
            self.logger.info(f"Exported {len(all_creds)} credentials to {filename}")
        except Exception as e:
            self.logger.error(f"Error exporting credentials: {str(e)}")
            raise
    
    def _format_timestamp(self, timestamp):
        """Format a timestamp.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            str: Formatted timestamp
        """
        from datetime import datetime
        
        if not timestamp:
            return ""
        
        # Convert to datetime and format
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def _calculate_success_rate(self, result):
        """Calculate success rate for an attack.
        
        Args:
            result: Attack result dictionary
            
        Returns:
            float: Success rate as a percentage
        """
        total_attempts = result.get('total_attempts', 0)
        successful_attempts = result.get('successful_attempts', 0)
        
        if total_attempts > 0:
            return (successful_attempts / total_attempts) * 100
        else:
            return 0.0
