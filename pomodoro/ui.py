"""UI selector: dynamically provides PomodoroCompanionPopup using GTK on Linux GNOME or PyQt across all platforms."""
import sys
from pomodoro.config import IS_LINUX

HAS_GTK = False
if IS_LINUX:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gtk
        HAS_GTK = True
    except Exception:
        HAS_GTK = False

if HAS_GTK:
    try:
        from pomodoro.gtk_ui import PomodoroCompanionPopup
    except Exception:
        from pomodoro.qt_ui import PomodoroCompanionPopup
else:
    from pomodoro.qt_ui import PomodoroCompanionPopup

__all__ = ["PomodoroCompanionPopup"]
