#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Preferences component.
This module provides the GUI panel for configuring application settings.
"""

import os
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango

from src.utils.logging import get_logger, LOG_LEVELS, DEFAULT_LOG_FORMAT, DEFAULT_LOG_DIR


class Preferences(Gtk.Box):
    """Preferences panel for configuring application settings."""
    
    def __init__(self):
        """Initialize the preferences panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Default config file path
        self.config_dir = os.path.join(os.path.expanduser("~"), ".erpct")
        self.config_file = os.path.join(self.config_dir, "config.json")
        
        # Default configuration
        self.config = {
            "general": {
                "default_target_port": 22,
                "save_results": True,
                "auto_save_results": True,
                "results_dir": os.path.join(self.config_dir, "results")
            },
            "logging": {
                "level": "info",
                "console_logging": True,
                "file_logging": True,
                "log_dir": DEFAULT_LOG_DIR,
                "log_format": DEFAULT_LOG_FORMAT
            },
            "attack": {
                "default_threads": 1,
                "default_timeout": 10,
                "default_delay": 0.0,
                "stop_on_success": False
            },
            "gui": {
                "confirm_exit": True,
                "show_tooltips": True,
                "dark_mode": False,
                "auto_scroll_logs": True
            }
        }
        
        # Load existing configuration
        self._load_config()
        
        # Create UI components
        self._create_notebook()
        self._create_buttons()
        
    def _create_notebook(self):
        """Create settings notebook with tabs."""
        notebook = Gtk.Notebook()
        self.pack_start(notebook, True, True, 0)
        
        # General settings tab
        general_page = self._create_general_tab()
        notebook.append_page(general_page, Gtk.Label(label="General"))
        
        # Logging settings tab
        logging_page = self._create_logging_tab()
        notebook.append_page(logging_page, Gtk.Label(label="Logging"))
        
        # Attack settings tab
        attack_page = self._create_attack_tab()
        notebook.append_page(attack_page, Gtk.Label(label="Attack"))
        
        # GUI settings tab
        gui_page = self._create_gui_tab()
        notebook.append_page(gui_page, Gtk.Label(label="Interface"))
    
    def _create_general_tab(self):
        """Create general settings tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        
        # Target settings
        frame = Gtk.Frame(label="Default Target Settings")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Default port
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Default Port:")
        port_label.set_width_chars(20)
        port_label.set_xalign(0)
        port_box.pack_start(port_label, False, False, 0)
        
        self.port_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=self.config["general"]["default_target_port"], 
                                 lower=1, upper=65535, step_increment=1, page_increment=10)
        self.port_spin.set_adjustment(adjustment)
        port_box.pack_start(self.port_spin, False, False, 0)
        
        box.pack_start(port_box, False, False, 0)
        page.pack_start(frame, False, False, 0)
        
        # Results settings
        frame = Gtk.Frame(label="Results Settings")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Save results
        save_results_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        save_results_label = Gtk.Label(label="Save Results:")
        save_results_label.set_width_chars(20)
        save_results_label.set_xalign(0)
        save_results_box.pack_start(save_results_label, False, False, 0)
        
        self.save_results_switch = Gtk.Switch()
        self.save_results_switch.set_active(self.config["general"]["save_results"])
        self.save_results_switch.connect("notify::active", self._on_save_results_toggled)
        save_results_box.pack_start(self.save_results_switch, False, False, 0)
        
        box.pack_start(save_results_box, False, False, 0)
        
        # Auto save results
        auto_save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        auto_save_label = Gtk.Label(label="Auto-save Results:")
        auto_save_label.set_width_chars(20)
        auto_save_label.set_xalign(0)
        auto_save_box.pack_start(auto_save_label, False, False, 0)
        
        self.auto_save_switch = Gtk.Switch()
        self.auto_save_switch.set_active(self.config["general"]["auto_save_results"])
        auto_save_box.pack_start(self.auto_save_switch, False, False, 0)
        
        box.pack_start(auto_save_box, False, False, 0)
        
        # Results directory
        results_dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        results_dir_label = Gtk.Label(label="Results Directory:")
        results_dir_label.set_width_chars(20)
        results_dir_label.set_xalign(0)
        results_dir_box.pack_start(results_dir_label, False, False, 0)
        
        self.results_dir_entry = Gtk.Entry()
        self.results_dir_entry.set_text(self.config["general"]["results_dir"])
        results_dir_box.pack_start(self.results_dir_entry, True, True, 0)
        
        results_dir_button = Gtk.Button(label="Browse...")
        results_dir_button.connect("clicked", self._on_results_dir_clicked)
        results_dir_box.pack_start(results_dir_button, False, False, 0)
        
        box.pack_start(results_dir_box, False, False, 0)
        page.pack_start(frame, False, False, 0)
        
        return page
    
    def _create_logging_tab(self):
        """Create logging settings tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        
        # Logging settings
        frame = Gtk.Frame(label="Logging Settings")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Log level
        log_level_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        log_level_label = Gtk.Label(label="Log Level:")
        log_level_label.set_width_chars(20)
        log_level_label.set_xalign(0)
        log_level_box.pack_start(log_level_label, False, False, 0)
        
        self.log_level_combo = Gtk.ComboBoxText()
        for level in ["debug", "info", "warning", "error", "critical"]:
            self.log_level_combo.append_text(level)
        self.log_level_combo.set_active_id(self.config["logging"]["level"])
        log_level_box.pack_start(self.log_level_combo, False, False, 0)
        
        box.pack_start(log_level_box, False, False, 0)
        
        # Console logging
        console_logging_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        console_logging_label = Gtk.Label(label="Console Logging:")
        console_logging_label.set_width_chars(20)
        console_logging_label.set_xalign(0)
        console_logging_box.pack_start(console_logging_label, False, False, 0)
        
        self.console_logging_switch = Gtk.Switch()
        self.console_logging_switch.set_active(self.config["logging"]["console_logging"])
        console_logging_box.pack_start(self.console_logging_switch, False, False, 0)
        
        box.pack_start(console_logging_box, False, False, 0)
        
        # File logging
        file_logging_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        file_logging_label = Gtk.Label(label="File Logging:")
        file_logging_label.set_width_chars(20)
        file_logging_label.set_xalign(0)
        file_logging_box.pack_start(file_logging_label, False, False, 0)
        
        self.file_logging_switch = Gtk.Switch()
        self.file_logging_switch.set_active(self.config["logging"]["file_logging"])
        self.file_logging_switch.connect("notify::active", self._on_file_logging_toggled)
        file_logging_box.pack_start(self.file_logging_switch, False, False, 0)
        
        box.pack_start(file_logging_box, False, False, 0)
        
        # Log directory
        log_dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        log_dir_label = Gtk.Label(label="Log Directory:")
        log_dir_label.set_width_chars(20)
        log_dir_label.set_xalign(0)
        log_dir_box.pack_start(log_dir_label, False, False, 0)
        
        self.log_dir_entry = Gtk.Entry()
        self.log_dir_entry.set_text(self.config["logging"]["log_dir"])
        log_dir_box.pack_start(self.log_dir_entry, True, True, 0)
        
        log_dir_button = Gtk.Button(label="Browse...")
        log_dir_button.connect("clicked", self._on_log_dir_clicked)
        log_dir_box.pack_start(log_dir_button, False, False, 0)
        
        box.pack_start(log_dir_box, False, False, 0)
        
        # Log format
        log_format_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        log_format_label = Gtk.Label(label="Log Format:")
        log_format_label.set_width_chars(20)
        log_format_label.set_xalign(0)
        log_format_box.pack_start(log_format_label, False, False, 0)
        
        self.log_format_entry = Gtk.Entry()
        self.log_format_entry.set_text(self.config["logging"]["log_format"])
        log_format_box.pack_start(self.log_format_entry, True, True, 0)
        
        box.pack_start(log_format_box, False, False, 0)
        
        # Log format help
        log_format_help_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        log_format_help_label = Gtk.Label()
        log_format_help_label.set_markup(
            "<small>Available format variables: %(asctime)s, %(levelname)s, %(name)s, %(message)s</small>"
        )
        log_format_help_label.set_xalign(0)
        log_format_help_box.pack_start(log_format_help_label, True, True, 0)
        
        box.pack_start(log_format_help_box, False, False, 0)
        
        page.pack_start(frame, False, False, 0)
        
        return page
    
    def _create_attack_tab(self):
        """Create attack settings tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        
        # Attack settings
        frame = Gtk.Frame(label="Default Attack Settings")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Default threads
        threads_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        threads_label = Gtk.Label(label="Default Threads:")
        threads_label.set_width_chars(25)
        threads_label.set_xalign(0)
        threads_box.pack_start(threads_label, False, False, 0)
        
        self.threads_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=self.config["attack"]["default_threads"], 
                                 lower=1, upper=100, step_increment=1, page_increment=5)
        self.threads_spin.set_adjustment(adjustment)
        threads_box.pack_start(self.threads_spin, False, False, 0)
        
        box.pack_start(threads_box, False, False, 0)
        
        # Default timeout
        timeout_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        timeout_label = Gtk.Label(label="Default Timeout (seconds):")
        timeout_label.set_width_chars(25)
        timeout_label.set_xalign(0)
        timeout_box.pack_start(timeout_label, False, False, 0)
        
        self.timeout_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=self.config["attack"]["default_timeout"], 
                                 lower=1, upper=60, step_increment=1, page_increment=5)
        self.timeout_spin.set_adjustment(adjustment)
        timeout_box.pack_start(self.timeout_spin, False, False, 0)
        
        box.pack_start(timeout_box, False, False, 0)
        
        # Default delay
        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        delay_label = Gtk.Label(label="Default Delay (seconds):")
        delay_label.set_width_chars(25)
        delay_label.set_xalign(0)
        delay_box.pack_start(delay_label, False, False, 0)
        
        self.delay_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=self.config["attack"]["default_delay"], 
                                 lower=0, upper=10, step_increment=0.1, page_increment=1)
        self.delay_spin.set_adjustment(adjustment)
        self.delay_spin.set_digits(1)
        delay_box.pack_start(self.delay_spin, False, False, 0)
        
        box.pack_start(delay_box, False, False, 0)
        
        # Stop on success
        stop_on_success_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        stop_on_success_label = Gtk.Label(label="Stop on First Success:")
        stop_on_success_label.set_width_chars(25)
        stop_on_success_label.set_xalign(0)
        stop_on_success_box.pack_start(stop_on_success_label, False, False, 0)
        
        self.stop_on_success_switch = Gtk.Switch()
        self.stop_on_success_switch.set_active(self.config["attack"]["stop_on_success"])
        stop_on_success_box.pack_start(self.stop_on_success_switch, False, False, 0)
        
        box.pack_start(stop_on_success_box, False, False, 0)
        
        page.pack_start(frame, False, False, 0)
        
        return page
    
    def _create_gui_tab(self):
        """Create GUI settings tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        
        # GUI settings
        frame = Gtk.Frame(label="Interface Settings")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Confirm exit
        confirm_exit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        confirm_exit_label = Gtk.Label(label="Confirm Exit:")
        confirm_exit_label.set_width_chars(20)
        confirm_exit_label.set_xalign(0)
        confirm_exit_box.pack_start(confirm_exit_label, False, False, 0)
        
        self.confirm_exit_switch = Gtk.Switch()
        self.confirm_exit_switch.set_active(self.config["gui"]["confirm_exit"])
        confirm_exit_box.pack_start(self.confirm_exit_switch, False, False, 0)
        
        box.pack_start(confirm_exit_box, False, False, 0)
        
        # Show tooltips
        tooltips_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tooltips_label = Gtk.Label(label="Show Tooltips:")
        tooltips_label.set_width_chars(20)
        tooltips_label.set_xalign(0)
        tooltips_box.pack_start(tooltips_label, False, False, 0)
        
        self.tooltips_switch = Gtk.Switch()
        self.tooltips_switch.set_active(self.config["gui"]["show_tooltips"])
        tooltips_box.pack_start(self.tooltips_switch, False, False, 0)
        
        box.pack_start(tooltips_box, False, False, 0)
        
        # Dark mode
        dark_mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dark_mode_label = Gtk.Label(label="Dark Mode:")
        dark_mode_label.set_width_chars(20)
        dark_mode_label.set_xalign(0)
        dark_mode_box.pack_start(dark_mode_label, False, False, 0)
        
        self.dark_mode_switch = Gtk.Switch()
        self.dark_mode_switch.set_active(self.config["gui"]["dark_mode"])
        dark_mode_box.pack_start(self.dark_mode_switch, False, False, 0)
        
        box.pack_start(dark_mode_box, False, False, 0)
        
        # Auto-scroll logs
        auto_scroll_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        auto_scroll_label = Gtk.Label(label="Auto-scroll Logs:")
        auto_scroll_label.set_width_chars(20)
        auto_scroll_label.set_xalign(0)
        auto_scroll_box.pack_start(auto_scroll_label, False, False, 0)
        
        self.auto_scroll_switch = Gtk.Switch()
        self.auto_scroll_switch.set_active(self.config["gui"]["auto_scroll_logs"])
        auto_scroll_box.pack_start(self.auto_scroll_switch, False, False, 0)
        
        box.pack_start(auto_scroll_box, False, False, 0)
        
        page.pack_start(frame, False, False, 0)
        
        # Appearance note
        note_label = Gtk.Label()
        note_label.set_markup("<i>Note: Some appearance changes may require restarting the application.</i>")
        note_label.set_xalign(0)
        page.pack_start(note_label, False, False, 10)
        
        return page
    
    def _create_buttons(self):
        """Create action buttons."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_end(button_box, False, False, 0)
        
        # Add spacer
        button_box.pack_start(Gtk.Label(), True, True, 0)
        
        # Reset button
        self.reset_button = Gtk.Button.new_with_label("Reset to Defaults")
        self.reset_button.connect("clicked", self._on_reset_clicked)
        button_box.pack_start(self.reset_button, False, False, 0)
        
        # Save button
        self.save_button = Gtk.Button.new_with_label("Save")
        self.save_button.connect("clicked", self._on_save_clicked)
        button_box.pack_start(self.save_button, False, False, 0)
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Update config with loaded values, keeping defaults for missing keys
                    for section in self.config:
                        if section in loaded_config:
                            for key in self.config[section]:
                                if key in loaded_config[section]:
                                    self.config[section][key] = loaded_config[section][key]
                    
                    self.logger.debug(f"Loaded configuration from {self.config_file}")
            else:
                self.logger.debug(f"Configuration file not found, using defaults")
                # Ensure config directory exists
                os.makedirs(self.config_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            # Update config with current UI values
            self._update_config_from_ui()
            
            # Ensure config directory exists
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
                
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def _update_config_from_ui(self):
        """Update configuration dictionary from UI values."""
        # General settings
        self.config["general"]["default_target_port"] = self.port_spin.get_value_as_int()
        self.config["general"]["save_results"] = self.save_results_switch.get_active()
        self.config["general"]["auto_save_results"] = self.auto_save_switch.get_active()
        self.config["general"]["results_dir"] = self.results_dir_entry.get_text()
        
        # Logging settings
        self.config["logging"]["level"] = self.log_level_combo.get_active_text()
        self.config["logging"]["console_logging"] = self.console_logging_switch.get_active()
        self.config["logging"]["file_logging"] = self.file_logging_switch.get_active()
        self.config["logging"]["log_dir"] = self.log_dir_entry.get_text()
        self.config["logging"]["log_format"] = self.log_format_entry.get_text()
        
        # Attack settings
        self.config["attack"]["default_threads"] = self.threads_spin.get_value_as_int()
        self.config["attack"]["default_timeout"] = self.timeout_spin.get_value_as_int()
        self.config["attack"]["default_delay"] = self.delay_spin.get_value()
        self.config["attack"]["stop_on_success"] = self.stop_on_success_switch.get_active()
        
        # GUI settings
        self.config["gui"]["confirm_exit"] = self.confirm_exit_switch.get_active()
        self.config["gui"]["show_tooltips"] = self.tooltips_switch.get_active()
        self.config["gui"]["dark_mode"] = self.dark_mode_switch.get_active()
        self.config["gui"]["auto_scroll_logs"] = self.auto_scroll_switch.get_active()
    
    def _on_save_clicked(self, button):
        """Handle save button click."""
        if self._save_config():
            # Show success dialog
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Settings Saved"
            )
            dialog.format_secondary_text("Settings have been saved. Some changes may require restarting the application.")
            dialog.run()
            dialog.destroy()
    
    def _on_reset_clicked(self, button):
        """Handle reset button click."""
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset to Defaults"
        )
        dialog.format_secondary_text("Are you sure you want to reset all settings to default values?")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Reinitialize config with defaults
            self.__init__()
    
    def _on_log_dir_clicked(self, button):
        """Handle log directory browse button click."""
        dialog = Gtk.FileChooserDialog(
            title="Select Log Directory",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )
        dialog.set_current_folder(self.log_dir_entry.get_text())
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.log_dir_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _on_results_dir_clicked(self, button):
        """Handle results directory browse button click."""
        dialog = Gtk.FileChooserDialog(
            title="Select Results Directory",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )
        dialog.set_current_folder(self.results_dir_entry.get_text())
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.results_dir_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _on_save_results_toggled(self, switch, gparam):
        """Handle save results toggle."""
        active = switch.get_active()
        self.auto_save_switch.set_sensitive(active)
    
    def _on_file_logging_toggled(self, switch, gparam):
        """Handle file logging toggle."""
        active = switch.get_active()
        self.log_dir_entry.set_sensitive(active)
    
    def get_config(self):
        """Get the current configuration.
        
        Returns:
            Dictionary with current configuration
        """
        self._update_config_from_ui()
        return self.config


class PreferencesPanel(Preferences):
    """Alias class for Preferences panel to maintain backwards compatibility."""
    
    def __init__(self):
        """Initialize the preferences panel."""
        super().__init__()
