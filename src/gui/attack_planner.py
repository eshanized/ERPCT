#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Attack Planner component.
This module provides the GUI panel for planning and executing password cracking attacks.
"""

import os
import json
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango, GObject

from src.utils.logging import get_logger
from src.utils.config import get_config_dir
from src.core.attack_types import AttackType
from src.core.protocols import Protocol


class AttackPlanner(Gtk.Box):
    """Attack planner panel for configuring and executing password attacks."""
    
    __gsignals__ = {
        'attack-started': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'attack-saved': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }
    
    def __init__(self):
        """Initialize the attack planner panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Configuration directories
        self.config_dir = get_config_dir()
        self.plans_dir = os.path.join(self.config_dir, "attack_plans")
        Path(self.plans_dir).mkdir(parents=True, exist_ok=True)
        
        # Create title
        title_label = Gtk.Label(label="Attack Planner")
        title_label.set_markup("<span size='large' weight='bold'>Attack Planner</span>")
        title_label.set_margin_bottom(10)
        self.pack_start(title_label, False, False, 0)
        
        # Create notebook for tabs
        self.notebook = Gtk.Notebook()
        self.pack_start(self.notebook, True, True, 0)
        
        # Create UI components
        self._create_target_tab()
        self._create_method_tab()
        self._create_options_tab()
        self._create_schedule_tab()
        self._create_action_buttons()
        
        # Load saved attack plans
        self.load_saved_plans()
    
    def _create_target_tab(self):
        """Create the target configuration tab."""
        target_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        target_page.set_border_width(10)
        
        # Target section
        target_frame = Gtk.Frame(label="Target Configuration")
        target_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        target_box.set_border_width(10)
        target_frame.add(target_box)
        
        # Protocol selection
        protocol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        protocol_label = Gtk.Label(label="Protocol:")
        protocol_label.set_width_chars(15)
        protocol_label.set_xalign(0)
        protocol_box.pack_start(protocol_label, False, False, 0)
        
        self.protocol_combo = Gtk.ComboBoxText()
        for protocol in Protocol:
            self.protocol_combo.append_text(protocol.name)
        self.protocol_combo.set_active(0)  # Default to first protocol
        self.protocol_combo.connect("changed", self._on_protocol_changed)
        protocol_box.pack_start(self.protocol_combo, True, True, 0)
        
        target_box.pack_start(protocol_box, False, False, 0)
        
        # Host/IP
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Host/IP:")
        host_label.set_width_chars(15)
        host_label.set_xalign(0)
        host_box.pack_start(host_label, False, False, 0)
        
        self.host_entry = Gtk.Entry()
        host_box.pack_start(self.host_entry, True, True, 0)
        
        target_box.pack_start(host_box, False, False, 0)
        
        # Port
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port:")
        port_label.set_width_chars(15)
        port_label.set_xalign(0)
        port_box.pack_start(port_label, False, False, 0)
        
        self.port_spin = Gtk.SpinButton()
        self.port_spin.set_range(1, 65535)
        self.port_spin.set_value(22)  # Default to SSH port
        self.port_spin.set_increments(1, 10)
        port_box.pack_start(self.port_spin, False, False, 0)
        
        target_box.pack_start(port_box, False, False, 0)
        
        target_page.pack_start(target_frame, False, False, 0)
        
        # Authentication section
        auth_frame = Gtk.Frame(label="Authentication")
        auth_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        auth_box.set_border_width(10)
        auth_frame.add(auth_box)
        
        # Single username
        username_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        username_label = Gtk.Label(label="Username:")
        username_label.set_width_chars(15)
        username_label.set_xalign(0)
        username_box.pack_start(username_label, False, False, 0)
        
        self.username_entry = Gtk.Entry()
        username_box.pack_start(self.username_entry, True, True, 0)
        
        auth_box.pack_start(username_box, False, False, 0)
        
        # Username list file
        username_file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        username_file_label = Gtk.Label(label="Username List:")
        username_file_label.set_width_chars(15)
        username_file_label.set_xalign(0)
        username_file_box.pack_start(username_file_label, False, False, 0)
        
        self.username_file_entry = Gtk.Entry()
        self.username_file_entry.set_sensitive(False)
        username_file_box.pack_start(self.username_file_entry, True, True, 0)
        
        self.username_file_button = Gtk.Button(label="Browse...")
        self.username_file_button.connect("clicked", self._on_username_file_clicked)
        self.username_file_button.set_sensitive(False)
        username_file_box.pack_start(self.username_file_button, False, False, 0)
        
        auth_box.pack_start(username_file_box, False, False, 0)
        
        # Use username file checkbox
        use_file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.use_username_file = Gtk.CheckButton(label="Use username list file")
        self.use_username_file.connect("toggled", self._on_use_username_file_toggled)
        use_file_box.pack_start(self.use_username_file, True, True, 0)
        
        auth_box.pack_start(use_file_box, False, False, 0)
        
        target_page.pack_start(auth_frame, False, False, 0)
        
        # Add target page to notebook
        label = Gtk.Label(label="Target")
        self.notebook.append_page(target_page, label)
    
    def _on_protocol_changed(self, combo):
        """Handle protocol selection change."""
        protocol_name = combo.get_active_text()
        if protocol_name:
            # Set default port based on protocol
            if protocol_name == Protocol.SSH.name:
                self.port_spin.set_value(22)
            elif protocol_name == Protocol.FTP.name:
                self.port_spin.set_value(21)
            elif protocol_name == Protocol.HTTP.name:
                self.port_spin.set_value(80)
            elif protocol_name == Protocol.HTTPS.name:
                self.port_spin.set_value(443)
            elif protocol_name == Protocol.SMB.name:
                self.port_spin.set_value(445)
            elif protocol_name == Protocol.SMTP.name:
                self.port_spin.set_value(25)
            elif protocol_name == Protocol.POP3.name:
                self.port_spin.set_value(110)
            elif protocol_name == Protocol.IMAP.name:
                self.port_spin.set_value(143)
            elif protocol_name == Protocol.RDP.name:
                self.port_spin.set_value(3389)
            elif protocol_name == Protocol.VNC.name:
                self.port_spin.set_value(5900)
    
    def _on_use_username_file_toggled(self, checkbox):
        """Handle username file checkbox toggle."""
        use_file = checkbox.get_active()
        self.username_entry.set_sensitive(not use_file)
        self.username_file_entry.set_sensitive(use_file)
        self.username_file_button.set_sensitive(use_file)
    
    def _on_username_file_clicked(self, button):
        """Handle username file browse button click."""
        dialog = Gtk.FileChooserDialog(
            title="Select Username List",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        
        # Add filters
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)
        
        filter_any = Gtk.FileFilter()
        filter_any.set_name("All files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.username_file_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _create_method_tab(self):
        """Create the attack method configuration tab."""
        method_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        method_page.set_border_width(10)
        
        # Attack type section
        type_frame = Gtk.Frame(label="Attack Type")
        type_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        type_box.set_border_width(10)
        type_frame.add(type_box)
        
        # Attack type selection
        type_box_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        type_label = Gtk.Label(label="Attack Type:")
        type_label.set_width_chars(15)
        type_label.set_xalign(0)
        type_box_row.pack_start(type_label, False, False, 0)
        
        self.attack_type_combo = Gtk.ComboBoxText()
        for attack_type in AttackType:
            self.attack_type_combo.append_text(attack_type.name)
        self.attack_type_combo.set_active(0)  # Default to first type
        self.attack_type_combo.connect("changed", self._on_attack_type_changed)
        type_box_row.pack_start(self.attack_type_combo, True, True, 0)
        
        type_box.pack_start(type_box_row, False, False, 0)
        
        # Attack description
        desc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        desc_label = Gtk.Label(label="Description:")
        desc_label.set_width_chars(15)
        desc_label.set_xalign(0)
        desc_box.pack_start(desc_label, False, False, 0)
        
        self.attack_description = Gtk.TextView()
        self.attack_description.set_editable(False)
        self.attack_description.set_cursor_visible(False)
        self.attack_description.set_wrap_mode(Gtk.WrapMode.WORD)
        self.attack_description.set_size_request(-1, 60)
        
        desc_scroll = Gtk.ScrolledWindow()
        desc_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        desc_scroll.add(self.attack_description)
        
        desc_box.pack_start(desc_scroll, True, True, 0)
        type_box.pack_start(desc_box, False, False, 0)
        
        method_page.pack_start(type_frame, False, False, 0)
        
        # Wordlist configuration section
        wordlist_frame = Gtk.Frame(label="Wordlist Configuration")
        wordlist_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        wordlist_box.set_border_width(10)
        wordlist_frame.add(wordlist_box)
        
        # Wordlist file
        wordlist_box_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        wordlist_label = Gtk.Label(label="Wordlist:")
        wordlist_label.set_width_chars(15)
        wordlist_label.set_xalign(0)
        wordlist_box_row.pack_start(wordlist_label, False, False, 0)
        
        self.wordlist_entry = Gtk.Entry()
        self.wordlist_entry.set_sensitive(True)
        wordlist_box_row.pack_start(self.wordlist_entry, True, True, 0)
        
        self.wordlist_button = Gtk.Button(label="Browse...")
        self.wordlist_button.connect("clicked", self._on_wordlist_clicked)
        wordlist_box_row.pack_start(self.wordlist_button, False, False, 0)
        
        wordlist_box.pack_start(wordlist_box_row, False, False, 0)
        
        # Rules file
        rules_box_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        rules_label = Gtk.Label(label="Rules File:")
        rules_label.set_width_chars(15)
        rules_label.set_xalign(0)
        rules_box_row.pack_start(rules_label, False, False, 0)
        
        self.rules_entry = Gtk.Entry()
        self.rules_entry.set_sensitive(False)  # Initially disabled
        rules_box_row.pack_start(self.rules_entry, True, True, 0)
        
        self.rules_button = Gtk.Button(label="Browse...")
        self.rules_button.connect("clicked", self._on_rules_clicked)
        self.rules_button.set_sensitive(False)  # Initially disabled
        rules_box_row.pack_start(self.rules_button, False, False, 0)
        
        wordlist_box.pack_start(rules_box_row, False, False, 0)
        
        # Mask pattern
        mask_box_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mask_label = Gtk.Label(label="Mask Pattern:")
        mask_label.set_width_chars(15)
        mask_label.set_xalign(0)
        mask_box_row.pack_start(mask_label, False, False, 0)
        
        self.mask_entry = Gtk.Entry()
        self.mask_entry.set_placeholder_text("?u?l?l?l?l?d?d")
        self.mask_entry.set_sensitive(False)  # Initially disabled
        mask_box_row.pack_start(self.mask_entry, True, True, 0)
        
        wordlist_box.pack_start(mask_box_row, False, False, 0)
        
        method_page.pack_start(wordlist_frame, False, False, 0)
        
        # Add help text for mask patterns
        help_label = Gtk.Label()
        help_label.set_markup("<small>Mask Patterns: ?d (digit), ?u (uppercase), ?l (lowercase), ?s (special), ?a (all)</small>")
        help_label.set_xalign(0)
        method_page.pack_start(help_label, False, False, 5)
        
        # Add method page to notebook
        label = Gtk.Label(label="Method")
        self.notebook.append_page(method_page, label)
        
        # Update the description based on the default selection
        self._update_attack_description()
    
    def _on_attack_type_changed(self, combo):
        """Handle attack type selection change."""
        self._update_attack_description()
        self._update_method_fields()
    
    def _update_attack_description(self):
        """Update the attack description based on the selected type."""
        attack_type_name = self.attack_type_combo.get_active_text()
        
        descriptions = {
            AttackType.DICTIONARY.name: "Tests passwords from a wordlist against the target.",
            AttackType.RULE_BASED.name: "Applies transformation rules to words from a wordlist.",
            AttackType.MASK.name: "Generates passwords matching a specific pattern or mask.",
            AttackType.HYBRID.name: "Combines dictionary words with mask patterns.",
            AttackType.BRUTEFORCE.name: "Tries all possible combinations systematically."
        }
        
        description = descriptions.get(attack_type_name, "")
        
        buffer = self.attack_description.get_buffer()
        buffer.set_text(description)
    
    def _update_method_fields(self):
        """Enable/disable fields based on the selected attack type."""
        attack_type_name = self.attack_type_combo.get_active_text()
        
        # Enable/disable wordlist fields
        wordlist_needed = attack_type_name in [
            AttackType.DICTIONARY.name, 
            AttackType.RULE_BASED.name, 
            AttackType.HYBRID.name
        ]
        self.wordlist_entry.set_sensitive(wordlist_needed)
        self.wordlist_button.set_sensitive(wordlist_needed)
        
        # Enable/disable rules fields
        rules_needed = attack_type_name == AttackType.RULE_BASED.name
        self.rules_entry.set_sensitive(rules_needed)
        self.rules_button.set_sensitive(rules_needed)
        
        # Enable/disable mask fields
        mask_needed = attack_type_name in [AttackType.MASK.name, AttackType.HYBRID.name]
        self.mask_entry.set_sensitive(mask_needed)
    
    def _on_wordlist_clicked(self, button):
        """Handle wordlist browse button click."""
        dialog = Gtk.FileChooserDialog(
            title="Select Wordlist",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        
        # Add filters
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)
        
        filter_any = Gtk.FileFilter()
        filter_any.set_name("All files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.wordlist_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _on_rules_clicked(self, button):
        """Handle rules file browse button click."""
        dialog = Gtk.FileChooserDialog(
            title="Select Rules File",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        
        # Add filters
        filter_rule = Gtk.FileFilter()
        filter_rule.set_name("Rule files")
        filter_rule.add_pattern("*.rule")
        dialog.add_filter(filter_rule)
        
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)
        
        filter_any = Gtk.FileFilter()
        filter_any.set_name("All files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.rules_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _create_options_tab(self):
        """Create the options configuration tab."""
        options_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        options_page.set_border_width(10)
        
        # Performance options section
        perf_frame = Gtk.Frame(label="Performance Options")
        perf_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        perf_box.set_border_width(10)
        perf_frame.add(perf_box)
        
        # Threads
        threads_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        threads_label = Gtk.Label(label="Threads:")
        threads_label.set_width_chars(20)
        threads_label.set_xalign(0)
        threads_box.pack_start(threads_label, False, False, 0)
        
        self.threads_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=4, lower=1, upper=64, step_increment=1, page_increment=5)
        self.threads_spin.set_adjustment(adjustment)
        threads_box.pack_start(self.threads_spin, False, False, 0)
        
        perf_box.pack_start(threads_box, False, False, 0)
        
        # Timeout
        timeout_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        timeout_label = Gtk.Label(label="Connection Timeout:")
        timeout_label.set_width_chars(20)
        timeout_label.set_xalign(0)
        timeout_box.pack_start(timeout_label, False, False, 0)
        
        self.timeout_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=30, lower=1, upper=3600, step_increment=1, page_increment=60)
        self.timeout_spin.set_adjustment(adjustment)
        timeout_box.pack_start(self.timeout_spin, False, False, 0)
        
        timeout_suffix = Gtk.Label(label="seconds")
        timeout_box.pack_start(timeout_suffix, False, False, 5)
        
        perf_box.pack_start(timeout_box, False, False, 0)
        
        options_page.pack_start(perf_frame, False, False, 0)
        
        # Output options section
        output_frame = Gtk.Frame(label="Output Options")
        output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        output_box.set_border_width(10)
        output_frame.add(output_box)
        
        # Output file
        output_box_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        output_label = Gtk.Label(label="Output File:")
        output_label.set_width_chars(20)
        output_label.set_xalign(0)
        output_box_row.pack_start(output_label, False, False, 0)
        
        self.output_entry = Gtk.Entry()
        output_box_row.pack_start(self.output_entry, True, True, 0)
        
        self.output_button = Gtk.Button(label="Browse...")
        self.output_button.connect("clicked", self._on_output_clicked)
        output_box_row.pack_start(self.output_button, False, False, 0)
        
        output_box.pack_start(output_box_row, False, False, 0)
        
        # Verbosity
        verbosity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        verbosity_label = Gtk.Label(label="Verbosity:")
        verbosity_label.set_width_chars(20)
        verbosity_label.set_xalign(0)
        verbosity_box.pack_start(verbosity_label, False, False, 0)
        
        self.verbosity_combo = Gtk.ComboBoxText()
        for level in ["Low", "Normal", "High", "Debug"]:
            self.verbosity_combo.append_text(level)
        self.verbosity_combo.set_active(1)  # Default to Normal
        verbosity_box.pack_start(self.verbosity_combo, False, False, 0)
        
        output_box.pack_start(verbosity_box, False, False, 0)
        
        # Keep stats checkbox
        keep_stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.keep_stats = Gtk.CheckButton(label="Save attack statistics")
        self.keep_stats.set_active(True)
        keep_stats_box.pack_start(self.keep_stats, True, True, 0)
        
        output_box.pack_start(keep_stats_box, False, False, 0)
        
        options_page.pack_start(output_frame, False, False, 0)
        
        # Advanced options section
        adv_frame = Gtk.Frame(label="Advanced Options")
        adv_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        adv_box.set_border_width(10)
        adv_frame.add(adv_box)
        
        # Resume checkbox
        resume_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.resume_check = Gtk.CheckButton(label="Resume previous attack if possible")
        resume_box.pack_start(self.resume_check, True, True, 0)
        
        adv_box.pack_start(resume_box, False, False, 0)
        
        # Stop on success checkbox
        stop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.stop_on_success = Gtk.CheckButton(label="Stop on first success")
        self.stop_on_success.set_active(True)
        stop_box.pack_start(self.stop_on_success, True, True, 0)
        
        adv_box.pack_start(stop_box, False, False, 0)
        
        options_page.pack_start(adv_frame, False, False, 0)
        
        # Add options page to notebook
        label = Gtk.Label(label="Options")
        self.notebook.append_page(options_page, label)
    
    def _on_output_clicked(self, button):
        """Handle output file browse button click."""
        dialog = Gtk.FileChooserDialog(
            title="Save Output File",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK
            )
        )
        
        # Add filters
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)
        
        filter_csv = Gtk.FileFilter()
        filter_csv.set_name("CSV files")
        filter_csv.add_pattern("*.csv")
        dialog.add_filter(filter_csv)
        
        filter_any = Gtk.FileFilter()
        filter_any.set_name("All files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)
        
        dialog.set_do_overwrite_confirmation(True)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.output_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _create_schedule_tab(self):
        """Create the schedule and plan management tab."""
        schedule_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        schedule_page.set_border_width(10)
        
        # Schedule section
        schedule_frame = Gtk.Frame(label="Schedule Attack")
        schedule_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        schedule_box.set_border_width(10)
        schedule_frame.add(schedule_box)
        
        # Schedule checkbox
        schedule_check_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.schedule_check = Gtk.CheckButton(label="Schedule attack for later")
        # TODO: Implement scheduling functionality in a later version
        self.schedule_check.set_sensitive(False)  # Disable for now
        schedule_check_box.pack_start(self.schedule_check, True, True, 0)
        
        schedule_box.pack_start(schedule_check_box, False, False, 0)
        
        # Max runtime
        max_runtime_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        max_runtime_label = Gtk.Label(label="Maximum Runtime:")
        max_runtime_label.set_width_chars(20)
        max_runtime_label.set_xalign(0)
        max_runtime_box.pack_start(max_runtime_label, False, False, 0)
        
        self.max_runtime_spin = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(value=0, lower=0, upper=999999, step_increment=1, page_increment=60)
        self.max_runtime_spin.set_adjustment(adjustment)
        max_runtime_box.pack_start(self.max_runtime_spin, False, False, 0)
        
        max_runtime_suffix = Gtk.Label(label="minutes (0 = unlimited)")
        max_runtime_box.pack_start(max_runtime_suffix, False, False, 5)
        
        schedule_box.pack_start(max_runtime_box, False, False, 0)
        
        schedule_page.pack_start(schedule_frame, False, False, 0)
        
        # Plan management section
        plans_frame = Gtk.Frame(label="Save Attack Plan")
        plans_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        plans_box.set_border_width(10)
        plans_frame.add(plans_box)
        
        # Plan name
        plan_name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        plan_name_label = Gtk.Label(label="Plan Name:")
        plan_name_label.set_width_chars(15)
        plan_name_label.set_xalign(0)
        plan_name_box.pack_start(plan_name_label, False, False, 0)
        
        self.plan_name_entry = Gtk.Entry()
        plan_name_box.pack_start(self.plan_name_entry, True, True, 0)
        
        plans_box.pack_start(plan_name_box, False, False, 0)
        
        # Save button
        save_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.save_plan_button = Gtk.Button.new_with_label("Save Plan")
        self.save_plan_button.connect("clicked", self._on_save_plan_clicked)
        save_button_box.pack_start(self.save_plan_button, False, False, 0)
        
        plans_box.pack_start(save_button_box, False, False, 0)
        
        # Saved plans
        saved_plans_label = Gtk.Label(label="Saved Plans:")
        saved_plans_label.set_xalign(0)
        plans_box.pack_start(saved_plans_label, False, False, 0)
        
        # Plans list (in scrollable area)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(100)
        
        # Create plans list store and view
        self.plans_store = Gtk.ListStore(str)  # Plan name
        self.plans_view = Gtk.TreeView(model=self.plans_store)
        
        # Add column
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Plan Name", renderer, text=0)
        self.plans_view.append_column(column)
        
        # Add selection handling
        self.plans_selection = self.plans_view.get_selection()
        self.plans_selection.connect("changed", self._on_plan_selection_changed)
        
        scrolled_window.add(self.plans_view)
        plans_box.pack_start(scrolled_window, True, True, 0)
        
        # Load and delete buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.load_plan_button = Gtk.Button.new_with_label("Load Selected Plan")
        self.load_plan_button.connect("clicked", self._on_load_plan_clicked)
        self.load_plan_button.set_sensitive(False)  # Initially disabled
        button_box.pack_start(self.load_plan_button, True, True, 0)
        
        self.delete_plan_button = Gtk.Button.new_with_label("Delete Selected Plan")
        self.delete_plan_button.connect("clicked", self._on_delete_plan_clicked)
        self.delete_plan_button.set_sensitive(False)  # Initially disabled
        button_box.pack_start(self.delete_plan_button, True, True, 0)
        
        plans_box.pack_start(button_box, False, False, 0)
        
        schedule_page.pack_start(plans_frame, True, True, 0)
        
        # Add schedule page to notebook
        label = Gtk.Label(label="Schedule & Plans")
        self.notebook.append_page(schedule_page, label)
    
    def _create_action_buttons(self):
        """Create action buttons at the bottom of the form."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_margin_top(10)
        
        # Progress bar (hidden by default)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_text("0%")
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_visible(False)
        button_box.pack_start(self.progress_bar, True, True, 0)
        
        # Start attack button
        self.start_button = Gtk.Button.new_with_label("Start Attack")
        self.start_button.get_style_context().add_class("suggested-action")  # Green button
        self.start_button.connect("clicked", self._on_start_attack_clicked)
        button_box.pack_start(self.start_button, False, False, 0)
        
        self.pack_end(button_box, False, False, 0)
    
    def _on_plan_selection_changed(self, selection):
        """Handle plan selection change."""
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            # Enable the load and delete buttons
            self.load_plan_button.set_sensitive(True)
            self.delete_plan_button.set_sensitive(True)
        else:
            # Disable the load and delete buttons
            self.load_plan_button.set_sensitive(False)
            self.delete_plan_button.set_sensitive(False)
    
    def _on_save_plan_clicked(self, button):
        """Handle save plan button click."""
        plan_name = self.plan_name_entry.get_text().strip()
        if not plan_name:
            self._show_error_dialog("Error", "Please enter a name for the plan.")
            return
        
        # Collect all configuration settings
        plan_data = self._collect_attack_config()
        
        # Save to file
        plan_file = os.path.join(self.plans_dir, f"{plan_name}.json")
        try:
            with open(plan_file, 'w') as f:
                json.dump(plan_data, f, indent=4)
            
            # Update plans list
            self.load_saved_plans()
            
            # Show success message
            self._show_info_dialog("Success", f"Attack plan '{plan_name}' saved successfully.")
            
            # Emit signal
            self.emit("attack-saved", plan_name)
            
        except Exception as e:
            self.logger.error(f"Failed to save attack plan: {str(e)}")
            self._show_error_dialog("Error", f"Failed to save attack plan: {str(e)}")
    
    def _on_load_plan_clicked(self, button):
        """Handle load plan button click."""
        model, treeiter = self.plans_selection.get_selected()
        if treeiter is None:
            return
            
        plan_name = model[treeiter][0]
        plan_file = os.path.join(self.plans_dir, f"{plan_name}.json")
        
        try:
            with open(plan_file, 'r') as f:
                plan_data = json.load(f)
            
            # Apply plan data to UI elements
            self._apply_plan_data(plan_data)
            
            # Show success message
            self._show_info_dialog("Success", f"Attack plan '{plan_name}' loaded successfully.")
            
        except Exception as e:
            self.logger.error(f"Failed to load attack plan: {str(e)}")
            self._show_error_dialog("Error", f"Failed to load attack plan: {str(e)}")
    
    def _on_delete_plan_clicked(self, button):
        """Handle delete plan button click."""
        model, treeiter = self.plans_selection.get_selected()
        if treeiter is None:
            return
            
        plan_name = model[treeiter][0]
        
        # Confirm deletion
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Confirm Delete"
        )
        dialog.format_secondary_text(f"Are you sure you want to delete the plan '{plan_name}'?")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            plan_file = os.path.join(self.plans_dir, f"{plan_name}.json")
            try:
                os.remove(plan_file)
                
                # Update plans list
                self.load_saved_plans()
                
                # Show success message
                self._show_info_dialog("Success", f"Attack plan '{plan_name}' deleted successfully.")
                
            except Exception as e:
                self.logger.error(f"Failed to delete attack plan: {str(e)}")
                self._show_error_dialog("Error", f"Failed to delete attack plan: {str(e)}")
    
    def _on_start_attack_clicked(self, button):
        """Handle start attack button click."""
        # Basic validation
        if not self.host_entry.get_text():
            self._show_error_dialog("Error", "Please enter a host/IP address.")
            return
        
        if self.use_username_file.get_active() and not self.username_file_entry.get_text():
            self._show_error_dialog("Error", "Please select a username list file.")
            return
        
        if not self.use_username_file.get_active() and not self.username_entry.get_text():
            self._show_error_dialog("Error", "Please enter a username.")
            return
        
        attack_type = self.attack_type_combo.get_active_text()
        
        # Validate wordlist for dictionary/rule-based attacks
        if attack_type in [AttackType.DICTIONARY.name, AttackType.RULE_BASED.name, AttackType.HYBRID.name]:
            if not self.wordlist_entry.get_text():
                self._show_error_dialog("Error", "Please select a wordlist file.")
                return
        
        # Validate rules file for rule-based attacks
        if attack_type == AttackType.RULE_BASED.name and not self.rules_entry.get_text():
            self._show_error_dialog("Error", "Please select a rules file.")
            return
        
        # Validate mask for mask attacks
        if attack_type in [AttackType.MASK.name, AttackType.HYBRID.name] and not self.mask_entry.get_text():
            self._show_error_dialog("Error", "Please enter a mask pattern.")
            return
        
        # Collect attack configuration
        attack_config = self._collect_attack_config()
        
        # Confirm with user
        msg = (f"Starting {attack_config['attack_type']} attack on {attack_config['host']}:{attack_config['port']} "
               f"using protocol {attack_config['protocol']}.\n\n"
               f"Are you sure you want to proceed?")
        
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Confirm Attack"
        )
        dialog.format_secondary_text(msg)
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Show progress bar and disable start button
            self.progress_bar.set_visible(True)
            self.start_button.set_sensitive(False)
            
            # Emit signal with attack configuration
            self.emit("attack-started", attack_config)
            
            # In a real application, we would connect to signals from the attack
            # to update the progress bar and re-enable the start button when done
    
    def _collect_attack_config(self):
        """Collect the attack configuration from UI elements.
        
        Returns:
            Dictionary containing attack configuration
        """
        return {
            "protocol": self.protocol_combo.get_active_text(),
            "host": self.host_entry.get_text(),
            "port": self.port_spin.get_value_as_int(),
            "username": None if self.use_username_file.get_active() else self.username_entry.get_text(),
            "username_file": self.username_file_entry.get_text() if self.use_username_file.get_active() else None,
            "attack_type": self.attack_type_combo.get_active_text(),
            "wordlist": self.wordlist_entry.get_text(),
            "rules_file": self.rules_entry.get_text(),
            "mask": self.mask_entry.get_text(),
            "threads": self.threads_spin.get_value_as_int(),
            "timeout": self.timeout_spin.get_value_as_int(),
            "output_file": self.output_entry.get_text(),
            "verbosity": self.verbosity_combo.get_active_text(),
            "keep_stats": self.keep_stats.get_active(),
            "resume": self.resume_check.get_active(),
            "stop_on_success": self.stop_on_success.get_active(),
            "scheduled": self.schedule_check.get_active(),
            "max_runtime": self.max_runtime_spin.get_value_as_int()
        }
    
    def _apply_plan_data(self, plan_data):
        """Apply loaded plan data to UI elements.
        
        Args:
            plan_data: Dictionary containing plan configuration
        """
        # Protocol
        protocol_index = 0
        protocol = plan_data.get("protocol")
        if protocol:
            for i in range(self.protocol_combo.get_model().iter_n_children(None)):
                if self.protocol_combo.get_model()[i][0] == protocol:
                    protocol_index = i
                    break
        self.protocol_combo.set_active(protocol_index)
        
        # Host and port
        self.host_entry.set_text(plan_data.get("host", ""))
        self.port_spin.set_value(plan_data.get("port", 22))
        
        # Username settings
        use_username_file = plan_data.get("username_file") is not None
        self.use_username_file.set_active(use_username_file)
        if use_username_file:
            self.username_file_entry.set_text(plan_data.get("username_file", ""))
        else:
            self.username_entry.set_text(plan_data.get("username", ""))
        
        # Attack type
        attack_type_index = 0
        attack_type = plan_data.get("attack_type")
        if attack_type:
            for i in range(self.attack_type_combo.get_model().iter_n_children(None)):
                if self.attack_type_combo.get_model()[i][0] == attack_type:
                    attack_type_index = i
                    break
        self.attack_type_combo.set_active(attack_type_index)
        
        # Method settings
        self.wordlist_entry.set_text(plan_data.get("wordlist", ""))
        self.rules_entry.set_text(plan_data.get("rules_file", ""))
        self.mask_entry.set_text(plan_data.get("mask", ""))
        
        # Options
        self.threads_spin.set_value(plan_data.get("threads", 4))
        self.timeout_spin.set_value(plan_data.get("timeout", 30))
        self.output_entry.set_text(plan_data.get("output_file", ""))
        
        # Verbosity
        verbosity_index = 1  # Default to Normal
        verbosity = plan_data.get("verbosity")
        if verbosity:
            verbosity_items = ["Low", "Normal", "High", "Debug"]
            if verbosity in verbosity_items:
                verbosity_index = verbosity_items.index(verbosity)
        self.verbosity_combo.set_active(verbosity_index)
        
        # Checkboxes
        self.keep_stats.set_active(plan_data.get("keep_stats", True))
        self.resume_check.set_active(plan_data.get("resume", False))
        self.stop_on_success.set_active(plan_data.get("stop_on_success", True))
        self.schedule_check.set_active(plan_data.get("scheduled", False))
        
        # Runtime
        self.max_runtime_spin.set_value(plan_data.get("max_runtime", 0))
        
        # Set plan name
        self.plan_name_entry.set_text(plan_data.get("name", ""))
    
    def load_saved_plans(self):
        """Load saved attack plans into list."""
        self.plans_store.clear()
        
        try:
            if not os.path.exists(self.plans_dir):
                return
                
            plans = [f[:-5] for f in os.listdir(self.plans_dir) if f.endswith('.json')]
            plans.sort()
            
            for plan in plans:
                self.plans_store.append([plan])
            
        except Exception as e:
            self.logger.error(f"Failed to load saved plans: {str(e)}")
            self._show_warning_dialog("Warning", f"Failed to load saved plans: {str(e)}")
    
    def _show_error_dialog(self, title, message):
        """Show an error dialog.
        
        Args:
            title: Dialog title
            message: Dialog message
        """
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
    
    def _show_warning_dialog(self, title, message):
        """Show a warning dialog.
        
        Args:
            title: Dialog title
            message: Dialog message
        """
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
    
    def _show_info_dialog(self, title, message):
        """Show an information dialog.
        
        Args:
            title: Dialog title
            message: Dialog message
        """
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
