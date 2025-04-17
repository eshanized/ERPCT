#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simplified ERPCT GUI.
This script provides a simplified version of the ERPCT GUI to isolate issues.
"""

import os
import sys
import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("simple_erpct.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("simple_erpct")

class SimpleMainWindow(Gtk.ApplicationWindow):
    """Simple main window for ERPCT."""
    
    def __init__(self, application):
        """Initialize the window."""
        logger.info("Creating main window")
        Gtk.ApplicationWindow.__init__(self, application=application)
        self.set_title("ERPCT - Simplified Version")
        self.set_default_size(1000, 700)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Create main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.main_box.set_border_width(10)
        self.add(self.main_box)
        
        # Header bar
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.props.title = "ERPCT"
        self.set_titlebar(self.header)
        
        # Create notebook
        self.notebook = Gtk.Notebook()
        self.main_box.pack_start(self.notebook, True, True, 0)
        
        # Add some basic tabs
        self._add_dashboard_tab()
        self._add_target_tab()
        self._add_attack_tab()
        
        # Show all widgets
        self.show_all()
        logger.info("Main window created successfully")
    
    def _add_dashboard_tab(self):
        """Add a simple dashboard tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_border_width(10)
        
        label = Gtk.Label(label="Dashboard")
        label.set_markup("<span size='xx-large' weight='bold'>ERPCT Dashboard</span>")
        page.pack_start(label, False, False, 0)
        
        info = Gtk.Label(label="Welcome to the Enhanced Rapid Password Cracking Tool")
        page.pack_start(info, False, False, 0)
        
        self.notebook.append_page(page, Gtk.Label(label="Dashboard"))
    
    def _add_target_tab(self):
        """Add a simple target configuration tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_border_width(10)
        
        label = Gtk.Label(label="Target Configuration")
        label.set_markup("<span size='xx-large' weight='bold'>Target Configuration</span>")
        page.pack_start(label, False, False, 0)
        
        # Add target host field
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Target Host:")
        host_label.set_width_chars(15)
        host_box.pack_start(host_label, False, False, 0)
        
        host_entry = Gtk.Entry()
        host_box.pack_start(host_entry, True, True, 0)
        
        page.pack_start(host_box, False, False, 0)
        
        # Add protocol selection
        protocol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        protocol_label = Gtk.Label(label="Protocol:")
        protocol_label.set_width_chars(15)
        protocol_box.pack_start(protocol_label, False, False, 0)
        
        protocol_combo = Gtk.ComboBoxText()
        for protocol in ["SSH", "FTP", "HTTP", "SMTP"]:
            protocol_combo.append_text(protocol)
        protocol_combo.set_active(0)
        protocol_box.pack_start(protocol_combo, True, True, 0)
        
        page.pack_start(protocol_box, False, False, 0)
        
        self.notebook.append_page(page, Gtk.Label(label="Target"))
    
    def _add_attack_tab(self):
        """Add a simple attack configuration tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_border_width(10)
        
        label = Gtk.Label(label="Attack Configuration")
        label.set_markup("<span size='xx-large' weight='bold'>Attack Configuration</span>")
        page.pack_start(label, False, False, 0)
        
        # Add username field
        username_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        username_label = Gtk.Label(label="Username:")
        username_label.set_width_chars(15)
        username_box.pack_start(username_label, False, False, 0)
        
        username_entry = Gtk.Entry()
        username_box.pack_start(username_entry, True, True, 0)
        
        page.pack_start(username_box, False, False, 0)
        
        # Add password field
        password_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        password_label = Gtk.Label(label="Password:")
        password_label.set_width_chars(15)
        password_box.pack_start(password_label, False, False, 0)
        
        password_entry = Gtk.Entry()
        password_entry.set_visibility(False)
        password_box.pack_start(password_entry, True, True, 0)
        
        page.pack_start(password_box, False, False, 0)
        
        # Add start button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        start_button = Gtk.Button(label="Start Attack")
        start_button.connect("clicked", self._on_start_clicked)
        button_box.pack_end(start_button, False, False, 0)
        
        page.pack_start(button_box, False, False, 0)
        
        self.notebook.append_page(page, Gtk.Label(label="Attack"))
    
    def _on_start_clicked(self, button):
        """Handle the start button click."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Attack Started"
        )
        dialog.format_secondary_text("This is a simplified demo, no actual attack will be performed.")
        dialog.run()
        dialog.destroy()

class SimpleApplication(Gtk.Application):
    """Simple ERPCT application."""
    
    def __init__(self):
        logger.info("Creating application")
        Gtk.Application.__init__(self, application_id="org.erpct.simple")
    
    def do_startup(self):
        """Handle application startup."""
        logger.info("Application startup")
        Gtk.Application.do_startup(self)
        
        # Add application actions
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)
        
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)
    
    def do_activate(self):
        """Handle application activation."""
        logger.info("Application activate")
        # Create the main window if it doesn't exist
        if not hasattr(self, "window") or self.window is None:
            self.window = SimpleMainWindow(self)
        
        self.window.present()
    
    def on_about(self, action, param):
        """Show the about dialog."""
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.set_program_name("Simple ERPCT")
        about_dialog.set_version("1.0.0")
        about_dialog.set_comments("A simplified version of the Enhanced Rapid Password Cracking Tool")
        about_dialog.run()
        about_dialog.destroy()
    
    def on_quit(self, action, param):
        """Quit the application."""
        self.quit()

def main():
    """Run the application."""
    try:
        logger.info("Starting application")
        app = SimpleApplication()
        return app.run(None)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 