"""Top-panel dock and adjacent indicator widget positioned immediately beside the system clock."""
import os
import sys
import threading
import gi

# Force X11 backend for reliable absolute window placement under Mutter/XWayland
os.environ["GDK_BACKEND"] = "x11"
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango

try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3
    HAS_APP_INDICATOR = True
except (ValueError, ImportError):
    HAS_APP_INDICATOR = False

from pomodoro.ipc import IPCClient


class PanelIndicatorWindow(Gtk.Window):
    def __init__(self, ipc_client: IPCClient, toggle_popup_cb):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.client = ipc_client
        self.toggle_popup_cb = toggle_popup_cb

        # Window properties
        self.set_title("PomodoroPanelIndicator")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_role("panel-indicator")

        # Visual styling
        self._apply_css()

        # Connect screen size changes
        screen = self.get_screen()
        screen.connect("size-changed", self._on_screen_changed)

        # UI elements
        self.button = Gtk.Button()
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        self.button.connect("clicked", self._on_button_clicked)
        self.button.connect("button-press-event", self._on_button_press)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_border_width(2)

        self.icon_label = Gtk.Label(label="◷")
        self.text_label = Gtk.Label(label="FOCUS")
        self.task_sub_label = Gtk.Label(label="")
        self.task_sub_label.set_no_show_all(True)

        box.pack_start(self.icon_label, False, False, 0)
        box.pack_start(self.text_label, False, False, 0)
        box.pack_start(self.task_sub_label, False, False, 0)
        self.button.add(box)
        self.add(self.button)

        self.panel_x_offset = 0
        self.indicator_width = 125
        self.indicator_height = 28
        self.set_size_request(self.indicator_width, self.indicator_height)

        # Initialize AppIndicator if available (native top-bar integration)
        self.app_indicator = None
        if HAS_APP_INDICATOR:
            self._init_app_indicator()

        # Fetch initial state and position
        self._update_from_daemon()
        self.reposition()

    def _apply_css(self):
        css_provider = Gtk.CssProvider()
        css = b"""
        window {
            background-color: #1e222b;
            border: 1px solid rgba(97, 175, 239, 0.5);
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
        }
        button {
            background-color: #21252b;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 3px 10px;
            font-family: Cantarell, "Segoe UI", Sans;
            font-size: 11pt;
            font-weight: bold;
            box-shadow: none;
            transition: all 120ms ease-in-out;
        }
        button:hover {
            background-color: #282c34;
            color: #61afef;
        }
        button:active {
            background-color: #3e4452;
        }
        .state-focus {
            color: #e06c75;
        }
        .state-break {
            color: #98c379;
        }
        .state-paused {
            color: #e5c07b;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _init_app_indicator(self):
        try:
            self.app_indicator = AyatanaAppIndicator3.Indicator.new(
                "kali-pomodoro-timer",
                "pomodoro",
                AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self.app_indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
            self.app_indicator.set_label("◷ FOCUS", "25:00")

            menu = Gtk.Menu()

            self.menu_item_status = Gtk.MenuItem(label="Pomodoro: IDLE (25:00)")
            menu.append(self.menu_item_status)
            menu.append(Gtk.SeparatorMenuItem())

            self.menu_item_toggle = Gtk.MenuItem(label="▶ Start Timer")
            self.menu_item_toggle.connect("activate", lambda w: self._send_cmd("toggle"))
            menu.append(self.menu_item_toggle)

            item_reset = Gtk.MenuItem(label="⟲ Reset Interval")
            item_reset.connect("activate", lambda w: self._send_cmd("reset"))
            menu.append(item_reset)

            item_skip = Gtk.MenuItem(label="⏭ Skip Session")
            item_skip.connect("activate", lambda w: self._send_cmd("skip"))
            menu.append(item_skip)

            menu.append(Gtk.SeparatorMenuItem())

            item_open = Gtk.MenuItem(label="📋 Open Controls & Tasks...")
            item_open.connect("activate", lambda w: self._on_button_clicked(None))
            menu.append(item_open)

            menu.show_all()
            self.app_indicator.set_menu(menu)
        except Exception as e:
            self.app_indicator = None

    def _send_cmd(self, cmd: str):
        try:
            self.client.send_command(cmd)
        except Exception:
            pass

    def reposition(self):
        """Calculates exact coordinates to place indicator immediately to the LEFT of the system clock."""
        display = Gdk.Display.get_default()
        if not display:
            return
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if not monitor:
            return

        geom = monitor.get_geometry()
        work = monitor.get_workarea()

        screen_width = geom.width
        top_bar_height = max(28, work.y) if work.y > 0 else 29

        # System clock in GNOME Shell is centered at screen_width // 2.
        center_x = screen_width // 2
        clock_width = 168
        clock_left = center_x - (clock_width // 2)

        # Place indicator immediately to the left of clock_left
        spacing = 8
        target_x = int(clock_left - self.indicator_width - spacing + self.panel_x_offset)
        # Position immediately touching the bottom of the top panel (or 2px into client area)
        target_y = int(top_bar_height) + 1

        self.move(target_x, target_y)

    def _on_screen_changed(self, screen):
        self.reposition()

    def _on_button_clicked(self, widget):
        if self.toggle_popup_cb:
            self.toggle_popup_cb()

    def _on_button_press(self, widget, event):
        # Right-click toggles start/pause directly
        if event.button == 3:
            self._send_cmd("toggle")
            return True
        return False

    def update_status(self, status: dict):
        state = status.get("state", "IDLE")
        panel_label = status.get("panel_label", "FOCUS")
        panel_icon = status.get("panel_icon", "◷")
        formatted = status.get("formatted_time", "25:00")

        self.icon_label.set_text(panel_icon)
        self.text_label.set_text(panel_label)

        context = self.button.get_style_context()
        for cls in ["state-focus", "state-break", "state-paused"]:
            context.remove_class(cls)

        if state == "FOCUS":
            context.add_class("state-focus")
        elif state in ("SHORT_BREAK", "LONG_BREAK"):
            context.add_class("state-break")
        elif state == "PAUSED":
            context.add_class("state-paused")

        task = status.get("active_task")
        task_str = f"Task: {task['name']}" if task else "No task active"
        tooltip = f"Pomodoro: {state} ({panel_label})\n{task_str}\nLeft-click: Open Menu\nRight-click: Toggle Start/Pause"
        self.button.set_tooltip_text(tooltip)

        # Update AppIndicator if active
        if self.app_indicator:
            try:
                self.app_indicator.set_label(f" {panel_icon} {panel_label}", " 25:00")
                self.menu_item_status.get_child().set_text(f"Pomodoro: {state} ({formatted})")
                if state in ("FOCUS", "SHORT_BREAK", "LONG_BREAK"):
                    self.menu_item_toggle.get_child().set_text("⏸ Pause Timer")
                elif state == "PAUSED":
                    self.menu_item_toggle.get_child().set_text("▶ Resume Timer")
                else:
                    self.menu_item_toggle.get_child().set_text("▶ Start Timer")
            except Exception:
                pass

        # Check settings offset
        settings = status.get("settings", {})
        new_offset = settings.get("panel_x_offset", 0)
        if new_offset != self.panel_x_offset:
            self.panel_x_offset = new_offset
            self.reposition()

    def _update_from_daemon(self):
        try:
            resp = self.client.send_command("status")
            if resp.get("ok"):
                self.update_status(resp["data"])
        except Exception:
            pass
