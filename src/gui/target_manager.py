#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Target Manager component.
This module provides the GUI panel for configuring target information.
"""

import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango

class TargetManager(Gtk.Box):
    """Target configuration panel."""
    
    def __init__(self):
        """Initialize the target manager panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        # Target configuration section
        self._create_target_section()
        self._create_credentials_section()
        
        # Create button to validate target configuration
        self.validate_button = Gtk.Button(label="Validate Target")
        self.validate_button.connect("clicked", self._on_validate_clicked)
        self.pack_end(self.validate_button, False, False, 0)
        
        # Callbacks
        self.on_target_change_callback = None
    
    def _create_target_section(self):
        """Create target input section."""
        frame = Gtk.Frame(label="Target")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Target type selector
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        type_label = Gtk.Label(label="Target type:")
        type_box.pack_start(type_label, False, False, 0)
        
        self.single_radio = Gtk.RadioButton.new_with_label_from_widget(None, "Single target")
        self.single_radio.connect("toggled", self._on_target_type_toggled)
        type_box.pack_start(self.single_radio, False, False, 0)
        
        self.file_radio = Gtk.RadioButton.new_with_label_from_widget(self.single_radio, "Target list from file")
        self.file_radio.connect("toggled", self._on_target_type_toggled)
        type_box.pack_start(self.file_radio, False, False, 0)
        
        box.pack_start(type_box, False, False, 0)
        
        # Single target inputs
        self.single_target_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.pack_start(self.single_target_box, False, False, 0)
        
        # Host input
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Host/IP:")
        host_label.set_width_chars(10)
        host_label.set_xalign(0)
        host_box.pack_start(host_label, False, False, 0)
        
        self.host_entry = Gtk.Entry()
        host_box.pack_start(self.host_entry, True, True, 0)
        
        self.single_target_box.pack_start(host_box, False, False, 0)
        
        # Port input
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port:")
        port_label.set_width_chars(10)
        port_label.set_xalign(0)
        port_box.pack_start(port_label, False, False, 0)
        
        self.port_entry = Gtk.Entry()
        port_box.pack_start(self.port_entry, True, True, 0)
        
        self.single_target_box.pack_start(port_box, False, False, 0)
        
        # File target inputs
        self.file_target_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.pack_start(self.file_target_box, False, False, 0)
        
        # File chooser
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        file_label = Gtk.Label(label="Target file:")
        file_label.set_width_chars(10)
        file_label.set_xalign(0)
        file_box.pack_start(file_label, False, False, 0)
        
        self.file_entry = Gtk.Entry()
        file_box.pack_start(self.file_entry, True, True, 0)
        
        self.file_button = Gtk.Button(label="Browse...")
        self.file_button.connect("clicked", self._on_browse_clicked)
        file_box.pack_start(self.file_button, False, False, 0)
        
        self.file_target_box.pack_start(file_box, False, False, 0)
        
        # File format description
        format_label = Gtk.Label()
        format_label.set_markup("<small>Format: host[:port] one per line</small>")
        format_label.set_xalign(0)
        self.file_target_box.pack_start(format_label, False, False, 0)
        
        # Hide file target box initially
        self.file_target_box.set_no_show_all(True)
        self.file_target_box.hide()
    
    def _create_credentials_section(self):
        """Create credentials input section."""
        frame = Gtk.Frame(label="Credentials")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Username inputs
        username_type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        username_label = Gtk.Label(label="Username:")
        username_label.set_width_chars(10)
        username_label.set_xalign(0)
        username_type_box.pack_start(username_label, False, False, 0)
        
        self.single_username_radio = Gtk.RadioButton.new_with_label_from_widget(None, "Single")
        self.single_username_radio.connect("toggled", self._on_username_type_toggled)
        username_type_box.pack_start(self.single_username_radio, False, False, 0)
        
        self.file_username_radio = Gtk.RadioButton.new_with_label_from_widget(self.single_username_radio, "From file")
        self.file_username_radio.connect("toggled", self._on_username_type_toggled)
        username_type_box.pack_start(self.file_username_radio, False, False, 0)
        
        box.pack_start(username_type_box, False, False, 0)
        
        # Single username
        self.single_username_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.username_entry = Gtk.Entry()
        self.single_username_box.pack_start(self.username_entry, True, True, 0)
        box.pack_start(self.single_username_box, False, False, 0)
        
        # Username file
        self.file_username_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.username_file_entry = Gtk.Entry()
        self.file_username_box.pack_start(self.username_file_entry, True, True, 0)
        
        self.username_file_button = Gtk.Button(label="Browse...")
        self.username_file_button.connect("clicked", self._on_browse_username_clicked)
        self.file_username_box.pack_start(self.username_file_button, False, False, 0)
        box.pack_start(self.file_username_box, False, False, 0)
        
        # Hide username file box initially
        self.file_username_box.set_no_show_all(True)
        self.file_username_box.hide()
        
        # Password inputs
        password_type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        password_label = Gtk.Label(label="Password:")
        password_label.set_width_chars(10)
        password_label.set_xalign(0)
        password_type_box.pack_start(password_label, False, False, 0)
        
        self.single_password_radio = Gtk.RadioButton.new_with_label_from_widget(None, "Single")
        self.single_password_radio.connect("toggled", self._on_password_type_toggled)
        password_type_box.pack_start(self.single_password_radio, False, False, 0)
        
        self.file_password_radio = Gtk.RadioButton.new_with_label_from_widget(self.single_password_radio, "Wordlist")
        self.file_password_radio.connect("toggled", self._on_password_type_toggled)
        password_type_box.pack_start(self.file_password_radio, False, False, 0)
        
        box.pack_start(password_type_box, False, False, 0)
        
        # Single password
        self.single_password_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.single_password_box.pack_start(self.password_entry, True, True, 0)
        box.pack_start(self.single_password_box, False, False, 0)
        
        # Password file
        self.file_password_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.password_file_entry = Gtk.Entry()
        self.file_password_box.pack_start(self.password_file_entry, True, True, 0)
        
        self.password_file_button = Gtk.Button(label="Browse...")
        self.password_file_button.connect("clicked", self._on_browse_password_clicked)
        self.file_password_box.pack_start(self.password_file_button, False, False, 0)
        box.pack_start(self.file_password_box, False, False, 0)
        
        # Hide password file box initially
        self.file_password_box.set_no_show_all(True)
        self.file_password_box.hide()
    
    def _on_target_type_toggled(self, button):
        """Handle target type radio button toggle.
        
        Args:
            button: Radio button that was toggled
        """
        if self.single_radio.get_active():
            self.single_target_box.show()
            self.file_target_box.hide()
        else:
            self.single_target_box.hide()
            self.file_target_box.show()
        
        if self.on_target_change_callback:
            self.on_target_change_callback()
    
    def _on_username_type_toggled(self, button):
        """Handle username type radio button toggle.
        
        Args:
            button: Radio button that was toggled
        """
        if self.single_username_radio.get_active():
            self.single_username_box.show()
            self.file_username_box.hide()
        else:
            self.single_username_box.hide()
            self.file_username_box.show()
        
        if self.on_target_change_callback:
            self.on_target_change_callback()
    
    def _on_password_type_toggled(self, button):
        """Handle password type radio button toggle.
        
        Args:
            button: Radio button that was toggled
        """
        if self.single_password_radio.get_active():
            self.single_password_box.show()
            self.file_password_box.hide()
        else:
            self.single_password_box.hide()
            self.file_password_box.show()
        
        if self.on_target_change_callback:
            self.on_target_change_callback()
    
    def _on_browse_clicked(self, button):
        """Handle browse button click for target file.
        
        Args:
            button: Button that was clicked
        """
        self._show_file_dialog(self.file_entry, "Select Target File")
    
    def _on_browse_username_clicked(self, button):
        """Handle browse button click for username file.
        
        Args:
            button: Button that was clicked
        """
        self._show_file_dialog(self.username_file_entry, "Select Username File")
    
    def _on_browse_password_clicked(self, button):
        """Handle browse button click for password file.
        
        Args:
            button: Button that was clicked
        """
        self._show_file_dialog(self.password_file_entry, "Select Password Wordlist")
    
    def _show_file_dialog(self, entry_widget, title):
        """Show file chooser dialog and update entry.
        
        Args:
            entry_widget: Entry widget to update with selected file
            title: Dialog title
        """
        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            entry_widget.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _on_validate_clicked(self, button):
        """Handle validate button click.
        
        Args:
            button: Button that was clicked
        """
        # Validate target configuration
        config = self.get_target_config()
        
        # TODO: Implement actual validation
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Target Configuration"
        )
        dialog.format_secondary_text(f"Target configuration validated.")
        dialog.run()
        dialog.destroy()
    
    def get_target_config(self):
        """Get the current target configuration.
        
        Returns:
            Dictionary with target configuration
        """
        config = {}
        
        # Target configuration
        if self.single_radio.get_active():
            config["target"] = self.host_entry.get_text()
            port = self.port_entry.get_text()
            if port:
                config["port"] = int(port)
        else:
            config["target_file"] = self.file_entry.get_text()
        
        # Username configuration
        if self.single_username_radio.get_active():
            config["username"] = self.username_entry.get_text()
        else:
            config["username_list"] = self.username_file_entry.get_text()
        
        # Password configuration
        if self.single_password_radio.get_active():
            config["password"] = self.password_entry.get_text()
        else:
            config["wordlist"] = self.password_file_entry.get_text()
        
        return config
    
    def set_on_target_change_callback(self, callback):
        """Set callback for when target configuration changes.
        
        Args:
            callback: Function to call when configuration changes
        """
        self.on_target_change_callback = callback
