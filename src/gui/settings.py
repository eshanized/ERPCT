#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Settings Panel.
This module provides access to various configuration panels.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from src.utils.logging import get_logger
from src.gui.config_editor import ConfigEditor
from src.gui.protocol_config import ProtocolConfigGenerator
from src.gui.log_viewer import LogViewer
try:
    from src.gui.preferences import PreferencesPanel
except ImportError:
    # Create a dummy class if preferences panel doesn't exist
    class PreferencesPanel(Gtk.Box):
        def __init__(self):
            Gtk.Box.__init__(self)
            label = Gtk.Label(label="Preferences panel not available")
            self.add(label)


class SettingsPanel(Gtk.Box):
    """Settings panel for accessing configuration tools."""
    
    def __init__(self):
        """Initialize the settings panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Create UI components
        self._create_header()
        self._create_notebook()
        
        self.show_all()
    
    def _create_header(self):
        """Create header with description."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        title = Gtk.Label(label="<b>Settings</b>", xalign=0)
        title.set_use_markup(True)
        header_box.pack_start(title, False, False, 0)
        
        description = Gtk.Label(
            label="Configure application settings and manage protocol configurations.",
            xalign=0
        )
        description.set_line_wrap(True)
        header_box.pack_start(description, False, False, 0)
        
        self.pack_start(header_box, False, False, 0)
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(separator, False, False, 10)
    
    def _create_notebook(self):
        """Create tabbed notebook interface."""
        self.notebook = Gtk.Notebook()
        
        # Add configuration editor tab
        config_editor = ConfigEditor()
        self.notebook.append_page(config_editor, Gtk.Label(label="Configuration Editor"))
        
        # Add protocol configuration tab
        protocol_config = ProtocolConfigGenerator()
        self.notebook.append_page(protocol_config, Gtk.Label(label="Protocol Configuration"))
        
        # Add log viewer tab
        self.log_viewer = LogViewer()
        self.notebook.append_page(self.log_viewer, Gtk.Label(label="Logs"))
        
        # Add preferences panel tab
        self.preferences_panel = PreferencesPanel()
        self.notebook.append_page(self.preferences_panel, Gtk.Label(label="Preferences"))
        
        self.pack_start(self.notebook, True, True, 0) 