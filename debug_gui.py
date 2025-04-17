#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug script for ERPCT GUI.
This script provides detailed error information when running the GUI.
"""

import os
import sys
import traceback
import logging

# Configure logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_debug.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Get a logger
logger = logging.getLogger("debug_gui")

def main():
    """Run the GUI application with debugging."""
    logger.info("Starting GUI debug script")
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    logger.info(f"Project root: {project_root}")
    
    # Create necessary directories
    os.makedirs(os.path.join(project_root, "config"), exist_ok=True)
    os.makedirs(os.path.join(project_root, "data"), exist_ok=True)
    
    # Try importing GTK
    try:
        logger.info("Importing GTK...")
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        logger.info("GTK imported successfully")
    except Exception as e:
        logger.error(f"Error importing GTK: {e}")
        traceback.print_exc()
        return 1
    
    # Try creating a basic GTK application
    try:
        logger.info("Testing GTK application...")
        app = Gtk.Application(application_id="org.erpct.debug")
        logger.info("GTK application created successfully")
    except Exception as e:
        logger.error(f"Error creating GTK application: {e}")
        traceback.print_exc()
        return 1
    
    # Try importing the main window
    try:
        logger.info("Importing main_window module...")
        from src.gui.main_window import ERPCTMainWindow, ERPCTApplication
        logger.info("Main window imported successfully")
    except Exception as e:
        logger.error(f"Error importing main window: {e}")
        traceback.print_exc()
        return 1
    
    # Try running the application
    try:
        logger.info("Starting ERPCT application...")
        app = ERPCTApplication()
        logger.info("ERPCT application created, running main loop...")
        return app.run(None)
    except Exception as e:
        logger.error(f"Error running application: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.critical(f"Uncaught exception: {e}")
        traceback.print_exc()
        sys.exit(1) 