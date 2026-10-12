"""Configuration constants and default settings for Kali Pomodoro Clock."""
import os
from pathlib import Path

# Base directories
APP_NAME = "kali-pomodoro"
APP_TITLE = "Pomodoro Productivity Clock"

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "pomodoro"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pomodoro"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "pomodoro"

DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "pomodoro.db"
SOCKET_PATH = RUNTIME_DIR / "pomodoro.sock"
PID_FILE = RUNTIME_DIR / "pomodoro.pid"
STATE_FILE = RUNTIME_DIR / "state.json"

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
