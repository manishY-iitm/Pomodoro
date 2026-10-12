"""Top-panel dock indicator widget positioned immediately to the left of the system clock."""
import os
import sys
import threading
import gi

# Ensure X11 backend for reliable absolute DOCK window placement under Mutter/XWayland
os.environ["GDK_BACKEND"] = "x11"
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango

from pomodoro.ipc import IPCClient


class PanelIndicatorWindow(Gtk.Window):
    def __init__(self, ipc_client: IPCClient, toggle_popup_cb):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.client = ipc_client
        self.toggle_popup_cb = toggle_popup_cb

        # Window properties for top-panel dock integration
        self.set_title("PomodoroPanelIndicator")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_role("panel-indicator")

        # Transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # Connect screen size change to reposition dynamically
        screen.connect("size-changed", self._on_screen_changed)

        # UI elements
        self.button = Gtk.Button()
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        self.button.connect("clicked", self._on_button_clicked)
        self.button.connect("button-press-event", self._on_button_press)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.icon_label = Gtk.Label(label="◷")
        self.text_label = Gtk.Label(label="FOCUS")

        box.pack_start(self.icon_label, False, False, 0)
        box.pack_start(self.text_label, False, False, 0)
        self.button.add(box)
        self.add(self.button)

        # Apply dark panel CSS matching GNOME Shell style
        self._apply_css()

        # Cache geometry and offset
        self.panel_x_offset = 0
        self.indicator_width = 105
        self.indicator_height = 26

        self.set_size_request(self.indicator_width, self.indicator_height)

        # Fetch initial status
        self._update_from_daemon()

        # Position window immediately to the left of the central clock
        self.reposition()

    def _apply_css(self):
        css_provider = Gtk.CssProvider()
        css = b"""
        window {
            background-color: transparent;
        }
        button {
            background-color: rgba(20, 20, 20, 0.4);
            color: #e6e6e6;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 999px;
            padding: 1px 10px;
            margin: 1px 0px;
            font-family: Cantarell, "Segoe UI", Sans;
            font-size: 11pt;
            font-weight: bold;
            box-shadow: none;
            transition: all 120ms ease-in-out;
        }
        button:hover {
            background-color: rgba(255, 255, 255, 0.16);
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.2);
        }
        button:active {
            background-color: rgba(255, 255, 255, 0.25);
            color: #ffffff;
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
        top_bar_height = max(24, work.y) if work.y > 0 else 29

        # In GNOME Shell, dateMenu is centered at screen_width / 2.
        # Estimated width of 'Mon Oct 12 11:08:05' with padding is ~168px.
        center_x = screen_width // 2
        clock_width = 168
        clock_left = center_x - (clock_width // 2)

        # Place indicator immediately to the left of clock_left with 8px margin
        spacing = 8
        target_x = int(clock_left - self.indicator_width - spacing + self.panel_x_offset)
        # Center vertically in the top bar
        target_y = max(0, int((top_bar_height - self.indicator_height) / 2))

        self.move(target_x, target_y)

    def _on_screen_changed(self, screen):
        self.reposition()

    def _on_button_clicked(self, widget):
        if self.toggle_popup_cb:
            self.toggle_popup_cb()

    def _on_button_press(self, widget, event):
        # Right-click toggles timer start/pause directly
        if event.button == 3:
            try:
                self.client.send_command("toggle")
            except Exception:
                pass
            return True
        return False

    def update_status(self, status: dict):
        state = status.get("state", "IDLE")
        panel_label = status.get("panel_label", "FOCUS")
        panel_icon = status.get("panel_icon", "◷")

        self.icon_label.set_text(panel_icon)
        self.text_label.set_text(panel_label)

        # Update styling class
        context = self.button.get_style_context()
        for cls in ["state-focus", "state-break", "state-paused"]:
            context.remove_class(cls)

        if state == "FOCUS":
            context.add_class("state-focus")
        elif state in ("SHORT_BREAK", "LONG_BREAK"):
            context.add_class("state-break")
        elif state == "PAUSED":
            context.add_class("state-paused")

        # Update tooltip
        task = status.get("active_task")
        task_str = f"Task: {task['name']}" if task else "No task active"
        tooltip = f"Pomodoro: {state} ({panel_label})\n{task_str}\nLeft-click: Open Menu\nRight-click: Toggle Start/Pause"
        self.button.set_tooltip_text(tooltip)

        # Check if panel offset changed in settings
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
