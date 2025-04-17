#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Status Panel component.
This module provides the GUI panel for displaying attack progress and results.
"""

import time
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango


class StatusPanel(Gtk.Box):
    """Status panel component showing attack progress and results."""
    
    def __init__(self):
        """Initialize the status panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        # Create UI components
        self._create_progress_section()
        self._create_results_section()
        self._create_control_buttons()
        
        # Attack status
        self.attack = None
        self.update_timer_id = None
    
    def _create_progress_section(self):
        """Create progress display section."""
        frame = Gtk.Frame(label="Progress")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_text("Ready")
        self.progress_bar.set_show_text(True)
        box.pack_start(self.progress_bar, False, False, 0)
        
        # Status grid
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(6)
        
        # Labels for status information
        grid.attach(Gtk.Label(label="Elapsed:", xalign=1), 0, 0, 1, 1)
        self.elapsed_label = Gtk.Label(label="00:00:00", xalign=0)
        grid.attach(self.elapsed_label, 1, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="ETA:", xalign=1), 2, 0, 1, 1)
        self.eta_label = Gtk.Label(label="00:00:00", xalign=0)
        grid.attach(self.eta_label, 3, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="Attempts:", xalign=1), 0, 1, 1, 1)
        self.attempts_label = Gtk.Label(label="0/0", xalign=0)
        grid.attach(self.attempts_label, 1, 1, 1, 1)
        
        grid.attach(Gtk.Label(label="Speed:", xalign=1), 2, 1, 1, 1)
        self.speed_label = Gtk.Label(label="0/s", xalign=0)
        grid.attach(self.speed_label, 3, 1, 1, 1)
        
        grid.attach(Gtk.Label(label="Success:", xalign=1), 0, 2, 1, 1)
        self.success_label = Gtk.Label(label="0", xalign=0)
        grid.attach(self.success_label, 1, 2, 1, 1)
        
        grid.attach(Gtk.Label(label="Errors:", xalign=1), 2, 2, 1, 1)
        self.errors_label = Gtk.Label(label="0", xalign=0)
        grid.attach(self.errors_label, 3, 2, 1, 1)
        
        box.pack_start(grid, False, False, 0)
    
    def _create_results_section(self):
        """Create results display section."""
        frame = Gtk.Frame(label="Results")
        self.pack_start(frame, True, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Scrollable results view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(200)
        
        # Results list
        self.results_store = Gtk.ListStore(str, str, str, str)  # Username, Password, Timestamp, Message
        self.results_view = Gtk.TreeView(model=self.results_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Username", renderer, text=0)
        column.set_resizable(True)
        self.results_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Password", renderer, text=1)
        column.set_resizable(True)
        self.results_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Timestamp", renderer, text=2)
        column.set_resizable(True)
        self.results_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Message", renderer, text=3)
        column.set_resizable(True)
        self.results_view.append_column(column)
        
        scrolled.add(self.results_view)
        box.pack_start(scrolled, True, True, 0)
    
    def _create_control_buttons(self):
        """Create control buttons section."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_start(button_box, False, False, 0)
        
        # Stop button
        self.stop_button = Gtk.Button.new_with_label("Stop Attack")
        self.stop_button.connect("clicked", self._on_stop_clicked)
        self.stop_button.set_sensitive(False)
        button_box.pack_start(self.stop_button, True, True, 0)
        
        # Save results button
        self.save_button = Gtk.Button.new_with_label("Save Results")
        self.save_button.connect("clicked", self._on_save_clicked)
        self.save_button.set_sensitive(False)
        button_box.pack_start(self.save_button, True, True, 0)
        
        # Clear results button
        self.clear_button = Gtk.Button.new_with_label("Clear Results")
        self.clear_button.connect("clicked", self._on_clear_clicked)
        button_box.pack_start(self.clear_button, True, True, 0)
    
    def _on_stop_clicked(self, button):
        """Handle stop button click.
        
        Args:
            button: Button that was clicked
        """
        if self.attack:
            self.attack.stop()
            self.stop_button.set_sensitive(False)
    
    def _on_save_clicked(self, button):
        """Handle save results button click.
        
        Args:
            button: Button that was clicked
        """
        dialog = Gtk.FileChooserDialog(
            title="Save Results",
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
        dialog.set_current_name(f"erpct_results_{int(time.time())}.txt")
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            
            # Determine format based on extension
            json_format = filename.lower().endswith(".json")
            
            self._save_results(filename, json_format)
        
        dialog.destroy()
    
    def _on_clear_clicked(self, button):
        """Handle clear results button click.
        
        Args:
            button: Button that was clicked
        """
        self.results_store.clear()
        self.save_button.set_sensitive(False)
    
    def _save_results(self, filename, json_format=False):
        """Save results to a file.
        
        Args:
            filename: Path to save file
            json_format: Whether to save in JSON format
        """
        try:
            if json_format:
                import json
                
                # Convert results to JSON
                results = []
                for row in self.results_store:
                    results.append({
                        "username": row[0],
                        "password": row[1],
                        "timestamp": row[2],
                        "message": row[3]
                    })
                
                with open(filename, 'w') as f:
                    json.dump(results, f, indent=2)
            else:
                # Save as plain text
                with open(filename, 'w') as f:
                    for row in self.results_store:
                        f.write(f"{row[0]}:{row[1]}\n")
            
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Results Saved"
            )
            dialog.format_secondary_text(f"Results saved to {filename}")
            dialog.run()
            dialog.destroy()
        
        except Exception as e:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Saving Results"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def start_attack(self, attack):
        """Start monitoring an attack.
        
        Args:
            attack: Attack instance to monitor
        """
        self.attack = attack
        
        # Clear results
        self.results_store.clear()
        
        # Reset progress display
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text("Starting...")
        self.elapsed_label.set_text("00:00:00")
        self.eta_label.set_text("00:00:00")
        self.attempts_label.set_text("0/0")
        self.speed_label.set_text("0/s")
        self.success_label.set_text("0")
        self.errors_label.set_text("0")
        
        # Enable stop button
        self.stop_button.set_sensitive(True)
        
        # Set up callback for successful credentials
        attack.set_on_success_callback(self._on_success)
        
        # Start update timer
        self.update_timer_id = GLib.timeout_add(500, self._update_status)
    
    def _on_success(self, result):
        """Handle successful authentication.
        
        Args:
            result: AttackResult with successful credentials
        """
        # Format timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result.timestamp))
        
        # Add to results store
        self.results_store.append([
            result.username,
            result.password,
            timestamp,
            result.message or "Success"
        ])
        
        # Enable save button
        self.save_button.set_sensitive(True)
    
    def _update_status(self):
        """Update status display with current attack progress.
        
        Returns:
            True to continue updating, False to stop
        """
        if not self.attack or not self.attack.status.running:
            if self.attack:
                # Final update after attack completion
                self._update_progress_display()
                self.progress_bar.set_text("Completed")
                self.stop_button.set_sensitive(False)
            else:
                self.progress_bar.set_text("Ready")
            
            # Stop timer
            self.update_timer_id = None
            return False
        
        # Update progress display
        self._update_progress_display()
        
        # Continue timer
        return True
    
    def _update_progress_display(self):
        """Update progress display with current attack status."""
        if not self.attack:
            return
        
        # Get attack statistics
        stats = self.attack.get_status()
        
        # Update progress bar
        progress = stats["progress_percent"] / 100.0
        self.progress_bar.set_fraction(min(1.0, max(0.0, progress)))
        self.progress_bar.set_text(f"{stats['progress_percent']:.1f}%")
        
        # Update status labels
        elapsed = stats["elapsed_seconds"]
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        self.elapsed_label.set_text(elapsed_str)
        
        eta = stats["estimated_time_remaining"]
        eta_str = time.strftime("%H:%M:%S", time.gmtime(eta))
        self.eta_label.set_text(eta_str)
        
        self.attempts_label.set_text(f"{stats['completed_attempts']}/{stats['total_attempts']}")
        self.speed_label.set_text(f"{stats['attempts_per_second']:.1f}/s")
        self.success_label.set_text(str(stats['successful_attempts']))
        self.errors_label.set_text(str(stats['error_attempts']))

    def get_active_attacks(self):
        """Get list of active attacks.
        
        Returns:
            list: List of active attack objects
        """
        if self.attack and self.attack.status.running:
            return [self.attack]
        return []
