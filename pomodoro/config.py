"""Configuration constants and default settings for Pomodoro Productivity Clock.
Fully cross-platform for Windows, macOS, and Linux.
"""
import os
import sys
import tempfile
from pathlib import Path

# Platform detection
IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

APP_NAME = "pomodoro"
APP_TITLE = "Pomodoro Productivity Clock"

# Cross-platform base directories
HOME_DIR = Path.home()

if IS_WINDOWS:
    _local_app_data = Path(os.environ.get("LOCALAPPDATA", HOME_DIR / "AppData" / "Local"))
    DATA_DIR = _local_app_data / "Pomodoro"
    CONFIG_DIR = _local_app_data / "Pomodoro" / "config"
    RUNTIME_DIR = Path(tempfile.gettempdir()) / "Pomodoro"
elif IS_MACOS:
    _app_support = HOME_DIR / "Library" / "Application Support" / "Pomodoro"
    DATA_DIR = _app_support
    CONFIG_DIR = _app_support / "config"
    RUNTIME_DIR = HOME_DIR / "Library" / "Caches" / "Pomodoro"
else: # Linux / BSD
    DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME_DIR / ".local" / "share")) / "pomodoro"
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME_DIR / ".config")) / "pomodoro"
    
    # Safe runtime dir lookup without assuming os.getuid()
    _uid = os.getuid() if hasattr(os, "getuid") else 1000
    _run_user_dir = Path(f"/run/user/{_uid}")
    if "XDG_RUNTIME_DIR" in os.environ:
        RUNTIME_DIR = Path(os.environ["XDG_RUNTIME_DIR"]) / "pomodoro"
    elif _run_user_dir.exists():
        RUNTIME_DIR = _run_user_dir / "pomodoro"
    else:
        RUNTIME_DIR = Path(tempfile.gettempdir()) / f"pomodoro-{_uid}"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "pomodoro.db"
SOCKET_PATH = RUNTIME_DIR / "pomodoro.sock"
PORT_FILE = RUNTIME_DIR / "pomodoro.port"
PID_FILE = RUNTIME_DIR / "pomodoro.pid"
INDICATOR_PID_FILE = RUNTIME_DIR / "indicator.pid"
STATE_FILE = RUNTIME_DIR / "state.json"

# TCP port for cross-platform IPC (especially Windows & non-Unix environments)
DEFAULT_TCP_PORT = 45321

# Default timer durations (in minutes)
DEFAULT_FOCUS_MINUTES = 25
DEFAULT_SHORT_BREAK_MINUTES = 5
DEFAULT_LONG_BREAK_MINUTES = 15
DEFAULT_SESSIONS_BEFORE_LONG_BREAK = 4

# Session states
STATE_IDLE = "IDLE"
STATE_FOCUS = "FOCUS"
STATE_SHORT_BREAK = "SHORT_BREAK"
STATE_LONG_BREAK = "LONG_BREAK"
STATE_PAUSED = "PAUSED"

# Default subjects
DEFAULT_SUBJECTS = [
    ("C++", "#61afef"),
    ("Data Structures and Algorithms", "#98c379"),
    ("Competitive Programming", "#e5c07b"),
    ("Mathematics", "#e06c75"),
    ("Probability and Statistics", "#c678dd"),
    ("IIT Madras coursework", "#56b6c2"),
    ("HFT preparation", "#d19a66"),
    ("Other", "#abb2bf"),
]
