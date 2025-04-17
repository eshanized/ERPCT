#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Wordlist Manager component.
This module provides the GUI panel for managing password wordlists.
"""

import os
import shutil
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango

from src.utils.logging import get_logger


class WordlistManager(Gtk.Box):
    """Wordlist management panel."""
    
    def __init__(self):
        """Initialize the wordlist manager panel."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Default wordlists directory (in the user's home)
        self.wordlists_dir = os.path.join(os.path.expanduser("~"), ".erpct", "wordlists")
        os.makedirs(self.wordlists_dir, exist_ok=True)
        
        # Create UI components
        self._create_wordlist_browser()
        self._create_action_buttons()
        
        # Refresh the wordlist display
        self.refresh_wordlists()
    
    def _create_wordlist_browser(self):
        """Create wordlist browser section."""
        frame = Gtk.Frame(label="Wordlists")
        self.pack_start(frame, True, True, 0)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        frame.add(box)
        
        # Scrollable wordlist view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(300)
        
        # Wordlist store and view
        self.wordlist_store = Gtk.ListStore(str, str, int, str)  # Name, Path, Size (bytes), Description
        self.wordlist_view = Gtk.TreeView(model=self.wordlist_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=0)
        column.set_resizable(True)
        column.set_min_width(150)
        self.wordlist_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Path", renderer, text=1)
        column.set_resizable(True)
        column.set_min_width(250)
        self.wordlist_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Size", renderer, text=2)
        column.set_resizable(True)
        column.set_min_width(100)
        self.wordlist_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Description", renderer, text=3)
        column.set_resizable(True)
        column.set_min_width(200)
        self.wordlist_view.append_column(column)
        
        scrolled.add(self.wordlist_view)
        box.pack_start(scrolled, True, True, 0)
        
        # Selection handling
        self.selection = self.wordlist_view.get_selection()
        self.selection.connect("changed", self._on_selection_changed)
    
    def _create_action_buttons(self):
        """Create action buttons section."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_start(button_box, False, False, 0)
        
        # Import button
        self.import_button = Gtk.Button.new_with_label("Import Wordlist")
        self.import_button.connect("clicked", self._on_import_clicked)
        button_box.pack_start(self.import_button, True, True, 0)
        
        # Remove button
        self.remove_button = Gtk.Button.new_with_label("Remove Wordlist")
        self.remove_button.connect("clicked", self._on_remove_clicked)
        self.remove_button.set_sensitive(False)
        button_box.pack_start(self.remove_button, True, True, 0)
        
        # View button
        self.view_button = Gtk.Button.new_with_label("View Wordlist")
        self.view_button.connect("clicked", self._on_view_clicked)
        self.view_button.set_sensitive(False)
        button_box.pack_start(self.view_button, True, True, 0)
        
        # Generate button
        self.generate_button = Gtk.Button.new_with_label("Generate Wordlist")
        self.generate_button.connect("clicked", self._on_generate_clicked)
        button_box.pack_start(self.generate_button, True, True, 0)
    
    def _on_selection_changed(self, selection):
        """Handle wordlist selection change.
        
        Args:
            selection: TreeSelection that changed
        """
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            self.remove_button.set_sensitive(True)
            self.view_button.set_sensitive(True)
        else:
            self.remove_button.set_sensitive(False)
            self.view_button.set_sensitive(False)
    
    def _on_import_clicked(self, button):
        """Handle import button click.
        
        Args:
            button: Button that was clicked
        """
        dialog = Gtk.FileChooserDialog(
            title="Import Wordlist",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
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
            source_path = dialog.get_filename()
            
            # Ask for description
            description_dialog = Gtk.Dialog(
                title="Wordlist Description",
                parent=dialog,
                flags=0,
                buttons=(
                    Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OK, Gtk.ResponseType.OK
                )
            )
            
            content_area = description_dialog.get_content_area()
            label = Gtk.Label(label="Enter a description for this wordlist:")
            content_area.add(label)
            
            entry = Gtk.Entry()
            entry.set_text("Imported wordlist")
            content_area.add(entry)
            content_area.show_all()
            
            description_response = description_dialog.run()
            description = entry.get_text()
            description_dialog.destroy()
            
            if description_response == Gtk.ResponseType.OK:
                self._import_wordlist(source_path, description)
        
        dialog.destroy()
    
    def _on_remove_clicked(self, button):
        """Handle remove button click.
        
        Args:
            button: Button that was clicked
        """
        model, treeiter = self.selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][0]
            path = model[treeiter][1]
            
            # Confirm deletion
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Remove Wordlist"
            )
            dialog.format_secondary_text(f"Are you sure you want to remove '{name}'?")
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                try:
                    # Remove the file
                    os.remove(path)
                    self.refresh_wordlists()
                except Exception as e:
                    self.logger.error(f"Error removing wordlist: {str(e)}")
                    
                    # Show error dialog
                    error_dialog = Gtk.MessageDialog(
                        transient_for=self.get_toplevel(),
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Error Removing Wordlist"
                    )
                    error_dialog.format_secondary_text(str(e))
                    error_dialog.run()
                    error_dialog.destroy()
    
    def _on_view_clicked(self, button):
        """Handle view button click.
        
        Args:
            button: Button that was clicked
        """
        model, treeiter = self.selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][0]
            path = model[treeiter][1]
            
            # Create dialog to view wordlist
            dialog = Gtk.Dialog(
                title=f"View Wordlist: {name}",
                parent=self.get_toplevel(),
                flags=0,
                buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
            )
            dialog.set_default_size(600, 400)
            
            # Add content
            content_area = dialog.get_content_area()
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            
            text_view = Gtk.TextView()
            text_view.set_editable(False)
            text_view.set_cursor_visible(False)
            text_view.set_monospace(True)
            
            # Load file content
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    text_view.get_buffer().set_text(content)
            except Exception as e:
                text_view.get_buffer().set_text(f"Error loading file: {str(e)}")
            
            scrolled.add(text_view)
            content_area.pack_start(scrolled, True, True, 0)
            
            # Set min size
            dialog.set_default_size(800, 600)
            
            # Show all content
            content_area.show_all()
            
            # Run dialog
            dialog.run()
            dialog.destroy()
    
    def _on_generate_clicked(self, button):
        """Handle generate button click.
        
        Args:
            button: Button that was clicked
        """
        # TODO: Implement wordlist generation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Generate Wordlist"
        )
        dialog.format_secondary_text("Wordlist generation is not implemented yet.")
        dialog.run()
        dialog.destroy()
    
    def _import_wordlist(self, source_path, description):
        """Import a wordlist file.
        
        Args:
            source_path: Path to the source file
            description: Description for the wordlist
        """
        try:
            # Get filename
            filename = os.path.basename(source_path)
            
            # Create destination path
            dest_path = os.path.join(self.wordlists_dir, filename)
            
            # Copy file
            shutil.copy2(source_path, dest_path)
            
            # Save metadata
            self._save_wordlist_metadata(dest_path, description)
            
            # Refresh display
            self.refresh_wordlists()
            
            # Show success message
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Wordlist Imported"
            )
            dialog.format_secondary_text(f"Successfully imported '{filename}'")
            dialog.run()
            dialog.destroy()
            
        except Exception as e:
            self.logger.error(f"Error importing wordlist: {str(e)}")
            
            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error Importing Wordlist"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def _save_wordlist_metadata(self, wordlist_path, description):
        """Save metadata for a wordlist.
        
        Args:
            wordlist_path: Path to wordlist file
            description: Description for the wordlist
        """
        # Create metadata directory if needed
        metadata_dir = os.path.join(os.path.dirname(self.wordlists_dir), "metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        
        # Create metadata file
        basename = os.path.basename(wordlist_path)
        metadata_path = os.path.join(metadata_dir, basename + ".meta")
        
        with open(metadata_path, 'w') as f:
            f.write(description)
    
    def _get_wordlist_metadata(self, wordlist_path):
        """Get metadata for a wordlist.
        
        Args:
            wordlist_path: Path to wordlist file
            
        Returns:
            Description string or default text
        """
        basename = os.path.basename(wordlist_path)
        metadata_path = os.path.join(
            os.path.dirname(self.wordlists_dir), 
            "metadata", 
            basename + ".meta"
        )
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    return f.read().strip()
            except:
                pass
        
        return "No description"
    
    def refresh_wordlists(self):
        """Refresh the wordlist display."""
        # Clear the store
        self.wordlist_store.clear()
        
        # Add default wordlists directory
        if os.path.exists(self.wordlists_dir):
            for filename in os.listdir(self.wordlists_dir):
                filepath = os.path.join(self.wordlists_dir, filename)
                if os.path.isfile(filepath):
                    try:
                        size = os.path.getsize(filepath)
                        description = self._get_wordlist_metadata(filepath)
                        self.wordlist_store.append([filename, filepath, size, description])
                    except:
                        pass
        
        # Sort by name
        self.wordlist_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
