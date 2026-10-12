"""Interactive companion popup window with Controls, Tasks, Statistics and Settings."""
import os
import sys
import datetime
from pathlib import Path
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango

from pomodoro.ipc import IPCClient


class PomodoroCompanionPopup(Gtk.Window):
    def __init__(self, ipc_client: IPCClient, on_settings_changed_cb=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.client = ipc_client
        self.on_settings_changed_cb = on_settings_changed_cb

        self.set_title("Pomodoro Productivity Clock")
        self.set_default_size(480, 560)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        # Local state cache
        self.current_status = {}
        self.stats_date = datetime.date.today()

        # Connect delete-event to hide instead of destroy
        self.connect("delete-event", lambda w, e: self.hide_on_delete())
        self.connect("key-press-event", self._on_key_press)

        self._build_ui()
        self._apply_theme()
        self.refresh_all()

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def _apply_theme(self):
        css_provider = Gtk.CssProvider()
        css = b"""
        window {
            background-color: #1e222b;
            color: #abb2bf;
        }
        headerbar {
            background: #181a1f;
            border-bottom: 1px solid #282c34;
        }
        notebook {
            background-color: #1e222b;
        }
        notebook tab {
            background-color: #21252b;
            color: #7f848e;
            padding: 8px 16px;
            font-weight: bold;
            border: none;
            border-bottom: 2px solid transparent;
        }
        notebook tab:checked {
            background-color: #1e222b;
            color: #61afef;
            border-bottom: 2px solid #61afef;
        }
        .timer-display {
            font-family: Cantarell, "Segoe UI", Monospace;
            font-size: 42pt;
            font-weight: bold;
            color: #ffffff;
        }
        .state-badge {
            font-size: 11pt;
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 999px;
        }
        .badge-focus {
            background-color: rgba(224, 108, 117, 0.2);
            color: #e06c75;
            border: 1px solid rgba(224, 108, 117, 0.4);
        }
        .badge-break {
            background-color: rgba(152, 195, 121, 0.2);
            color: #98c379;
            border: 1px solid rgba(152, 195, 121, 0.4);
        }
        .badge-paused {
            background-color: rgba(229, 192, 123, 0.2);
            color: #e5c07b;
            border: 1px solid rgba(229, 192, 123, 0.4);
        }
        .badge-idle {
            background-color: rgba(171, 178, 191, 0.15);
            color: #abb2bf;
            border: 1px solid rgba(171, 178, 191, 0.3);
        }
        .btn-primary {
            background-color: #98c379;
            color: #1e222b;
            font-weight: bold;
            border-radius: 8px;
            padding: 8px 18px;
        }
        .btn-primary:hover {
            background-color: #a3cc85;
        }
        .btn-danger {
            background-color: #e06c75;
            color: #ffffff;
            font-weight: bold;
            border-radius: 8px;
            padding: 8px 18px;
        }
        .card {
            background-color: #21252b;
            border: 1px solid #282c34;
            border-radius: 10px;
            padding: 14px;
        }
        .stat-val {
            font-size: 20pt;
            font-weight: bold;
            color: #61afef;
        }
        .stat-lbl {
            font-size: 9pt;
            color: #7f848e;
            font-weight: bold;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        # Header
        header = Gtk.HeaderBar()
        header.set_title("Pomodoro Clock")
        header.set_subtitle("Kali Linux Productivity")
        header.set_show_close_button(True)
        main_box.pack_start(header, False, False, 0)

        # Notebook tabs
        self.notebook = Gtk.Notebook()
        main_box.pack_start(self.notebook, True, True, 0)

        # Tab 1: Timer Controls
        self.tab_timer = self._build_timer_tab()
        self.notebook.append_page(self.tab_timer, Gtk.Label(label="⏱ Timer"))

        # Tab 2: Tasks
        self.tab_tasks = self._build_tasks_tab()
        self.notebook.append_page(self.tab_tasks, Gtk.Label(label="📋 Tasks"))

        # Tab 3: Statistics
        self.tab_stats = self._build_stats_tab()
        self.notebook.append_page(self.tab_stats, Gtk.Label(label="📊 Statistics"))

        # Tab 4: Settings
        self.tab_settings = self._build_settings_tab()
        self.notebook.append_page(self.tab_settings, Gtk.Label(label="⚙ Settings"))

    # ==================== TAB 1: TIMER ====================
    def _build_timer_tab(self) -> Gtk.Widget:
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        container.set_border_width(20)

        # State badge & cycle indicator
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.state_badge = Gtk.Label(label="IDLE")
        self.state_badge.get_style_context().add_class("state-badge")
        self.state_badge.get_style_context().add_class("badge-idle")

        self.cycle_label = Gtk.Label(label="Session 0 of 4")
        self.cycle_label.set_halign(Gtk.Align.END)

        top_row.pack_start(self.state_badge, False, False, 0)
        top_row.pack_end(self.cycle_label, False, False, 0)
        container.pack_start(top_row, False, False, 0)

        # Large countdown
        self.time_label = Gtk.Label(label="25:00")
        self.time_label.get_style_context().add_class("timer-display")
        container.pack_start(self.time_label, False, False, 8)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        container.pack_start(self.progress_bar, False, False, 0)

        # Control Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)

        self.btn_reset = Gtk.Button(label="⟲ Reset")
        self.btn_reset.connect("clicked", lambda w: self._send_cmd("reset"))

        self.btn_toggle = Gtk.Button(label="▶ Start")
        self.btn_toggle.get_style_context().add_class("btn-primary")
        self.btn_toggle.connect("clicked", lambda w: self._send_cmd("toggle"))

        self.btn_skip = Gtk.Button(label="⏭ Skip")
        self.btn_skip.connect("clicked", lambda w: self._send_cmd("skip"))

        btn_box.pack_start(self.btn_reset, False, False, 0)
        btn_box.pack_start(self.btn_toggle, False, False, 0)
        btn_box.pack_start(self.btn_skip, False, False, 0)
        container.pack_start(btn_box, False, False, 8)

        # Active Task Card
        task_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        task_card.get_style_context().add_class("card")

        card_title = Gtk.Label(label="CURRENT STUDY TASK")
        card_title.get_style_context().add_class("stat-lbl")
        card_title.set_halign(Gtk.Align.START)
        task_card.pack_start(card_title, False, False, 0)

        self.active_task_name = Gtk.Label(label="No task selected")
        self.active_task_name.set_halign(Gtk.Align.START)
        self.active_task_name.get_style_context().add_class("bold")

        self.active_task_details = Gtk.Label(label="Select a task below or study freely")
        self.active_task_details.set_halign(Gtk.Align.START)

        task_card.pack_start(self.active_task_name, False, False, 0)
        task_card.pack_start(self.active_task_details, False, False, 0)

        # Quick task switch combo
        quick_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.task_combo = Gtk.ComboBoxText()
        self.task_combo.append("0", "-- None (Free Study) --")
        self.task_combo.connect("changed", self._on_task_combo_changed)
        quick_row.pack_start(self.task_combo, True, True, 0)

        self.btn_complete_active = Gtk.Button(label="✓ Mark Done")
        self.btn_complete_active.connect("clicked", self._on_complete_active_task)
        quick_row.pack_start(self.btn_complete_active, False, False, 0)

        task_card.pack_start(quick_row, False, False, 4)
        container.pack_start(task_card, False, False, 0)

        return container

    # ==================== TAB 2: TASKS ====================
    def _build_tasks_tab(self) -> Gtk.Widget:
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        container.set_border_width(16)

        # Top bar: Filter & Add button
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.task_filter_combo = Gtk.ComboBoxText()
        self.task_filter_combo.append("pending", "Pending Tasks")
        self.task_filter_combo.append("all", "All Tasks (including Done)")
        self.task_filter_combo.set_active(0)
        self.task_filter_combo.connect("changed", lambda w: self.refresh_tasks())
        top_bar.pack_start(self.task_filter_combo, True, True, 0)

        btn_show_add = Gtk.Button(label="+ New Task")
        btn_show_add.connect("clicked", self._on_toggle_add_task_panel)
        top_bar.pack_end(btn_show_add, False, False, 0)
        container.pack_start(top_bar, False, False, 0)

        # New Task Panel (collapsible)
        self.add_task_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_task_box.get_style_context().add_class("card")
        self.add_task_box.set_no_show_all(True)
        self.add_task_box.hide()

        lbl_add_title = Gtk.Label(label="CREATE NEW TASK")
        lbl_add_title.get_style_context().add_class("stat-lbl")
        lbl_add_title.set_halign(Gtk.Align.START)
        self.add_task_box.pack_start(lbl_add_title, False, False, 0)

        self.entry_task_name = Gtk.Entry()
        self.entry_task_name.set_placeholder_text("Task name (e.g. Solve 3 Codeforces problems)")
        self.add_task_box.pack_start(self.entry_task_name, False, False, 0)

        row_fields = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.combo_subject = Gtk.ComboBoxText()
        row_fields.pack_start(self.combo_subject, True, True, 0)

        self.entry_target = Gtk.Entry()
        self.entry_target.set_placeholder_text("Target (e.g. 3 problems)")
        row_fields.pack_start(self.entry_target, True, True, 0)
        self.add_task_box.pack_start(row_fields, False, False, 0)

        self.entry_notes = Gtk.Entry()
        self.entry_notes.set_placeholder_text("Optional notes")
        self.add_task_box.pack_start(self.entry_notes, False, False, 0)

        btn_save_task = Gtk.Button(label="Save Task")
        btn_save_task.get_style_context().add_class("btn-primary")
        btn_save_task.connect("clicked", self._on_save_new_task)
        self.add_task_box.pack_start(btn_save_task, False, False, 0)

        container.pack_start(self.add_task_box, False, False, 0)

        # Tasks List in ScrolledWindow
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.task_list_store = Gtk.ListStore(int, str, str, str, str, bool) # id, name, subject, target, notes, completed
        self.task_tree = Gtk.TreeView(model=self.task_list_store)
        self.task_tree.set_headers_visible(True)

        # Column 1: Status checkbox
        toggle_cell = Gtk.CellRendererToggle()
        toggle_cell.connect("toggled", self._on_task_toggled)
        col_done = Gtk.TreeViewColumn("Done", toggle_cell, active=5)
        self.task_tree.append_column(col_done)

        # Column 2: Name
        cell_name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn("Task Name", cell_name, text=1)
        col_name.set_expand(True)
        self.task_tree.append_column(col_name)

        # Column 3: Subject
        cell_subj = Gtk.CellRendererText()
        col_subj = Gtk.TreeViewColumn("Subject", cell_subj, text=2)
        self.task_tree.append_column(col_subj)

        # Column 4: Target
        cell_target = Gtk.CellRendererText()
        col_target = Gtk.TreeViewColumn("Target", cell_target, text=3)
        self.task_tree.append_column(col_target)

        scrolled.add(self.task_tree)
        container.pack_start(scrolled, True, True, 0)

        # Bottom actions row
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_select_task = Gtk.Button(label="🎯 Select for Timer")
        btn_select_task.connect("clicked", self._on_select_tree_task)
        actions_row.pack_start(btn_select_task, True, True, 0)

        btn_delete_task = Gtk.Button(label="🗑 Delete")
        btn_delete_task.connect("clicked", self._on_delete_tree_task)
        actions_row.pack_start(btn_delete_task, False, False, 0)

        container.pack_start(actions_row, False, False, 0)

        return container

    def _on_toggle_add_task_panel(self, widget):
        if self.add_task_box.get_visible():
            self.add_task_box.hide()
        else:
            self._refresh_subject_combo()
            self.add_task_box.show_all()

    def _refresh_subject_combo(self):
        self.combo_subject.remove_all()
        try:
            resp = self.client.send_command("list_subjects")
            for s in resp.get("subjects", []):
                self.combo_subject.append(str(s["id"]), s["name"])
            if resp.get("subjects"):
                self.combo_subject.set_active(0)
        except Exception:
            pass

    def _on_save_new_task(self, widget):
        name = self.entry_task_name.get_text().strip()
        if not name:
            return
        sub_id_str = self.combo_subject.get_active_id()
        sub_id = int(sub_id_str) if sub_id_str else None
        target = self.entry_target.get_text().strip() or None
        notes = self.entry_notes.get_text().strip() or None

        self.client.send_command(
            "add_task",
            name=name,
            subject_id=sub_id,
            target=target,
            notes=notes,
        )
        self.entry_task_name.set_text("")
        self.entry_target.set_text("")
        self.entry_notes.set_text("")
        self.add_task_box.hide()
        self.refresh_tasks()

    def _on_task_toggled(self, widget, path):
        model = self.task_list_store
        task_id = model[path][0]
        curr_val = model[path][5]
        new_val = not curr_val
        self.client.send_command("complete_task", task_id=task_id, completed=new_val)
        self.refresh_tasks()
        self.refresh_stats()

    def _on_select_tree_task(self, widget):
        selection = self.task_tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            task_id = model[treeiter][0]
            self.client.send_command("set_task", task_id=task_id)
            self.notebook.set_current_page(0)

    def _on_delete_tree_task(self, widget):
        selection = self.task_tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            task_id = model[treeiter][0]
            self.client.send_command("delete_task", task_id=task_id)
            self.refresh_tasks()

    def _on_task_combo_changed(self, combo):
        active_id = combo.get_active_id()
        if active_id is not None:
            task_id = int(active_id) if active_id != "0" else None
            curr_task = self.current_status.get("active_task")
            curr_id = curr_task["id"] if curr_task else None
            if task_id != curr_id:
                self.client.send_command("set_task", task_id=task_id)

    def _on_complete_active_task(self, widget):
        curr_task = self.current_status.get("active_task")
        if curr_task:
            self.client.send_command("complete_task", task_id=curr_task["id"], completed=True)
            self.client.send_command("set_task", task_id=None)
            self.refresh_tasks()
            self.refresh_stats()

    # ==================== TAB 3: STATISTICS ====================
    def _build_stats_tab(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        container.set_border_width(16)
        scrolled.add(container)

        # Date Selector
        date_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_prev = Gtk.Button(label="◀ Prev")
        btn_prev.connect("clicked", lambda w: self._nav_date(-1))

        self.lbl_stats_date = Gtk.Label(label="Today")
        self.lbl_stats_date.get_style_context().add_class("bold")

        btn_today = Gtk.Button(label="Today")
        btn_today.connect("clicked", lambda w: self._nav_date(0))

        btn_next = Gtk.Button(label="Next ▶")
        btn_next.connect("clicked", lambda w: self._nav_date(1))

        date_bar.pack_start(btn_prev, False, False, 0)
        date_bar.pack_start(btn_today, False, False, 0)
        date_bar.pack_start(self.lbl_stats_date, True, True, 0)
        date_bar.pack_end(btn_next, False, False, 0)
        container.pack_start(date_bar, False, False, 0)

        # 4 Stat Cards in Grid
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)

        # Card 1: Focus Time
        card1 = self._create_stat_card("TOTAL FOCUSED TIME", "0m")
        self.val_focus_time = card1.get_children()[1]
        grid.attach(card1, 0, 0, 1, 1)

        # Card 2: Sessions
        card2 = self._create_stat_card("SESSIONS COMPLETED", "0")
        self.val_sessions = card2.get_children()[1]
        grid.attach(card2, 1, 0, 1, 1)

        # Card 3: Tasks Done
        card3 = self._create_stat_card("TASKS COMPLETED", "0")
        self.val_tasks_done = card3.get_children()[1]
        grid.attach(card3, 0, 1, 1, 1)

        # Card 4: Top Subject
        card4 = self._create_stat_card("TOP SUBJECT", "None")
        self.val_top_subject = card4.get_children()[1]
        grid.attach(card4, 1, 1, 1, 1)

        container.pack_start(grid, False, False, 0)

        # Subject Breakdown
        lbl_subj = Gtk.Label(label="FOCUS TIME BY SUBJECT")
        lbl_subj.get_style_context().add_class("stat-lbl")
        lbl_subj.set_halign(Gtk.Align.START)
        container.pack_start(lbl_subj, False, False, 4)

        self.box_subjects_breakdown = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.box_subjects_breakdown.get_style_context().add_class("card")
        container.pack_start(self.box_subjects_breakdown, False, False, 0)

        # Past 7 Days History
        lbl_hist = Gtk.Label(label="PAST 7 DAYS HISTORY")
        lbl_hist.get_style_context().add_class("stat-lbl")
        lbl_hist.set_halign(Gtk.Align.START)
        container.pack_start(lbl_hist, False, False, 4)

        self.history_store = Gtk.ListStore(str, str, int, int) # Date, Focus Time, Sessions, Tasks
        self.history_tree = Gtk.TreeView(model=self.history_store)
        self.history_tree.get_style_context().add_class("card")

        col1 = Gtk.TreeViewColumn("Date", Gtk.CellRendererText(), text=0)
        col2 = Gtk.TreeViewColumn("Focused Time", Gtk.CellRendererText(), text=1)
        col3 = Gtk.TreeViewColumn("Sessions", Gtk.CellRendererText(), text=2)
        col4 = Gtk.TreeViewColumn("Tasks Done", Gtk.CellRendererText(), text=3)
        self.history_tree.append_column(col1)
        self.history_tree.append_column(col2)
        self.history_tree.append_column(col3)
        self.history_tree.append_column(col4)
        container.pack_start(self.history_tree, False, False, 0)

        return scrolled

    def _create_stat_card(self, title: str, value: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.get_style_context().add_class("card")
        lbl_title = Gtk.Label(label=title)
        lbl_title.get_style_context().add_class("stat-lbl")
        lbl_title.set_halign(Gtk.Align.START)
        lbl_val = Gtk.Label(label=value)
        lbl_val.get_style_context().add_class("stat-val")
        lbl_val.set_halign(Gtk.Align.START)
        box.pack_start(lbl_title, False, False, 0)
        box.pack_start(lbl_val, False, False, 0)
        return box

    def _nav_date(self, offset: int):
        if offset == 0:
            self.stats_date = datetime.date.today()
        else:
            self.stats_date = self.stats_date + datetime.timedelta(days=offset)
        self.refresh_stats()

    # ==================== TAB 4: SETTINGS ====================
    def _build_settings_tab(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        container.set_border_width(16)
        scrolled.add(container)

        # Durations Section
        lbl_dur = Gtk.Label(label="TIMER DURATIONS")
        lbl_dur.get_style_context().add_class("stat-lbl")
        lbl_dur.set_halign(Gtk.Align.START)
        container.pack_start(lbl_dur, False, False, 0)

        dur_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        dur_box.get_style_context().add_class("card")

        self.spin_focus = self._add_spin_row(dur_box, "Focus duration (minutes):", 1, 180, 25)
        self.spin_short_break = self._add_spin_row(dur_box, "Short break duration (minutes):", 1, 60, 5)
        self.spin_long_break = self._add_spin_row(dur_box, "Long break duration (minutes):", 1, 60, 15)
        self.spin_sessions = self._add_spin_row(dur_box, "Sessions before long break:", 1, 16, 4)
        container.pack_start(dur_box, False, False, 0)

        # Automation & Notifications Section
        lbl_notif = Gtk.Label(label="AUTOMATION & NOTIFICATIONS")
        lbl_notif.get_style_context().add_class("stat-lbl")
        lbl_notif.set_halign(Gtk.Align.START)
        container.pack_start(lbl_notif, False, False, 0)

        notif_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        notif_box.get_style_context().add_class("card")

        self.switch_auto_break = self._add_switch_row(notif_box, "Auto-start breaks after focus:")
        self.switch_auto_focus = self._add_switch_row(notif_box, "Auto-start focus after break:")
        self.switch_notif = self._add_switch_row(notif_box, "Desktop notifications:")
        self.switch_sound = self._add_switch_row(notif_box, "Sound notification alert:")
        container.pack_start(notif_box, False, False, 0)

        # Placement fine-tuning
        lbl_placement = Gtk.Label(label="TOP PANEL PLACEMENT")
        lbl_placement.get_style_context().add_class("stat-lbl")
        lbl_placement.set_halign(Gtk.Align.START)
        container.pack_start(lbl_placement, False, False, 0)

        place_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        place_box.get_style_context().add_class("card")
        self.spin_offset = self._add_spin_row(place_box, "Horizontal offset adjustment (px):", -300, 300, 0)
        container.pack_start(place_box, False, False, 0)

        # Save Button
        btn_save = Gtk.Button(label="💾 Save Settings")
        btn_save.get_style_context().add_class("btn-primary")
        btn_save.connect("clicked", self._on_save_settings)
        container.pack_start(btn_save, False, False, 8)

        return scrolled

    def _add_spin_row(self, parent: Gtk.Box, label_text: str, min_v: int, max_v: int, val: int) -> Gtk.SpinButton:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label_text)
        lbl.set_halign(Gtk.Align.START)
        spin = Gtk.SpinButton.new_with_range(min_v, max_v, 1)
        spin.set_value(val)
        row.pack_start(lbl, True, True, 0)
        row.pack_end(spin, False, False, 0)
        parent.pack_start(row, False, False, 0)
        return spin

    def _add_switch_row(self, parent: Gtk.Box, label_text: str) -> Gtk.Switch:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label_text)
        lbl.set_halign(Gtk.Align.START)
        sw = Gtk.Switch()
        row.pack_start(lbl, True, True, 0)
        row.pack_end(sw, False, False, 0)
        parent.pack_start(row, False, False, 0)
        return sw

    def _on_save_settings(self, widget):
        updates = {
            "focus_duration": int(self.spin_focus.get_value()),
            "short_break_duration": int(self.spin_short_break.get_value()),
            "long_break_duration": int(self.spin_long_break.get_value()),
            "sessions_before_long_break": int(self.spin_sessions.get_value()),
            "auto_start_breaks": self.switch_auto_break.get_active(),
            "auto_start_focus": self.switch_auto_focus.get_active(),
            "notifications_enabled": self.switch_notif.get_active(),
            "sound_enabled": self.switch_sound.get_active(),
            "panel_x_offset": int(self.spin_offset.get_value()),
        }
        resp = self.client.send_command("update_settings", settings=updates)
        if resp.get("ok"):
            if self.on_settings_changed_cb:
                self.on_settings_changed_cb(updates)
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Settings Saved",
            )
            dialog.format_secondary_text("Pomodoro preferences have been updated and persisted.")
            dialog.run()
            dialog.destroy()

    # ==================== DATA SYNC ====================
    def _send_cmd(self, cmd: str):
        try:
            resp = self.client.send_command(cmd)
            if resp.get("ok"):
                self.update_status(resp["data"])
        except Exception:
            pass

    def update_status(self, status: dict):
        self.current_status = status
        state = status.get("state", "IDLE")
        formatted = status.get("formatted_time", "25:00")
        progress = status.get("progress", 0.0)
        cycle = status.get("cycle_count", 0)
        target_cycle = status.get("sessions_before_long_break", 4)

        # Update Time & Progress
        self.time_label.set_text(formatted)
        self.progress_bar.set_fraction(progress)

        # Cycle indicator
        dots = "●" * (cycle % target_cycle) + "○" * (target_cycle - (cycle % target_cycle))
        self.cycle_label.set_text(f"Session {cycle % target_cycle + 1} of {target_cycle}  [{dots}]")

        # Update State Badge
        self.state_badge.set_text(state)
        ctx = self.state_badge.get_style_context()
        for cls in ["badge-focus", "badge-break", "badge-paused", "badge-idle"]:
            ctx.remove_class(cls)
        if state == "FOCUS":
            ctx.add_class("badge-focus")
            self.btn_toggle.set_label("⏸ Pause")
        elif state in ("SHORT_BREAK", "LONG_BREAK"):
            ctx.add_class("badge-break")
            self.btn_toggle.set_label("⏸ Pause")
        elif state == "PAUSED":
            ctx.add_class("badge-paused")
            self.btn_toggle.set_label("▶ Resume")
        else:
            ctx.add_class("badge-idle")
            self.btn_toggle.set_label("▶ Start")

        # Active Task Card
        task = status.get("active_task")
        if task:
            subj_str = f"[{task.get('subject_name', 'General')}] " if task.get("subject_name") else ""
            self.active_task_name.set_text(f"{subj_str}{task['name']}")
            details = []
            if task.get("target"):
                details.append(f"Target: {task['target']}")
            if task.get("notes"):
                details.append(f"Notes: {task['notes']}")
            self.active_task_details.set_text(" | ".join(details) if details else "Active Task")
            self.btn_complete_active.set_sensitive(True)
        else:
            self.active_task_name.set_text("No task selected")
            self.active_task_details.set_text("Study freely or pick a task from the dropdown")
            self.btn_complete_active.set_sensitive(False)

    def refresh_tasks(self):
        try:
            show_all = self.task_filter_combo.get_active_id() == "all"
            resp = self.client.send_command("list_tasks", include_completed=show_all)
            tasks = resp.get("tasks", [])

            self.task_list_store.clear()
            for t in tasks:
                self.task_list_store.append([
                    t["id"],
                    t["name"],
                    t.get("subject_name") or "Other",
                    t.get("target") or "-",
                    t.get("notes") or "",
                    bool(t["completed"]),
                ])

            # Update quick combo dropdown
            curr_active_id = self.task_combo.get_active_id()
            self.task_combo.handler_block_by_func(self._on_task_combo_changed)
            self.task_combo.remove_all()
            self.task_combo.append("0", "-- None (Free Study) --")
            curr_task = self.current_status.get("active_task")
            target_id = "0"
            for t in tasks:
                if not t["completed"]:
                    self.task_combo.append(str(t["id"]), f"{t['name']} [{t.get('subject_name','Other')}]")
                    if curr_task and curr_task["id"] == t["id"]:
                        target_id = str(t["id"])
            self.task_combo.set_active_id(target_id)
            self.task_combo.handler_unblock_by_func(self._on_task_combo_changed)

        except Exception:
            pass

    def refresh_stats(self):
        try:
            is_today = self.stats_date == datetime.date.today()
            date_str = self.stats_date.isoformat()
            self.lbl_stats_date.set_text(f"Today ({date_str})" if is_today else date_str)

            resp = self.client.send_command("get_stats", date=date_str)
            if resp.get("ok"):
                st = resp["stats"]
                self.val_focus_time.set_text(st["formatted_focus_time"])
                self.val_sessions.set_text(str(st["completed_sessions"]))
                self.val_tasks_done.set_text(str(st["completed_tasks"]))
                self.val_top_subject.set_text(st["top_subject"])

                # Clear and populate subjects breakdown
                for child in self.box_subjects_breakdown.get_children():
                    self.box_subjects_breakdown.remove(child)

                if st["by_subject"]:
                    for s in st["by_subject"]:
                        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                        hrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                        lbl_name = Gtk.Label(label=s["name"])
                        lbl_name.set_halign(Gtk.Align.START)
                        lbl_time = Gtk.Label(label=f"{s['formatted']} ({s['percentage']}%)")
                        lbl_time.set_halign(Gtk.Align.END)
                        hrow.pack_start(lbl_name, False, False, 0)
                        hrow.pack_end(lbl_time, False, False, 0)

                        pbar = Gtk.ProgressBar()
                        pbar.set_fraction(s["percentage"] / 100.0)

                        row.pack_start(hrow, False, False, 0)
                        row.pack_start(pbar, False, False, 0)
                        self.box_subjects_breakdown.pack_start(row, False, False, 2)
                    self.box_subjects_breakdown.show_all()
                else:
                    empty_lbl = Gtk.Label(label="No focus time recorded for this date.")
                    empty_lbl.set_halign(Gtk.Align.START)
                    self.box_subjects_breakdown.pack_start(empty_lbl, False, False, 0)
                    self.box_subjects_breakdown.show_all()

            # Past 7 Days History
            h_resp = self.client.send_command("get_history", days=7)
            if h_resp.get("ok"):
                self.history_store.clear()
                for h in h_resp.get("history", []):
                    self.history_store.append([
                        h["date"],
                        h["formatted_focus_time"],
                        h["completed_sessions"],
                        h["completed_tasks"],
                    ])

        except Exception:
            pass

    def refresh_settings(self):
        try:
            resp = self.client.send_command("get_settings")
            if resp.get("ok"):
                s = resp["settings"]
                self.spin_focus.set_value(s.get("focus_duration", 25))
                self.spin_short_break.set_value(s.get("short_break_duration", 5))
                self.spin_long_break.set_value(s.get("long_break_duration", 15))
                self.spin_sessions.set_value(s.get("sessions_before_long_break", 4))
                self.switch_auto_break.set_active(s.get("auto_start_breaks", False))
                self.switch_auto_focus.set_active(s.get("auto_start_focus", False))
                self.switch_notif.set_active(s.get("notifications_enabled", True))
                self.switch_sound.set_active(s.get("sound_enabled", True))
                self.spin_offset.set_value(s.get("panel_x_offset", 0))
        except Exception:
            pass

    def refresh_all(self):
        try:
            resp = self.client.send_command("status")
            if resp.get("ok"):
                self.update_status(resp["data"])
        except Exception:
            pass
        self.refresh_tasks()
        self.refresh_stats()
        self.refresh_settings()
