#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Distributed Panel.
This module provides a GUI for managing distributed attack operations.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from src.utils.logging import get_logger


class DistributedPanel(Gtk.Box):
    """Distributed operations panel."""
    
    def __init__(self):
        """Initialize the distributed panel widget."""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(10)
        
        self.logger = get_logger(__name__)
        
        # Agent management frame
        agent_frame = Gtk.Frame(label="Agent Management")
        self.pack_start(agent_frame, True, True, 0)
        
        agent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        agent_box.set_border_width(10)
        agent_frame.add(agent_box)
        
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        agent_box.pack_start(toolbar, False, False, 0)
        
        # Add agent button
        add_button = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        add_button.set_tooltip_text("Add Agent")
        add_button.connect("clicked", self._on_add_agent)
        toolbar.pack_start(add_button, False, False, 0)
        
        # Remove agent button
        remove_button = Gtk.Button.new_from_icon_name("list-remove-symbolic", Gtk.IconSize.BUTTON)
        remove_button.set_tooltip_text("Remove Agent")
        remove_button.connect("clicked", self._on_remove_agent)
        toolbar.pack_start(remove_button, False, False, 0)
        
        # Refresh button
        refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_button.set_tooltip_text("Refresh Agent Status")
        refresh_button.connect("clicked", self._on_refresh_agents)
        toolbar.pack_start(refresh_button, False, False, 0)
        
        # Agent list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        agent_box.pack_start(scrolled, True, True, 0)
        
        # List store columns
        # ID, Name, Host, Status, CPU Load, Memory Usage, Active Tasks, Is Selected
        self.agent_store = Gtk.ListStore(str, str, str, str, float, float, int, bool)
        
        # Tree view
        self.agent_view = Gtk.TreeView(model=self.agent_store)
        self.agent_view.set_headers_visible(True)
        scrolled.add(self.agent_view)
        
        # Columns
        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.connect("toggled", self._on_agent_toggled)
        column = Gtk.TreeViewColumn("", toggle_renderer, active=7)
        self.agent_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        self.agent_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Host", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        self.agent_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Status", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        self.agent_view.append_column(column)
        
        renderer = Gtk.CellRendererProgress()
        column = Gtk.TreeViewColumn("CPU Load", renderer, value=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        self.agent_view.append_column(column)
        
        renderer = Gtk.CellRendererProgress()
        column = Gtk.TreeViewColumn("Memory", renderer, value=5)
        column.set_sort_column_id(5)
        column.set_resizable(True)
        self.agent_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Active Tasks", renderer, text=6)
        column.set_sort_column_id(6)
        column.set_resizable(True)
        self.agent_view.append_column(column)
        
        # Task distribution frame
        task_frame = Gtk.Frame(label="Task Distribution")
        self.pack_start(task_frame, True, True, 0)
        
        task_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        task_box.set_border_width(10)
        task_frame.add(task_box)
        
        # Task mode options
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_label = Gtk.Label(label="Distribution Mode:", xalign=0)
        mode_box.pack_start(mode_label, False, False, 0)
        
        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append_text("Automatic - Load Balanced")
        self.mode_combo.append_text("Manual - User Assigned")
        self.mode_combo.append_text("Hybrid - Priority Based")
        self.mode_combo.set_active(0)
        mode_box.pack_start(self.mode_combo, True, True, 0)
        
        task_box.pack_start(mode_box, False, False, 0)
        
        # Task parameters
        params_grid = Gtk.Grid()
        params_grid.set_column_spacing(12)
        params_grid.set_row_spacing(6)
        task_box.pack_start(params_grid, False, False, 0)
        
        # Split method
        label = Gtk.Label(label="Split Method:", xalign=0)
        params_grid.attach(label, 0, 0, 1, 1)
        
        self.split_combo = Gtk.ComboBoxText()
        self.split_combo.append_text("By Wordlist Chunks")
        self.split_combo.append_text("By Username Blocks")
        self.split_combo.append_text("By Target Range")
        self.split_combo.set_active(0)
        params_grid.attach(self.split_combo, 1, 0, 1, 1)
        
        # Chunk size
        label = Gtk.Label(label="Chunk Size:", xalign=0)
        params_grid.attach(label, 0, 1, 1, 1)
        
        adjustment = Gtk.Adjustment(value=1000, lower=100, upper=100000, step_increment=100, page_increment=1000)
        self.chunk_spin = Gtk.SpinButton()
        self.chunk_spin.set_adjustment(adjustment)
        params_grid.attach(self.chunk_spin, 1, 1, 1, 1)
        
        # Max tasks per agent
        label = Gtk.Label(label="Max Tasks per Agent:", xalign=0)
        params_grid.attach(label, 0, 2, 1, 1)
        
        adjustment = Gtk.Adjustment(value=2, lower=1, upper=16, step_increment=1, page_increment=2)
        self.max_tasks_spin = Gtk.SpinButton()
        self.max_tasks_spin.set_adjustment(adjustment)
        params_grid.attach(self.max_tasks_spin, 1, 2, 1, 1)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        task_box.pack_start(button_box, False, False, 10)
        
        self.distribute_button = Gtk.Button(label="Distribute Attack")
        self.distribute_button.connect("clicked", self._on_distribute_attack)
        button_box.pack_end(self.distribute_button, False, False, 0)
        
        # Tasks frame
        running_frame = Gtk.Frame(label="Running Tasks")
        self.pack_start(running_frame, True, True, 0)
        
        running_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        running_box.set_border_width(10)
        running_frame.add(running_box)
        
        # Running tasks list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        running_box.pack_start(scrolled, True, True, 0)
        
        # List store columns
        # ID, Agent Name, Description, Progress, Status, Start Time, ETA
        self.task_store = Gtk.ListStore(str, str, str, float, str, str, str)
        
        # Tree view
        self.task_view = Gtk.TreeView(model=self.task_store)
        self.task_view.set_headers_visible(True)
        scrolled.add(self.task_view)
        
        # Columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Agent", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Description", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererProgress()
        column = Gtk.TreeViewColumn("Progress", renderer, value=3)
        column.set_sort_column_id(3)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Status", renderer, text=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Start Time", renderer, text=5)
        column.set_sort_column_id(5)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("ETA", renderer, text=6)
        column.set_sort_column_id(6)
        column.set_resizable(True)
        self.task_view.append_column(column)
        
        # Task action buttons
        task_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        running_box.pack_start(task_button_box, False, False, 0)
        
        self.pause_button = Gtk.Button(label="Pause Task")
        self.pause_button.connect("clicked", self._on_pause_task)
        task_button_box.pack_start(self.pause_button, False, False, 0)
        
        self.resume_button = Gtk.Button(label="Resume Task")
        self.resume_button.connect("clicked", self._on_resume_task)
        task_button_box.pack_start(self.resume_button, False, False, 0)
        
        self.stop_button = Gtk.Button(label="Stop Task")
        self.stop_button.connect("clicked", self._on_stop_task)
        task_button_box.pack_start(self.stop_button, False, False, 0)
        
        # Add some sample data
        self._add_sample_data()
        
    def _add_sample_data(self):
        """Add sample data for demonstration purposes."""
        # Sample agents
        self.agent_store.append(["agent1", "Agent-01", "192.168.1.101", "Online", 45.2, 28.7, 1, True])
        self.agent_store.append(["agent2", "Agent-02", "192.168.1.102", "Online", 12.5, 15.3, 0, False])
        self.agent_store.append(["agent3", "Agent-03", "192.168.1.103", "Offline", 0.0, 0.0, 0, False])
        self.agent_store.append(["agent4", "Agent-04", "192.168.1.104", "Online", 78.9, 62.5, 2, True])
        
        # Sample tasks
        self.task_store.append(["task1", "Agent-01", "SSH Attack on 10.0.0.1", 35.8, "Running", "10:15:22", "00:45:12"])
        self.task_store.append(["task2", "Agent-04", "FTP Attack on 10.0.0.5", 68.2, "Running", "09:58:13", "00:12:30"])
        self.task_store.append(["task3", "Agent-04", "HTTP Attack on 10.0.0.10", 12.3, "Running", "10:22:05", "01:15:43"])
        
    def _on_add_agent(self, button):
        """Handle add agent button click."""
        dialog = AgentDialog(self.get_toplevel())
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            name = dialog.name_entry.get_text()
            host = dialog.host_entry.get_text()
            port = dialog.port_spin.get_value_as_int()
            
            if name and host:
                # In a real implementation, this would attempt to connect to the agent
                agent_id = f"agent{len(self.agent_store) + 1}"
                self.agent_store.append([agent_id, name, f"{host}:{port}", "Connecting...", 0.0, 0.0, 0, False])
                self.logger.info(f"Added agent {name} at {host}:{port}")
                
                # Simulate connection status update after a delay
                GLib.timeout_add(2000, self._update_agent_status, agent_id)
        
        dialog.destroy()
        
    def _update_agent_status(self, agent_id):
        """Update agent status after connection attempt."""
        for row in self.agent_store:
            if row[0] == agent_id:
                # Simulate success (in reality would depend on connection result)
                row[3] = "Online"
                return False  # Remove the timeout
        return False
        
    def _on_remove_agent(self, button):
        """Handle remove agent button click."""
        selection = self.agent_view.get_selection()
        model, paths = selection.get_selected_rows()
        
        if paths:
            # Get all paths and convert to row references (which remain valid after deletion)
            row_refs = []
            for path in paths:
                row_refs.append(Gtk.TreeRowReference.new(model, path))
            
            # Delete each selected row
            for row_ref in row_refs:
                if row_ref.valid():
                    path = row_ref.get_path()
                    iter = model.get_iter(path)
                    agent_id = model.get_value(iter, 0)
                    agent_name = model.get_value(iter, 1)
                    self.logger.info(f"Removed agent {agent_name} (ID: {agent_id})")
                    model.remove(iter)
        
    def _on_refresh_agents(self, button):
        """Handle refresh agents button click."""
        # In a real implementation, this would query all agents for status updates
        self.logger.info("Refreshing agent status")
        
        for row in self.agent_store:
            if row[3] == "Online":
                # Simulate random resource changes
                import random
                row[4] = min(100.0, max(0.0, row[4] + random.uniform(-10.0, 10.0)))
                row[5] = min(100.0, max(0.0, row[5] + random.uniform(-8.0, 8.0)))
        
    def _on_agent_toggled(self, renderer, path):
        """Handle agent selection toggle."""
        iter = self.agent_store.get_iter(path)
        current_value = self.agent_store.get_value(iter, 7)
        self.agent_store.set_value(iter, 7, not current_value)
        
    def _on_distribute_attack(self, button):
        """Handle distribute attack button click."""
        # Count selected agents
        selected_agents = []
        for row in self.agent_store:
            if row[7] and row[3] == "Online":  # Selected and online
                selected_agents.append((row[0], row[1]))  # ID and name
        
        if not selected_agents:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No Agents Selected"
            )
            dialog.format_secondary_text("Please select at least one online agent to distribute the attack.")
            dialog.run()
            dialog.destroy()
            return
            
        # In a real implementation, this would create and distribute tasks
        self.logger.info(f"Distributing attack to {len(selected_agents)} agents")
        
        # Simulate task creation (in a real implementation, would get attack config from elsewhere)
        import time
        import random
        
        protocols = ["SSH", "FTP", "HTTP", "IMAP", "POP3", "SMTP"]
        targets = ["10.0.0.1", "10.0.0.5", "10.0.0.10", "10.0.0.15", "10.0.0.20"]
        
        for agent_id, agent_name in selected_agents:
            # Assign 1-2 random tasks per selected agent
            task_count = random.randint(1, 2)
            for _ in range(task_count):
                protocol = random.choice(protocols)
                target = random.choice(targets)
                
                task_id = f"task{len(self.task_store) + 1}"
                progress = 0.0
                current_time = time.strftime("%H:%M:%S")
                eta = "00:" + str(random.randint(10, 59)) + ":" + str(random.randint(10, 59))
                
                self.task_store.append([task_id, agent_name, f"{protocol} Attack on {target}", 
                                      progress, "Starting", current_time, eta])
                
                # Increment agent task count
                for row in self.agent_store:
                    if row[0] == agent_id:
                        row[6] += 1
                        break
                
                # Start task progress simulation
                GLib.timeout_add(2000, self._update_task_progress, task_id)
                
    def _update_task_progress(self, task_id):
        """Update task progress simulation."""
        for row in self.task_store:
            if row[0] == task_id:
                if row[3] < 100.0:
                    # Update progress
                    import random
                    progress_increment = random.uniform(0.5, 2.0)
                    row[3] = min(100.0, row[3] + progress_increment)
                    
                    # Update status if just started
                    if row[4] == "Starting":
                        row[4] = "Running"
                    
                    # Update ETA based on progress
                    remaining = 100.0 - row[3]
                    if remaining > 0:
                        mins_remaining = int(remaining / progress_increment * 2 / 60)
                        secs_remaining = int((remaining / progress_increment * 2) % 60)
                        row[6] = f"00:{mins_remaining:02d}:{secs_remaining:02d}"
                    
                    return True  # Keep the timeout
                else:
                    # Task completed
                    row[4] = "Completed"
                    row[6] = "00:00:00"
                    
                    # Decrement agent task count
                    agent_name = row[1]
                    for agent_row in self.agent_store:
                        if agent_row[1] == agent_name:
                            agent_row[6] = max(0, agent_row[6] - 1)
                            break
                    
                    return False  # Remove the timeout
        
        return False  # Task not found, remove the timeout
        
    def _on_pause_task(self, button):
        """Handle pause task button click."""
        selection = self.task_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            task_id = model.get_value(iter, 0)
            task_desc = model.get_value(iter, 2)
            current_status = model.get_value(iter, 4)
            
            if current_status == "Running":
                model.set_value(iter, 4, "Paused")
                self.logger.info(f"Paused task {task_id}: {task_desc}")
        
    def _on_resume_task(self, button):
        """Handle resume task button click."""
        selection = self.task_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            task_id = model.get_value(iter, 0)
            task_desc = model.get_value(iter, 2)
            current_status = model.get_value(iter, 4)
            
            if current_status == "Paused":
                model.set_value(iter, 4, "Running")
                self.logger.info(f"Resumed task {task_id}: {task_desc}")
                
                # Restart progress simulation
                GLib.timeout_add(2000, self._update_task_progress, task_id)
        
    def _on_stop_task(self, button):
        """Handle stop task button click."""
        selection = self.task_view.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            task_id = model.get_value(iter, 0)
            task_desc = model.get_value(iter, 2)
            agent_name = model.get_value(iter, 1)
            
            model.set_value(iter, 4, "Stopped")
            self.logger.info(f"Stopped task {task_id}: {task_desc}")
            
            # Decrement agent task count
            for agent_row in self.agent_store:
                if agent_row[1] == agent_name:
                    agent_row[6] = max(0, agent_row[6] - 1)
                    break


class AgentDialog(Gtk.Dialog):
    """Dialog for adding a new agent."""
    
    def __init__(self, parent):
        """Initialize the agent dialog.
        
        Args:
            parent: Parent window
        """
        Gtk.Dialog.__init__(
            self, title="Add Agent",
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
        
        # Agent name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Agent Name:", xalign=0)
        name_label.set_width_chars(12)
        name_box.pack_start(name_label, False, False, 0)
        
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Enter agent name")
        name_box.pack_start(self.name_entry, True, True, 0)
        
        box.add(name_box)
        
        # Host
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Host:", xalign=0)
        host_label.set_width_chars(12)
        host_box.pack_start(host_label, False, False, 0)
        
        self.host_entry = Gtk.Entry()
        self.host_entry.set_placeholder_text("Enter hostname or IP address")
        host_box.pack_start(self.host_entry, True, True, 0)
        
        box.add(host_box)
        
        # Port
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port:", xalign=0)
        port_label.set_width_chars(12)
        port_box.pack_start(port_label, False, False, 0)
        
        adjustment = Gtk.Adjustment(value=7654, lower=1024, upper=65535, step_increment=1, page_increment=100)
        self.port_spin = Gtk.SpinButton()
        self.port_spin.set_adjustment(adjustment)
        port_box.pack_start(self.port_spin, True, True, 0)
        
        box.add(port_box)
        
        # Show all widgets
        self.show_all() 