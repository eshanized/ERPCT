#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Rule Editor component.
This module provides the GUI panel for editing password mutation rules.
"""

import os
import re
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango, Gdk

from src.utils.logging import get_logger


class RuleEditor(Gtk.Box):
    """Rule editor panel for editing password mutation rules."""
    
    def __init__(self):
        """Initialize the rule editor panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Default rules directory
        self.rules_dir = os.path.join(os.path.expanduser("~"), ".erpct", "rules")
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

# Append digits
$1
$2
$123

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
        scrolled.set_min_content_height(100)
        scrolled.add(self.results_view)
        
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
        
        # Add spacer
        button_box.pack_start(Gtk.Label(), True, True, 0)
        
        # Save button
        self.save_button = Gtk.Button.new_with_label("Save")
        self.save_button.connect("clicked", self._on_save_clicked)
        self.save_button.set_sensitive(False)
        button_box.pack_start(self.save_button, False, False, 0)
        
        # Delete button
        self.delete_button = Gtk.Button.new_with_label("Delete")
        self.delete_button.connect("clicked", self._on_delete_clicked)
        self.delete_button.set_sensitive(False)
        button_box.pack_start(self.delete_button, False, False, 0)
    
    def _setup_syntax_highlighting(self):
        """Set up syntax highlighting for rule editor."""
        # Create tags for syntax highlighting
        self.rule_buffer.create_tag("comment", foreground="#009900")  # Green for comments
        self.rule_buffer.create_tag("command", foreground="#0000FF")  # Blue for commands
        self.rule_buffer.create_tag("parameter", foreground="#FF00FF")  # Purple for parameters
    
    def _apply_syntax_highlighting(self):
        """Apply syntax highlighting to the rule buffer."""
        if not self.rule_buffer:
            return
            
        # Get all text
        start = self.rule_buffer.get_start_iter()
        end = self.rule_buffer.get_end_iter()
        text = self.rule_buffer.get_text(start, end, False)
        
        # Remove all tags
        self.rule_buffer.remove_all_tags(start, end)
        
        # Apply syntax highlighting
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_start = self.rule_buffer.get_iter_at_line(i)
            
            # Comment line
            if line.strip().startswith('#'):
                line_end = self.rule_buffer.get_iter_at_line_offset(i, len(line))
                self.rule_buffer.apply_tag_by_name("comment", line_start, line_end)
                continue
            
            # Empty line
            if not line.strip():
                continue
            
            # Commands and parameters
            j = 0
            while j < len(line):
                char = line[j]
                
                # Skip whitespace
                if char.isspace():
                    j += 1
                    continue
                
                # Command characters
                if char in ":lucrtdsz@^$<>(){}[]'":
                    command_start = self.rule_buffer.get_iter_at_line_offset(i, j)
                    command_end = self.rule_buffer.get_iter_at_line_offset(i, j + 1)
                    self.rule_buffer.apply_tag_by_name("command", command_start, command_end)
                    
                    # Check for parameters
                    if char in "s@^$<>()[]'" and j + 1 < len(line):
                        param_start = self.rule_buffer.get_iter_at_line_offset(i, j + 1)
                        
                        # Find parameter end
                        k = j + 1
                        while k < len(line) and not line[k].isspace() and line[k] not in ":lucrtdsz@^$<>(){}[]'":
                            k += 1
                        
                        if k > j + 1:
                            param_end = self.rule_buffer.get_iter_at_line_offset(i, k)
                            self.rule_buffer.apply_tag_by_name("parameter", param_start, param_end)
                            j = k
                            continue
                
                j += 1
    
    def _on_selection_changed(self, selection):
        """Handle rule file selection change.
        
        Args:
            selection: TreeSelection that changed
        """
        # Check if there are unsaved changes
        if self.modified:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Unsaved Changes"
            )
            dialog.format_secondary_text(
                "You have unsaved changes. Do you want to save them before loading another file?"
            )
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                self._save_current_file()
        
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            rule_path = model[treeiter][1]
            self.load_rule_file(rule_path)
            self.delete_button.set_sensitive(True)
        else:
            self.delete_button.set_sensitive(False)
    
    def _on_rule_buffer_changed(self, buffer):
        """Handle rule buffer content change.
        
        Args:
            buffer: TextBuffer that changed
        """
        self.modified = True
        self.save_button.set_sensitive(True)
        
        # Apply syntax highlighting
        self._apply_syntax_highlighting()
    
    def _on_rule_editor_key_press(self, widget, event):
        """Handle key press in rule editor.
        
        Args:
            widget: Widget that received the event
            event: Key event
        """
        # Tab key adds 4 spaces instead of changing focus
        if event.keyval == Gdk.KEY_Tab:
            self.rule_buffer.insert_at_cursor("    ")
            return True
        
        return False
    
    def _on_new_clicked(self, button):
        """Handle new button click.
        
        Args:
            button: Button that was clicked
        """
        # Check if there are unsaved changes
        if self.modified:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.WARNING,
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
        
        # Create dialog for new file name
        dialog = Gtk.Dialog(
            title="New Rule File",
            parent=self.get_toplevel(),
            flags=0,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        
        box = dialog.get_content_area()
        box.set_border_width(10)
        
        label = Gtk.Label(label="Enter name for new rule file:")
        box.pack_start(label, False, False, 0)
        
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        box.pack_start(entry, False, False, 0)
        
        box.show_all()
        
        response = dialog.run()
        file_name = entry.get_text()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and file_name:
            # Ensure file name has .rule extension
            if not file_name.endswith('.rule'):
                file_name += '.rule'
            
            # Create new file
            file_path = os.path.join(self.rules_dir, file_name)
            
            # Check if file already exists
            if os.path.exists(file_path):
                error_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="File Already Exists"
                )
                error_dialog.format_secondary_text(f"A rule file named '{file_name}' already exists.")
                error_dialog.run()
                error_dialog.destroy()
                return
            
            # Create new file with sample content
            try:
                with open(file_path, 'w') as f:
                    f.write(self.sample_rules)
                
                # Refresh rules list
                self.refresh_rules()
                
                # Select and load the new file
                for i, row in enumerate(self.rules_store):
                    if row[1] == file_path:
                        self.rules_view.set_cursor(Gtk.TreePath(i), None, False)
                        break
                
            except Exception as e:
                self.logger.error(f"Error creating new rule file: {str(e)}")
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
    
    def _on_save_clicked(self, button):
        """Handle save button click.
        
        Args:
            button: Button that was clicked
        """
        if self.current_rule_file:
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
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Delete Rule File"
        )
        dialog.format_secondary_text(f"Are you sure you want to delete the rule file '{os.path.basename(self.current_rule_file)}'?")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            try:
                os.remove(self.current_rule_file)
                
                # Clear current file
                self.current_rule_file = None
                self.rule_buffer.set_text("")
                self.modified = False
                self.save_button.set_sensitive(False)
                self.delete_button.set_sensitive(False)
                
                # Refresh rules list
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
        
        # Apply each rule to the password
        for rule in rules:
            result = self._apply_rule(password, rule)
            results.append(f"{rule}: {password} → {result}")
        
        return results
    
    def _apply_rule(self, password, rule):
        """Apply a single rule to a password.
        
        Args:
            password: Password to transform
            rule: Rule to apply
            
        Returns:
            Transformed password
        """
        result = password
        
        # Simple rule processing for testing
        i = 0
        while i < len(rule):
            char = rule[i]
            
            # Process based on rule character
            if char == ':':
                # Do nothing
                pass
            elif char == 'l':
                # Lowercase
                result = result.lower()
            elif char == 'u':
                # Uppercase
                result = result.upper()
            elif char == 'c':
                # Capitalize
                if result:
                    result = result[0].upper() + result[1:]
            elif char == 'r':
                # Reverse
                result = result[::-1]
            elif char == 'd':
                # Duplicate
                result = result + result
            elif char == 's' and i + 2 < len(rule):
                # Substitute
                a = rule[i+1]
                b = rule[i+2]
                result = result.replace(a, b)
                i += 2
            elif char == '@' and i + 1 < len(rule):
                # Purge character
                a = rule[i+1]
                result = result.replace(a, '')
                i += 1
            elif char == '^' and i + 1 < len(rule):
                # Prepend
                a = rule[i+1]
                result = a + result
                i += 1
            elif char == '$' and i + 1 < len(rule):
                # Append
                a = rule[i+1]
                result = result + a
                i += 1
            elif char == '<' and i + 1 < len(rule) and rule[i+1].isdigit():
                # Truncate
                n = int(rule[i+1])
                result = result[:n]
                i += 1
            elif char == '>' and i + 1 < len(rule) and rule[i+1].isdigit():
                # Skip first N
                n = int(rule[i+1])
                result = result[n:]
                i += 1
            
            i += 1
        
        return result
    
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
        
        # Add rule files from directory
        if os.path.exists(self.rules_dir):
            for filename in os.listdir(self.rules_dir):
                filepath = os.path.join(self.rules_dir, filename)
                if os.path.isfile(filepath) and filename.endswith(".rule"):
                    self.rules_store.append([filename, filepath])
        
        # Sort by name
        self.rules_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
    
    def get_current_rule_file(self):
        """Get the path of the currently loaded rule file.
        
        Returns:
            Path to current rule file or None if no file is loaded
        """
        return self.current_rule_file
