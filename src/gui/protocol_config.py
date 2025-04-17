#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Protocol Configuration Generator.
This module provides a specialized GUI for editing protocol configurations.
"""

import os
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango

from src.utils.logging import get_logger
from src.utils.config import get_config_dir
from src.protocols import get_all_protocols, get_protocol, protocol_exists


class ProtocolConfigGenerator(Gtk.Box):
    """Protocol configuration generator panel."""
    
    def __init__(self):
        """Initialize the protocol configuration generator panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Load existing protocols config
        self.protocols_data = self._load_protocols_config()
        
        # Create UI components
        self._create_header()
        self._create_protocol_list()
        self._create_editor()
        self._create_buttons()
        
        self.show_all()
    
    def _create_header(self):
        """Create header with description and instructions."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        title = Gtk.Label(label="<b>Protocol Configuration Generator</b>", xalign=0)
        title.set_use_markup(True)
        header_box.pack_start(title, False, False, 0)
        
        description = Gtk.Label(
            label="Manage protocol configurations for ERPCT. "
                  "Add, edit, or remove protocols from the system configuration.",
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
    
    def _create_protocol_list(self):
        """Create protocol list and management controls."""
        # Main box for protocol list and controls
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        # Protocol list with scrolled window
        list_frame = Gtk.Frame(label="Configured Protocols")
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        scrolled_window.set_size_request(-1, 150)  # Set minimum height
        
        # ListStore model: protocol name, display name
        self.protocol_store = Gtk.ListStore(str, str)
        
        # Create TreeView
        self.protocol_view = Gtk.TreeView(model=self.protocol_store)
        
        # Create columns
        name_column = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0)
        name_column.set_sort_column_id(0)
        self.protocol_view.append_column(name_column)
        
        display_column = Gtk.TreeViewColumn("Display Name", Gtk.CellRendererText(), text=1)
        display_column.set_sort_column_id(1)
        self.protocol_view.append_column(display_column)
        
        # Selection
        self.protocol_selection = self.protocol_view.get_selection()
        self.protocol_selection.connect("changed", self._on_protocol_selected)
        
        # Populate the list
        self._populate_protocol_list()
        
        scrolled_window.add(self.protocol_view)
        list_frame.add(scrolled_window)
        list_box.pack_start(list_frame, True, True, 0)
        
        # Protocol management buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        new_button = Gtk.Button(label="New Protocol")
        new_button.connect("clicked", self._on_new_protocol)
        button_box.pack_start(new_button, False, False, 0)
        
        delete_button = Gtk.Button(label="Delete Protocol")
        delete_button.connect("clicked", self._on_delete_protocol)
        button_box.pack_start(delete_button, False, False, 0)
        
        list_box.pack_start(button_box, False, False, 0)
        
        self.pack_start(list_box, False, False, 0)
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(separator, False, False, 10)
    
    def _create_editor(self):
        """Create protocol editor form."""
        editor_frame = Gtk.Frame(label="Protocol Properties")
        
        # Grid for form layout
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(6)
        grid.set_border_width(10)
        
        # Form fields
        row = 0
        
        # Name field
        name_label = Gtk.Label(label="Name:", xalign=0)
        grid.attach(name_label, 0, row, 1, 1)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_width_chars(30)
        grid.attach(self.name_entry, 1, row, 1, 1)
        
        row += 1
        
        # Display name field
        display_name_label = Gtk.Label(label="Display Name:", xalign=0)
        grid.attach(display_name_label, 0, row, 1, 1)
        self.display_name_entry = Gtk.Entry()
        grid.attach(self.display_name_entry, 1, row, 1, 1)
        
        row += 1
        
        # Module field
        module_label = Gtk.Label(label="Module:", xalign=0)
        grid.attach(module_label, 0, row, 1, 1)
        self.module_entry = Gtk.Entry()
        grid.attach(self.module_entry, 1, row, 1, 1)
        
        row += 1
        
        # Class field
        class_label = Gtk.Label(label="Class:", xalign=0)
        grid.attach(class_label, 0, row, 1, 1)
        self.class_entry = Gtk.Entry()
        grid.attach(self.class_entry, 1, row, 1, 1)
        
        row += 1
        
        # Description field
        description_label = Gtk.Label(label="Description:", xalign=0)
        grid.attach(description_label, 0, row, 1, 1)
        self.description_entry = Gtk.Entry()
        grid.attach(self.description_entry, 1, row, 1, 1)
        
        row += 1
        
        # Category field
        category_label = Gtk.Label(label="Category:", xalign=0)
        grid.attach(category_label, 0, row, 1, 1)
        
        # Category combo box
        self.category_combo = Gtk.ComboBoxText()
        categories = [
            "remote_access",
            "file_transfer",
            "web",
            "mail",
            "directory_services",
            "database",
            "other"
        ]
        for category in categories:
            self.category_combo.append_text(category)
        grid.attach(self.category_combo, 1, row, 1, 1)
        
        editor_frame.add(grid)
        self.pack_start(editor_frame, False, False, 0)
    
    def _create_buttons(self):
        """Create save/apply buttons."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Apply changes to selected protocol
        apply_button = Gtk.Button(label="Apply Changes")
        apply_button.connect("clicked", self._on_apply_clicked)
        button_box.pack_start(apply_button, False, False, 0)
        
        # Spacer
        button_box.pack_start(Gtk.Box(), True, True, 0)
        
        # Save all changes to config file
        save_all_button = Gtk.Button(label="Save All Changes")
        save_all_button.connect("clicked", self._on_save_all_clicked)
        button_box.pack_start(save_all_button, False, False, 0)
        
        self.pack_start(button_box, False, False, 10)
    
    def _load_protocols_config(self):
        """Load the protocols configuration file.
        
        Returns:
            Dictionary with protocols configuration
        """
        # Try to load from user config first
        config_dir = get_config_dir()
        user_config_path = os.path.join(config_dir, "protocols.json")
        
        if os.path.exists(user_config_path):
            try:
                with open(user_config_path, 'r') as f:
                    config_data = json.load(f)
                    self.logger.debug(f"Loaded protocols config from {user_config_path}")
                    return config_data
            except Exception as e:
                self.logger.error(f"Error loading user protocols config: {str(e)}")
        
        # Try package default config
        package_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config", 
            "protocols.json"
        )
        
        if os.path.exists(package_config_path):
            try:
                with open(package_config_path, 'r') as f:
                    config_data = json.load(f)
                    self.logger.debug(f"Loaded default protocols config from {package_config_path}")
                    return config_data
            except Exception as e:
                self.logger.error(f"Error loading default protocols config: {str(e)}")
        
        # No config found, return empty structure
        return {"protocols": []}
    
    def _save_protocols_config(self):
        """Save the protocols configuration to file."""
        config_dir = get_config_dir()
        config_path = os.path.join(config_dir, "protocols.json")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(self.protocols_data, f, indent=2)
                
            self.logger.info(f"Saved protocols config to {config_path}")
            self.status_label.set_markup("<span foreground='green'>Configuration saved successfully</span>")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving protocols config: {str(e)}")
            self.status_label.set_markup(f"<span foreground='red'>Error saving: {str(e)}</span>")
            return False
    
    def _populate_protocol_list(self):
        """Populate the protocol list from the configuration."""
        # Clear existing entries
        self.protocol_store.clear()
        
        # Add protocols from config
        for protocol in self.protocols_data.get("protocols", []):
            self.protocol_store.append([
                protocol.get("name", ""),
                protocol.get("display_name", "")
            ])
    
    def _on_protocol_selected(self, selection):
        """Handle protocol selection change."""
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            # Get protocol name
            protocol_name = model[treeiter][0]
            
            # Find protocol in config
            for protocol in self.protocols_data.get("protocols", []):
                if protocol.get("name") == protocol_name:
                    # Populate form with protocol data
                    self.name_entry.set_text(protocol.get("name", ""))
                    self.display_name_entry.set_text(protocol.get("display_name", ""))
                    self.module_entry.set_text(protocol.get("module", ""))
                    self.class_entry.set_text(protocol.get("class", ""))
                    self.description_entry.set_text(protocol.get("description", ""))
                    
                    # Set category
                    category = protocol.get("category", "")
                    category_model = self.category_combo.get_model()
                    for i, row in enumerate(category_model):
                        if row[0] == category:
                            self.category_combo.set_active(i)
                            break
                    else:
                        # Category not found, set to first option
                        self.category_combo.set_active(0)
                    
                    break
    
    def _on_new_protocol(self, button):
        """Handle new protocol button click."""
        # Clear form
        self.name_entry.set_text("")
        self.display_name_entry.set_text("")
        self.module_entry.set_text("src.protocols.")
        self.class_entry.set_text("")
        self.description_entry.set_text("")
        self.category_combo.set_active(0)
        
        # Clear selection
        self.protocol_selection.unselect_all()
    
    def _on_delete_protocol(self, button):
        """Handle delete protocol button click."""
        model, treeiter = self.protocol_selection.get_selected()
        if treeiter is None:
            self.status_label.set_markup("<span foreground='red'>No protocol selected</span>")
            return
            
        protocol_name = model[treeiter][0]
        
        # Confirm deletion
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete protocol '{protocol_name}'?"
        )
        dialog.format_secondary_text(
            "This will remove the protocol from the configuration."
        )
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Remove protocol from data
            protocols = self.protocols_data.get("protocols", [])
            for i, protocol in enumerate(protocols):
                if protocol.get("name") == protocol_name:
                    del protocols[i]
                    break
                    
            # Update list
            self.protocol_store.remove(treeiter)
            
            # Clear form
            self.name_entry.set_text("")
            self.display_name_entry.set_text("")
            self.module_entry.set_text("")
            self.class_entry.set_text("")
            self.description_entry.set_text("")
            self.category_combo.set_active(0)
            
            self.status_label.set_markup(f"<span foreground='green'>Deleted protocol '{protocol_name}'</span>")
    
    def _on_apply_clicked(self, button):
        """Apply changes to the selected protocol or create a new one."""
        # Get form data
        name = self.name_entry.get_text().strip()
        display_name = self.display_name_entry.get_text().strip()
        module = self.module_entry.get_text().strip()
        class_name = self.class_entry.get_text().strip()
        description = self.description_entry.get_text().strip()
        category = self.category_combo.get_active_text() or "other"
        
        # Validate required fields
        if not name:
            self.status_label.set_markup("<span foreground='red'>Protocol name is required</span>")
            return
            
        if not module:
            self.status_label.set_markup("<span foreground='red'>Module path is required</span>")
            return
            
        if not class_name:
            self.status_label.set_markup("<span foreground='red'>Class name is required</span>")
            return
        
        # Check if this is an update or new protocol
        is_update = False
        model, treeiter = self.protocol_selection.get_selected()
        
        if treeiter is not None:
            selected_name = model[treeiter][0]
            
            # If name changed, check if it already exists
            if name != selected_name:
                for protocol in self.protocols_data.get("protocols", []):
                    if protocol.get("name") == name:
                        self.status_label.set_markup(
                            f"<span foreground='red'>Protocol with name '{name}' already exists</span>"
                        )
                        return
            
            # This is an update
            is_update = True
            
            # Update data
            for protocol in self.protocols_data.get("protocols", []):
                if protocol.get("name") == selected_name:
                    protocol["name"] = name
                    protocol["display_name"] = display_name
                    protocol["module"] = module
                    protocol["class"] = class_name
                    protocol["description"] = description
                    protocol["category"] = category
                    break
                    
            # Update list view
            model[treeiter][0] = name
            model[treeiter][1] = display_name
            
        else:
            # This is a new protocol, check if name already exists
            for protocol in self.protocols_data.get("protocols", []):
                if protocol.get("name") == name:
                    self.status_label.set_markup(
                        f"<span foreground='red'>Protocol with name '{name}' already exists</span>"
                    )
                    return
            
            # Create new protocol
            new_protocol = {
                "name": name,
                "display_name": display_name,
                "module": module,
                "class": class_name,
                "description": description,
                "category": category
            }
            
            # Add to data
            if "protocols" not in self.protocols_data:
                self.protocols_data["protocols"] = []
                
            self.protocols_data["protocols"].append(new_protocol)
            
            # Add to list view
            treeiter = self.protocol_store.append([name, display_name])
            
            # Select the new protocol
            self.protocol_selection.select_iter(treeiter)
        
        # Update status
        if is_update:
            self.status_label.set_markup(f"<span foreground='green'>Updated protocol '{name}'</span>")
        else:
            self.status_label.set_markup(f"<span foreground='green'>Created protocol '{name}'</span>")
    
    def _on_save_all_clicked(self, button):
        """Save all changes to the config file."""
        self._save_protocols_config() 