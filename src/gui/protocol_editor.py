#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Protocol Editor.
A specialized GUI for editing protocol configurations.
"""

import os
import sys
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango


class ProtocolEditor(Gtk.Window):
    """Standalone window for editing protocol configurations."""
    
    def __init__(self):
        """Initialize the protocol editor window."""
        Gtk.Window.__init__(self, title="ERPCT Protocol Editor")
        self.set_default_size(800, 650)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Config file path
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, "protocols.json")
        
        # Protocol data
        self.protocols = []
        self.load_protocols()
        
        # Categories for protocols
        self.categories = [
            "remote_access",
            "file_transfer",
            "web",
            "mail",
            "directory_services",
            "database",
            "other"
        ]
        
        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_box.set_border_width(15)
        self.add(self.main_box)
        
        # Create UI components
        self._create_header()
        self._create_main_ui()
        
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
        title.set_markup("<span size='x-large' weight='bold'>ERPCT Protocol Editor</span>")
        title.set_xalign(0)
        header_box.pack_start(title, False, False, 0)
        
        # Description
        description = Gtk.Label(
            label="Edit protocol configurations for the Enhanced Rapid Password Cracking Tool. "
                 "Add, remove, or modify protocol definitions that can be used for authentication attacks.",
        )
        description.set_xalign(0)
        description.set_line_wrap(True)
        header_box.pack_start(description, False, False, 0)
        
        # Config file
        config_path = Gtk.Label()
        config_path.set_markup(f"<span style='italic'>Config file: {self.config_file}</span>")
        config_path.set_xalign(0)
        header_box.pack_start(config_path, False, False, 5)
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.pack_start(separator, False, False, 5)
        
        self.main_box.pack_start(header_box, False, False, 0)
    
    def _create_main_ui(self):
        """Create the main UI components."""
        # Main panel (horizontal box with protocol list and editor)
        main_panel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        
        # Left side: Protocol list
        list_frame = Gtk.Frame(label="Protocols")
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        list_box.set_border_width(10)
        list_frame.add(list_box)
        
        # Protocol list with scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_size_request(250, -1)
        
        # List store and view
        self.protocol_store = Gtk.ListStore(str, str)  # id, display name
        self.protocol_view = Gtk.TreeView(model=self.protocol_store)
        self.protocol_view.set_headers_visible(True)
        
        # Name column
        name_column = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0)
        name_column.set_sort_column_id(0)
        self.protocol_view.append_column(name_column)
        
        # Display name column
        display_column = Gtk.TreeViewColumn("Display Name", Gtk.CellRendererText(), text=1)
        display_column.set_sort_column_id(1)
        self.protocol_view.append_column(display_column)
        
        # Selection handling
        self.selection = self.protocol_view.get_selection()
        self.selection.connect("changed", self._on_protocol_selected)
        
        # Fill list with protocols
        self._populate_protocol_list()
        
        scrolled_window.add(self.protocol_view)
        list_box.pack_start(scrolled_window, True, True, 0)
        
        # Protocol list buttons
        list_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        # New button
        new_button = Gtk.Button(label="New")
        new_button.connect("clicked", self._on_new_clicked)
        list_buttons.pack_start(new_button, True, True, 0)
        
        # Delete button
        delete_button = Gtk.Button(label="Delete")
        delete_button.connect("clicked", self._on_delete_clicked)
        list_buttons.pack_start(delete_button, True, True, 0)
        
        list_box.pack_end(list_buttons, False, False, 0)
        
        # Right side: Protocol editor
        editor_frame = Gtk.Frame(label="Protocol Details")
        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.editor_box.set_border_width(10)
        editor_frame.add(self.editor_box)
        
        # Editor form
        self._create_editor_form()
        
        # Pack both sides
        main_panel.pack_start(list_frame, False, True, 0)
        main_panel.pack_start(editor_frame, True, True, 0)
        
        # Add to main box
        self.main_box.pack_start(main_panel, True, True, 0)
        
        # Bottom buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Save button
        save_button = Gtk.Button(label="Save All Changes")
        save_button.connect("clicked", self._on_save_clicked)
        button_box.pack_end(save_button, False, False, 0)
        
        # Apply button
        apply_button = Gtk.Button(label="Apply Changes")
        apply_button.connect("clicked", self._on_apply_clicked)
        button_box.pack_end(apply_button, False, False, 0)
        
        self.main_box.pack_end(button_box, False, False, 0)
    
    def _create_editor_form(self):
        """Create the protocol editor form."""
        # Form grid
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(False)
        
        # Row counter
        row = 0
        
        # Protocol Name
        name_label = Gtk.Label(label="Protocol Name:")
        name_label.set_xalign(0)
        grid.attach(name_label, 0, row, 1, 1)
        
        self.name_entry = Gtk.Entry()
        grid.attach(self.name_entry, 1, row, 1, 1)
        
        row += 1
        
        # Display Name
        display_label = Gtk.Label(label="Display Name:")
        display_label.set_xalign(0)
        grid.attach(display_label, 0, row, 1, 1)
        
        self.display_entry = Gtk.Entry()
        grid.attach(self.display_entry, 1, row, 1, 1)
        
        row += 1
        
        # Module Path
        module_label = Gtk.Label(label="Module Path:")
        module_label.set_xalign(0)
        grid.attach(module_label, 0, row, 1, 1)
        
        self.module_entry = Gtk.Entry()
        grid.attach(self.module_entry, 1, row, 1, 1)
        
        row += 1
        
        # Class Name
        class_label = Gtk.Label(label="Class Name:")
        class_label.set_xalign(0)
        grid.attach(class_label, 0, row, 1, 1)
        
        self.class_entry = Gtk.Entry()
        grid.attach(self.class_entry, 1, row, 1, 1)
        
        row += 1
        
        # Category
        category_label = Gtk.Label(label="Category:")
        category_label.set_xalign(0)
        grid.attach(category_label, 0, row, 1, 1)
        
        self.category_combo = Gtk.ComboBoxText()
        for category in self.categories:
            self.category_combo.append_text(category)
        grid.attach(self.category_combo, 1, row, 1, 1)
        
        row += 1
        
        # Description
        desc_label = Gtk.Label(label="Description:")
        desc_label.set_xalign(0)
        grid.attach(desc_label, 0, row, 1, 1)
        
        self.desc_entry = Gtk.Entry()
        grid.attach(self.desc_entry, 1, row, 1, 1)
        
        # Add to editor box
        self.editor_box.pack_start(grid, False, False, 0)
        
        # Info
        info_label = Gtk.Label()
        info_label.set_markup("<i>Note: Changes are applied when you click 'Apply Changes' and saved to disk when you click 'Save All Changes'.</i>")
        info_label.set_xalign(0)
        info_label.set_line_wrap(True)
        self.editor_box.pack_end(info_label, False, False, 10)
    
    def load_protocols(self):
        """Load protocols from the configuration file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.protocols = config.get("protocols", [])
            else:
                self.protocols = []
                self._set_status("Protocol configuration file not found. A new one will be created.", "info")
        except Exception as e:
            self._set_status(f"Error loading protocols: {str(e)}", "error")
            self.protocols = []
    
    def save_protocols(self):
        """Save protocols to the configuration file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump({"protocols": self.protocols}, f, indent=2)
            
            self._set_status("Protocols saved successfully", "success")
            return True
        except Exception as e:
            self._set_status(f"Error saving protocols: {str(e)}", "error")
            return False
    
    def _populate_protocol_list(self):
        """Populate the protocol list from the loaded protocols."""
        self.protocol_store.clear()
        
        for protocol in self.protocols:
            self.protocol_store.append([
                protocol.get("name", ""),
                protocol.get("display_name", "")
            ])
    
    def _on_protocol_selected(self, selection):
        """Handle protocol selection change."""
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            # Get protocol data
            protocol_name = model[treeiter][0]
            
            # Find protocol in list
            for protocol in self.protocols:
                if protocol.get("name") == protocol_name:
                    # Populate form
                    self._populate_form(protocol)
                    break
    
    def _populate_form(self, protocol):
        """Populate form with protocol data."""
        self.name_entry.set_text(protocol.get("name", ""))
        self.display_entry.set_text(protocol.get("display_name", ""))
        self.module_entry.set_text(protocol.get("module", ""))
        self.class_entry.set_text(protocol.get("class", ""))
        self.desc_entry.set_text(protocol.get("description", ""))
        
        # Set category
        category = protocol.get("category", "other")
        for i, cat in enumerate(self.categories):
            if cat == category:
                self.category_combo.set_active(i)
                break
        else:
            # Default to first category
            self.category_combo.set_active(0)
    
    def _clear_form(self):
        """Clear the form fields."""
        self.name_entry.set_text("")
        self.display_entry.set_text("")
        self.module_entry.set_text("src.protocols.")
        self.class_entry.set_text("")
        self.desc_entry.set_text("")
        self.category_combo.set_active(0)
    
    def _on_new_clicked(self, button):
        """Handle new protocol button click."""
        # Clear form
        self._clear_form()
        
        # Clear selection
        self.selection.unselect_all()
        
        self._set_status("Created new protocol. Fill in details and click 'Apply Changes'.", "info")
    
    def _on_delete_clicked(self, button):
        """Handle delete protocol button click."""
        model, treeiter = self.selection.get_selected()
        if treeiter is None:
            self._set_status("No protocol selected", "warning")
            return
        
        protocol_name = model[treeiter][0]
        
        # Confirm deletion
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete protocol '{protocol_name}'?"
        )
        dialog.format_secondary_text("This action cannot be undone.")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Remove from list
            for i, protocol in enumerate(self.protocols):
                if protocol.get("name") == protocol_name:
                    del self.protocols[i]
                    break
            
            # Update list view
            self.protocol_store.remove(treeiter)
            
            # Clear form
            self._clear_form()
            
            self._set_status(f"Deleted protocol '{protocol_name}'", "success")
    
    def _on_apply_clicked(self, button):
        """Handle apply changes button click."""
        # Get values from form
        name = self.name_entry.get_text().strip()
        display_name = self.display_entry.get_text().strip()
        module = self.module_entry.get_text().strip()
        class_name = self.class_entry.get_text().strip()
        description = self.desc_entry.get_text().strip()
        category = self.category_combo.get_active_text() or "other"
        
        # Validate
        if not name:
            self._set_status("Protocol name is required", "error")
            return
        
        if not module:
            self._set_status("Module path is required", "error")
            return
        
        if not class_name:
            self._set_status("Class name is required", "error")
            return
        
        # Check if selected in list
        model, treeiter = self.selection.get_selected()
        if treeiter is None:
            # New protocol
            
            # Check for existing protocol with same name
            for protocol in self.protocols:
                if protocol.get("name") == name:
                    self._set_status(f"Protocol with name '{name}' already exists", "error")
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
            
            # Add to list
            self.protocols.append(new_protocol)
            
            # Add to tree view
            new_iter = self.protocol_store.append([name, display_name])
            
            # Select new item
            self.selection.select_iter(new_iter)
            
            self._set_status(f"Added new protocol '{name}'", "success")
        else:
            # Update existing protocol
            old_name = model[treeiter][0]
            
            # Check for name change collision
            if name != old_name:
                for protocol in self.protocols:
                    if protocol.get("name") == name:
                        self._set_status(f"Protocol with name '{name}' already exists", "error")
                        return
            
            # Update protocol
            for protocol in self.protocols:
                if protocol.get("name") == old_name:
                    protocol["name"] = name
                    protocol["display_name"] = display_name
                    protocol["module"] = module
                    protocol["class"] = class_name
                    protocol["description"] = description
                    protocol["category"] = category
                    break
            
            # Update tree view
            model[treeiter][0] = name
            model[treeiter][1] = display_name
            
            self._set_status(f"Updated protocol '{name}'", "success")
    
    def _on_save_clicked(self, button):
        """Handle save button click."""
        self.save_protocols()
    
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
        """Handle window close event."""
        # Check for unsaved changes
        # For simplicity, always ask
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Exit Protocol Editor"
        )
        dialog.format_secondary_text("Save changes before exiting?")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self.save_protocols()
        
        Gtk.main_quit()
        return False


def main():
    """Run the protocol editor application."""
    app = ProtocolEditor()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main()) 