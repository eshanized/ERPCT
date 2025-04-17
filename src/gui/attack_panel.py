#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Attack Panel component.
This module provides the GUI panel for configuring attack parameters.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from src.protocols import protocol_registry


class AttackPanel(Gtk.Box):
    """Attack configuration panel."""
    
    def __init__(self):
        """Initialize the attack panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
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
        
        # Add protocols from registry
        protocols = protocol_registry.get_all_protocols()
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
    
    def _on_protocol_changed(self, combo):
        """Handle protocol selection change.
        
        Args:
            combo: ComboBox that triggered the event
        """
        # Clear protocol options container
        for child in self.protocol_options_container.get_children():
            self.protocol_options_container.remove(child)
        
        # Get selected protocol
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            protocol_id = model[tree_iter][0]
            
            # TODO: Create protocol-specific options based on protocol schema
    
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
            "username_first": self.username_first_radio.get_active()
        }
        
        # Get selected protocol
        tree_iter = self.protocol_combo.get_active_iter()
        if tree_iter is not None:
            model = self.protocol_combo.get_model()
            config["protocol"] = model[tree_iter][0]
        
        return config
    
    def set_start_attack_callback(self, callback):
        """Set callback for when the start button is clicked.
        
        Args:
            callback: Function to call with attack configuration
        """
        self.start_attack_callback = callback
