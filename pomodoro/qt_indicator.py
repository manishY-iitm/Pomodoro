"""Cross-platform System Tray Indicator using PyQt6 / PyQt5.
Integrates with the Windows Taskbar, macOS Menu Bar, and Linux System Tray.
"""
import sys
from pathlib import Path
from typing import Optional

try:
    from PyQt6 import QtWidgets, QtCore, QtGui
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
    from PyQt6.QtCore import Qt, QTimer
    QT_VERSION = 6
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
    from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
    from PyQt5.QtCore import Qt, QTimer
    QT_VERSION = 5

from pomodoro.ipc import IPCClient
from pomodoro.qt_ui import PomodoroCompanionPopup


class QtAppIndicator:
    def __init__(self, ipc_client: Optional[IPCClient] = None, popup: Optional[PomodoroCompanionPopup] = None):
        self.client = ipc_client or IPCClient()
        self.popup = popup or PomodoroCompanionPopup(ipc_client=self.client)

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._create_icon("#abb2bf"))
        self.tray.setToolTip("Pomodoro: IDLE (25:00)")

        self._build_menu()
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self._update_from_daemon()

    def _create_icon(self, color_hex: str) -> QIcon:
        """Draws a clean, high-DPI vector-style round indicator icon."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        if QT_VERSION == 6:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        else:
            painter.setRenderHint(QPainter.Antialiasing)

        # Draw tomato clock circle
        painter.setBrush(QColor(color_hex))
        painter.setPen(QColor(0, 0, 0, 0))
        painter.drawEllipse(4, 4, 56, 56)

        # Draw small inner highlight
        painter.setBrush(QColor(255, 255, 255, 60))
        painter.drawEllipse(12, 12, 16, 16)

        painter.end()
        return QIcon(pixmap)

    def _build_menu(self):
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #21252b;
                color: #abb2bf;
                border: 1px solid #282c34;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #353b45;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #282c34;
                margin: 4px 8px;
            }
        """)

        # Status header
        self.action_header = QAction("Pomodoro: IDLE (25:00)", self.menu)
        self.action_header.setEnabled(False)
        self.menu.addAction(self.action_header)

        # Task label
        self.action_task = QAction("Task: (Free Study)", self.menu)
        self.action_task.setEnabled(False)
        self.menu.addAction(self.action_task)

        self.menu.addSeparator()

        # Controls
        self.action_toggle = QAction("▶ Start Timer", self.menu)
        self.action_toggle.triggered.connect(lambda: self._send_cmd("toggle"))
        self.menu.addAction(self.action_toggle)

        action_reset = QAction("⟲ Reset Interval", self.menu)
        action_reset.triggered.connect(lambda: self._send_cmd("reset"))
        self.menu.addAction(action_reset)

        action_skip = QAction("⏭ Skip Session", self.menu)
        action_skip.triggered.connect(lambda: self._send_cmd("skip"))
        self.menu.addAction(action_skip)

        self.menu.addSeparator()

        # Open Companion Window
        action_open = QAction("📋 Open Controls & Tasks...", self.menu)
        action_open.triggered.connect(self._toggle_popup)
        self.menu.addAction(action_open)

        self.menu.addSeparator()

        # Quit
        action_quit = QAction("✕ Exit", self.menu)
        action_quit.triggered.connect(self._exit_app)
        self.menu.addAction(action_quit)

        self.tray.setContextMenu(self.menu)

    def _on_tray_activated(self, reason):
        # Trigger popup on single click or double click
        trigger_reason = QSystemTrayIcon.ActivationReason.Trigger if QT_VERSION == 6 else QSystemTrayIcon.Trigger
        double_click = QSystemTrayIcon.ActivationReason.DoubleClick if QT_VERSION == 6 else QSystemTrayIcon.DoubleClick
        if reason in (trigger_reason, double_click):
            self._toggle_popup()

    def _toggle_popup(self):
        if self.popup.isVisible():
            self.popup.hide()
        else:
            self.popup.refresh_all()
            self.popup.show()
            self.popup.raise_()
            self.popup.activateWindow()

    def _exit_app(self):
        self.tray.hide()
        QApplication.quit()

    def _send_cmd(self, cmd: str):
        try:
            self.client.send_command(cmd)
        except Exception:
            pass

    def update_status(self, status: dict):
        state = status.get("state", "IDLE")
        formatted = status.get("formatted_time", "25:00")
        panel_label = status.get("panel_label", "FOCUS")
        panel_icon = status.get("panel_icon", "◷")

        # Choose color for tray icon
        if state == "FOCUS":
            icon_color = "#e06c75"
        elif state in ("SHORT_BREAK", "LONG_BREAK"):
            icon_color = "#98c379"
        elif state == "PAUSED":
            icon_color = "#e5c07b"
        else:
            icon_color = "#abb2bf"

        self.tray.setIcon(self._create_icon(icon_color))
        self.tray.setToolTip(f"Pomodoro: {state} ({formatted})")

        # Update menu items
        self.action_header.setText(f"Pomodoro: {state} ({formatted})")
        if state in ("FOCUS", "SHORT_BREAK", "LONG_BREAK"):
            self.action_toggle.setText("⏸ Pause Timer")
        elif state == "PAUSED":
            self.action_toggle.setText("▶ Resume Timer")
        else:
            self.action_toggle.setText("▶ Start Timer")

        task = status.get("active_task")
        if task:
            self.action_task.setText(f"Task: {task['name']}")
        else:
            self.action_task.setText("Task: (Free Study)")

        # Sync companion popup if open
        if self.popup.isVisible():
            self.popup.update_status(status)

    def _update_from_daemon(self):
        try:
            resp = self.client.send_command("status")
            if resp.get("ok"):
                self.update_status(resp["data"])
        except Exception:
            pass
