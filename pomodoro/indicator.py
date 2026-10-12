"""Top-panel indicator integration (AppIndicator beside the system clock)."""
import os
import sys
import threading
import gi

# Ensure GTK and AyatanaAppIndicator
gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import Gtk, AyatanaAppIndicator3, GLib

from pomodoro.ipc import IPCClient
from pomodoro.ui import PomodoroCompanionPopup


class PanelAppIndicator:
    def __init__(self, ipc_client: IPCClient):
        self.client = ipc_client
        self.popup = PomodoroCompanionPopup(ipc_client=self.client)

        # Create native top-bar AppIndicator
        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "kali-pomodoro-timer",
            "pomodoro",
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_label("◷ 25:00", " 25:00")

        self._build_menu()
        self._update_from_daemon()

    def _build_menu(self):
        self.menu = Gtk.Menu()

        self.item_header = Gtk.MenuItem(label="Pomodoro: IDLE (25:00)")
        self.menu.append(self.item_header)

        self.item_task = Gtk.MenuItem(label="Task: (None)")
        self.menu.append(self.item_task)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.item_toggle = Gtk.MenuItem(label="▶ Start Timer")
        self.item_toggle.connect("activate", lambda w: self._send_cmd("toggle"))
        self.menu.append(self.item_toggle)

        item_reset = Gtk.MenuItem(label="⟲ Reset Interval")
        item_reset.connect("activate", lambda w: self._send_cmd("reset"))
        self.menu.append(item_reset)

        item_skip = Gtk.MenuItem(label="⏭ Skip Session")
        item_skip.connect("activate", lambda w: self._send_cmd("skip"))
        self.menu.append(item_skip)

        self.menu.append(Gtk.SeparatorMenuItem())

        item_open = Gtk.MenuItem(label="📋 Open Controls & Tasks...")
        item_open.connect("activate", self._toggle_popup)
        self.menu.append(item_open)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def _toggle_popup(self, widget=None):
        if self.popup.get_visible():
            self.popup.hide()
        else:
            self.popup.refresh_all()
            self.popup.show_all()
            self.popup.present()

    def _send_cmd(self, cmd: str):
        try:
            self.client.send_command(cmd)
        except Exception:
            pass

    def update_status(self, status: dict):
        state = status.get("state", "IDLE")
        panel_label = status.get("panel_label", "FOCUS")
        panel_icon = status.get("panel_icon", "◷")
        formatted = status.get("formatted_time", "25:00")

        # Set panel label beside clock
        self.indicator.set_label(f" {panel_icon} {panel_label}", " 25:00")

        # Update menu items
        self.item_header.get_child().set_text(f"Pomodoro: {state} ({formatted})")
        if state in ("FOCUS", "SHORT_BREAK", "LONG_BREAK"):
            self.item_toggle.get_child().set_text("⏸ Pause Timer")
        elif state == "PAUSED":
            self.item_toggle.get_child().set_text("▶ Resume Timer")
        else:
            self.item_toggle.get_child().set_text("▶ Start Timer")

        task = status.get("active_task")
        if task:
            self.item_task.get_child().set_text(f"Task: {task['name']}")
        else:
            self.item_task.get_child().set_text("Task: (Free Study)")

        # Sync companion popup if open
        if self.popup.get_visible():
            self.popup.update_status(status)

    def _update_from_daemon(self):
        try:
            resp = self.client.send_command("status")
            if resp.get("ok"):
                self.update_status(resp["data"])
        except Exception:
            pass
