#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Log Viewer component.
This module provides the GUI panel for viewing application logs.
"""

import os
import re
import time
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango, Gdk

from src.utils.logging import get_logger, DEFAULT_LOG_DIR


class LogViewer(Gtk.Box):
    """Log viewer panel."""
    
    def __init__(self):
        """Initialize the log viewer panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Default logs directory
        self.logs_dir = DEFAULT_LOG_DIR
        
        # Currently displayed log file
        self.current_log_file = None
        self.update_timer_id = None
        
        # Create UI components
        self._create_log_selector()
        self._create_log_viewer()
        self._create_control_buttons()
        
        # Refresh log list
        self.refresh_logs()
    
    def _create_log_selector(self):
        """Create log selector section."""
        frame = Gtk.Frame(label="Log Files")
        frame.set_size_request(-1, 100)
        self.pack_start(frame, False, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Scrollable log file list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Log files store and view
        self.logs_store = Gtk.ListStore(str, str, str)  # Name, Date, Path
        self.logs_view = Gtk.TreeView(model=self.logs_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Log File", renderer, text=0)
        column.set_resizable(True)
        column.set_min_width(250)
        self.logs_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Date", renderer, text=1)
        column.set_resizable(True)
        column.set_min_width(150)
        self.logs_view.append_column(column)
        
        scrolled.add(self.logs_view)
        box.pack_start(scrolled, True, True, 0)
        
        # Selection handling
        self.selection = self.logs_view.get_selection()
        self.selection.connect("changed", self._on_selection_changed)
    
    def _create_log_viewer(self):
        """Create log viewer section."""
        frame = Gtk.Frame(label="Log Content")
        self.pack_start(frame, True, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Filter options
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(filter_box, False, False, 0)
        
        # Level filter
        level_label = Gtk.Label(label="Level:")
        filter_box.pack_start(level_label, False, False, 0)
        
        self.level_combo = Gtk.ComboBoxText()
        self.level_combo.append_text("All")
        self.level_combo.append_text("DEBUG")
        self.level_combo.append_text("INFO")
        self.level_combo.append_text("WARNING")
        self.level_combo.append_text("ERROR")
        self.level_combo.append_text("CRITICAL")
        self.level_combo.set_active(0)
        self.level_combo.connect("changed", self._on_filter_changed)
        filter_box.pack_start(self.level_combo, False, False, 0)
        
        # Search filter
        search_label = Gtk.Label(label="Search:")
        filter_box.pack_start(search_label, False, False, 0)
        
        self.search_entry = Gtk.Entry()
        self.search_entry.connect("changed", self._on_filter_changed)
        filter_box.pack_start(self.search_entry, True, True, 0)
        
        # Scrollable log content view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Text view for log content
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        
        # Set up text buffer with mark for auto-scrolling
        self.log_buffer = self.log_view.get_buffer()
        self.log_buffer.create_mark("end", self.log_buffer.get_end_iter(), False)
        
        # Create text tags for colors
        self.log_buffer.create_tag("debug", foreground="#808080")  # Gray
        self.log_buffer.create_tag("info", foreground="#000000")   # Black
        self.log_buffer.create_tag("warning", foreground="#FF8800")  # Orange
        self.log_buffer.create_tag("error", foreground="#FF0000")  # Red
        self.log_buffer.create_tag("critical", background="#FF0000", foreground="#FFFFFF")  # White on Red
        self.log_buffer.create_tag("highlight", background="#FFFF00")  # Yellow highlight
        
        scrolled.add(self.log_view)
        box.pack_start(scrolled, True, True, 0)
    
    def _create_control_buttons(self):
        """Create control buttons section."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_start(button_box, False, False, 0)
        
        # Auto-scroll switch
        auto_scroll_label = Gtk.Label(label="Auto-scroll:")
        button_box.pack_start(auto_scroll_label, False, False, 0)
        
        self.auto_scroll_switch = Gtk.Switch()
        self.auto_scroll_switch.set_active(True)
        button_box.pack_start(self.auto_scroll_switch, False, False, 0)
        
        # Live update switch
        live_update_label = Gtk.Label(label="Live update:")
        button_box.pack_start(live_update_label, False, False, 0)
        
        self.live_update_switch = Gtk.Switch()
        self.live_update_switch.set_active(True)
        self.live_update_switch.connect("notify::active", self._on_live_update_toggled)
        button_box.pack_start(self.live_update_switch, False, False, 0)
        
        # Add spacer
        button_box.pack_start(Gtk.Label(), True, True, 0)
        
        # Refresh button
        self.refresh_button = Gtk.Button.new_with_label("Refresh")
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        button_box.pack_start(self.refresh_button, False, False, 0)
        
        # Clear button
        self.clear_button = Gtk.Button.new_with_label("Clear View")
        self.clear_button.connect("clicked", self._on_clear_clicked)
        button_box.pack_start(self.clear_button, False, False, 0)
        
        # Clear Log File button
        self.clear_file_button = Gtk.Button.new_with_label("Clear Log File")
        self.clear_file_button.connect("clicked", self._on_clear_file_clicked)
        button_box.pack_start(self.clear_file_button, False, False, 0)
    
    def _on_selection_changed(self, selection):
        """Handle log file selection change.
        
        Args:
            selection: TreeSelection that changed
        """
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            log_path = model[treeiter][2]
            self.load_log_file(log_path)
    
    def _on_filter_changed(self, widget):
        """Handle filter change.
        
        Args:
            widget: Widget that triggered the event
        """
        # Re-apply filters to current log file
        if self.current_log_file:
            self.load_log_file(self.current_log_file, refresh=True)
    
    def _on_live_update_toggled(self, switch, gparam):
        """Handle live update toggle.
        
        Args:
            switch: Switch widget
            gparam: GObject parameter
        """
        if switch.get_active():
            # Start timer if not already running
            if self.update_timer_id is None and self.current_log_file:
                self.update_timer_id = GLib.timeout_add(1000, self._update_log_content)
        else:
            # Stop timer if running
            if self.update_timer_id is not None:
                GLib.source_remove(self.update_timer_id)
                self.update_timer_id = None
    
    def _on_refresh_clicked(self, button):
        """Handle refresh button click.
        
        Args:
            button: Button that was clicked
        """
        self.refresh_logs()
        
        # Reload current log file
        if self.current_log_file:
            self.load_log_file(self.current_log_file, refresh=True)
    
    def _on_clear_clicked(self, button):
        """Handle clear button click.
        
        Args:
            button: Button that was clicked
        """
        self.log_buffer.set_text("")
    
    def _on_clear_file_clicked(self, button):
        """Handle clear log file button click.
        
        Args:
            button: Button that was clicked
        """
        if self.current_log_file:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Clear Log File"
            )
            dialog.format_secondary_text(
                f"Are you sure you want to clear the log file?\n{os.path.basename(self.current_log_file)}"
            )
            response = dialog.run()
            
            if response == Gtk.ResponseType.YES:
                try:
                    # Clear the file
                    with open(self.current_log_file, 'w') as f:
                        f.write("")
                    
                    # Clear the buffer
                    self.log_buffer.set_text("")
                    
                    self.logger.info(f"Log file cleared: {self.current_log_file}")
                except Exception as e:
                    self.logger.error(f"Error clearing log file: {str(e)}")
                    
                    error_dialog = Gtk.MessageDialog(
                        transient_for=self.get_toplevel(),
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Error"
                    )
                    error_dialog.format_secondary_text(f"Could not clear log file: {str(e)}")
                    error_dialog.run()
                    error_dialog.destroy()
            
            dialog.destroy()
    
    def load_log_file(self, log_path, refresh=False):
        """Load a log file into the viewer.
        
        Args:
            log_path: Path to log file
            refresh: Whether to force refresh even if same file
        """
        if not refresh and log_path == self.current_log_file:
            return
            
        self.current_log_file = log_path
        
        # Clear the buffer if not refreshing
        if not refresh:
            self.log_buffer.set_text("")
        
        # Get current filter settings
        level_filter = self.level_combo.get_active_text()
        search_filter = self.search_entry.get_text()
        
        try:
            with open(log_path, 'r') as f:
                log_lines = f.readlines()
                
                # Apply filters and add to buffer
                self._process_log_lines(log_lines, level_filter, search_filter)
                
            # Scroll to end if auto-scroll is enabled
            if self.auto_scroll_switch.get_active():
                self._scroll_to_end()
                
            # Start live update if enabled
            if self.live_update_switch.get_active() and self.update_timer_id is None:
                self.update_timer_id = GLib.timeout_add(1000, self._update_log_content)
                
        except Exception as e:
            self.logger.error(f"Error loading log file: {str(e)}")
            self.log_buffer.set_text(f"Error loading log file: {str(e)}")
    
    def _process_log_lines(self, log_lines, level_filter, search_filter):
        """Process log lines and add to buffer with appropriate formatting.
        
        Args:
            log_lines: List of log lines
            level_filter: Level filter string
            search_filter: Search filter string
        """
        # Regular expression to parse log lines
        # Example log line: 2023-05-10 12:34:56 [INFO] module.name: Message text
        log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([A-Z]+)\] ([^:]+): (.+)'
        
        # Start batch update
        self.log_buffer.begin_user_action()
        
        for line in log_lines:
            line = line.strip()
            if not line:
                continue
                
            match = re.match(log_pattern, line)
            if match:
                timestamp, level, module, message = match.groups()
                
                # Apply level filter
                if level_filter != "All" and level != level_filter:
                    continue
                
                # Apply search filter
                if search_filter and search_filter.lower() not in line.lower():
                    continue
                
                # Determine tag for level
                tag = level.lower()
                if tag not in ["debug", "info", "warning", "error", "critical"]:
                    tag = "info"  # Default to info for unknown levels
                
                # Add the line with appropriate tag
                end_iter = self.log_buffer.get_end_iter()
                
                # Add timestamp and level
                self.log_buffer.insert(end_iter, f"{timestamp} [{level}] {module}: ")
                
                # Add message with appropriate tag
                message_start = self.log_buffer.get_end_iter()
                self.log_buffer.insert(end_iter, f"{message}\n")
                message_end = self.log_buffer.get_end_iter()
                
                # Apply tag to the whole line
                start_iter = self.log_buffer.get_iter_at_line(message_start.get_line())
                self.log_buffer.apply_tag_by_name(tag, start_iter, message_end)
                
                # Apply highlight to search matches if specified
                if search_filter:
                    # Find all occurrences of search_filter in the line
                    line_start = self.log_buffer.get_iter_at_line(message_start.get_line())
                    line_text = self.log_buffer.get_text(line_start, message_end, False)
                    
                    search_lower = search_filter.lower()
                    text_lower = line_text.lower()
                    
                    offset = 0
                    while True:
                        match_pos = text_lower.find(search_lower, offset)
                        if match_pos == -1:
                            break
                            
                        highlight_start = line_start.copy()
                        highlight_start.forward_chars(match_pos)
                        
                        highlight_end = highlight_start.copy()
                        highlight_end.forward_chars(len(search_filter))
                        
                        self.log_buffer.apply_tag_by_name("highlight", highlight_start, highlight_end)
                        
                        offset = match_pos + len(search_filter)
            else:
                # If line doesn't match pattern, add it as plain text
                # Apply filters
                if level_filter != "All" or (search_filter and search_filter.lower() not in line.lower()):
                    continue
                    
                end_iter = self.log_buffer.get_end_iter()
                self.log_buffer.insert(end_iter, f"{line}\n")
        
        # End batch update
        self.log_buffer.end_user_action()
    
    def _update_log_content(self):
        """Update log content from file for live updates.
        
        Returns:
            True to continue timer, False to stop
        """
        if not self.current_log_file or not self.live_update_switch.get_active():
            self.update_timer_id = None
            return False
        
        try:
            # Get current content length
            with open(self.current_log_file, 'r') as f:
                log_lines = f.readlines()
            
            # Get current buffer content
            start_iter = self.log_buffer.get_start_iter()
            end_iter = self.log_buffer.get_end_iter()
            current_text = self.log_buffer.get_text(start_iter, end_iter, False)
            
            # Count lines in current buffer
            current_lines = current_text.count('\n')
            
            # If there are new lines, add them
            if len(log_lines) > current_lines:
                new_lines = log_lines[current_lines:]
                
                # Get current filter settings
                level_filter = self.level_combo.get_active_text()
                search_filter = self.search_entry.get_text()
                
                # Process new lines
                self._process_log_lines(new_lines, level_filter, search_filter)
                
                # Scroll to end if auto-scroll is enabled
                if self.auto_scroll_switch.get_active():
                    self._scroll_to_end()
        
        except Exception as e:
            self.logger.error(f"Error updating log content: {str(e)}")
        
        # Continue timer
        return True
    
    def _scroll_to_end(self):
        """Scroll the log view to the end."""
        end_mark = self.log_buffer.get_mark("end")
        self.log_view.scroll_to_mark(end_mark, 0.0, True, 0.0, 1.0)
    
    def refresh_logs(self):
        """Refresh the list of log files."""
        # Clear the store
        self.logs_store.clear()
        
        # Add logs from directory
        if os.path.exists(self.logs_dir):
            for filename in os.listdir(self.logs_dir):
                filepath = os.path.join(self.logs_dir, filename)
                if os.path.isfile(filepath) and filename.endswith(".log"):
                    try:
                        mtime = os.path.getmtime(filepath)
                        date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                        
                        self.logs_store.append([
                            filename,
                            date_str,
                            filepath
                        ])
                    except:
                        pass
        
        # Sort by modification date (newest first)
        self.logs_store.set_sort_column_id(1, Gtk.SortType.DESCENDING)
    
    def get_current_log_file(self):
        """Get the current log file path.
        
        Returns:
            str: Path to current log file, or None
        """
        return self.current_log_file
        
    def clear_current_log(self):
        """Clear the contents of the current log file."""
        if self.current_log_file and os.path.exists(self.current_log_file):
            try:
                # Write empty content to the file
                with open(self.current_log_file, 'w') as f:
                    f.write("")
                
                # Reload the file
                self.load_log_file(self.current_log_file, refresh=True)
                
                self.logger.info(f"Cleared log file: {self.current_log_file}")
                return True
            except Exception as e:
                self.logger.error(f"Error clearing log file: {str(e)}")
                return False
        return False
        
    def start_log_monitoring(self):
        """Start monitoring logs for updates."""
        # If there is already an active log file, start live updating it
        if self.current_log_file and os.path.exists(self.current_log_file):
            self.live_update_switch.set_active(True)
            self._on_live_update_toggled(self.live_update_switch, None)
            self.logger.debug("Started log monitoring for current log file")
        else:
            # Try to select the first log file in the list
            if len(self.logs_store) > 0:
                first_iter = self.logs_store.get_iter_first()
                if first_iter:
                    self.selection.select_iter(first_iter)
                    self.logger.debug("Selected first log file for monitoring")
        
        return True
