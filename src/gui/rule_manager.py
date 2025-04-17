#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Rule Manager component.
This module provides UI integration for rule management functionality.
"""

import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango

from src.utils.logging import get_logger
from src.rules.parser import RuleParser
from src.rules.transformer import RuleTransformer, apply_rule, apply_rules
from src.rules.generator import RuleGenerator
from src.gui.rule_editor import RuleEditor


class RuleManager(Gtk.Box):
    """Rule management panel for managing rule operations in the GUI."""
    
    def __init__(self):
        """Initialize the rule manager panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Initialize rule components
        self.rule_parser = RuleParser()
        self.rule_transformer = RuleTransformer()
        self.rule_generator = RuleGenerator()
        
        # Create UI components
        self._create_notebook()
    
    def _create_notebook(self):
        """Create notebook with rule-related tabs."""
        self.notebook = Gtk.Notebook()
        self.pack_start(self.notebook, True, True, 0)
        
        # Rule editor tab
        self.rule_editor = RuleEditor()
        self.notebook.append_page(self.rule_editor, Gtk.Label(label="Rule Editor"))
        
        # Rule tester tab
        self.rule_tester = self._create_rule_tester()
        self.notebook.append_page(self.rule_tester, Gtk.Label(label="Rule Tester"))
        
        # Rule generator tab
        self.rule_generator_tab = self._create_rule_generator()
        self.notebook.append_page(self.rule_generator_tab, Gtk.Label(label="Rule Generator"))
    
    def _create_rule_tester(self):
        """Create the rule tester panel.
        
        Returns:
            Gtk.Box: The rule tester panel
        """
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Rule file selection
        selector_frame = Gtk.Frame(label="Select Rule File")
        selector_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        selector_box.set_border_width(10)
        selector_frame.add(selector_box)
        
        rule_files = self.rule_parser.get_available_rule_files()
        
        self.rule_file_combo = Gtk.ComboBoxText()
        for filename in sorted(rule_files.keys()):
            self.rule_file_combo.append_text(filename)
        
        if rule_files:
            self.rule_file_combo.set_active(0)
            
        selector_box.pack_start(self.rule_file_combo, False, False, 0)
        box.pack_start(selector_frame, False, False, 0)
        
        # Test input
        input_frame = Gtk.Frame(label="Test Input")
        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        input_box.set_border_width(10)
        input_frame.add(input_box)
        
        # Password input
        password_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        password_label = Gtk.Label(label="Password:")
        password_label.set_width_chars(12)
        password_box.pack_start(password_label, False, False, 0)
        
        self.password_entry = Gtk.Entry()
        self.password_entry.set_text("password")
        password_box.pack_start(self.password_entry, True, True, 0)
        
        input_box.pack_start(password_box, False, False, 0)
        
        # Test button
        self.test_button = Gtk.Button.new_with_label("Test Rules")
        self.test_button.connect("clicked", self._on_test_rules_clicked)
        input_box.pack_start(self.test_button, False, False, 0)
        
        box.pack_start(input_frame, False, False, 0)
        
        # Results
        results_frame = Gtk.Frame(label="Test Results")
        results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        results_box.set_border_width(10)
        results_frame.add(results_box)
        
        # Create scrollable window for results
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(-1, 300)
        
        # Results store and view
        self.results_store = Gtk.ListStore(str, str, str)  # Rule, Original, Transformed
        self.results_view = Gtk.TreeView(model=self.results_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Rule", renderer, text=0)
        column.set_resizable(True)
        column.set_min_width(150)
        self.results_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Original", renderer, text=1)
        column.set_resizable(True)
        column.set_min_width(150)
        self.results_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Transformed", renderer, text=2)
        column.set_resizable(True)
        column.set_min_width(150)
        self.results_view.append_column(column)
        
        scrolled.add(self.results_view)
        results_box.pack_start(scrolled, True, True, 0)
        
        # Add a summary label
        self.summary_label = Gtk.Label()
        self.summary_label.set_xalign(0)
        results_box.pack_start(self.summary_label, False, False, 0)
        
        # Export button
        self.export_button = Gtk.Button.new_with_label("Export Results")
        self.export_button.connect("clicked", self._on_export_results_clicked)
        self.export_button.set_sensitive(False)
        results_box.pack_start(self.export_button, False, False, 0)
        
        box.pack_start(results_frame, True, True, 0)
        
        return box
    
    def _create_rule_generator(self):
        """Create the rule generator panel.
        
        Returns:
            Gtk.Box: The rule generator panel
        """
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Rule generation settings
        settings_frame = Gtk.Frame(label="Rule Generation Settings")
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        settings_box.set_border_width(10)
        settings_frame.add(settings_box)
        
        # File name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="File Name:")
        name_label.set_width_chars(15)
        name_box.pack_start(name_label, False, False, 0)
        
        self.gen_name_entry = Gtk.Entry()
        self.gen_name_entry.set_text("generated.rule")
        name_box.pack_start(self.gen_name_entry, True, True, 0)
        
        settings_box.pack_start(name_box, False, False, 0)
        
        # Complexity
        complexity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        complexity_label = Gtk.Label(label="Complexity:")
        complexity_label.set_width_chars(15)
        complexity_box.pack_start(complexity_label, False, False, 0)
        
        self.complexity_combo = Gtk.ComboBoxText()
        self.complexity_combo.append_text("Basic")
        self.complexity_combo.append_text("Medium")
        self.complexity_combo.append_text("Advanced")
        self.complexity_combo.set_active(1)  # Default to Medium
        complexity_box.pack_start(self.complexity_combo, True, True, 0)
        
        settings_box.pack_start(complexity_box, False, False, 0)
        
        # Rule count
        count_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        count_label = Gtk.Label(label="Number of Rules:")
        count_label.set_width_chars(15)
        count_box.pack_start(count_label, False, False, 0)
        
        adjustment = Gtk.Adjustment(value=100, lower=10, upper=1000, step_increment=10, page_increment=50)
        self.count_spinner = Gtk.SpinButton()
        self.count_spinner.set_adjustment(adjustment)
        count_box.pack_start(self.count_spinner, True, True, 0)
        
        settings_box.pack_start(count_box, False, False, 0)
        
        # Description
        desc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        desc_label = Gtk.Label(label="Description:")
        desc_label.set_width_chars(15)
        desc_box.pack_start(desc_label, False, False, 0)
        
        self.desc_entry = Gtk.Entry()
        self.desc_entry.set_text("Generated password mutation rules")
        desc_box.pack_start(self.desc_entry, True, True, 0)
        
        settings_box.pack_start(desc_box, False, False, 0)
        
        # Generate button
        self.generate_button = Gtk.Button.new_with_label("Generate Rules")
        self.generate_button.connect("clicked", self._on_generate_rules_clicked)
        settings_box.pack_start(self.generate_button, False, False, 0)
        
        box.pack_start(settings_frame, False, False, 0)
        
        # Generator info
        info_frame = Gtk.Frame(label="Rule Generator Information")
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info_box.set_border_width(10)
        info_frame.add(info_box)
        
        info_text = """
<b>Rule Generation Options:</b>

<b>Basic Complexity:</b> Creates simple rules including case changes, single character substitutions, and basic prefixes/suffixes. Ideal for testing and quick mutations.

<b>Medium Complexity:</b> Combines basic rules with some more advanced transformations. Includes multiple character substitutions and combined operations.

<b>Advanced Complexity:</b> Creates comprehensive rule sets with complex mutations, multiple substitutions, and specialized transformations designed for thorough password testing.

Generated rules are saved in your user rule directory and can be further edited in the Rule Editor tab.
"""
        
        info_label = Gtk.Label()
        info_label.set_markup(info_text)
        info_label.set_line_wrap(True)
        info_label.set_xalign(0)
        
        info_box.pack_start(info_label, False, False, 0)
        
        box.pack_start(info_frame, False, False, 0)
        
        # Recent generations
        history_frame = Gtk.Frame(label="Recently Generated Rule Files")
        history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        history_box.set_border_width(10)
        history_frame.add(history_box)
        
        # Create scrollable window for history
        history_scrolled = Gtk.ScrolledWindow()
        history_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        history_scrolled.set_size_request(-1, 150)
        
        # History store and view
        self.history_store = Gtk.ListStore(str, str, str, str)  # Name, Date, Complexity, Count
        self.history_view = Gtk.TreeView(model=self.history_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("File", renderer, text=0)
        column.set_resizable(True)
        self.history_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Date", renderer, text=1)
        column.set_resizable(True)
        self.history_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Complexity", renderer, text=2)
        column.set_resizable(True)
        self.history_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Rules", renderer, text=3)
        column.set_resizable(True)
        self.history_view.append_column(column)
        
        history_scrolled.add(self.history_view)
        history_box.pack_start(history_scrolled, True, True, 0)
        
        # Add a refresh button
        refresh_button = Gtk.Button.new_with_label("Refresh List")
        refresh_button.connect("clicked", self._on_refresh_history_clicked)
        history_box.pack_start(refresh_button, False, False, 0)
        
        box.pack_start(history_frame, True, True, 0)
        
        # Initialize the history list
        self._refresh_history()
        
        return box
    
    def _on_test_rules_clicked(self, button):
        """Handle test rules button click.
        
        Args:
            button: Button that was clicked
        """
        rule_file = self.rule_file_combo.get_active_text()
        password = self.password_entry.get_text()
        
        if not rule_file or not password:
            return
        
        # Clear results store
        self.results_store.clear()
        
        # Apply rules to password
        try:
            results = self.rule_transformer.apply_rule_file_with_info(password, rule_file)
            
            # Add results to store
            for result in results:
                self.results_store.append([
                    result['rule'],
                    result['password'],
                    result['transformed']
                ])
            
            # Update summary
            self.summary_label.set_text(f"Applied {len(results)} rules from {rule_file}")
            
            # Enable export button
            self.export_button.set_sensitive(True)
            
        except Exception as e:
            self.logger.error(f"Error testing rules: {str(e)}")
            error_dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Testing Rules"
            )
            error_dialog.format_secondary_text(str(e))
            error_dialog.run()
            error_dialog.destroy()
    
    def _on_export_results_clicked(self, button):
        """Handle export results button click.
        
        Args:
            button: Button that was clicked
        """
        dialog = Gtk.FileChooserDialog(
            title="Save Results",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT
            )
        )
        
        dialog.set_current_name("rule_test_results.csv")
        dialog.set_do_overwrite_confirmation(True)
        
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            try:
                with open(filename, 'w') as f:
                    # Write CSV header
                    f.write("Rule,Original,Transformed\n")
                    
                    # Write results
                    for row in self.results_store:
                        f.write(f"\"{row[0]}\",\"{row[1]}\",\"{row[2]}\"\n")
                
                info_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Export Successful"
                )
                info_dialog.format_secondary_text(f"Results exported to {filename}")
                info_dialog.run()
                info_dialog.destroy()
                
            except Exception as e:
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Export Failed"
                )
                error_dialog.format_secondary_text(str(e))
                error_dialog.run()
                error_dialog.destroy()
        
        dialog.destroy()
    
    def _on_generate_rules_clicked(self, button):
        """Handle generate rules button click.
        
        Args:
            button: Button that was clicked
        """
        filename = self.gen_name_entry.get_text().strip()
        complexity = ["basic", "medium", "advanced"][self.complexity_combo.get_active()]
        count = self.count_spinner.get_value_as_int()
        description = self.desc_entry.get_text().strip()
        
        # Generate the rule file
        try:
            success = self.rule_generator.generate_rule_file(
                filename, 
                complexity, 
                count, 
                description
            )
            
            if success:
                # Update rule file combo
                self._refresh_rule_files()
                
                # Update history
                self._refresh_history()
                
                # Show success message
                info_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Rule Generation Successful"
                )
                info_dialog.format_secondary_text(f"Generated {count} rules with {complexity} complexity and saved to {filename}")
                info_dialog.run()
                info_dialog.destroy()
                
                # Update rule editor
                self.rule_editor.refresh_rules()
            else:
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Rule Generation Failed"
                )
                error_dialog.format_secondary_text("Failed to generate rule file")
                error_dialog.run()
                error_dialog.destroy()
                
        except Exception as e:
            error_dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Rule Generation Error"
            )
            error_dialog.format_secondary_text(str(e))
            error_dialog.run()
            error_dialog.destroy()
    
    def _on_refresh_history_clicked(self, button):
        """Handle refresh history button click.
        
        Args:
            button: Button that was clicked
        """
        self._refresh_history()
    
    def _refresh_rule_files(self):
        """Refresh the list of rule files in the combo box."""
        # Get available rule files
        rule_files = self.rule_parser.get_available_rule_files()
        
        # Clear combo box
        self.rule_file_combo.remove_all()
        
        # Add files to combo box
        for filename in sorted(rule_files.keys()):
            self.rule_file_combo.append_text(filename)
        
        # Select first file if available
        if rule_files:
            self.rule_file_combo.set_active(0)
    
    def _refresh_history(self):
        """Refresh the list of recently generated rule files."""
        # Clear the store
        self.history_store.clear()
        
        # Get rule files
        rule_files = self.rule_parser.get_available_rule_files()
        
        # Check each file to see if it was generated
        for filename, filepath in rule_files.items():
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                    # Check if it's a generated file
                    if "Generated by ERPCT Rule Generator" in content:
                        # Get file info
                        import os
                        import datetime
                        
                        # Get creation date
                        stats = os.stat(filepath)
                        creation_date = datetime.datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M")
                        
                        # Get complexity and rule count
                        complexity = "Unknown"
                        if "Basic password mutation rules" in content:
                            complexity = "Basic"
                        elif "Medium complexity password mutation rules" in content:
                            complexity = "Medium"
                        elif "Advanced password mutation rules" in content:
                            complexity = "Advanced"
                        
                        # Count actual rules
                        rule_count = 0
                        for line in content.split('\n'):
                            if line.strip() and not line.strip().startswith('#'):
                                rule_count += 1
                        
                        # Add to history
                        self.history_store.append([
                            filename,
                            creation_date,
                            complexity,
                            str(rule_count)
                        ])
            except Exception as e:
                self.logger.warning(f"Error analyzing rule file {filepath}: {str(e)}")
        
        # Sort by date (newest first)
        self.history_store.set_sort_column_id(1, Gtk.SortType.DESCENDING) 