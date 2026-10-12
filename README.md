# 🍅 Pomodoro Productivity Clock (For Everyone)

A functional, lightweight, native-styled Pomodoro productivity application engineered to run seamlessly across **Windows**, **macOS**, and **Linux (including Kali Linux)**.

---

## 🌟 Supported Operating Systems & Indicator Placement

| Operating System | Tray / Indicator Placement | Backend Integration |
| :--- | :--- | :--- |
| **Windows 10 / 11** | **Taskbar System Tray** (right next to the clock) | Native Windows Tray + Qt Companion Window |
| **macOS** (Intel / M-Series) | **Top Menu Bar** (right next to the menu clock) | Native macOS Menu Bar + Qt Companion Window |
| **Kali Linux / GNOME** | **Top Panel Bar** (immediately to the left of clock) | GNOME Shell Extension / GTK / Qt |
| **Linux (KDE, XFCE, etc.)** | **Panel System Tray** (beside system clock) | Native Freedesktop System Tray + Qt |

---

## 🚀 Quick Installation

### On Windows (PowerShell):
Open PowerShell in the project directory and run:
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```
*(Or double-click `install.bat`)*

### On macOS / Linux (Terminal):
Open your terminal in the project directory and run:
```bash
./install.sh
```

### Universal Python Package Installation (Any OS):
```bash
pip install -e .
```
To enable the GUI and System Tray on Windows or macOS:
```bash
pip install PyQt6
```

---

## ⏱️ Quick Start & Controls

### Start the Application:
```bash
pomodoro-app
```
*(Or launch **Pomodoro Clock** from your Applications menu or Desktop shortcut).*

### Check Live Status from Terminal:
```bash
pomodoroctl status
```

### Stop Application & Background Daemon:
```bash
pomodoro-app --stop
```

---

## 🖥️ Indicator Appearance & Controls

| State | Indicator Display | Visual Highlight |
| :--- | :--- | :--- |
| **Idle** | `◷ FOCUS` | Minimalist dark badge |
| **Focus Running** | `◷ 24:35` | Soft tomato-red highlight (`#e06c75`) |
| **Short Break** | `☕ 04:20` | Subtle sage green highlight (`#98c379`) |
| **Long Break** | `🌴 14:15` | Soft cyan/emerald highlight |
| **Paused** | `⏸ 24:35` | Warm amber highlight (`#e5c07b`) |

### Mouse Actions:
- **Click Indicator:** Toggles the interactive companion popup window right below the indicator.
- **Right-Click Indicator:** Opens the quick action menu (Start, Pause, Reset, Skip, Tasks, Exit).

---

## 📋 Interactive Companion Popup (4 Tabs)

1. **⏱ Timer Tab:**
   - Prominent large countdown display (42pt typography).
   - Dynamic state pill (`[FOCUS]`, `[SHORT BREAK]`, `[LONG BREAK]`, `[PAUSED]`, `[IDLE]`).
   - Session cycle progress (e.g. `Session 1 of 4  [● ○ ○ ○]`).
   - Smooth visual progress bar showing elapsed percentage.
   - Quick action buttons: `[ ▶ Start / ⏸ Pause ]`, `[ ⟲ Reset ]`, `[ ⏭ Skip ]`.
   - Active study task card with subject badge and target.
   - Quick task selector dropdown + `[ ✓ Mark Done ]` button.

2. **📋 Tasks Tab:**
   - Task list with filter: *Pending Tasks* vs *All Tasks*.
   - Editable pre-configured subjects (`C++`, `Competitive Programming`, `Mathematics`, etc.).
   - Create new task with: Name, Subject, Target (e.g. *Solve 3 Codeforces problems*), and Notes.
   - `[ 🎯 Select for Timer ]` button to attribute focused study time to that task.
   - Mark complete or delete tasks.

3. **📊 Statistics Tab:**
   - Date navigation: *Previous Day*, *Today*, *Next Day*.
   - Calculated metrics from SQLite:
     - Total focused study time today (e.g. `2h 30m`).
     - Completed focus sessions.
     - Completed tasks.
     - Top subject.
   - Subject breakdown: Detailed progress bars showing study minutes and percentages.
   - Past 7 days history summary table.

4. **⚙ Settings Tab:**
   - Customizable durations (Focus, Short Break, Long Break, Cycles).
   - Automation switches (Auto-start breaks, Auto-start focus).
   - Native notifications and audio alert chime toggle.

---

## 💻 Command-Line Interface (`pomodoroctl`)

You can control every aspect of the timer from any shell (Bash, Zsh, PowerShell, CMD):

```bash
# Timer controls
pomodoroctl status          # Show rich summary of status, cycle, active task and stats
pomodoroctl start           # Start the focus countdown
pomodoroctl pause           # Pause the countdown
pomodoroctl resume          # Resume from paused state
pomodoroctl toggle          # Toggle between start/resume and pause
pomodoroctl reset           # Reset interval to beginning
pomodoroctl skip            # Skip directly to next session (focus -> break or break -> focus)

# Task management
pomodoroctl task list       # List all active tasks
pomodoroctl task list --all # List all tasks including completed
pomodoroctl task add "Solve 3 Codeforces problems" --subject "Competitive Programming" --target "3 problems"
pomodoroctl task select 1   # Set active task to ID 1
pomodoroctl task complete 1 # Mark task 1 as completed
pomodoroctl task clear      # Clear active task (free study)

# Statistics
pomodoroctl stats           # View today's detailed study statistics
pomodoroctl stats --date 2026-10-12
```

---

## 🏗️ Architecture & Cross-Platform Design

1. **Monotonic Clock Engine (`engine.py`):**
   Uses `time.monotonic()` to guarantee microsecond accuracy across system load, window switching, and sleep/resume without drifting or double-counting.
2. **Local SQLite Database (`db.py`):**
   Persists all tasks, subjects, sessions, and daily statistics into a local database file:
   - **Windows:** `%LOCALAPPDATA%\Pomodoro\pomodoro.db`
   - **macOS:** `~/Library/Application Support/Pomodoro/pomodoro.db`
   - **Linux:** `~/.local/share/pomodoro/pomodoro.db`
3. **Dual-Mode IPC Server (`ipc.py`):**
   Communicates over **Unix Domain Sockets** on Linux/macOS and **Localhost TCP (`127.0.0.1:45321`)** on Windows and cross-platform clients.
4. **Native Alerts (`notify.py`):**
   - **Windows:** PowerShell Toast & `winsound` chimes.
   - **macOS:** AppleScript notifications & `afplay` chimes.
   - **Linux:** `notify-send` & `canberra-gtk-play` / `paplay`.
5. **Adaptive UI Backends (`qt_ui.py` / `ui.py`):**
   Uses **PyQt6 / PyQt5** on Windows, macOS, and standard desktops, and **GTK3 / Ayatana** on GNOME Linux.
