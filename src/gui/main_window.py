#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Main Window.
This module provides the main application window for the GUI.
"""

import os
import gi
import time
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio, GdkPixbuf

from src.core.attack import Attack
from src.utils.logging import get_logger
from src.gui.target_manager import TargetManager
from src.gui.attack_panel import AttackPanel
from src.gui.status_panel import StatusPanel
from src.gui.wordlist_manager import WordlistManager
from src.gui.results_explorer import ResultsExplorer
from src.gui.log_viewer import LogViewer
from src.gui.protocol_configurator import ProtocolConfigurator
from src.gui.distributed_panel import DistributedPanel
from src.gui.report_generator import ReportGenerator
from src.gui.task_scheduler import TaskScheduler
from src.gui.network_scanner import NetworkScanner
from src.gui.dashboard import Dashboard
from src.gui.settings import SettingsPanel


class ERPCTMainWindow(Gtk.ApplicationWindow):
    """Main application window."""
    
    def __init__(self, application):
        """Initialize the main window.
        
        Args:
            application: Parent Gtk.Application
        """
        Gtk.ApplicationWindow.__init__(self, application=application)
        self.set_title("ERPCT - Enhanced Rapid Password Cracking Tool")
        self.set_default_size(1200, 800)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        self.logger = get_logger(__name__)
        
        # Current attack instance
        self.current_attack = None
        
        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.main_box)
        
        # Header bar with logo
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.props.title = "ERPCT"
        self.set_titlebar(self.header)
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_tooltip_text("Menu")
        menu_icon = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
        menu_button.add(menu_icon)
        self.header.pack_end(menu_button)
        
        # Build menu
        menu = Gio.Menu()
        menu.append("About", "app.about")
        menu.append("Preferences", "app.preferences")
        menu.append("Quit", "app.quit")
        menu_button.set_menu_model(menu)
        
        # Create the main interface components
        self.create_notebook()
        
        # Show all widgets
        self.show_all()
    
    def create_notebook(self):
        """Create the main notebook with tabs."""
        notebook = Gtk.Notebook()
        self.main_box.pack_start(notebook, True, True, 0)
        
        # Dashboard tab
        self.dashboard = Dashboard()
        notebook.append_page(self.dashboard, Gtk.Label(label="Dashboard"))
        
        # Target Configuration tab
        self.target_manager = TargetManager()
        notebook.append_page(self.target_manager, Gtk.Label(label="Target"))
        
        # Attack Configuration tab
        self.attack_panel = AttackPanel()
        self.attack_panel.set_start_attack_callback(self.start_attack)
        notebook.append_page(self.attack_panel, Gtk.Label(label="Attack"))
        
        # Protocol Configuration tab
        self.protocol_configurator = ProtocolConfigurator()
        notebook.append_page(self.protocol_configurator, Gtk.Label(label="Protocols"))
        
        # Network Scanner tab
        self.network_scanner = NetworkScanner()
        self.network_scanner.set_target_callback(self.add_scan_target)
        notebook.append_page(self.network_scanner, Gtk.Label(label="Scanner"))
        
        # Distributed tab
        self.distributed_panel = DistributedPanel()
        self.distributed_panel.set_attack_callback(self.start_distributed_attack)
        notebook.append_page(self.distributed_panel, Gtk.Label(label="Distributed"))
        
        # Wordlist Manager tab
        self.wordlist_manager = WordlistManager()
        notebook.append_page(self.wordlist_manager, Gtk.Label(label="Wordlists"))
        
        # Task Scheduler tab
        self.task_scheduler = TaskScheduler()
        self.task_scheduler.set_attack_callback(self.schedule_attack)
        notebook.append_page(self.task_scheduler, Gtk.Label(label="Scheduler"))
        
        # Execution tab
        self.status_panel = StatusPanel()
        notebook.append_page(self.status_panel, Gtk.Label(label="Execution"))
        
        # Results tab
        self.results_explorer = ResultsExplorer()
        notebook.append_page(self.results_explorer, Gtk.Label(label="Results"))
        
        # Reports tab
        self.report_generator = ReportGenerator()
        self.report_generator.set_results_source(self.results_explorer)
        notebook.append_page(self.report_generator, Gtk.Label(label="Reports"))
        
        # Settings tab
        self.settings_panel = SettingsPanel()
        notebook.append_page(self.settings_panel, Gtk.Label(label="Settings"))

        # Store the notebook for later access
        self.notebook = notebook
        
        # Initialize data connections
        self._initialize_data_connections()
    
    def _initialize_data_connections(self):
        """Initialize connections between components and data sources."""
        # Connect dashboard to data sources
        self.dashboard.connect_to_data_sources(
            attack_source=self.status_panel,
            results_source=self.results_explorer,
            system_monitor=self._get_system_monitor()
        )
        
        # Set target manager's parent reference
        self.target_manager.parent_window = self
        
        # Set protocol change callback
        if hasattr(self.protocol_configurator, 'set_on_protocol_change_callback'):
            self.protocol_configurator.set_on_protocol_change_callback(self._on_protocol_change)
        
        # Connect other components as needed
        # Check if log viewer is directly available or via settings panel
        if hasattr(self, 'log_viewer'):
            self.log_viewer.start_log_monitoring()
        elif hasattr(self, 'settings_panel') and hasattr(self.settings_panel, 'log_viewer'):
            self.settings_panel.log_viewer.start_log_monitoring()
    
    def start_attack(self, attack_config):
        """Start a new attack with the given configuration.
        
        Args:
            attack_config: Dictionary with attack parameters
        """
        # Stop any existing attack
        if self.current_attack and self.current_attack.status.running:
            self.current_attack.stop()
            self.current_attack = None
        
        try:
            # Get target configuration
            target_config = self.target_manager.get_target_config()
            
            # Validate required fields
            if not attack_config.get("protocol"):
                raise ValueError("Protocol must be specified")
            
            if not target_config.get("target"):
                raise ValueError("Target host/IP must be specified")
            
            # Merge configurations
            config = {**target_config, **attack_config}
            
            # Create attack instance
            self.current_attack = Attack(config)
            
            # Set up callback for when attack completes
            self.current_attack.set_on_complete_callback(self._on_attack_complete)
            
            # Show execution tab
            self.notebook.set_current_page(3)  # Execution tab
            
            # Start monitoring in status panel
            self.status_panel.start_attack(self.current_attack)
            
            # Start the attack
            self.current_attack.start()
            
            self.logger.info(f"Attack started with configuration: {config}")
            
        except Exception as e:
            self.logger.error(f"Error starting attack: {str(e)}")
            
            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Starting Attack"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def _on_attack_complete(self):
        """Handle attack completion."""
        if not self.current_attack:
            return
            
        # Get attack statistics
        stats = self.current_attack.get_status()
        
        # Get successful credentials
        credentials = []
        for username, password in self.current_attack.get_successful_credentials():
            credentials.append({
                "username": username,
                "password": password,
                "timestamp": time.time(),
                "message": "Success"
            })
        
        # Create result data
        result_data = {
            "name": f"{self.current_attack.config.get('protocol', 'unknown')}_{self.current_attack.config.get('target', 'unknown')}",
            "timestamp": time.time(),
            "target": self.current_attack.config.get("target", ""),
            "protocol": self.current_attack.config.get("protocol", ""),
            "duration": stats["elapsed_seconds"],
            "total_attempts": stats["total_attempts"],
            "completed_attempts": stats["completed_attempts"],
            "successful_attempts": stats["successful_attempts"],
            "credentials": credentials
        }
        
        # Add to results explorer
        self.results_explorer.add_result(result_data)
        
        # Show notification dialog
        if len(credentials) > 0:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Attack Completed"
            )
            dialog.format_secondary_text(f"Found {len(credentials)} valid credentials. View them in the Results tab.")
            dialog.run()
            dialog.destroy()
    
    def add_scan_target(self, target_data):
        """Add a target discovered by the network scanner.
        
        Args:
            target_data: Dictionary with target information
        """
        self.target_manager.add_target(target_data)
        # Switch to target tab
        self.notebook.set_current_page(1)  # Target tab index
        
        self.logger.info(f"Added target from scanner: {target_data.get('host', '')}")
    
    def start_distributed_attack(self, distributed_config):
        """Start a distributed attack.
        
        Args:
            distributed_config: Dictionary with distributed attack configuration
        """
        # Get target and attack configurations
        target_config = self.target_manager.get_target_config()
        attack_config = self.attack_panel.get_attack_config()
        protocol_config = self.protocol_configurator.get_protocol_config()
        
        try:
            # Validate required fields
            if not protocol_config or not protocol_config[0]:
                raise ValueError("Protocol must be specified")
            
            if not target_config.get("target"):
                raise ValueError("Target host/IP must be specified")
            
            # Merge configurations
            config = {
                **target_config, 
                **attack_config,
                "protocol_name": protocol_config[0],
                "protocol_config": protocol_config[1],
                "distributed": True,
                "distributed_config": distributed_config
            }
            
            # Create attack instance with distributed config
            from src.core.distributed import DistributedAttackController
            self.distributed_controller = DistributedAttackController(config)
            
            # Set up callback for when attack completes
            self.distributed_controller.set_on_complete_callback(self._on_distributed_attack_complete)
            
            # Show execution tab
            self.notebook.set_current_page(8)  # Execution tab
            
            # Start monitoring in status panel
            self.status_panel.start_distributed_attack(self.distributed_controller)
            
            # Start the attack
            self.distributed_controller.start()
            
            self.logger.info(f"Distributed attack started with configuration: {config}")
            
        except Exception as e:
            self.logger.error(f"Error starting distributed attack: {str(e)}")
            
            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Starting Distributed Attack"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def schedule_attack(self, schedule_config):
        """Schedule an attack for later execution.
        
        Args:
            schedule_config: Dictionary with schedule parameters
        """
        # Get target and attack configurations
        target_config = self.target_manager.get_target_config()
        attack_config = self.attack_panel.get_attack_config()
        protocol_config = self.protocol_configurator.get_protocol_config()
        
        try:
            # Validate required fields
            if not protocol_config or not protocol_config[0]:
                raise ValueError("Protocol must be specified")
            
            if not target_config.get("target"):
                raise ValueError("Target host/IP must be specified")
            
            # Merge configurations
            config = {
                **target_config, 
                **attack_config,
                "protocol_name": protocol_config[0],
                "protocol_config": protocol_config[1],
                "schedule": schedule_config
            }
            
            from src.core.scheduler import TaskScheduler as CoreScheduler
            scheduler = CoreScheduler()
            task_id = scheduler.schedule_task(config)
            
            self.logger.info(f"Attack scheduled with ID {task_id} and configuration: {config}")
            
            # Show confirmation dialog
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Attack Scheduled"
            )
            dialog.format_secondary_text(f"Attack has been scheduled as task {task_id}.")
            dialog.run()
            dialog.destroy()
            
        except Exception as e:
            self.logger.error(f"Error scheduling attack: {str(e)}")
            
            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Scheduling Attack"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def _on_distributed_attack_complete(self, results):
        """Handle distributed attack completion.
        
        Args:
            results: Attack results data
        """
        # Add to results explorer
        self.results_explorer.add_result(results)
        
        # Show notification dialog
        credentials_count = len(results.get("credentials", []))
        if credentials_count > 0:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Distributed Attack Completed"
            )
            dialog.format_secondary_text(f"Found {credentials_count} valid credentials. View them in the Results tab.")
            dialog.run()
            dialog.destroy()
    
    def _get_system_monitor(self):
        """Get the system monitor instance.
        
        Returns:
            SystemMonitor: System monitoring instance
        """
        from src.utils.system_monitor import SystemMonitor
        return SystemMonitor()

    def _on_protocol_change(self, protocol_name, protocol_config):
        """Handle protocol configuration change.
        
        Args:
            protocol_name: Name of selected protocol
            protocol_config: Protocol configuration
        """
        self.logger.debug(f"Protocol changed to {protocol_name}")
        
        # Update target port based on protocol
        if protocol_name and hasattr(self.target_manager, 'update_port_for_protocol'):
            self.target_manager.update_port_for_protocol(protocol_name)
        
        # Update attack panel for protocol-specific options
        if protocol_name and hasattr(self.attack_panel, 'update_for_protocol'):
            self.attack_panel.update_for_protocol(protocol_name, protocol_config)


class ERPCTApplication(Gtk.Application):
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        Gtk.Application.__init__(
            self,
            application_id="com.example.erpct",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.window = None
    
    def do_startup(self):
        """Handle application startup."""
        Gtk.Application.do_startup(self)
        
        # Add actions
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)
        
        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.on_preferences)
        self.add_action(action)
        
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)
    
    def do_activate(self):
        """Handle application activation."""
        # Create the main window if it doesn't exist
        if not self.window:
            self.window = ERPCTMainWindow(self)
        
        self.window.present()
    
    def on_about(self, action, param):
        """Show about dialog.
        
        Args:
            action: Action that triggered this callback
            param: Action parameters
        """
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.set_program_name("ERPCT")
        about_dialog.set_version("0.1.0")
        about_dialog.set_copyright("Copyright © 2023 ERPCT Team")
        about_dialog.set_comments("Enhanced Rapid Password Cracking Tool")
        about_dialog.set_website("https://github.com/eshanized/ERPCT")
        about_dialog.set_authors(["ERPCT Team"])
        about_dialog.run()
        about_dialog.destroy()
    
    def on_preferences(self, action, param):
        """Show preferences dialog.
        
        Args:
            action: Action that triggered this callback
            param: Action parameters
        """
        # TODO: Create preferences dialog
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Preferences"
        )
        dialog.format_secondary_text("Preferences dialog is not implemented yet.")
        dialog.run()
        dialog.destroy()
    
    def on_quit(self, action, param):
        """Quit the application.
        
        Args:
            action: Action that triggered this callback
            param: Action parameters
        """
        if self.window and hasattr(self.window, 'current_attack') and self.window.current_attack:
            if self.window.current_attack.status.running:
                self.window.current_attack.stop()
        
        self.quit()


def main():
    """Application entry point."""
    app = ERPCTApplication()
    return app.run(None)


if __name__ == "__main__":
    main()
