#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Task Scheduler.
This module provides a GUI for scheduling attack tasks.
"""

import gi
import time
from datetime import datetime, timedelta

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from src.utils.logging import get_logger


class TaskScheduler(Gtk.Box):
    """Task scheduler widget."""
    
    def __init__(self):
        """Initialize the task scheduler widget."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        self.attack_callback = None
        
        # Scheduled tasks frame
        task_frame = Gtk.Frame(label="Scheduled Tasks")
        self.pack_start(task_frame, True, True, 0)
        
        task_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        task_box.set_border_width(10)
        task_frame.add(task_box)
        
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        task_box.pack_start(toolbar, False, False, 0)
        
        # Add task button
        add_button = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        add_button.set_tooltip_text("Add Task")
        add_button.connect("clicked", self._on_add_task)
        toolbar.pack_start(add_button, False, False, 0)
        
        # Remove task button
        remove_button = Gtk.Button.new_from_icon_name("list-remove-symbolic", Gtk.IconSize.BUTTON)
        remove_button.set_tooltip_text("Remove Task")
        remove_button.connect("clicked", self._on_remove_task)
        toolbar.pack_start(remove_button, False, False, 0)
        
        # Edit task button
        edit_button = Gtk.Button.new_from_icon_name("document-edit-symbolic", Gtk.IconSize.BUTTON)
        edit_button.set_tooltip_text("Edit Task")
        edit_button.connect("clicked", self._on_edit_task)
        toolbar.pack_start(edit_button, False, False, 0)
        
        # Task list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        task_box.pack_start(scrolled, True, True, 0)
        
        # List store columns
        # ID, Name, Description, Schedule Type, Next Run, Status, Progress
        self.task_store = Gtk.ListStore(str, str, str, str, str, str, float)
        
        # Tree view
        self.task_view = Gtk.TreeView(model=self.task_store)
        self.task_view.set_headers_visible(True)
        scrolled.add(self.task_view)
        
        # Columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Description", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Schedule", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Next Run", renderer, text=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Status", renderer, text=5)
        column.set_sort_column_id(5)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererProgress()
        column = Gtk.TreeViewColumn("Progress", renderer, value=6)
        column.set_sort_column_id(6)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        task_box.pack_start(button_box, False, False, 0)
        
        self.run_now_button = Gtk.Button(label="Run Now")
        self.run_now_button.connect("clicked", self._on_run_now)
        button_box.pack_start(self.run_now_button, False, False, 0)
        
        self.pause_button = Gtk.Button(label="Pause Task")
        self.pause_button.connect("clicked", self._on_pause_task)
        button_box.pack_start(self.pause_button, False, False, 0)
        
        self.resume_button = Gtk.Button(label="Resume Task")
        self.resume_button.connect("clicked", self._on_resume_task)
        button_box.pack_start(self.resume_button, False, False, 0)
        
        # Add some sample data
        self._add_sample_data()
        
        # Start the task update timer
        GLib.timeout_add(1000, self._update_tasks)
        
    def _add_sample_data(self):
        """Add sample data for demonstration purposes."""
        now = datetime.now()
        
        # Sample tasks
        self.task_store.append([
            "task1", 
            "Daily SSH Scan", 
            "Scan SSH on internal network", 
            "Daily at 01:00", 
            (now + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"), 
            "Waiting", 
            0.0
        ])
        
        self.task_store.append([
            "task2", 
            "Weekly Web Scan", 
            "Scan web services for vulnerabilities", 
            "Weekly on Sunday", 
            (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"), 
            "Waiting", 
            0.0
        ])
        
        self.task_store.append([
            "task3", 
            "Monthly Full Audit", 
            "Comprehensive security audit", 
            "Monthly on day 1", 
            (now + timedelta(days=15)).strftime("%Y-%m-%d %H:%M"), 
            "Waiting", 
            0.0
        ])
        
    def _update_tasks(self):
        """Update task status and progress."""
        now = datetime.now()
        
        for row in self.task_store:
            # Check if there's a running task to update
            if row[5] == "Running":
                progress = row[6]
                if progress < 100.0:
                    # Update progress
                    row[6] += 0.5
                else:
                    # Task completed
                    row[5] = "Completed"
                    
                    # Calculate next run time based on schedule type
                    schedule_type = row[3]
                    if schedule_type.startswith("Daily"):
                        next_run = now + timedelta(days=1)
                    elif schedule_type.startswith("Weekly"):
                        next_run = now + timedelta(days=7)
                    else:  # Monthly
                        if now.month == 12:
                            next_run = datetime(now.year + 1, 1, 1)
                        else:
                            next_run = datetime(now.year, now.month + 1, 1)
                    
                    row[4] = next_run.strftime("%Y-%m-%d %H:%M")
                    row[5] = "Waiting"
                    row[6] = 0.0
            
            # Check if it's time to run a waiting task
            elif row[5] == "Waiting":
                next_run = datetime.strptime(row[4], "%Y-%m-%d %H:%M")
                if now >= next_run:
                    row[5] = "Running"
                    self.logger.info(f"Starting scheduled task: {row[1]}")
        
        return True  # Keep the timeout active
    
    def _on_add_task(self, button):
        """Handle add task button click."""
        dialog = TaskDialog(self.get_toplevel())
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            name = dialog.name_entry.get_text()
            description = dialog.desc_entry.get_text()
            schedule_type = dialog.schedule_combo.get_active_text()
            
            if name and schedule_type:
                # Calculate first run time based on schedule
                now = datetime.now()
                
                if schedule_type == "Daily at 01:00":
                    # Next 1 AM
                    if now.hour < 1:
                        next_run = datetime(now.year, now.month, now.day, 1, 0)
                    else:
                        tomorrow = now + timedelta(days=1)
                        next_run = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 1, 0)
                
                elif schedule_type == "Weekly on Sunday":
                    # Next Sunday
                    days_ahead = 6 - now.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    next_run = now + timedelta(days=days_ahead)
                    next_run = datetime(next_run.year, next_run.month, next_run.day, 2, 0)
                
                elif schedule_type == "Monthly on day 1":
                    # 1st of next month
                    if now.month == 12:
                        next_run = datetime(now.year + 1, 1, 1, 3, 0)
                    else:
                        next_run = datetime(now.year, now.month + 1, 1, 3, 0)
                
                else:
                    # Custom time (just use now + 1 hour for demonstration)
                    next_run = now + timedelta(hours=1)
                
                task_id = f"task{len(self.task_store) + 1}"
                self.task_store.append([
                    task_id,
                    name,
                    description,
                    schedule_type,
                    next_run.strftime("%Y-%m-%d %H:%M"),
                    "Waiting",
                    0.0
                ])
                
                self.logger.info(f"Added scheduled task: {name}")
                
                # Prepare schedule configuration
                schedule_config = {
                    "task_id": task_id,
                    "name": name,
                    "description": description,
                    "schedule_type": schedule_type,
                    "next_run": next_run.strftime("%Y-%m-%d %H:%M"),
                    "immediate": False
                }
                
                # Call the attack callback if set
                if self.attack_callback:
                    self.attack_callback(schedule_config)
                else:
                    self.logger.warning("No attack callback set, task will only be tracked in UI")
        
        dialog.destroy()
    
    def _on_remove_task(self, button):
        """Handle remove task button click."""
        selection = self.task_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            task_id = model.get_value(iter, 0)
            task_name = model.get_value(iter, 1)
            
            # Confirm deletion
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Remove Task: {task_name}?"
            )
            dialog.format_secondary_text("This will remove the scheduled task.")
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                model.remove(iter)
                self.logger.info(f"Removed scheduled task: {task_name} (ID: {task_id})")
    
    def _on_edit_task(self, button):
        """Handle edit task button click."""
        selection = self.task_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            task_id = model.get_value(iter, 0)
            task_name = model.get_value(iter, 1)
            task_desc = model.get_value(iter, 2)
            task_schedule = model.get_value(iter, 3)
            
            dialog = TaskDialog(self.get_toplevel(), edit_mode=True)
            dialog.name_entry.set_text(task_name)
            dialog.desc_entry.set_text(task_desc)
            
            # Set active schedule
            if task_schedule == "Daily at 01:00":
                dialog.schedule_combo.set_active(0)
            elif task_schedule == "Weekly on Sunday":
                dialog.schedule_combo.set_active(1)
            elif task_schedule == "Monthly on day 1":
                dialog.schedule_combo.set_active(2)
            else:
                dialog.schedule_combo.set_active(3)
            
            response = dialog.run()
            
            if response == Gtk.ResponseType.OK:
                new_name = dialog.name_entry.get_text()
                new_desc = dialog.desc_entry.get_text()
                new_schedule = dialog.schedule_combo.get_active_text()
                
                if new_name:
                    model.set_value(iter, 1, new_name)
                    model.set_value(iter, 2, new_desc)
                    
                    # Only update schedule if it changed
                    if new_schedule != task_schedule:
                        model.set_value(iter, 3, new_schedule)
                        
                        # Calculate new next run time
                        now = datetime.now()
                        
                        if new_schedule == "Daily at 01:00":
                            if now.hour < 1:
                                next_run = datetime(now.year, now.month, now.day, 1, 0)
                            else:
                                tomorrow = now + timedelta(days=1)
                                next_run = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 1, 0)
                        
                        elif new_schedule == "Weekly on Sunday":
                            days_ahead = 6 - now.weekday()
                            if days_ahead <= 0:
                                days_ahead += 7
                            next_run = now + timedelta(days=days_ahead)
                            next_run = datetime(next_run.year, next_run.month, next_run.day, 2, 0)
                        
                        elif new_schedule == "Monthly on day 1":
                            if now.month == 12:
                                next_run = datetime(now.year + 1, 1, 1, 3, 0)
                            else:
                                next_run = datetime(now.year, now.month + 1, 1, 3, 0)
                        
                        else:
                            next_run = now + timedelta(hours=1)
                        
                        model.set_value(iter, 4, next_run.strftime("%Y-%m-%d %H:%M"))
                    
                    self.logger.info(f"Updated scheduled task: {new_name} (ID: {task_id})")
            
            dialog.destroy()
    
    def _on_run_now(self, button):
        """Handle run now button click."""
        selection = self.task_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            task_id = model.get_value(iter, 0)
            task_name = model.get_value(iter, 1)
            task_desc = model.get_value(iter, 2)
            schedule_type = model.get_value(iter, 3)
            current_status = model.get_value(iter, 5)
            
            if current_status != "Running":
                # Start the task now
                model.set_value(iter, 5, "Running")
                model.set_value(iter, 6, 0.0)
                self.logger.info(f"Manually started task: {task_name} (ID: {task_id})")
                
                # Prepare schedule configuration
                schedule_config = {
                    "task_id": task_id,
                    "name": task_name,
                    "description": task_desc,
                    "schedule_type": schedule_type,
                    "immediate": True
                }
                
                # Call the attack callback if set
                if self.attack_callback:
                    self.attack_callback(schedule_config)
                else:
                    self.logger.error("No attack callback set")
    
    def _on_pause_task(self, button):
        """Handle pause task button click."""
        selection = self.task_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            task_id = model.get_value(iter, 0)
            task_name = model.get_value(iter, 1)
            current_status = model.get_value(iter, 5)
            
            if current_status == "Running":
                model.set_value(iter, 5, "Paused")
                self.logger.info(f"Paused task: {task_name} (ID: {task_id})")
    
    def _on_resume_task(self, button):
        """Handle resume task button click."""
        selection = self.task_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            task_id = model.get_value(iter, 0)
            task_name = model.get_value(iter, 1)
            current_status = model.get_value(iter, 5)
            
            if current_status == "Paused":
                model.set_value(iter, 5, "Running")
                self.logger.info(f"Resumed task: {task_name} (ID: {task_id})")

    def set_attack_callback(self, callback):
        """Set callback function for scheduled attacks.
        
        Args:
            callback: Function to call with schedule config
        """
        self.attack_callback = callback


class TaskDialog(Gtk.Dialog):
    """Dialog for adding or editing a scheduled task."""
    
    def __init__(self, parent, edit_mode=False):
        """Initialize the task dialog.
        
        Args:
            parent: Parent window
            edit_mode: Whether dialog is for editing an existing task
        """
        title = "Edit Task" if edit_mode else "Add Task"
        
        Gtk.Dialog.__init__(
            self, title=title,
            transient_for=parent,
            flags=0,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK
            )
        )
        
        self.set_default_size(400, -1)
        box = self.get_content_area()
        box.set_spacing(6)
        box.set_border_width(10)
        
        # Task name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Task Name:", xalign=0)
        name_label.set_width_chars(12)
        name_box.pack_start(name_label, False, False, 0)
        
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Enter task name")
        name_box.pack_start(self.name_entry, True, True, 0)
        
        box.add(name_box)
        
        # Description
        desc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        desc_label = Gtk.Label(label="Description:", xalign=0)
        desc_label.set_width_chars(12)
        desc_box.pack_start(desc_label, False, False, 0)
        
        self.desc_entry = Gtk.Entry()
        self.desc_entry.set_placeholder_text("Enter task description")
        desc_box.pack_start(self.desc_entry, True, True, 0)
        
        box.add(desc_box)
        
        # Schedule
        schedule_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        schedule_label = Gtk.Label(label="Schedule:", xalign=0)
        schedule_label.set_width_chars(12)
        schedule_box.pack_start(schedule_label, False, False, 0)
        
        self.schedule_combo = Gtk.ComboBoxText()
        self.schedule_combo.append_text("Daily at 01:00")
        self.schedule_combo.append_text("Weekly on Sunday")
        self.schedule_combo.append_text("Monthly on day 1")
        self.schedule_combo.append_text("Custom schedule")
        self.schedule_combo.set_active(0)
        schedule_box.pack_start(self.schedule_combo, True, True, 0)
        
        box.add(schedule_box)
        
        # Show all widgets
        self.show_all()