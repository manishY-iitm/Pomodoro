"""Cross-platform Companion GUI Window using PyQt6/PyQt5.
Runs on Windows, macOS, and Linux with the identical dark theme and feature set.
"""
import sys
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from PyQt6 import QtWidgets, QtCore, QtGui
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QProgressBar, QComboBox,
        QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QSpinBox,
        QCheckBox, QTabWidget, QScrollArea, QFrame, QMessageBox, QAbstractItemView
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QDate
    from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QPainter
    QT_VERSION = 6
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QProgressBar, QComboBox,
        QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QSpinBox,
        QCheckBox, QTabWidget, QScrollArea, QFrame, QMessageBox, QAbstractItemView
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDate
    from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QPainter
    QT_VERSION = 5

from pomodoro.ipc import IPCClient


def _align(horizontal: str = "left", vertical: str = "center"):
    h = getattr(Qt.AlignmentFlag if QT_VERSION == 6 else Qt, f"Align{horizontal.capitalize()}")
    v = getattr(Qt.AlignmentFlag if QT_VERSION == 6 else Qt, f"Align{vertical.capitalize()}")
    return h | v


DARK_STYLESHEET = """
QMainWindow, QWidget#centralWidget {
    background-color: #1e222b;
    color: #abb2bf;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Cantarell", sans-serif;
}
QTabWidget::pane {
    border: 1px solid #282c34;
    background-color: #1e222b;
}
QTabBar::tab {
    background-color: #21252b;
    color: #7f848e;
    padding: 8px 18px;
    font-weight: bold;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    background-color: #1e222b;
    color: #61afef;
    border-bottom: 2px solid #61afef;
}
QLabel {
    color: #abb2bf;
}
QPushButton {
    background-color: #282c34;
    color: #abb2bf;
    border: 1px solid #3e4451;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #353b45;
    color: #ffffff;
}
QPushButton#btnPrimary {
    background-color: #98c379;
    color: #1e222b;
    border: none;
}
QPushButton#btnPrimary:hover {
    background-color: #a3cc85;
}
QPushButton#btnDanger {
    background-color: #e06c75;
    color: #ffffff;
    border: none;
}
QPushButton#btnDanger:hover {
    background-color: #e88289;
}
QFrame#card {
    background-color: #21252b;
    border: 1px solid #282c34;
    border-radius: 8px;
    padding: 12px;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #181a1f;
    color: #ffffff;
    border: 1px solid #3e4451;
    border-radius: 4px;
    padding: 5px 8px;
}
QTableWidget {
    background-color: #21252b;
    color: #abb2bf;
    gridline-color: #282c34;
    border: 1px solid #282c34;
    border-radius: 6px;
}
QHeaderView::section {
    background-color: #181a1f;
    color: #7f848e;
    padding: 6px;
    font-weight: bold;
    border: none;
}
QProgressBar {
    border: 1px solid #282c34;
    border-radius: 5px;
    text-align: center;
    background-color: #181a1f;
    color: #ffffff;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #61afef;
    border-radius: 4px;
}
QCheckBox {
    color: #abb2bf;
}
"""


class PomodoroCompanionPopup(QMainWindow):
    status_updated = pyqtSignal(dict)

    def __init__(self, ipc_client: Optional[IPCClient] = None, on_settings_changed_cb=None):
        super().__init__()
        self.client = ipc_client or IPCClient()
        self.on_settings_changed_cb = on_settings_changed_cb

        self.setWindowTitle("Pomodoro Productivity Clock")
        self.resize(500, 580)
        self.setStyleSheet(DARK_STYLESHEET)

        self.current_status: Dict[str, Any] = {}
        self.stats_date = datetime.date.today()

        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        header_title = QLabel("🍅 Pomodoro Productivity Clock")
        header_title.setStyleSheet("font-size: 15pt; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Notebook tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Timer Controls
        self.tab_timer = self._build_timer_tab()
        self.tabs.addTab(self.tab_timer, "⏱ Timer")

        # Tab 2: Tasks
        self.tab_tasks = self._build_tasks_tab()
        self.tabs.addTab(self.tab_tasks, "📋 Tasks")

        # Tab 3: Statistics
        self.tab_stats = self._build_stats_tab()
        self.tabs.addTab(self.tab_stats, "📊 Statistics")

        # Tab 4: Settings
        self.tab_settings = self._build_settings_tab()
        self.tabs.addTab(self.tab_settings, "⚙ Settings")

    # ==================== TAB 1: TIMER ====================
    def _build_timer_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Top row: State pill & cycle
        top_row = QHBoxLayout()
        self.state_badge = QLabel("IDLE")
        self.state_badge.setStyleSheet(
            "font-size: 10pt; font-weight: bold; padding: 4px 12px; border-radius: 12px; "
            "background-color: rgba(171, 178, 191, 0.15); color: #abb2bf; border: 1px solid rgba(171, 178, 191, 0.3);"
        )
        self.cycle_label = QLabel("Session 0 of 4")
        self.cycle_label.setStyleSheet("color: #7f848e; font-weight: bold;")

        top_row.addWidget(self.state_badge)
        top_row.addStretch()
        top_row.addWidget(self.cycle_label)
        layout.addLayout(top_row)

        # Large countdown display
        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(_align("center", "center"))
        self.time_label.setStyleSheet("font-size: 46pt; font-weight: bold; color: #ffffff;")
        layout.addWidget(self.time_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Action Buttons: Reset, Toggle, Skip
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_reset = QPushButton("⟲ Reset")
        self.btn_reset.clicked.connect(lambda: self._send_cmd("reset"))

        self.btn_toggle = QPushButton("▶ Start")
        self.btn_toggle.setObjectName("btnPrimary")
        self.btn_toggle.clicked.connect(lambda: self._send_cmd("toggle"))

        self.btn_skip = QPushButton("⏭ Skip")
        self.btn_skip.clicked.connect(lambda: self._send_cmd("skip"))

        btn_box.addStretch()
        btn_box.addWidget(self.btn_reset)
        btn_box.addWidget(self.btn_toggle)
        btn_box.addWidget(self.btn_skip)
        btn_box.addStretch()
        layout.addLayout(btn_box)

        # Active Task Card
        task_card = QFrame()
        task_card.setObjectName("card")
        tc_layout = QVBoxLayout(task_card)
        tc_layout.setSpacing(6)

        lbl_task_title = QLabel("CURRENT STUDY TASK")
        lbl_task_title.setStyleSheet("font-size: 8pt; font-weight: bold; color: #7f848e;")
        tc_layout.addWidget(lbl_task_title)

        self.active_task_name = QLabel("No task selected")
        self.active_task_name.setStyleSheet("font-size: 11pt; font-weight: bold; color: #ffffff;")
        tc_layout.addWidget(self.active_task_name)

        self.active_task_details = QLabel("Select a task below or study freely")
        self.active_task_details.setStyleSheet("font-size: 9pt; color: #7f848e;")
        tc_layout.addWidget(self.active_task_details)

        # Quick task switch combo
        quick_row = QHBoxLayout()
        self.task_combo = QComboBox()
        self.task_combo.addItem("-- None (Free Study) --", 0)
        self.task_combo.currentIndexChanged.connect(self._on_task_combo_changed)
        quick_row.addWidget(self.task_combo, 1)

        self.btn_complete_active = QPushButton("✓ Mark Done")
        self.btn_complete_active.clicked.connect(self._on_complete_active_task)
        quick_row.addWidget(self.btn_complete_active)
        tc_layout.addLayout(quick_row)

        layout.addWidget(task_card)
        layout.addStretch()
        return w

    # ==================== TAB 2: TASKS ====================
    def _build_tasks_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Top bar: Filter & Add button
        top_bar = QHBoxLayout()
        self.task_filter_combo = QComboBox()
        self.task_filter_combo.addItem("Pending Tasks", "pending")
        self.task_filter_combo.addItem("All Tasks (including Done)", "all")
        self.task_filter_combo.currentIndexChanged.connect(lambda: self.refresh_tasks())
        top_bar.addWidget(self.task_filter_combo, 1)

        btn_show_add = QPushButton("+ New Task")
        btn_show_add.clicked.connect(self._on_toggle_add_task_panel)
        top_bar.addWidget(btn_show_add)
        layout.addLayout(top_bar)

        # Collapsible New Task Box
        self.add_task_box = QFrame()
        self.add_task_box.setObjectName("card")
        self.add_task_box.setVisible(False)
        at_layout = QVBoxLayout(self.add_task_box)
        at_layout.setSpacing(8)

        lbl_at_title = QLabel("CREATE NEW TASK")
        lbl_at_title.setStyleSheet("font-size: 8pt; font-weight: bold; color: #7f848e;")
        at_layout.addWidget(lbl_at_title)

        self.entry_task_name = QLineEdit()
        self.entry_task_name.setPlaceholderText("Task name (e.g. Solve 3 Codeforces problems)")
        at_layout.addWidget(self.entry_task_name)

        row_fields = QHBoxLayout()
        self.combo_subject = QComboBox()
        row_fields.addWidget(self.combo_subject, 1)

        self.entry_target = QLineEdit()
        self.entry_target.setPlaceholderText("Target (e.g. 3 problems)")
        row_fields.addWidget(self.entry_target, 1)
        at_layout.addLayout(row_fields)

        self.entry_notes = QLineEdit()
        self.entry_notes.setPlaceholderText("Optional notes")
        at_layout.addWidget(self.entry_notes)

        btn_save_task = QPushButton("Save Task")
        btn_save_task.setObjectName("btnPrimary")
        btn_save_task.clicked.connect(self._on_save_new_task)
        at_layout.addWidget(btn_save_task)
        layout.addWidget(self.add_task_box)

        # Table for tasks
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(["Done", "Task Name", "Subject", "Target"])
        header = self.task_table.horizontalHeader()
        if QT_VERSION == 6:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        else:
            header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows if QT_VERSION == 6 else QAbstractItemView.SelectRows)
        self.task_table.cellChanged.connect(self._on_task_cell_changed)
        layout.addWidget(self.task_table, 1)

        # Bottom actions
        act_row = QHBoxLayout()
        btn_select_task = QPushButton("🎯 Select for Timer")
        btn_select_task.clicked.connect(self._on_select_tree_task)
        act_row.addWidget(btn_select_task, 1)

        btn_delete_task = QPushButton("🗑 Delete")
        btn_delete_task.setObjectName("btnDanger")
        btn_delete_task.clicked.connect(self._on_delete_tree_task)
        act_row.addWidget(btn_delete_task)
        layout.addLayout(act_row)

        return w

    # ==================== TAB 3: STATISTICS ====================
    def _build_stats_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Date navigator
        date_bar = QHBoxLayout()
        btn_prev = QPushButton("◀ Prev")
        btn_prev.clicked.connect(lambda: self._nav_date(-1))

        self.lbl_stats_date = QLabel("Today")
        self.lbl_stats_date.setAlignment(_align("center", "center"))
        self.lbl_stats_date.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff;")

        btn_today = QPushButton("Today")
        btn_today.clicked.connect(lambda: self._nav_date(0))

        btn_next = QPushButton("Next ▶")
        btn_next.clicked.connect(lambda: self._nav_date(1))

        date_bar.addWidget(btn_prev)
        date_bar.addWidget(btn_today)
        date_bar.addWidget(self.lbl_stats_date, 1)
        date_bar.addWidget(btn_next)
        layout.addLayout(date_bar)

        # 4 Stat Cards in 2x2 Grid
        grid = QGridLayout()
        grid.setSpacing(10)

        card1, self.val_focus_time = self._create_stat_card("TOTAL FOCUSED TIME", "0m")
        card2, self.val_sessions = self._create_stat_card("SESSIONS COMPLETED", "0")
        card3, self.val_tasks_done = self._create_stat_card("TASKS COMPLETED", "0")
        card4, self.val_top_subject = self._create_stat_card("TOP SUBJECT", "None")

        grid.addWidget(card1, 0, 0)
        grid.addWidget(card2, 0, 1)
        grid.addWidget(card3, 1, 0)
        grid.addWidget(card4, 1, 1)
        layout.addLayout(grid)

        # Subject breakdown
        lbl_subj = QLabel("FOCUS TIME BY SUBJECT")
        lbl_subj.setStyleSheet("font-size: 8pt; font-weight: bold; color: #7f848e; margin-top: 8px;")
        layout.addWidget(lbl_subj)

        self.box_subjects_card = QFrame()
        self.box_subjects_card.setObjectName("card")
        self.box_subjects_layout = QVBoxLayout(self.box_subjects_card)
        layout.addWidget(self.box_subjects_card)

        # Past 7 days history
        lbl_hist = QLabel("PAST 7 DAYS HISTORY")
        lbl_hist.setStyleSheet("font-size: 8pt; font-weight: bold; color: #7f848e; margin-top: 8px;")
        layout.addWidget(lbl_hist)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Date", "Focused Time", "Sessions", "Tasks Done"])
        h_header = self.history_table.horizontalHeader()
        if QT_VERSION == 6:
            h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        else:
            h_header.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.history_table)

        scroll.setWidget(w)
        return scroll

    def _create_stat_card(self, title: str, default_val: str):
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 8pt; font-weight: bold; color: #7f848e;")
        lbl_v = QLabel(default_val)
        lbl_v.setStyleSheet("font-size: 18pt; font-weight: bold; color: #61afef;")
        cl.addWidget(lbl_t)
        cl.addWidget(lbl_v)
        return card, lbl_v

    def _nav_date(self, offset: int):
        if offset == 0:
            self.stats_date = datetime.date.today()
        else:
            self.stats_date = self.stats_date + datetime.timedelta(days=offset)
        self.refresh_stats()

    # ==================== TAB 4: SETTINGS ====================
    def _build_settings_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # Durations Section
        lbl_dur = QLabel("TIMER DURATIONS")
        lbl_dur.setStyleSheet("font-size: 8pt; font-weight: bold; color: #7f848e;")
        layout.addWidget(lbl_dur)

        dur_card = QFrame()
        dur_card.setObjectName("card")
        dl = QVBoxLayout(dur_card)
        self.spin_focus = self._add_spin_row(dl, "Focus duration (minutes):", 1, 180, 25)
        self.spin_short_break = self._add_spin_row(dl, "Short break duration (minutes):", 1, 60, 5)
        self.spin_long_break = self._add_spin_row(dl, "Long break duration (minutes):", 1, 60, 15)
        self.spin_sessions = self._add_spin_row(dl, "Sessions before long break:", 1, 16, 4)
        layout.addWidget(dur_card)

        # Automation & Notifications
        lbl_notif = QLabel("AUTOMATION & NOTIFICATIONS")
        lbl_notif.setStyleSheet("font-size: 8pt; font-weight: bold; color: #7f848e;")
        layout.addWidget(lbl_notif)

        notif_card = QFrame()
        notif_card.setObjectName("card")
        nl = QVBoxLayout(notif_card)
        self.check_auto_break = QCheckBox("Auto-start breaks after focus")
        self.check_auto_focus = QCheckBox("Auto-start focus after break")
        self.check_notif = QCheckBox("Desktop notifications")
        self.check_sound = QCheckBox("Sound notification alert chime")
        nl.addWidget(self.check_auto_break)
        nl.addWidget(self.check_auto_focus)
        nl.addWidget(self.check_notif)
        nl.addWidget(self.check_sound)
        layout.addWidget(notif_card)

        btn_save = QPushButton("💾 Save Settings")
        btn_save.setObjectName("btnPrimary")
        btn_save.clicked.connect(self._on_save_settings)
        layout.addWidget(btn_save)
        layout.addStretch()

        scroll.setWidget(w)
        return scroll

    def _add_spin_row(self, parent_layout: QVBoxLayout, label_text: str, min_v: int, max_v: int, val: int) -> QSpinBox:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(val)
        row.addWidget(lbl, 1)
        row.addWidget(spin)
        parent_layout.addLayout(row)
        return spin

    # ==================== DATA SYNC & ACTIONS ====================
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

        self.time_label.setText(formatted)
        self.progress_bar.setValue(int(progress * 1000))

        dots = "●" * (cycle % target_cycle) + "○" * (target_cycle - (cycle % target_cycle))
        self.cycle_label.setText(f"Session {cycle % target_cycle + 1} of {target_cycle}  [{dots}]")

        self.state_badge.setText(state)
        if state == "FOCUS":
            self.state_badge.setStyleSheet(
                "font-size: 10pt; font-weight: bold; padding: 4px 12px; border-radius: 12px; "
                "background-color: rgba(224, 108, 117, 0.2); color: #e06c75; border: 1px solid rgba(224, 108, 117, 0.4);"
            )
            self.btn_toggle.setText("⏸ Pause")
        elif state in ("SHORT_BREAK", "LONG_BREAK"):
            self.state_badge.setStyleSheet(
                "font-size: 10pt; font-weight: bold; padding: 4px 12px; border-radius: 12px; "
                "background-color: rgba(152, 195, 121, 0.2); color: #98c379; border: 1px solid rgba(152, 195, 121, 0.4);"
            )
            self.btn_toggle.setText("⏸ Pause")
        elif state == "PAUSED":
            self.state_badge.setStyleSheet(
                "font-size: 10pt; font-weight: bold; padding: 4px 12px; border-radius: 12px; "
                "background-color: rgba(229, 192, 123, 0.2); color: #e5c07b; border: 1px solid rgba(229, 192, 123, 0.4);"
            )
            self.btn_toggle.setText("▶ Resume")
        else:
            self.state_badge.setStyleSheet(
                "font-size: 10pt; font-weight: bold; padding: 4px 12px; border-radius: 12px; "
                "background-color: rgba(171, 178, 191, 0.15); color: #abb2bf; border: 1px solid rgba(171, 178, 191, 0.3);"
            )
            self.btn_toggle.setText("▶ Start")

        task = status.get("active_task")
        if task:
            subj_str = f"[{task.get('subject_name', 'General')}] " if task.get("subject_name") else ""
            self.active_task_name.setText(f"{subj_str}{task['name']}")
            details = []
            if task.get("target"):
                details.append(f"Target: {task['target']}")
            if task.get("notes"):
                details.append(f"Notes: {task['notes']}")
            self.active_task_details.setText(" | ".join(details) if details else "Active Task")
            self.btn_complete_active.setEnabled(True)
        else:
            self.active_task_name.setText("No task selected")
            self.active_task_details.setText("Study freely or pick a task from the dropdown")
            self.btn_complete_active.setEnabled(False)

    def refresh_tasks(self):
        try:
            show_all = self.task_filter_combo.currentData() == "all"
            resp = self.client.send_command("list_tasks", include_completed=show_all)
            tasks = resp.get("tasks", [])

            self.task_table.blockSignals(True)
            self.task_table.setRowCount(len(tasks))
            for row, t in enumerate(tasks):
                # Checkbox item
                check_item = QTableWidgetItem()
                check_item.setFlags(
                    (Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    if QT_VERSION == 6 else (Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                )
                check_state = (Qt.CheckState.Checked if t["completed"] else Qt.CheckState.Unchecked) if QT_VERSION == 6 else (Qt.Checked if t["completed"] else Qt.Unchecked)
                check_item.setCheckState(check_state)
                check_item.setData(Qt.ItemDataRole.UserRole if QT_VERSION == 6 else Qt.UserRole, t["id"])
                self.task_table.setItem(row, 0, check_item)

                name_item = QTableWidgetItem(t["name"])
                name_item.setData(Qt.ItemDataRole.UserRole if QT_VERSION == 6 else Qt.UserRole, t["id"])
                self.task_table.setItem(row, 1, name_item)

                subj_item = QTableWidgetItem(t.get("subject_name") or "Other")
                self.task_table.setItem(row, 2, subj_item)

                target_item = QTableWidgetItem(t.get("target") or "-")
                self.task_table.setItem(row, 3, target_item)

            self.task_table.blockSignals(False)

            # Update quick combo dropdown
            self.task_combo.blockSignals(True)
            self.task_combo.clear()
            self.task_combo.addItem("-- None (Free Study) --", 0)
            curr_task = self.current_status.get("active_task")
            target_idx = 0
            for t in tasks:
                if not t["completed"]:
                    self.task_combo.addItem(f"{t['name']} [{t.get('subject_name','Other')}]", t["id"])
                    if curr_task and curr_task["id"] == t["id"]:
                        target_idx = self.task_combo.count() - 1
            self.task_combo.setCurrentIndex(target_idx)
            self.task_combo.blockSignals(False)

        except Exception:
            pass

    def _on_task_cell_changed(self, row: int, col: int):
        if col == 0:
            item = self.task_table.item(row, col)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole if QT_VERSION == 6 else Qt.UserRole)
                checked = item.checkState() == (Qt.CheckState.Checked if QT_VERSION == 6 else Qt.Checked)
                self.client.send_command("complete_task", task_id=task_id, completed=checked)
                self.refresh_tasks()
                self.refresh_stats()

    def _on_toggle_add_task_panel(self):
        vis = not self.add_task_box.isVisible()
        self.add_task_box.setVisible(vis)
        if vis:
            self._refresh_subject_combo()

    def _refresh_subject_combo(self):
        self.combo_subject.clear()
        try:
            resp = self.client.send_command("list_subjects")
            for s in resp.get("subjects", []):
                self.combo_subject.addItem(s["name"], s["id"])
        except Exception:
            pass

    def _on_save_new_task(self):
        name = self.entry_task_name.text().strip()
        if not name:
            return
        sub_id = self.combo_subject.currentData()
        target = self.entry_target.text().strip() or None
        notes = self.entry_notes.text().strip() or None

        self.client.send_command("add_task", name=name, subject_id=sub_id, target=target, notes=notes)
        self.entry_task_name.clear()
        self.entry_target.clear()
        self.entry_notes.clear()
        self.add_task_box.setVisible(False)
        self.refresh_tasks()

    def _on_select_tree_task(self):
        row = self.task_table.currentRow()
        if row >= 0:
            item = self.task_table.item(row, 1)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole if QT_VERSION == 6 else Qt.UserRole)
                self.client.send_command("set_task", task_id=task_id)
                self.tabs.setCurrentIndex(0)

    def _on_delete_tree_task(self):
        row = self.task_table.currentRow()
        if row >= 0:
            item = self.task_table.item(row, 1)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole if QT_VERSION == 6 else Qt.UserRole)
                self.client.send_command("delete_task", task_id=task_id)
                self.refresh_tasks()

    def _on_task_combo_changed(self, idx: int):
        task_id = self.task_combo.currentData()
        task_id = task_id if task_id != 0 else None
        curr_task = self.current_status.get("active_task")
        curr_id = curr_task["id"] if curr_task else None
        if task_id != curr_id:
            self.client.send_command("set_task", task_id=task_id)

    def _on_complete_active_task(self):
        curr_task = self.current_status.get("active_task")
        if curr_task:
            self.client.send_command("complete_task", task_id=curr_task["id"], completed=True)
            self.client.send_command("set_task", task_id=None)
            self.refresh_tasks()
            self.refresh_stats()

    def refresh_stats(self):
        try:
            is_today = self.stats_date == datetime.date.today()
            date_str = self.stats_date.isoformat()
            self.lbl_stats_date.setText(f"Today ({date_str})" if is_today else date_str)

            resp = self.client.send_command("get_stats", date=date_str)
            if resp.get("ok"):
                st = resp["stats"]
                self.val_focus_time.setText(st["formatted_focus_time"])
                self.val_sessions.setText(str(st["completed_sessions"]))
                self.val_tasks_done.setText(str(st["completed_tasks"]))
                self.val_top_subject.setText(st["top_subject"])

                # Clear and repopulate subject breakdown
                while self.box_subjects_layout.count():
                    item = self.box_subjects_layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

                if st["by_subject"]:
                    for s in st["by_subject"]:
                        r_layout = QVBoxLayout()
                        hdr = QHBoxLayout()
                        hdr.addWidget(QLabel(s["name"]))
                        hdr.addStretch()
                        lbl_t = QLabel(f"{s['formatted']} ({s['percentage']}%)")
                        lbl_t.setStyleSheet("color: #7f848e; font-weight: bold;")
                        hdr.addWidget(lbl_t)
                        r_layout.addLayout(hdr)

                        pb = QProgressBar()
                        pb.setRange(0, 100)
                        pb.setValue(int(s["percentage"]))
                        pb.setTextVisible(False)
                        pb.setStyleSheet(f"QProgressBar::chunk {{ background-color: {s.get('color', '#61afef')}; }}")
                        r_layout.addWidget(pb)
                        self.box_subjects_layout.addLayout(r_layout)
                else:
                    self.box_subjects_layout.addWidget(QLabel("No focus time recorded for this date."))

            # History table
            h_resp = self.client.send_command("get_history", days=7)
            if h_resp.get("ok"):
                hist = h_resp.get("history", [])
                self.history_table.setRowCount(len(hist))
                for row, h in enumerate(hist):
                    self.history_table.setItem(row, 0, QTableWidgetItem(h["date"]))
                    self.history_table.setItem(row, 1, QTableWidgetItem(h["formatted_focus_time"]))
                    self.history_table.setItem(row, 2, QTableWidgetItem(str(h["completed_sessions"])))
                    self.history_table.setItem(row, 3, QTableWidgetItem(str(h["completed_tasks"])))

        except Exception:
            pass

    def refresh_settings(self):
        try:
            resp = self.client.send_command("get_settings")
            if resp.get("ok"):
                s = resp["settings"]
                self.spin_focus.setValue(s.get("focus_duration", 25))
                self.spin_short_break.setValue(s.get("short_break_duration", 5))
                self.spin_long_break.setValue(s.get("long_break_duration", 15))
                self.spin_sessions.setValue(s.get("sessions_before_long_break", 4))
                self.check_auto_break.setChecked(s.get("auto_start_breaks", False))
                self.check_auto_focus.setChecked(s.get("auto_start_focus", False))
                self.check_notif.setChecked(s.get("notifications_enabled", True))
                self.check_sound.setChecked(s.get("sound_enabled", True))
        except Exception:
            pass

    def _on_save_settings(self):
        updates = {
            "focus_duration": self.spin_focus.value(),
            "short_break_duration": self.spin_short_break.value(),
            "long_break_duration": self.spin_long_break.value(),
            "sessions_before_long_break": self.spin_sessions.value(),
            "auto_start_breaks": self.check_auto_break.isChecked(),
            "auto_start_focus": self.check_auto_focus.isChecked(),
            "notifications_enabled": self.check_notif.isChecked(),
            "sound_enabled": self.check_sound.isChecked(),
        }
        resp = self.client.send_command("update_settings", settings=updates)
        if resp.get("ok"):
            if self.on_settings_changed_cb:
                self.on_settings_changed_cb(updates)
            QMessageBox.information(self, "Settings Saved", "Pomodoro preferences have been updated and persisted.")

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
