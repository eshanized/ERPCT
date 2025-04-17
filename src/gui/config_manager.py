#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Configuration Manager.
A standalone GUI application for editing configuration files in the config/ directory.
"""

import os
import sys
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango


class ConfigManager(Gtk.Window):
    """Standalone window for managing ERPCT configuration files."""
    
    def __init__(self):
        """Initialize the configuration manager window."""
        Gtk.Window.__init__(self, title="ERPCT Configuration Manager")
        self.set_default_size(800, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Base directory for configuration files
        self.config_dir = self._get_config_dir()
        
        # Available config files
        self.config_files = [
            {"name": "default", "title": "Default Settings", "description": "General application settings"},
            {"name": "ui", "title": "UI Settings", "description": "User interface configuration"},
            {"name": "protocols", "title": "Protocols", "description": "Available protocol implementations"},
            {"name": "distributed", "title": "Distributed", "description": "Distributed attack settings"},
            {"name": "evasion", "title": "Evasion", "description": "Evasion technique settings"}
        ]
        
        # Create the main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_box.set_border_width(15)
        self.add(self.main_box)
        
        # Create header
        self._create_header()
        
        # Create the main UI components
        self._create_panel_switcher()
        
        # Status bar
        self.status_bar = Gtk.Label()
        self.status_bar.set_xalign(0)
        self.main_box.pack_end(self.status_bar, False, False, 5)
        
        # Show all widgets
        self.show_all()
        
        # Connect delete event
        self.connect("delete-event", self._on_window_close)
    
    def _get_config_dir(self):
        """Get the directory containing configuration files.
        
        Returns:
            Path to the config directory
        """
        # Try to find config directory based on script location
        script_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        config_dir = os.path.join(script_dir, "config")
        
        # Check if config directory exists
        if os.path.isdir(config_dir):
            return config_dir
        
        # Fallback to user's config directory
        home_dir = os.path.expanduser("~")
        user_config = os.path.join(home_dir, ".config", "erpct")
        
        # Create if it doesn't exist
        if not os.path.isdir(user_config):
            try:
                os.makedirs(user_config, exist_ok=True)
            except Exception:
                # Final fallback: current directory
                return os.path.join(os.getcwd(), "config")
        
        return user_config
    
    def _create_header(self):
        """Create header with title and description."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>ERPCT Configuration Manager</span>")
        title.set_xalign(0)
        header_box.pack_start(title, False, False, 0)
        
        # Description
        description = Gtk.Label(
            label="Edit configuration files for the Enhanced Rapid Password Cracking Tool. "
                 "Changes are saved directly to the configuration files in the config directory.",
        )
        description.set_xalign(0)
        description.set_line_wrap(True)
        header_box.pack_start(description, False, False, 0)
        
        # Config directory
        config_path = Gtk.Label()
        config_path.set_markup(f"<span style='italic'>Config directory: {self.config_dir}</span>")
        config_path.set_xalign(0)
        header_box.pack_start(config_path, False, False, 5)
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.pack_start(separator, False, False, 5)
        
        self.main_box.pack_start(header_box, False, False, 0)
    
    def _create_panel_switcher(self):
        """Create notebook with editor panels for each config file."""
        # Main notebook
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        
        # Create editor panels for each config file
        for config_file in self.config_files:
            # Create editor panel
            editor = self._create_editor_panel(config_file)
            
            # Add to notebook
            label = Gtk.Label(label=config_file["title"])
            self.notebook.append_page(editor, label)
        
        self.main_box.pack_start(self.notebook, True, True, 0)
    
    def _create_editor_panel(self, config_file):
        """Create an editor panel for a config file.
        
        Args:
            config_file: Dictionary with config file information
            
        Returns:
            Gtk.Box containing the editor panel
        """
        # Main box for this panel
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        panel.set_border_width(10)
        
        # Description
        description = Gtk.Label()
        description.set_markup(f"<b>{config_file['description']}</b>")
        description.set_xalign(0)
        panel.pack_start(description, False, False, 0)
        
        # Path to config file
        file_path = os.path.join(self.config_dir, f"{config_file['name']}.json")
        path_label = Gtk.Label(f"File: {file_path}")
        path_label.set_xalign(0)
        panel.pack_start(path_label, False, False, 0)
        
        # Editor frame
        editor_frame = Gtk.Frame()
        
        # Scrolled window for text view
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Text view for editing
        text_view = Gtk.TextView()
        text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        text_view.set_left_margin(10)
        text_view.set_right_margin(10)
        text_view.set_top_margin(10)
        text_view.set_bottom_margin(10)
        
        # Set monospace font for better JSON editing
        text_view.override_font(Pango.FontDescription("Monospace 11"))
        
        # Get text buffer
        text_buffer = text_view.get_buffer()
        
        # Store references
        config_file["text_view"] = text_view
        config_file["text_buffer"] = text_buffer
        
        # Load content
        self._load_config_content(config_file)
        
        scrolled_window.add(text_view)
        editor_frame.add(scrolled_window)
        panel.pack_start(editor_frame, True, True, 0)
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Format/validate button
        format_button = Gtk.Button(label="Format JSON")
        format_button.connect("clicked", self._on_format_clicked, config_file)
        button_box.pack_start(format_button, False, False, 0)
        
        # Reset button
        reset_button = Gtk.Button(label="Reset to Default")
        reset_button.connect("clicked", self._on_reset_clicked, config_file)
        button_box.pack_start(reset_button, False, False, 0)
        
        # Space filler
        button_box.pack_start(Gtk.Box(), True, True, 0)
        
        # Save button
        save_button = Gtk.Button(label="Save")
        save_button.connect("clicked", self._on_save_clicked, config_file)
        button_box.pack_end(save_button, False, False, 0)
        
        panel.pack_end(button_box, False, False, 0)
        
        return panel
    
    def _load_config_content(self, config_file):
        """Load content from config file into text buffer.
        
        Args:
            config_file: Dictionary with config file information
        """
        # Get file path
        file_path = os.path.join(self.config_dir, f"{config_file['name']}.json")
        
        try:
            # Load content from file if it exists
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = json.load(f)
                    # Pretty-print JSON
                    formatted_json = json.dumps(content, indent=2)
                    config_file["text_buffer"].set_text(formatted_json)
            else:
                # Create empty JSON object
                config_file["text_buffer"].set_text("{}")
                self._set_status(f"Warning: Config file {file_path} does not exist. It will be created when you save.", "warning")
        except Exception as e:
            # Show error
            self._set_status(f"Error loading {file_path}: {str(e)}", "error")
            config_file["text_buffer"].set_text("{}")
    
    def _on_format_clicked(self, button, config_file):
        """Format and validate JSON content.
        
        Args:
            button: Button that was clicked
            config_file: Dictionary with config file information
        """
        # Get current text
        text_buffer = config_file["text_buffer"]
        start_iter, end_iter = text_buffer.get_bounds()
        current_text = text_buffer.get_text(start_iter, end_iter, True)
        
        try:
            # Parse and format JSON
            parsed_json = json.loads(current_text)
            formatted_json = json.dumps(parsed_json, indent=2)
            
            # Update text buffer
            text_buffer.set_text(formatted_json)
            
            self._set_status("JSON validated and formatted successfully", "success")
        except json.JSONDecodeError as e:
            self._set_status(f"JSON validation error: {str(e)}", "error")
    
    def _on_reset_clicked(self, button, config_file):
        """Reset config file to default.
        
        Args:
            button: Button that was clicked
            config_file: Dictionary with config file information
        """
        # Confirm reset
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Reset {config_file['title']} to default?"
        )
        dialog.format_secondary_text("This will discard all changes and restore the default configuration.")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self._load_config_content(config_file)
            self._set_status(f"Reset {config_file['title']} to default", "info")
    
    def _on_save_clicked(self, button, config_file):
        """Save config file.
        
        Args:
            button: Button that was clicked
            config_file: Dictionary with config file information
        """
        # Get current text
        text_buffer = config_file["text_buffer"]
        start_iter, end_iter = text_buffer.get_bounds()
        current_text = text_buffer.get_text(start_iter, end_iter, True)
        
        try:
            # Parse JSON to validate
            parsed_json = json.loads(current_text)
            
            # Get file path
            file_path = os.path.join(self.config_dir, f"{config_file['name']}.json")
            
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(parsed_json, f, indent=2)
            
            self._set_status(f"Saved {config_file['title']} configuration to {file_path}", "success")
        except json.JSONDecodeError as e:
            self._set_status(f"JSON validation error: {str(e)}", "error")
        except Exception as e:
            self._set_status(f"Error saving file: {str(e)}", "error")
    
    def _set_status(self, message, status_type="info"):
        """Set status bar message.
        
        Args:
            message: Status message to display
            status_type: Type of status (info, success, warning, error)
        """
        if status_type == "success":
            color = "#27ae60"  # Green
        elif status_type == "warning":
            color = "#f39c12"  # Orange
        elif status_type == "error":
            color = "#e74c3c"  # Red
        else:
            color = "#3498db"  # Blue
        
        self.status_bar.set_markup(f"<span foreground='{color}'>{message}</span>")
    
    def _on_window_close(self, widget, event):
        """Handle window close event.
        
        Args:
            widget: Window widget
            event: Event object
            
        Returns:
            False to continue with default handler
        """
        # Check for unsaved changes
        has_unsaved = False
        
        for config_file in self.config_files:
            if "text_buffer" in config_file:
                text_buffer = config_file["text_buffer"]
                if text_buffer.get_modified():
                    has_unsaved = True
                    break
        
        if has_unsaved:
            # Confirm close
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="You have unsaved changes"
            )
            dialog.format_secondary_text("Are you sure you want to exit without saving?")
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.NO:
                # Don't close
                return True
        
        # Exit application
        Gtk.main_quit()
        return False


def main():
    """Run the configuration manager application."""
    app = ConfigManager()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main()) 