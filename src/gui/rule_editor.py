#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Rule Editor component.
This module provides the GUI panel for editing password mutation rules.
"""

import os
import re
import time
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango, Gdk

from src.utils.logging import get_logger
from src.rules.parser import RuleParser
from src.rules.transformer import apply_rule, apply_rules
from src.rules.generator import RuleGenerator


class RuleEditor(Gtk.Box):
    """Rule editor panel for editing password mutation rules."""
    
    def __init__(self):
        """Initialize the rule editor panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Initialize rule modules
        self.rule_parser = RuleParser()
        self.rule_generator = RuleGenerator()
        
        # Default rules directory - use the one from rule parser
        self.rules_dir = self.rule_parser.rules_directories[0] if self.rule_parser.rules_directories else os.path.join(os.path.expanduser("~"), ".erpct", "rules")
        os.makedirs(self.rules_dir, exist_ok=True)
        
        # Currently loaded rule file
        self.current_rule_file = None
        self.modified = False
        
        # Create UI components
        self._create_rule_selector()
        self._create_rule_editor()
        self._create_test_area()
        self._create_action_buttons()
        
        # Refresh rule list
        self.refresh_rules()
        
        # Sample rules for new files
        self.sample_rules = """# Basic password mutation rules
# Use these as examples or customize them for your needs

# Basic transformations
:
l
u
c
r
d

# Common character substitutions 
sa@
se3
si!
sl1
so0

# Word mangling
c
^admin
$2023

# Combined transformations
c$123
sa@se3
c$!2023"""
    
    def _create_rule_selector(self):
        """Create rule selector section."""
        frame = Gtk.Frame(label="Rule Files")
        frame.set_size_request(-1, 100)
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Scrollable rule file list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Rule files store and view
        self.rules_store = Gtk.ListStore(str, str)  # Name, Path
        self.rules_view = Gtk.TreeView(model=self.rules_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Rule File", renderer, text=0)
        column.set_resizable(True)
        self.rules_view.append_column(column)
        
        scrolled.add(self.rules_view)
        box.pack_start(scrolled, True, True, 0)
        
        # Selection handling
        self.selection = self.rules_view.get_selection()
        self.selection.connect("changed", self._on_selection_changed)
    
    def _create_rule_editor(self):
        """Create rule editor section."""
        frame = Gtk.Frame(label="Rule Editor")
        self.pack_start(frame, True, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Scrollable rule editor
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Text view for rule content
        self.rule_view = Gtk.TextView()
        self.rule_view.set_monospace(True)
        self.rule_view.connect("key-press-event", self._on_rule_editor_key_press)
        
        # Set up text buffer
        self.rule_buffer = self.rule_view.get_buffer()
        self.rule_buffer.connect("changed", self._on_rule_buffer_changed)
        
        # Setup syntax highlighting for rules
        self._setup_syntax_highlighting()
        
        scrolled.add(self.rule_view)
        box.pack_start(scrolled, True, True, 0)
        
        # Help expander
        expander = Gtk.Expander(label="Rule Syntax Help")
        box.pack_start(expander, False, False, 0)
        
        help_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        help_text = """
<b>Basic Rule Commands:</b>
:  - Do nothing
l  - Convert to lowercase (password → password)
u  - Convert to uppercase (password → PASSWORD)
c  - Capitalize (password → Password)
r  - Reverse (password → drowssap)
d  - Duplicate (password → passwordpassword)

<b>Character Substitutions:</b>
s[a][b]  - Replace all a with b (sao: password → possword)
@[x]     - Purge all instances of x (@s: password → paword)

<b>Prefixes and Suffixes:</b>
^[x]  - Prepend character x (^1: password → 1password)
$[x]  - Append character x ($1: password → password1)

<b>Length Control:</b>
<[N]  - Truncate to N characters (<5: password → passw)
>[N]  - Skip first N characters (>2: password → ssword)
        """
        
        help_label = Gtk.Label()
        help_label.set_markup(help_text)
        help_label.set_line_wrap(True)
        help_label.set_xalign(0)
        
        help_box.pack_start(help_label, False, False, 0)
        expander.add(help_box)
    
    def _create_test_area(self):
        """Create rule testing section."""
        frame = Gtk.Frame(label="Test Rules")
        self.pack_start(frame, False, False, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Test input
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_label = Gtk.Label(label="Test Password:")
        input_box.pack_start(input_label, False, False, 0)
        
        self.test_input = Gtk.Entry()
        self.test_input.set_text("password")
        input_box.pack_start(self.test_input, True, True, 0)
        
        self.test_button = Gtk.Button.new_with_label("Test")
        self.test_button.connect("clicked", self._on_test_clicked)
        input_box.pack_start(self.test_button, False, False, 0)
        
        box.pack_start(input_box, False, False, 0)
        
        # Test results
        results_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        results_label = Gtk.Label(label="Results:")
        results_box.pack_start(results_label, False, False, 0)
        
        self.results_view = Gtk.TextView()
        self.results_view.set_editable(False)
        self.results_view.set_cursor_visible(False)
        self.results_view.set_wrap_mode(Gtk.WrapMode.WORD)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.results_view)
        scrolled.set_size_request(-1, 150)
        
        results_box.pack_start(scrolled, True, True, 0)
        box.pack_start(results_box, True, True, 0)
    
    def _create_action_buttons(self):
        """Create action buttons section."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_start(button_box, False, False, 0)
        
        # New button
        self.new_button = Gtk.Button.new_with_label("New Rule File")
        self.new_button.connect("clicked", self._on_new_clicked)
        button_box.pack_start(self.new_button, False, False, 0)
        
        # Save button (initially disabled)
        self.save_button = Gtk.Button.new_with_label("Save")
        self.save_button.connect("clicked", self._on_save_clicked)
        self.save_button.set_sensitive(False)
        button_box.pack_start(self.save_button, False, False, 0)
        
        # Delete button (initially disabled)
        self.delete_button = Gtk.Button.new_with_label("Delete")
        self.delete_button.connect("clicked", self._on_delete_clicked)
        self.delete_button.set_sensitive(False)
        button_box.pack_start(self.delete_button, False, False, 0)
        
        # Generate button
        self.generate_button = Gtk.Button.new_with_label("Generate Rules")
        self.generate_button.connect("clicked", self._on_generate_clicked)
        button_box.pack_start(self.generate_button, False, False, 0)
        
        # Spacer
        button_box.pack_start(Gtk.Label(), True, True, 0)
    
    def _setup_syntax_highlighting(self):
        """Set up syntax highlighting for rule commands."""
        # Nothing to do for basic implementation
        pass
        
    def _apply_syntax_highlighting(self):
        """Apply syntax highlighting to current rule buffer content."""
        # Simple highlighting implementation could be added here
        pass
    
    def _on_selection_changed(self, selection):
        """Handle rule file selection change.
        
        Args:
            selection: The TreeSelection that changed
        """
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            # Get the selected rule file path
            rule_path = model[treeiter][1]
            
            # Check if current file has unsaved changes
            if self.modified:
                dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.QUESTION,
                    buttons=Gtk.ButtonsType.YES_NO,
                    text="Unsaved Changes"
                )
                dialog.format_secondary_text(
                    "You have unsaved changes. Do you want to save them before loading the new file?"
                )
                response = dialog.run()
                dialog.destroy()
                
                if response == Gtk.ResponseType.YES:
                    self._save_current_file()
            
            # Load the selected rule file
            self.load_rule_file(rule_path)
            self.delete_button.set_sensitive(True)
    
    def _on_rule_buffer_changed(self, buffer):
        """Handle rule text buffer changes.
        
        Args:
            buffer: The text buffer that changed
        """
        if not self.modified:
            self.modified = True
            self.save_button.set_sensitive(True)
            
        # Could apply syntax highlighting here
    
    def _on_rule_editor_key_press(self, widget, event):
        """Handle key press in the rule editor.
        
        Args:
            widget: The widget where the key was pressed
            event: The key event
            
        Returns:
            True if the event was handled, False otherwise
        """
        return False  # Let default handler process the event
    
    def _on_new_clicked(self, button):
        """Handle new button click.
        
        Args:
            button: Button that was clicked
        """
        # Check if current file has unsaved changes
        if self.modified:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Unsaved Changes"
            )
            dialog.format_secondary_text(
                "You have unsaved changes. Do you want to save them before creating a new file?"
            )
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                self._save_current_file()
        
        # Create new file dialog
        dialog = Gtk.Dialog(
            title="Create New Rule File",
            transient_for=self.get_toplevel(),
            flags=0,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK
            )
        )
        dialog.set_default_size(400, 100)
        
        # File name entry
        box = dialog.get_content_area()
        box.set_spacing(6)
        
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="File Name:")
        name_box.pack_start(name_label, False, False, 0)
        
        name_entry = Gtk.Entry()
        name_entry.set_text("custom.rule")
        name_box.pack_start(name_entry, True, True, 0)
        
        box.pack_start(name_box, False, False, 0)
        
        # Template options
        template_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        template_label = Gtk.Label(label="Template:")
        template_box.pack_start(template_label, False, False, 0)
        
        template_combo = Gtk.ComboBoxText()
        template_combo.append_text("Empty File")
        template_combo.append_text("Basic Examples")
        template_combo.append_text("Generate Basic Rules")
        template_combo.append_text("Generate Advanced Rules")
        template_combo.set_active(1)  # Default to Basic Examples
        template_box.pack_start(template_combo, True, True, 0)
        
        box.pack_start(template_box, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            filename = name_entry.get_text().strip()
            template_option = template_combo.get_active()
            
            # Make sure filename has .rule extension
            if not filename.endswith('.rule'):
                filename += '.rule'
                
            # Create the new rule file
            filepath = os.path.join(self.rules_dir, filename)
            
            try:
                content = ""
                
                if template_option == 0:  # Empty File
                    content = "# ERPCT Rule File\n# Created: " + \
                             time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
                elif template_option == 1:  # Basic Examples
                    content = self.sample_rules
                elif template_option == 2:  # Generate Basic Rules
                    # Create the file directly using the rule generator
                    self.rule_generator.generate_rule_file(
                        filename, 
                        "basic", 
                        50, 
                        "Basic password mutation rules"
                    )
                    self.refresh_rules()
                    
                    # Select the newly created file
                    for i, row in enumerate(self.rules_store):
                        if os.path.basename(row[1]) == filename:
                            self.rules_view.set_cursor(Gtk.TreePath(i), None, False)
                            break
                            
                    dialog.destroy()
                    return
                elif template_option == 3:  # Generate Advanced Rules
                    # Create the file directly using the rule generator
                    self.rule_generator.generate_rule_file(
                        filename, 
                        "advanced", 
                        100, 
                        "Advanced password mutation rules"
                    )
                    self.refresh_rules()
                    
                    # Select the newly created file
                    for i, row in enumerate(self.rules_store):
                        if os.path.basename(row[1]) == filename:
                            self.rules_view.set_cursor(Gtk.TreePath(i), None, False)
                            break
                            
                    dialog.destroy()
                    return
                
                with open(filepath, 'w') as f:
                    f.write(content)
                
                # Load the new file
                self.current_rule_file = filepath
                self.rule_buffer.set_text(content)
                self.modified = False
                self.save_button.set_sensitive(False)
                self.delete_button.set_sensitive(True)
                
                # Refresh the list
                self.refresh_rules()
                
                # Select the newly created file
                for i, row in enumerate(self.rules_store):
                    if row[1] == filepath:
                        self.rules_view.set_cursor(Gtk.TreePath(i), None, False)
                        break
                
            except Exception as e:
                self.logger.error(f"Error creating rule file: {str(e)}")
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Error Creating File"
                )
                error_dialog.format_secondary_text(str(e))
                error_dialog.run()
                error_dialog.destroy()
        
        dialog.destroy()
    
    def _on_generate_clicked(self, button):
        """Handle generate button click.
        
        Args:
            button: Button that was clicked
        """
        # Create dialog for rule generation
        dialog = Gtk.Dialog(
            title="Generate Rules",
            transient_for=self.get_toplevel(),
            flags=0,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK
            )
        )
        dialog.set_default_size(400, 200)
        
        # Setup dialog content
        box = dialog.get_content_area()
        box.set_spacing(6)
        
        # File name entry
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="File Name:")
        name_box.pack_start(name_label, False, False, 0)
        
        name_entry = Gtk.Entry()
        name_entry.set_text("generated.rule")
        name_box.pack_start(name_entry, True, True, 0)
        
        box.pack_start(name_box, False, False, 0)
        
        # Complexity selection
        complexity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        complexity_label = Gtk.Label(label="Complexity:")
        complexity_box.pack_start(complexity_label, False, False, 0)
        
        complexity_combo = Gtk.ComboBoxText()
        complexity_combo.append_text("Basic")
        complexity_combo.append_text("Medium")
        complexity_combo.append_text("Advanced")
        complexity_combo.set_active(1)  # Default to Medium
        complexity_box.pack_start(complexity_combo, True, True, 0)
        
        box.pack_start(complexity_box, False, False, 0)
        
        # Rule count
        count_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        count_label = Gtk.Label(label="Number of Rules:")
        count_box.pack_start(count_label, False, False, 0)
        
        count_adjustment = Gtk.Adjustment(value=100, lower=10, upper=1000, step_increment=10, page_increment=50)
        count_spinner = Gtk.SpinButton()
        count_spinner.set_adjustment(count_adjustment)
        count_box.pack_start(count_spinner, True, True, 0)
        
        box.pack_start(count_box, False, False, 0)
        
        # Description
        desc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        desc_label = Gtk.Label(label="Description:")
        desc_box.pack_start(desc_label, False, False, 0)
        
        desc_entry = Gtk.Entry()
        desc_entry.set_text("Generated password mutation rules")
        desc_box.pack_start(desc_entry, True, True, 0)
        
        box.pack_start(desc_box, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            filename = name_entry.get_text().strip()
            complexity = ["basic", "medium", "advanced"][complexity_combo.get_active()]
            count = count_spinner.get_value_as_int()
            description = desc_entry.get_text().strip()
            
            # Generate the rule file
            success = self.rule_generator.generate_rule_file(
                filename, 
                complexity, 
                count, 
                description
            )
            
            if success:
                self.refresh_rules()
                
                # Select the newly created file
                for i, row in enumerate(self.rules_store):
                    if os.path.basename(row[1]) == filename or os.path.basename(row[1]) == filename + ".rule":
                        self.rules_view.set_cursor(Gtk.TreePath(i), None, False)
                        break
            else:
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Error Generating Rules"
                )
                error_dialog.format_secondary_text("Failed to generate rule file.")
                error_dialog.run()
                error_dialog.destroy()
        
        dialog.destroy()
    
    def _on_save_clicked(self, button):
        """Handle save button click.
        
        Args:
            button: Button that was clicked
        """
        self._save_current_file()
    
    def _on_delete_clicked(self, button):
        """Handle delete button click.
        
        Args:
            button: Button that was clicked
        """
        if not self.current_rule_file:
            return
            
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Delete Rule File"
        )
        dialog.format_secondary_text(
            f"Are you sure you want to delete {os.path.basename(self.current_rule_file)}?"
        )
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            try:
                os.remove(self.current_rule_file)
                
                # Clear the editor
                self.current_rule_file = None
                self.rule_buffer.set_text("")
                self.modified = False
                self.save_button.set_sensitive(False)
                self.delete_button.set_sensitive(False)
                
                # Refresh the list
                self.refresh_rules()
                
            except Exception as e:
                self.logger.error(f"Error deleting rule file: {str(e)}")
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Error Deleting File"
                )
                error_dialog.format_secondary_text(str(e))
                error_dialog.run()
                error_dialog.destroy()
    
    def _on_test_clicked(self, button):
        """Handle test button click.
        
        Args:
            button: Button that was clicked
        """
        test_password = self.test_input.get_text()
        if not test_password:
            return
            
        # Get current rules
        start = self.rule_buffer.get_start_iter()
        end = self.rule_buffer.get_end_iter()
        rules_text = self.rule_buffer.get_text(start, end, False)
        
        # Apply rules to test password
        results = self._apply_rules_to_password(test_password, rules_text)
        
        # Show results
        results_buffer = self.results_view.get_buffer()
        results_buffer.set_text("")
        
        if results:
            for i, result in enumerate(results):
                if i > 0:
                    results_buffer.insert_at_cursor("\n")
                results_buffer.insert_at_cursor(result)
        else:
            results_buffer.set_text("No valid rules found or all rules were commented out.")
    
    def _apply_rules_to_password(self, password, rules_text):
        """Apply rules to a password.
        
        Args:
            password: Password to transform
            rules_text: Rules to apply
            
        Returns:
            List of transformed passwords
        """
        results = []
        
        # Parse rules (ignoring comments and empty lines)
        rules = []
        for line in rules_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                rules.append(line)
        
        # Apply each rule to the password using the transformer module
        for rule in rules:
            try:
                result = apply_rule(password, rule)
                results.append(f"{rule}: {password} → {result}")
            except Exception as e:
                self.logger.warning(f"Error applying rule '{rule}': {str(e)}")
                results.append(f"{rule}: ERROR - {str(e)}")
        
        return results
    
    def _save_current_file(self):
        """Save the current rule file."""
        if not self.current_rule_file:
            return False
            
        try:
            # Get current content
            start = self.rule_buffer.get_start_iter()
            end = self.rule_buffer.get_end_iter()
            content = self.rule_buffer.get_text(start, end, False)
            
            # Save to file
            with open(self.current_rule_file, 'w') as f:
                f.write(content)
            
            self.modified = False
            self.save_button.set_sensitive(False)
            self.logger.debug(f"Saved rule file: {self.current_rule_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving rule file: {str(e)}")
            error_dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Saving File"
            )
            error_dialog.format_secondary_text(str(e))
            error_dialog.run()
            error_dialog.destroy()
            return False
    
    def load_rule_file(self, rule_path):
        """Load a rule file into the editor.
        
        Args:
            rule_path: Path to rule file
        """
        if not os.path.exists(rule_path):
            return
            
        self.current_rule_file = rule_path
        
        try:
            with open(rule_path, 'r') as f:
                content = f.read()
                self.rule_buffer.set_text(content)
                
            self.modified = False
            self.save_button.set_sensitive(False)
            self.delete_button.set_sensitive(True)
            
            # Apply syntax highlighting
            self._apply_syntax_highlighting()
            
        except Exception as e:
            self.logger.error(f"Error loading rule file: {str(e)}")
            error_dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Loading File"
            )
            error_dialog.format_secondary_text(str(e))
            error_dialog.run()
            error_dialog.destroy()
    
    def refresh_rules(self):
        """Refresh the list of rule files."""
        # Clear the store
        self.rules_store.clear()
        
        # Get rule files from parser
        rule_files = self.rule_parser.get_available_rule_files()
        
        # Add to store
        for filename, filepath in rule_files.items():
            self.rules_store.append([filename, filepath])
            
        # Sort by name
        self.rules_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
    
    def get_current_rule_file(self):
        """Get the path of the currently loaded rule file.
        
        Returns:
            Path to current rule file or None if no file is loaded
        """
        return self.current_rule_file
