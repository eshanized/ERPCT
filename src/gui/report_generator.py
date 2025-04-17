#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Report Generator.
This module provides a GUI for generating and viewing attack reports.
"""

import os
import gi
import json
import time
from datetime import datetime

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango

from src.utils.logging import get_logger


class ReportGenerator(Gtk.Box):
    """Report generation and viewer widget."""
    
    def __init__(self):
        """Initialize the report generator widget."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        self.results_source = None
        
        # Available reports
        report_frame = Gtk.Frame(label="Available Reports")
        self.pack_start(report_frame, True, True, 0)
        
        report_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        report_box.set_border_width(10)
        report_frame.add(report_box)
        
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        report_box.pack_start(toolbar, False, False, 0)
        
        # Refresh button
        refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_button.set_tooltip_text("Refresh Reports")
        refresh_button.connect("clicked", self._on_refresh_reports)
        toolbar.pack_start(refresh_button, False, False, 0)
        
        # Delete report button
        delete_button = Gtk.Button.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON)
        delete_button.set_tooltip_text("Delete Report")
        delete_button.connect("clicked", self._on_delete_report)
        toolbar.pack_start(delete_button, False, False, 0)
        
        # Export button
        export_button = Gtk.Button.new_from_icon_name("document-save-symbolic", Gtk.IconSize.BUTTON)
        export_button.set_tooltip_text("Export Report")
        export_button.connect("clicked", self._on_export_report)
        toolbar.pack_start(export_button, False, False, 0)
        
        # Search
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search reports...")
        search_entry.connect("search-changed", self._on_search_changed)
        toolbar.pack_end(search_entry, False, False, 0)
        self.search_entry = search_entry
        
        # Report list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        report_box.pack_start(scrolled, True, True, 0)
        
        # List store columns
        # ID, Name, Date, Type, Target, Success Rate, Credentials Found
        self.report_store = Gtk.ListStore(str, str, str, str, str, float, int)
        
        # Create filter
        self.report_filter = self.report_store.filter_new()
        self.report_filter.set_visible_func(self._filter_reports)
        
        # Tree view
        self.report_view = Gtk.TreeView(model=self.report_filter)
        self.report_view.set_headers_visible(True)
        self.report_view.connect("row-activated", self._on_report_activated)
        scrolled.add(self.report_view)
        
        # Columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        self.report_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Date", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        self.report_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Type", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        self.report_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Target", renderer, text=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        self.report_view.append_column(column)
        
        renderer = Gtk.CellRendererProgress()
        column = Gtk.TreeViewColumn("Success Rate", renderer, value=5)
        column.set_sort_column_id(5)
        column.set_resizable(True)
        self.report_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Credentials", renderer, text=6)
        column.set_sort_column_id(6)
        column.set_resizable(True)
        self.report_view.append_column(column)
        
        # Report generation form
        form_frame = Gtk.Frame(label="Generate New Report")
        self.pack_start(form_frame, False, False, 0)
        
        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        form_box.set_border_width(10)
        form_frame.add(form_box)
        
        # Report type
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        type_label = Gtk.Label(label="Report Type:", xalign=0)
        type_label.set_width_chars(12)
        type_box.pack_start(type_label, False, False, 0)
        
        self.type_combo = Gtk.ComboBoxText()
        self.type_combo.append_text("Attack Summary")
        self.type_combo.append_text("Success Analysis")
        self.type_combo.append_text("Password Statistics")
        self.type_combo.append_text("Target Vulnerability")
        self.type_combo.append_text("Comprehensive Report")
        self.type_combo.set_active(0)
        type_box.pack_start(self.type_combo, True, True, 0)
        
        form_box.pack_start(type_box, False, False, 0)
        
        # Report name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Report Name:", xalign=0)
        name_label.set_width_chars(12)
        name_box.pack_start(name_label, False, False, 0)
        
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Enter report name")
        name_box.pack_start(self.name_entry, True, True, 0)
        
        form_box.pack_start(name_box, False, False, 0)
        
        # Attack results to include
        include_frame = Gtk.Frame(label="Include Attack Results")
        form_box.pack_start(include_frame, False, False, 0)
        
        include_scrolled = Gtk.ScrolledWindow()
        include_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        include_scrolled.set_shadow_type(Gtk.ShadowType.NONE)
        include_scrolled.set_size_request(-1, 100)
        include_frame.add(include_scrolled)
        
        # Attack results store and list
        # Selected, ID, Name, Date, Protocol, Target
        self.attack_store = Gtk.ListStore(bool, str, str, str, str, str)
        
        attack_view = Gtk.TreeView(model=self.attack_store)
        attack_view.set_headers_visible(True)
        include_scrolled.add(attack_view)
        
        # Columns for attack selection
        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.connect("toggled", self._on_attack_toggled)
        column = Gtk.TreeViewColumn("", toggle_renderer, active=0)
        attack_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Date", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Protocol", renderer, text=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Target", renderer, text=5)
        column.set_sort_column_id(5)
        column.set_resizable(True)
        attack_view.append_column(column)
        
        # Generate button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        form_box.pack_start(button_box, False, False, 10)
        
        self.generate_button = Gtk.Button(label="Generate Report")
        self.generate_button.connect("clicked", self._on_generate_report)
        button_box.pack_end(self.generate_button, False, False, 0)
        
        # Report viewer
        viewer_frame = Gtk.Frame(label="Report Viewer")
        self.pack_start(viewer_frame, True, True, 0)
        
        viewer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        viewer_box.set_border_width(10)
        viewer_frame.add(viewer_box)
        
        # Report content text view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        viewer_box.pack_start(scrolled, True, True, 0)
        
        self.report_text = Gtk.TextView()
        self.report_text.set_editable(False)
        self.report_text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.report_text.get_buffer().set_text("Select a report to view its content.")
        self.report_text.override_font(Pango.FontDescription("Monospace 10"))
        scrolled.add(self.report_text)
        
        # Add some sample data
        self._add_sample_data()
        
    def _add_sample_data(self):
        """Add sample data for demonstration purposes."""
        # Sample reports
        self.report_store.append([
            "report1", 
            "SSH Brute Force Analysis", 
            "2023-03-15 14:22", 
            "Attack Summary", 
            "192.168.1.10", 
            25.5, 
            3
        ])
        
        self.report_store.append([
            "report2", 
            "Web Services Vulnerability Scan", 
            "2023-03-17 09:35", 
            "Comprehensive Report", 
            "example.com", 
            42.1, 
            7
        ])
        
        self.report_store.append([
            "report3", 
            "FTP Password Analysis", 
            "2023-03-20 11:08", 
            "Password Statistics", 
            "ftp.example.org", 
            68.5, 
            12
        ])
        
        # Sample attack results
        self.attack_store.append([
            False, 
            "attack1", 
            "SSH Scan - Server1", 
            "2023-03-15 13:45", 
            "SSH", 
            "192.168.1.10"
        ])
        
        self.attack_store.append([
            False, 
            "attack2", 
            "Web Login - example.com", 
            "2023-03-17 08:20", 
            "HTTP", 
            "example.com"
        ])
        
        self.attack_store.append([
            False, 
            "attack3", 
            "FTP Test - Storage Server", 
            "2023-03-20 10:30", 
            "FTP", 
            "ftp.example.org"
        ])
        
    def _on_refresh_reports(self, button):
        """Handle refresh reports button click."""
        # In a real implementation, this would update the report list from storage
        self.logger.info("Refreshing report list")
        
        # Sample implementation just adds a new sample report
        import random
        protocols = ["SSH", "HTTP", "FTP", "SMTP", "MySQL", "PostgreSQL"]
        targets = ["10.0.0.1", "10.0.0.5", "192.168.1.10", "example.com", "test.local"]
        
        protocol = random.choice(protocols)
        target = random.choice(targets)
        success_rate = random.uniform(10.0, 90.0)
        creds_found = random.randint(0, 15)
        
        report_id = f"report{len(self.report_store) + 1}"
        report_name = f"{protocol} Attack on {target}"
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        report_type = random.choice(["Attack Summary", "Success Analysis", "Password Statistics"])
        
        self.report_store.append([
            report_id, 
            report_name, 
            report_date, 
            report_type,
            target, 
            success_rate, 
            creds_found
        ])
        
    def _on_delete_report(self, button):
        """Handle delete report button click."""
        selection = self.report_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            report_id = model.get_value(iter, 0)
            report_name = model.get_value(iter, 1)
            
            # Confirm deletion
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Delete Report: {report_name}?"
            )
            dialog.format_secondary_text("This action cannot be undone.")
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                # Get the real iterator from the filter model
                filter_path = model.get_path(iter)
                filter_iter = model.get_iter(filter_path)
                child_path = model.convert_iter_to_child_path(filter_iter)
                
                # Remove from the source model
                child_iter = self.report_store.get_iter(child_path)
                self.report_store.remove(child_iter)
                
                # Clear report view if it was displaying the deleted report
                self.report_text.get_buffer().set_text("Select a report to view its content.")
                self.logger.info(f"Deleted report: {report_name} (ID: {report_id})")
        
    def _on_export_report(self, button):
        """Handle export report button click."""
        selection = self.report_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            report_id = model.get_value(iter, 0)
            report_name = model.get_value(iter, 1)
            
            # Create file chooser dialog
            dialog = Gtk.FileChooserDialog(
                title="Export Report",
                parent=self.get_toplevel(),
                action=Gtk.FileChooserAction.SAVE
            )
            dialog.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK
            )
            
            # File filters
            pdf_filter = Gtk.FileFilter()
            pdf_filter.set_name("PDF files")
            pdf_filter.add_mime_type("application/pdf")
            pdf_filter.add_pattern("*.pdf")
            dialog.add_filter(pdf_filter)
            
            html_filter = Gtk.FileFilter()
            html_filter.set_name("HTML files")
            html_filter.add_mime_type("text/html")
            html_filter.add_pattern("*.html")
            dialog.add_filter(html_filter)
            
            text_filter = Gtk.FileFilter()
            text_filter.set_name("Text files")
            text_filter.add_mime_type("text/plain")
            text_filter.add_pattern("*.txt")
            dialog.add_filter(text_filter)
            
            # Set default filename
            safe_name = report_name.replace(" ", "_").replace(":", "-")
            dialog.set_current_name(f"{safe_name}.pdf")
            
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename()
                
                # Check file extension
                if not filename.endswith((".pdf", ".html", ".txt")):
                    current_filter = dialog.get_filter()
                    if current_filter == pdf_filter:
                        filename += ".pdf"
                    elif current_filter == html_filter:
                        filename += ".html"
                    else:
                        filename += ".txt"
                
                # In a real implementation, this would export the report
                self.logger.info(f"Exporting report '{report_name}' to {filename}")
                
                # Show a success message
                msg_dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Report Exported"
                )
                msg_dialog.format_secondary_text(f"Report has been exported to:\n{filename}")
                msg_dialog.run()
                msg_dialog.destroy()
                
            dialog.destroy()
            
    def _filter_reports(self, model, iter, data):
        """Filter function for reports."""
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True
            
        name = model.get_value(iter, 1).lower()
        report_type = model.get_value(iter, 3).lower()
        target = model.get_value(iter, 4).lower()
        
        return (search_text in name or search_text in report_type or search_text in target)
            
    def _on_search_changed(self, entry):
        """Handle search entry changes."""
        self.report_filter.refilter()
        
    def _on_attack_toggled(self, renderer, path):
        """Handle attack selection toggle."""
        iter = self.attack_store.get_iter(path)
        current_value = self.attack_store.get_value(iter, 0)
        self.attack_store.set_value(iter, 0, not current_value)
    
    def _on_report_activated(self, treeview, path, column):
        """Handle report row activation (double-click or Enter)."""
        model = treeview.get_model()
        iter = model.get_iter(path)
        report_id = model.get_value(iter, 0)
        report_name = model.get_value(iter, 1)
        
        # Get the report content (in a real implementation, this would load from storage)
        self._display_report_content(report_id, report_name)
    
    def _on_generate_report(self, button):
        """Handle generate report button click."""
        report_name = self.name_entry.get_text()
        report_type = self.type_combo.get_active_text()
        
        if not report_name:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Missing Report Name"
            )
            dialog.format_secondary_text("Please enter a name for the report.")
            dialog.run()
            dialog.destroy()
            return
            
        # Get selected attacks
        selected_attacks = []
        for row in self.attack_store:
            if row[0]:  # If selected
                selected_attacks.append({
                    "id": row[1],
                    "name": row[2],
                    "date": row[3],
                    "protocol": row[4],
                    "target": row[5]
                })
        
        if not selected_attacks:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No Attacks Selected"
            )
            dialog.format_secondary_text("Please select at least one attack to include in the report.")
            dialog.run()
            dialog.destroy()
            return
            
        # In a real implementation, this would generate the report
        import random
        
        report_id = f"report{len(self.report_store) + 1}"
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Calculate some stats based on selected attacks
        total_creds = random.randint(len(selected_attacks), len(selected_attacks) * 5)
        success_rate = random.uniform(10.0, 90.0)
        
        # Add to reports list
        self.report_store.append([
            report_id,
            report_name,
            report_date,
            report_type,
            ", ".join([a["target"] for a in selected_attacks]),
            success_rate,
            total_creds
        ])
        
        self.logger.info(f"Generated report: {report_name} with {len(selected_attacks)} attacks")
        
        # Generate and display report content
        self._display_report_content(report_id, report_name, selected_attacks, report_type)
        
        # Reset form
        self.name_entry.set_text("")
        # Unselect all attacks
        for row in self.attack_store:
            row[0] = False
            
    def _display_report_content(self, report_id, report_name, attacks=None, report_type=None):
        """Display report content in the viewer.
        
        Args:
            report_id: Report ID
            report_name: Report name
            attacks: Optional list of attacks to include
            report_type: Optional report type
        """
        # In a real implementation, this would load/generate the report content
        buffer = self.report_text.get_buffer()
        
        # If attacks provided, generate a new report
        if attacks:
            # Generate a simple report based on the selected attacks
            content = [
                f"ERPCT REPORT: {report_name}",
                f"Type: {report_type}",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "-" * 80,
                "",
                "SUMMARY",
                "-------",
                f"Total Attacks: {len(attacks)}",
                f"Targets: {', '.join(set(a['target'] for a in attacks))}",
                f"Protocols: {', '.join(set(a['protocol'] for a in attacks))}",
                "",
                "ATTACK DETAILS",
                "--------------"
            ]
            
            for i, attack in enumerate(attacks, 1):
                content.extend([
                    f"{i}. {attack['name']}",
                    f"   Date: {attack['date']}",
                    f"   Protocol: {attack['protocol']}",
                    f"   Target: {attack['target']}",
                    f"   Status: {'Completed' if i % 2 == 0 else 'Partial Success'}",
                    ""
                ])
                
            content.extend([
                "FINDINGS",
                "--------",
                "1. Several default credentials were identified",
                "2. Password complexity requirements appear to be inadequate",
                "3. Account lockout policies are not properly enforced",
                "",
                "RECOMMENDATIONS",
                "--------------",
                "1. Implement stronger password policies",
                "2. Enable account lockout after failed attempts",
                "3. Consider implementing multi-factor authentication",
                "4. Regular security awareness training for users",
                "",
                "End of Report"
            ])
            
            buffer.set_text("\n".join(content))
            
        else:
            # Load existing report based on ID (simulated here)
            content = [
                f"ERPCT REPORT: {report_name}",
                f"ID: {report_id}",
                f"Generated: {'2023-03-15 14:22' if report_id == 'report1' else datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "-" * 80,
                "",
                "SUMMARY",
                "-------",
                "This report summarizes the findings from password attacks conducted against target systems.",
                "Several vulnerabilities were identified, primarily related to weak password policies",
                "and insufficient account security measures.",
                "",
                "STATISTICS",
                "----------",
                "Attempts: 5,283",
                "Successful: 17",
                "Success Rate: 0.32%",
                "Average Attempt Time: 0.45s",
                "Total Execution Time: 39m 27s",
                "",
                "DISCOVERED CREDENTIALS",
                "---------------------",
                "1. admin:admin123",
                "2. user:password",
                "3. guest:guest",
                "...",
                "",
                "RECOMMENDATIONS",
                "--------------",
                "1. Implement stronger password policies",
                "2. Enable account lockout after failed attempts",
                "3. Consider implementing multi-factor authentication",
                "4. Regular security awareness training for users",
                "",
                "End of Report"
            ]
            
            buffer.set_text("\n".join(content)) 

    def set_results_source(self, results_source):
        """Set the results source for the report generator.
        
        Args:
            results_source: The results explorer instance to use as data source
        """
        self.results_source = results_source
        self.logger.info("Results source set for report generator") 