#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Configuration Editor.
This module provides a GUI for editing and generating configuration files.
"""

import os
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango

from src.utils.logging import get_logger
from src.utils.config import load_config, save_config, get_config_dir


class ConfigEditor(Gtk.Box):
    """Configuration editor panel for managing config files."""
    
    def __init__(self):
        """Initialize the configuration editor panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Config files list
        self.config_files = [
            "default",
            "ui",
            "protocols",
            "distributed",
            "evasion"
        ]
        
        # Create UI components
        self._create_header()
        self._create_file_selector()
        self._create_editor()
        self._create_buttons()
        
        # Select first file by default
        if self.config_files:
            self.file_combo.set_active(0)
            
        self.show_all()
    
    def _create_header(self):
        """Create header with description and instructions."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        title = Gtk.Label(label="<b>Configuration Editor</b>", xalign=0)
        title.set_use_markup(True)
        header_box.pack_start(title, False, False, 0)
        
        description = Gtk.Label(
            label="Edit and generate configuration files for ERPCT. "
                  "Changes are saved to the application's configuration directory.",
            xalign=0
        )
        description.set_line_wrap(True)
        header_box.pack_start(description, False, False, 0)
        
        self.status_label = Gtk.Label(label="", xalign=0)
        header_box.pack_start(self.status_label, False, False, 0)
        
        self.pack_start(header_box, False, False, 0)
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(separator, False, False, 10)
    
    def _create_file_selector(self):
        """Create config file selector."""
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        file_label = Gtk.Label(label="Config File:", xalign=0)
        file_box.pack_start(file_label, False, False, 0)
        
        self.file_combo = Gtk.ComboBoxText()
        for config_file in self.config_files:
            self.file_combo.append_text(config_file)
        
        self.file_combo.connect("changed", self._on_file_selected)
        file_box.pack_start(self.file_combo, True, True, 0)
        
        self.pack_start(file_box, False, False, 0)
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(separator, False, False, 10)
    
    def _create_editor(self):
        """Create the main editor area."""
        # Scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        
        # Text view with monospace font for JSON editing
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_left_margin(10)
        self.text_view.set_right_margin(10)
        
        # Use monospace font
        self.text_view.override_font(Pango.FontDescription("Monospace 11"))
        
        # Text buffer
        self.text_buffer = self.text_view.get_buffer()
        
        scrolled_window.add(self.text_view)
        
        # Pack into frame with title
        editor_frame = Gtk.Frame(label="Editor")
        editor_frame.add(scrolled_window)
        self.pack_start(editor_frame, True, True, 0)
    
    def _create_buttons(self):
        """Create action buttons."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Format/validate button
        format_button = Gtk.Button(label="Format JSON")
        format_button.connect("clicked", self._on_format_clicked)
        button_box.pack_start(format_button, False, False, 0)
        
        # Reset button
        reset_button = Gtk.Button(label="Reset to Defaults")
        reset_button.connect("clicked", self._on_reset_clicked)
        button_box.pack_start(reset_button, False, False, 0)
        
        # Spacer
        button_box.pack_start(Gtk.Box(), True, True, 0)
        
        # Save button
        self.save_button = Gtk.Button(label="Save Changes")
        self.save_button.connect("clicked", self._on_save_clicked)
        button_box.pack_start(self.save_button, False, False, 0)
        
        self.pack_start(button_box, False, False, 10)
    
    def _on_file_selected(self, combo):
        """Handle file selection change."""
        selected_file = combo.get_active_text()
        if not selected_file:
            return
            
        # Load and display the selected config file
        self._load_config_file(selected_file)
    
    def _load_config_file(self, config_name):
        """Load a configuration file into the editor."""
        # Clear status
        self.status_label.set_text("")
        
        # Get path to config file
        config_dir = get_config_dir()
        config_path = os.path.join(config_dir, f"{config_name}.json")
        
        # If user config doesn't exist, check package default
        package_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config", 
            f"{config_name}.json"
        )
        
        try:
            if os.path.exists(config_path):
                # Load from user config
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    self.logger.debug(f"Loaded user config from {config_path}")
            elif os.path.exists(package_config_path):
                # Load from package defaults
                with open(package_config_path, 'r') as f:
                    config_data = json.load(f)
                    self.logger.debug(f"Loaded package config from {package_config_path}")
            else:
                # No config found, use empty object
                config_data = {}
                self.logger.warning(f"No config found for {config_name}, using empty object")
                
            # Format JSON and set text
            formatted_json = json.dumps(config_data, indent=2)
            self.text_buffer.set_text(formatted_json)
            
        except Exception as e:
            self.logger.error(f"Error loading config {config_name}: {str(e)}")
            self.status_label.set_markup(f"<span foreground='red'>Error: {str(e)}</span>")
            # Set empty text
            self.text_buffer.set_text("{}")
    
    def _on_format_clicked(self, button):
        """Format and validate the JSON content."""
        # Get current text
        start_iter, end_iter = self.text_buffer.get_bounds()
        current_text = self.text_buffer.get_text(start_iter, end_iter, True)
        
        try:
            # Parse and format JSON
            parsed_json = json.loads(current_text)
            formatted_json = json.dumps(parsed_json, indent=2)
            
            # Update text buffer
            self.text_buffer.set_text(formatted_json)
            
            self.status_label.set_markup("<span foreground='green'>JSON validated and formatted successfully</span>")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON validation error: {str(e)}")
            self.status_label.set_markup(f"<span foreground='red'>JSON Error: {str(e)}</span>")
    
    def _on_reset_clicked(self, button):
        """Reset the current config to defaults."""
        selected_file = self.file_combo.get_active_text()
        if not selected_file:
            return
            
        # Confirm before reset
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Reset {selected_file}.json to defaults?"
        )
        dialog.format_secondary_text(
            "This will discard all changes and restore the default configuration."
        )
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Get path to package default
            package_config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config", 
                f"{selected_file}.json"
            )
            
            try:
                if os.path.exists(package_config_path):
                    # Load from package defaults
                    with open(package_config_path, 'r') as f:
                        config_data = json.load(f)
                        
                    # Format JSON and set text
                    formatted_json = json.dumps(config_data, indent=2)
                    self.text_buffer.set_text(formatted_json)
                    
                    self.status_label.set_markup("<span foreground='green'>Reset to defaults</span>")
                else:
                    self.status_label.set_markup("<span foreground='red'>Default configuration not found</span>")
                    
            except Exception as e:
                self.logger.error(f"Error resetting config: {str(e)}")
                self.status_label.set_markup(f"<span foreground='red'>Error: {str(e)}</span>")
    
    def _on_save_clicked(self, button):
        """Save the current configuration."""
        selected_file = self.file_combo.get_active_text()
        if not selected_file:
            return
            
        # Get current text
        start_iter, end_iter = self.text_buffer.get_bounds()
        current_text = self.text_buffer.get_text(start_iter, end_iter, True)
        
        try:
            # Parse JSON to validate
            config_data = json.loads(current_text)
            
            # Get path to save
            config_dir = get_config_dir()
            config_path = os.path.join(config_dir, f"{selected_file}.json")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Save to file
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
                
            self.logger.info(f"Saved config to {config_path}")
            self.status_label.set_markup("<span foreground='green'>Configuration saved successfully</span>")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON validation error: {str(e)}")
            self.status_label.set_markup(f"<span foreground='red'>JSON Error: {str(e)}</span>")
            
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")
            self.status_label.set_markup(f"<span foreground='red'>Error saving: {str(e)}</span>") 