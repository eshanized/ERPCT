#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Protocol Configuration.
This module provides a GUI for configuring protocol-specific options for attacks.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

# Updated imports
from src.protocols import get_all_protocols, get_protocol, protocol_exists
from src.utils.logging import get_logger


class ProtocolConfigurator(Gtk.Box):
    """Protocol configuration widget."""
    
    def __init__(self):
        """Initialize the protocol configurator widget."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Protocol selection
        protocol_frame = Gtk.Frame(label="Protocol Selection")
        self.pack_start(protocol_frame, False, False, 0)
        
        protocol_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        protocol_box.set_border_width(10)
        protocol_frame.add(protocol_box)
        
        # Protocol combo box
        protocol_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        protocol_label = Gtk.Label(label="Protocol:", xalign=0)
        protocol_hbox.pack_start(protocol_label, False, False, 0)
        
        self.protocol_combo = Gtk.ComboBoxText()
        # Add all available protocols
        protocols = get_all_protocols()
        for name in sorted(protocols.keys()):
            self.protocol_combo.append_text(name)
        
        # Select first protocol by default if available
        if protocols:
            self.protocol_combo.set_active(0)
            
        self.protocol_combo.connect("changed", self._on_protocol_changed)
        protocol_hbox.pack_start(self.protocol_combo, True, True, 0)
        protocol_box.pack_start(protocol_hbox, False, False, 0)
        
        # Protocol info
        self.protocol_info_label = Gtk.Label(xalign=0)
        self.protocol_info_label.set_line_wrap(True)
        protocol_box.pack_start(self.protocol_info_label, False, False, 0)
        
        # Protocol options container
        options_frame = Gtk.Frame(label="Protocol Options")
        self.pack_start(options_frame, True, True, 0)
        
        self.options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.options_box.set_border_width(10)
        options_frame.add(self.options_box)
        
        # Dictionary to store option widgets
        self.option_widgets = {}
        
        # Initialize with the first protocol
        self._on_protocol_changed(self.protocol_combo)
        
        self.show_all()

    def _on_protocol_changed(self, combo):
        """Handle protocol selection change.
        
        Args:
            combo: The protocol combo box widget
        """
        # Clear existing options
        for child in self.options_box.get_children():
            self.options_box.remove(child)
        
        self.option_widgets = {}
        
        # Get selected protocol
        protocol_name = combo.get_active_text()
        if not protocol_name:
            return
            
        try:
            # Get protocol class and create an instance
            protocol_class = get_protocol(protocol_name)
            
            # Create a default config with host to prevent initialization errors
            default_config = {}
            
            # Host-based protocols
            if protocol_name.lower() in ["ftp", "ssh", "telnet", "smtp", "pop3", "imap", "vnc", "smb", "ldap"]:
                default_config["host"] = "example.com"  # Default placeholder host
            
            # URL-based protocols 
            elif protocol_name.lower() in ["http-form", "httpform", "http", "https"]:
                default_config["url"] = "https://example.com/login"  # Default placeholder URL
            
            # Database protocols
            elif protocol_name.lower() in ["mysql", "postgres", "postgresql"]:
                default_config["host"] = "example.com"
                default_config["database"] = "example"
            
            # RDP protocol
            elif protocol_name.lower() == "rdp":
                default_config["host"] = "example.com"
                default_config["domain"] = ""
            
            # Custom protocol special handling
            elif protocol_name.lower() == "custom":
                default_config["host"] = "example.com"
                default_config["method_type"] = "command"  # Use command method by default, which doesn't require script path
                default_config["command"] = "echo 'Test authentication'"
            
            try:
                protocol = protocol_class(default_config)
                
                # Update info label
                info_text = f"{protocol.__doc__ or 'No description'}\nDefault port: {protocol.default_port}"
                self.protocol_info_label.set_text(info_text)
                
                # Get protocol options
                options = protocol.get_options()
                
                if not options:
                    label = Gtk.Label(label="No configurable options for this protocol.")
                    self.options_box.pack_start(label, False, False, 0)
                else:
                    # Create widgets for each option
                    for option_name, option_info in options.items():
                        option_type = option_info.get("type", "string")
                        option_default = option_info.get("default", "")
                        option_desc = option_info.get("description", "")
                        
                        # Create option row
                        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        
                        # Label with tooltip
                        label = Gtk.Label(label=f"{option_name}:", xalign=0)
                        label.set_tooltip_text(option_desc)
                        label.set_size_request(150, -1)
                        hbox.pack_start(label, False, False, 0)
                        
                        # Widget depends on option type
                        if option_type == "boolean":
                            widget = Gtk.CheckButton()
                            widget.set_active(bool(option_default))
                            
                        elif option_type == "integer":
                            adjustment = Gtk.Adjustment(
                                value=int(option_default) if option_default else 0,
                                lower=-1000000,
                                upper=1000000,
                                step_increment=1,
                                page_increment=10
                            )
                            widget = Gtk.SpinButton()
                            widget.set_adjustment(adjustment)
                            
                        elif option_type == "select":
                            widget = Gtk.ComboBoxText()
                            for choice in option_info.get("choices", []):
                                widget.append_text(str(choice))
                            
                            # Set default if in choices
                            if option_default in option_info.get("choices", []):
                                index = option_info.get("choices", []).index(option_default)
                                widget.set_active(index)
                            elif option_info.get("choices", []):
                                widget.set_active(0)
                                
                        else:  # Default to string
                            widget = Gtk.Entry()
                            widget.set_text(str(option_default) if option_default is not None else "")
                        
                        hbox.pack_start(widget, True, True, 0)
                        self.options_box.pack_start(hbox, False, False, 0)
                        
                        # Store widget reference
                        self.option_widgets[option_name] = widget
                
                self.options_box.show_all()
            except ImportError as e:
                self.logger.error(f"Missing dependency for protocol {protocol_name}: {str(e)}")
                label = Gtk.Label(label=f"This protocol requires additional dependencies:\n{str(e)}")
                self.options_box.pack_start(label, False, False, 0)
                self.options_box.show_all()
            
        except Exception as e:
            self.logger.error(f"Error loading protocol options: {str(e)}")
            label = Gtk.Label(label=f"Error loading protocol options: {str(e)}")
            self.options_box.pack_start(label, False, False, 0)
            self.options_box.show_all()
        
        # Call protocol change callback if set
        if hasattr(self, 'protocol_change_callback') and self.protocol_change_callback and protocol_name:
            _, config = self.get_protocol_config()
            self.protocol_change_callback(protocol_name, config)

    def get_protocol_config(self):
        """Get the selected protocol and configuration.
        
        Returns:
            tuple: (protocol_name, config_dict)
        """
        protocol_name = self.protocol_combo.get_active_text()
        if not protocol_name:
            return None, {}
            
        # Extract values from widgets
        config = {}
        
        for option_name, widget in self.option_widgets.items():
            if isinstance(widget, Gtk.CheckButton):
                config[option_name] = widget.get_active()
                
            elif isinstance(widget, Gtk.SpinButton):
                config[option_name] = widget.get_value_as_int()
                
            elif isinstance(widget, Gtk.ComboBoxText):
                config[option_name] = widget.get_active_text()
                
            elif isinstance(widget, Gtk.Entry):
                config[option_name] = widget.get_text()
        
        return protocol_name, config 

    def get_selected_protocol(self):
        """Get the name of the currently selected protocol.
        
        Returns:
            str: Protocol name or None if none selected
        """
        return self.protocol_combo.get_active_text()

    def set_on_protocol_change_callback(self, callback):
        """Set callback for when protocol configuration changes.
        
        Args:
            callback: Function to call with (protocol_name, config_dict)
        """
        self.protocol_change_callback = callback
        
        # If a protocol is already selected, call the callback immediately
        protocol_name = self.get_selected_protocol()
        if protocol_name and callback:
            _, config = self.get_protocol_config()
            callback(protocol_name, config) 