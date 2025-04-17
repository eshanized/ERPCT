#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT GUI Runner.
This script runs the ERPCT GUI application and handles dependency setup.
"""

import os
import sys
import subprocess
import importlib
import traceback
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("erpct.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("run_gui")

# Required packages
REQUIRED_PACKAGES = [
    "PyGObject",      # GTK bindings
    "pycairo",        # Required for PyGObject
    "paramiko",       # SSH support
    "requests",       # HTTP support
    "beautifulsoup4", # HTML parsing
    "colorama",       # Colored terminal output
]

def check_and_install_dependencies():
    """Check for required dependencies and install if missing."""
    missing_packages = []
    
    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package.replace('-', '_').lower())
            logger.info(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            logger.info(f"✗ {package} is missing")
    
    if missing_packages:
        logger.info("\nInstalling missing packages...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                *missing_packages, "--upgrade"
            ])
            logger.info("Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error installing dependencies: {e}")
            return False
    
    return True

def setup_development_paths():
    """Set up Python path for development mode."""
    # Add the project root directory to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Create necessary directories
    config_dir = os.path.join(project_root, "config")
    data_dir = os.path.join(project_root, "data")
    
    if not os.path.exists(config_dir):
        logger.info(f"Creating config directory: {config_dir}")
        os.makedirs(config_dir, exist_ok=True)
    
    if not os.path.exists(data_dir):
        logger.info(f"Creating data directory: {data_dir}")
        os.makedirs(data_dir, exist_ok=True)
    
    return project_root

def check_gtk():
    """Test GTK import and configuration."""
    try:
        # Test GTK
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        logger.info("GTK configuration successful")
        
        # Test if we can create a window
        window = Gtk.Window(title="GTK Test")
        logger.info("GTK window creation successful")
        
        return True
    except Exception as e:
        logger.error(f"GTK error: {e}")
        traceback.print_exc()
        return False

def run_simplified_gui():
    """Run a simplified version of the GUI."""
    logger.info("Running simplified GUI version")
    
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib, Gio
    
    class SimpleMainWindow(Gtk.ApplicationWindow):
        """Simple main window for ERPCT."""
        
        def __init__(self, application):
            """Initialize the window."""
            logger.info("Creating main window")
            Gtk.ApplicationWindow.__init__(self, application=application)
            self.set_title("ERPCT - Enhanced Rapid Password Cracking Tool")
            self.set_default_size(1000, 700)
            self.set_position(Gtk.WindowPosition.CENTER)
            
            # Create main layout
            self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            self.main_box.set_border_width(10)
            self.add(self.main_box)
            
            # Add notice label
            notice = Gtk.Label()
            notice.set_markup(
                "<span size='large' foreground='red'>"
                "Running in simplified mode due to initialization errors with the full GUI.\n"
                "Check the log file (erpct.log) for details."
                "</span>"
            )
            self.main_box.pack_start(notice, False, False, 10)
            
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
            about_dialog.set_program_name("ERPCT")
            about_dialog.set_version("1.0.0")
            about_dialog.set_comments("Enhanced Rapid Password Cracking Tool")
            about_dialog.run()
            about_dialog.destroy()
        
        def on_quit(self, action, param):
            """Quit the application."""
            self.quit()
    
    app = SimpleApplication()
    return app.run(None)

def run_gui():
    """Run the GUI application."""
    try:
        # Check if we're in development mode
        project_root = setup_development_paths()
        logger.info(f"Project root: {project_root}")
        
        # Test GTK
        if not check_gtk():
            logger.error("GTK test failed. Cannot continue.")
            return 1
        
        # Import and run the application
        logger.info("Starting main application...")
        
        try:
            from src.gui.main_window import main
            logger.info("Successfully imported main window module")
            return main()
        except Exception as e:
            logger.error(f"Error importing or running main application: {e}")
            traceback.print_exc()
            
            # Fall back to simplified GUI
            logger.info("Falling back to simplified GUI")
            return run_simplified_gui()
            
    except ImportError as e:
        logger.error(f"Error importing GUI modules: {e}")
        traceback.print_exc()
        
        # Fall back to simplified GUI
        try:
            return run_simplified_gui()
        except Exception as fallback_e:
            logger.critical(f"Simplified GUI also failed: {fallback_e}")
            traceback.print_exc()
        
        return 1
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    logger.info("ERPCT GUI Runner")
    logger.info("================")
    
    # Check and install dependencies
    if check_and_install_dependencies():
        # Run the application
        sys.exit(run_gui())
    else:
        logger.error("Failed to install required dependencies. Please install them manually.")
        sys.exit(1) 