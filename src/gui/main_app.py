#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT GUI Application.
Main entry point for the Enhanced Rapid Password Cracking Tool GUI.
"""

import os
import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango

# Import our custom modules
from src.gui.config_manager import ConfigManager
from src.gui.protocol_editor import ProtocolEditor


class MainApplication(Gtk.Window):
    """Main ERPCT application window."""
    
    def __init__(self):
        """Initialize the main application window."""
        Gtk.Window.__init__(self, title="ERPCT - Enhanced Rapid Password Cracking Tool")
        self.set_default_size(960, 720)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Setup icon if available
        try:
            self.set_icon_from_file(os.path.join(os.path.dirname(__file__), "../../assets/icon.png"))
        except:
            pass
        
        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_box.set_border_width(15)
        self.add(self.main_box)
        
        # Create UI components
        self._create_header()
        self._create_dashboard()
        
        # Status bar
        self.status_bar = Gtk.Label()
        self.status_bar.set_xalign(0)
        self.main_box.pack_end(self.status_bar, False, False, 5)
        
        # Show all widgets
        self.show_all()
        
        # Connect delete event
        self.connect("delete-event", Gtk.main_quit)
    
    def _create_header(self):
        """Create header with title and description."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>ERPCT</span>")
        title.set_xalign(0)
        header_box.pack_start(title, False, False, 0)
        
        # Description
        description = Gtk.Label(
            label="Enhanced Rapid Password Cracking Tool - Configuration & Management Interface",
        )
        description.set_xalign(0)
        description.set_line_wrap(True)
        header_box.pack_start(description, False, False, 0)
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.pack_start(separator, False, False, 5)
        
        self.main_box.pack_start(header_box, False, False, 0)
    
    def _create_dashboard(self):
        """Create the main dashboard with action buttons."""
        # Create a grid for the dashboard items
        dashboard_grid = Gtk.Grid()
        dashboard_grid.set_column_spacing(20)
        dashboard_grid.set_row_spacing(20)
        dashboard_grid.set_column_homogeneous(True)
        
        # Configuration editors
        config_title = Gtk.Label()
        config_title.set_markup("<span size='large' weight='bold'>Configuration</span>")
        config_title.set_xalign(0)
        dashboard_grid.attach(config_title, 0, 0, 2, 1)
        
        # General Config Editor
        config_btn = self._create_dashboard_button(
            "General Configuration",
            "Edit system-wide settings and preferences",
            "document-properties-symbolic"
        )
        config_btn.connect("clicked", self._on_config_clicked)
        dashboard_grid.attach(config_btn, 0, 1, 1, 1)
        
        # Protocol Editor
        protocol_btn = self._create_dashboard_button(
            "Protocol Editor",
            "Manage authentication protocols for password attacks",
            "network-wired-symbolic"
        )
        protocol_btn.connect("clicked", self._on_protocol_clicked)
        dashboard_grid.attach(protocol_btn, 1, 1, 1, 1)
        
        # Attack tools
        attack_title = Gtk.Label()
        attack_title.set_markup("<span size='large' weight='bold'>Attack Tools</span>")
        attack_title.set_xalign(0)
        dashboard_grid.attach(attack_title, 0, 2, 2, 1)
        
        # Quick Attack
        quick_btn = self._create_dashboard_button(
            "Quick Attack",
            "Start a simple password attack with minimal configuration",
            "media-playback-start-symbolic"
        )
        quick_btn.connect("clicked", self._on_quick_attack_clicked)
        dashboard_grid.attach(quick_btn, 0, 3, 1, 1)
        
        # Advanced Attack
        adv_btn = self._create_dashboard_button(
            "Advanced Attack",
            "Configure and launch a customized password attack",
            "emblem-system-symbolic"
        )
        adv_btn.connect("clicked", self._on_advanced_attack_clicked)
        dashboard_grid.attach(adv_btn, 1, 3, 1, 1)
        
        # Utilities
        utils_title = Gtk.Label()
        utils_title.set_markup("<span size='large' weight='bold'>Utilities</span>")
        utils_title.set_xalign(0)
        dashboard_grid.attach(utils_title, 0, 4, 2, 1)
        
        # Wordlist Manager
        wordlist_btn = self._create_dashboard_button(
            "Wordlist Manager",
            "Manage and customize wordlists for attacks",
            "format-text-symbolic"
        )
        wordlist_btn.connect("clicked", self._on_wordlist_clicked)
        dashboard_grid.attach(wordlist_btn, 0, 5, 1, 1)
        
        # Results Viewer
        results_btn = self._create_dashboard_button(
            "Results Viewer",
            "View and analyze attack results",
            "document-open-recent-symbolic"
        )
        results_btn.connect("clicked", self._on_results_clicked)
        dashboard_grid.attach(results_btn, 1, 5, 1, 1)
        
        # Add to main box
        self.main_box.pack_start(dashboard_grid, True, True, 0)
    
    def _create_dashboard_button(self, title, description, icon_name):
        """Create a stylish dashboard button with icon, title and description.
        
        Args:
            title: Button title
            description: Button description
            icon_name: Icon name
            
        Returns:
            A Gtk.Button with custom styling
        """
        button = Gtk.Button()
        
        # Container for button contents
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(15)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        box.pack_start(icon, False, False, 0)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup(f"<span weight='bold' size='large'>{title}</span>")
        box.pack_start(title_label, False, False, 0)
        
        # Description
        desc_label = Gtk.Label(label=description)
        desc_label.set_line_wrap(True)
        desc_label.set_max_width_chars(25)
        desc_label.set_justify(Gtk.Justification.CENTER)
        box.pack_start(desc_label, False, False, 0)
        
        button.add(box)
        return button
    
    def _on_config_clicked(self, button):
        """Open the configuration manager."""
        config_app = ConfigManager()
        config_app.connect("delete-event", lambda w, e: w.destroy())
        config_app.show_all()
    
    def _on_protocol_clicked(self, button):
        """Open the protocol editor."""
        protocol_app = ProtocolEditor()
        protocol_app.connect("delete-event", lambda w, e: w.destroy())
        protocol_app.show_all()
    
    def _on_quick_attack_clicked(self, button):
        """Launch quick attack dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Quick Attack Feature"
        )
        dialog.format_secondary_text("This feature is not yet implemented.")
        dialog.run()
        dialog.destroy()
    
    def _on_advanced_attack_clicked(self, button):
        """Launch advanced attack configuration."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Advanced Attack Feature"
        )
        dialog.format_secondary_text("This feature is not yet implemented.")
        dialog.run()
        dialog.destroy()
    
    def _on_wordlist_clicked(self, button):
        """Open wordlist manager."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Wordlist Manager"
        )
        dialog.format_secondary_text("This feature is not yet implemented.")
        dialog.run()
        dialog.destroy()
    
    def _on_results_clicked(self, button):
        """Open results viewer."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Results Viewer"
        )
        dialog.format_secondary_text("This feature is not yet implemented.")
        dialog.run()
        dialog.destroy()


def main():
    """Run the main application."""
    app = MainApplication()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main()) 