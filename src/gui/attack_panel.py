#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Attack Panel component.
This module provides the GUI panel for configuring attack parameters.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

# Updated import for the new protocol registry system
from src.protocols import get_all_protocols, get_protocol
from src.utils.logging import get_logger


class AttackPanel(Gtk.Box):
    """Attack configuration panel."""
    
    def __init__(self):
        """Initialize the attack panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        # Initialize logger
        self.logger = get_logger(__name__)
        
        # Dictionary to store protocol-specific field widgets
        self.protocol_fields = {}
        
        # Attack configuration section
        self._create_protocol_selector()
        self._create_attack_options()
        self._create_threading_options()
        
        # Create a button to start the attack
        self.start_button = Gtk.Button(label="Start Attack")
        self.start_button.connect("clicked", self._on_start_clicked)
        self.pack_end(self.start_button, False, False, 0)
        
        # Callback for when attack is started
        self.start_attack_callback = None
        
        # Select the first protocol by default if available
        if len(self.protocol_store) > 0:
            self.protocol_combo.set_active(0)
            self.logger.debug("Selected first protocol by default")
        else:
            self.logger.warning("No protocols available to select")
    
    def _create_protocol_selector(self):
        """Create protocol selection widgets."""
        frame = Gtk.Frame(label="Protocol")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Protocol combo box
        protocol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        protocol_label = Gtk.Label(label="Protocol:")
        protocol_box.pack_start(protocol_label, False, False, 0)
        
        # Create protocol store and combo box
        self.protocol_store = Gtk.ListStore(str, str)  # id, display name
        
        # Add protocols from registry - updated to use the new method
        protocols = get_all_protocols()
        for name, _ in protocols.items():
            self.protocol_store.append([name, name])
        
        self.protocol_combo = Gtk.ComboBox.new_with_model(self.protocol_store)
        renderer_text = Gtk.CellRendererText()
        self.protocol_combo.pack_start(renderer_text, True)
        self.protocol_combo.add_attribute(renderer_text, "text", 1)
        self.protocol_combo.connect("changed", self._on_protocol_changed)
        protocol_box.pack_start(self.protocol_combo, True, True, 0)
        
        box.pack_start(protocol_box, False, False, 0)
        
        # Container for protocol-specific options
        self.protocol_options_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.pack_start(self.protocol_options_container, False, False, 0)
    
    def _create_attack_options(self):
        """Create widgets for attack options."""
        frame = Gtk.Frame(label="Attack Options")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Username/password ordering options
        order_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        order_label = Gtk.Label(label="Attack order:")
        order_box.pack_start(order_label, False, False, 0)
        
        self.username_first_radio = Gtk.RadioButton.new_with_label_from_widget(None, "Try all passwords for each username")
        order_box.pack_start(self.username_first_radio, False, False, 0)
        
        self.password_first_radio = Gtk.RadioButton.new_with_label_from_widget(
            self.username_first_radio, "Try all usernames for each password")
        order_box.pack_start(self.password_first_radio, False, False, 0)
        
        box.pack_start(order_box, False, False, 0)
        
        # Username and password file selection
        user_file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_file_label = Gtk.Label(label="Username file:")
        user_file_box.pack_start(user_file_label, False, False, 0)
        
        self.username_file_entry = Gtk.Entry()
        user_file_box.pack_start(self.username_file_entry, True, True, 0)
        
        username_file_button = Gtk.Button(label="Browse...")
        username_file_button.connect("clicked", self._on_username_file_clicked)
        user_file_box.pack_start(username_file_button, False, False, 0)
        
        box.pack_start(user_file_box, False, False, 0)
        
        # Single username entry
        single_user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        single_user_label = Gtk.Label(label="Single username:")
        single_user_box.pack_start(single_user_label, False, False, 0)
        
        self.single_username_entry = Gtk.Entry()
        single_user_box.pack_start(self.single_username_entry, True, True, 0)
        
        box.pack_start(single_user_box, False, False, 0)
        
        # Password file selection
        pass_file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pass_file_label = Gtk.Label(label="Password file:")
        pass_file_box.pack_start(pass_file_label, False, False, 0)
        
        self.password_file_entry = Gtk.Entry()
        pass_file_box.pack_start(self.password_file_entry, True, True, 0)
        
        password_file_button = Gtk.Button(label="Browse...")
        password_file_button.connect("clicked", self._on_password_file_clicked)
        pass_file_box.pack_start(password_file_button, False, False, 0)
        
        box.pack_start(pass_file_box, False, False, 0)
        
        # Single password entry
        single_pass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        single_pass_label = Gtk.Label(label="Single password:")
        single_pass_box.pack_start(single_pass_label, False, False, 0)
        
        self.single_password_entry = Gtk.Entry()
        single_pass_box.pack_start(self.single_password_entry, True, True, 0)
        
        box.pack_start(single_pass_box, False, False, 0)
    
    def _create_threading_options(self):
        """Create widgets for threading options."""
        frame = Gtk.Frame(label="Performance")
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Threads option
        threads_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        threads_label = Gtk.Label(label="Threads:")
        threads_box.pack_start(threads_label, False, False, 0)
        
        self.threads_adjustment = Gtk.Adjustment(value=1, lower=1, upper=100, step_increment=1, page_increment=10)
        self.threads_spin = Gtk.SpinButton()
        self.threads_spin.set_adjustment(self.threads_adjustment)
        threads_box.pack_start(self.threads_spin, False, False, 0)
        
        box.pack_start(threads_box, False, False, 0)
        
        # Delay option
        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        delay_label = Gtk.Label(label="Delay (seconds):")
        delay_box.pack_start(delay_label, False, False, 0)
        
        self.delay_adjustment = Gtk.Adjustment(value=0, lower=0, upper=60, step_increment=0.1, page_increment=1)
        self.delay_spin = Gtk.SpinButton()
        self.delay_spin.set_adjustment(self.delay_adjustment)
        self.delay_spin.set_digits(1)
        delay_box.pack_start(self.delay_spin, False, False, 0)
        
        box.pack_start(delay_box, False, False, 0)
        
        # Timeout option
        timeout_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        timeout_label = Gtk.Label(label="Timeout (seconds):")
        timeout_box.pack_start(timeout_label, False, False, 0)
        
        self.timeout_adjustment = Gtk.Adjustment(value=10, lower=1, upper=60, step_increment=1, page_increment=5)
        self.timeout_spin = Gtk.SpinButton()
        self.timeout_spin.set_adjustment(self.timeout_adjustment)
        timeout_box.pack_start(self.timeout_spin, False, False, 0)
        
        box.pack_start(timeout_box, False, False, 0)
    
    def _on_username_file_clicked(self, button):
        """Handle username file button click."""
        dialog = Gtk.FileChooserDialog(
            title="Select Username File",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.username_file_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _on_password_file_clicked(self, button):
        """Handle password file button click."""
        dialog = Gtk.FileChooserDialog(
            title="Select Password File",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.password_file_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _create_field_for_property(self, property_name, property_def, container):
        """Create appropriate GUI field based on property definition.
        
        Args:
            property_name: Name of the property
            property_def: Property definition from schema
            container: Container to add the field to
            
        Returns:
            Created widget for the field
        """
        field_type = property_def.get("type", "string")
        title = property_def.get("title", property_name.capitalize())
        description = property_def.get("description", "")
        default = property_def.get("default", "")
        
        # Create container for the field
        field_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Create label
        label = Gtk.Label(label=f"{title}:")
        label.set_tooltip_text(description)
        field_box.pack_start(label, False, False, 0)
        
        # Create appropriate widget based on type
        widget = None
        
        if field_type == "boolean":
            widget = Gtk.CheckButton()
            widget.set_active(bool(default))
            field_box.pack_start(widget, False, False, 0)
            
        elif field_type == "integer":
            min_val = property_def.get("minimum", 0)
            max_val = property_def.get("maximum", 65535)
            adjustment = Gtk.Adjustment(value=default or min_val, 
                                        lower=min_val, 
                                        upper=max_val, 
                                        step_increment=1, 
                                        page_increment=10)
            widget = Gtk.SpinButton()
            widget.set_adjustment(adjustment)
            field_box.pack_start(widget, True, True, 0)
            
        elif field_type == "number":
            min_val = property_def.get("minimum", 0.0)
            max_val = property_def.get("maximum", 1000.0)
            adjustment = Gtk.Adjustment(value=default or min_val, 
                                        lower=min_val, 
                                        upper=max_val, 
                                        step_increment=0.1, 
                                        page_increment=1.0)
            widget = Gtk.SpinButton()
            widget.set_adjustment(adjustment)
            widget.set_digits(2)
            field_box.pack_start(widget, True, True, 0)
            
        elif field_type == "string" and property_def.get("enum"):
            # Create combo box for enum values
            store = Gtk.ListStore(str)
            for item in property_def.get("enum", []):
                store.append([str(item)])
                
            widget = Gtk.ComboBoxText.new_with_entry()
            widget.set_model(store)
            
            # Set default if provided
            if default:
                widget.get_child().set_text(str(default))
                
            field_box.pack_start(widget, True, True, 0)
            
        else:  # Default to string entry
            widget = Gtk.Entry()
            if default is not None:
                widget.set_text(str(default))
            field_box.pack_start(widget, True, True, 0)
        
        # Add tooltip to widget
        if widget and description:
            widget.set_tooltip_text(description)
        
        # Add to container
        container.pack_start(field_box, False, False, 0)
        
        return widget
    
    def _on_protocol_changed(self, combo):
        """Handle protocol selection change.
        
        Args:
            combo: ComboBox that triggered the event
        """
        # Clear protocol options container
        for child in self.protocol_options_container.get_children():
            self.protocol_options_container.remove(child)
        
        # Clear protocol fields dictionary
        self.protocol_fields = {}
        
        # Get selected protocol
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            protocol_id = model[tree_iter][0]
            
            try:
                # Get protocol class
                protocol_class = get_protocol(protocol_id)
                
                # Create dummy config for initialization
                dummy_config = {"host": "example.com"}
                
                # Create instance to get schema
                try:
                    protocol_instance = protocol_class(dummy_config)
                    schema = protocol_instance.get_config_schema()
                    
                    # Create fields for each property in schema
                    if schema and "properties" in schema:
                        properties = schema.get("properties", {})
                        for prop_name, prop_def in properties.items():
                            # Skip username and password as they're handled separately
                            if prop_name in ["username", "password"]:
                                continue
                                
                            # Create field for property
                            widget = self._create_field_for_property(
                                prop_name, prop_def, self.protocol_options_container)
                            
                            # Store widget for later retrieval
                            self.protocol_fields[prop_name] = widget
                    
                except Exception as e:
                    self.logger.error(f"Error creating protocol instance: {str(e)}")
                    error_label = Gtk.Label(label=f"Error: {str(e)}")
                    error_label.set_line_wrap(True)
                    self.protocol_options_container.pack_start(error_label, False, False, 0)
                
            except ValueError as e:
                self.logger.error(f"Error getting protocol {protocol_id}: {str(e)}")
                error_label = Gtk.Label(label=f"Error: {str(e)}")
                self.protocol_options_container.pack_start(error_label, False, False, 0)
        
        # Show all widgets
        self.protocol_options_container.show_all()
    
    def _get_widget_value(self, widget):
        """Get value from a widget based on its type.
        
        Args:
            widget: GTK widget
            
        Returns:
            Value from the widget
        """
        if isinstance(widget, Gtk.CheckButton):
            return widget.get_active()
        elif isinstance(widget, Gtk.SpinButton):
            if widget.get_digits() > 0:
                return widget.get_value()
            else:
                return widget.get_value_as_int()
        elif isinstance(widget, Gtk.ComboBoxText):
            return widget.get_active_text()
        elif isinstance(widget, Gtk.Entry):
            return widget.get_text()
        else:
            return None
    
    def _on_start_clicked(self, button):
        """Handle start button click.
        
        Args:
            button: Button that triggered the event
        """
        if self.start_attack_callback:
            # Collect attack configuration
            config = self.get_attack_config()
            self.start_attack_callback(config)
    
    def get_attack_config(self):
        """Get the current attack configuration.
        
        Returns:
            Dictionary with attack configuration
        """
        config = {
            "threads": self.threads_spin.get_value_as_int(),
            "delay": self.delay_spin.get_value(),
            "timeout": self.timeout_spin.get_value_as_int(),
            "username_first": self.username_first_radio.get_active(),
            "protocol": ""  # Default to empty string
        }
        
        # Get selected protocol
        tree_iter = self.protocol_combo.get_active_iter()
        if tree_iter is not None:
            model = self.protocol_combo.get_model()
            config["protocol"] = model[tree_iter][0]
            self.logger.debug(f"Selected protocol: {config['protocol']}")
        else:
            # If no protocol is selected but there are protocols available, select the first one
            if len(self.protocol_store) > 0:
                self.protocol_combo.set_active(0)
                tree_iter = self.protocol_combo.get_active_iter()
                if tree_iter is not None:
                    model = self.protocol_combo.get_model()
                    config["protocol"] = model[tree_iter][0]
                    self.logger.debug(f"Automatically selected protocol: {config['protocol']}")
                else:
                    self.logger.warning("Failed to select protocol automatically")
            else:
                self.logger.warning("No protocols available")
        
        # Add username/password information
        username = self.single_username_entry.get_text().strip()
        if username:
            config["username"] = username
            
        password = self.single_password_entry.get_text().strip()
        if password:
            config["password"] = password
            
        username_file = self.username_file_entry.get_text().strip()
        if username_file:
            config["username_list"] = username_file
            
        password_file = self.password_file_entry.get_text().strip()
        if password_file:
            config["wordlist"] = password_file
            
        # Add protocol-specific options
        for field_name, widget in self.protocol_fields.items():
            value = self._get_widget_value(widget)
            if value is not None and value != "":
                config[field_name] = value
        
        return config
    
    def set_start_attack_callback(self, callback):
        """Set callback for when the start button is clicked.
        
        Args:
            callback: Function to call with attack configuration
        """
        self.start_attack_callback = callback
