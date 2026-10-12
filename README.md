# Pomodoro Productivity Clock for Kali Linux

A functional, lightweight, native-styled Pomodoro productivity application engineered specifically for Kali Linux GNOME on Wayland.

---

## 1. System Inspection & Architecture Decisions

Before implementing the clock, your live laptop environment was inspected:
- **Operating System:** Kali Linux (Debian testing base)
- **Desktop Environment (`$XDG_CURRENT_DESKTOP`):** GNOME Shell 50.4
- **Session Type (`$XDG_SESSION_TYPE`):** Wayland with rootless XWayland on `:0`
- **Panel:** GNOME Shell top panel (`/usr/bin/gnome-shell --mode=user`)
- **System Clock:** Centered date and time indicator (`Main.panel.statusArea['dateMenu']`)
- **Display Geometry:** 1366 × 768 px, top bar height: 29 px (work area starts at `y=29`)

### Mandatory Implementation Hierarchy Chosen:
1. **Live Top-Panel Indicator (Fallback A / B Architecture - Active Immediately):**
   - Implemented as a borderless, transparent, always-on-top dock widget using `Gdk.WindowTypeHint.DOCK` and TrueColor RGBA transparency.
   - Positioned at `root_x = 486`, `root_y = 1`, width = 105 px, height = 32 px.
   - **Exact Placement:** Mathematically aligned **immediately to the LEFT** of the central system clock (`Mon Oct 12 ...`), remaining fully visible above Chrome, VS Code, terminals, and all applications.
   - Requires zero restarts of your current desktop session, protecting all your active terminal and browser sessions.
2. **Native GNOME Shell Extension (`pomodoro@antigravity.org` - Primary Architecture):**
   - Complete GNOME Shell 45–50 ESM extension (`metadata.json`, `extension.js`, `stylesheet.css`).
   - Hooks into `Main.panel._centerBox` and dynamically inserts itself at the index of `dateMenu` container via `Main.panel.addToStatusArea('pomodoro-indicator', this._indicator, dateMenuIndex, 'center')`.
   - Pre-installed and registered into `~/.local/share/gnome-shell/extensions/pomodoro@antigravity.org`.
3. **Unified Background Daemon & IPC Single Source of Truth:**
   - Both the top-panel indicator, the GNOME extension, and the CLI interface connect to the same Python background daemon (`pomodoro-daemon`) over a secure Unix domain socket (`/run/user/1000/pomodoro/pomodoro.sock`).
   - Monotonic clock timing (`time.monotonic()`) guarantees microsecond accuracy across system load, window switching, and sleep/resume without drifting or double-counting.
   - Local SQLite database (`~/.local/share/pomodoro/pomodoro.db`) persists all tasks, subjects, sessions, and daily statistics.

---

## 2. Quick Start & Launch Commands

### Start the application:
```bash
pomodoro-app
```
*(Or launch **Pomodoro Clock** from the Kali Linux Applications menu).*

### Check live status from terminal:
```bash
pomodoroctl status
```

### Stop the application and daemon:
```bash
pomodoro-app --stop
```

---

## 3. Top Panel Appearance & Mouse Controls

| State | Indicator Display | Visual Styling |
| :--- | :--- | :--- |
| **Idle** | `◷ FOCUS` | Minimalist dark pill matching GNOME Shell |
| **Focus Running** | `◷ 24:35` | Soft tomato-red highlight (`#e06c75`) |
| **Short Break** | `☕ 04:20` | Subtle sage green highlight (`#98c379`) |
| **Long Break** | `🌴 14:15` | Soft cyan/emerald highlight |
| **Paused** | `⏸ 24:35` | Warm amber highlight (`#e5c07b`) |

### Mouse Actions:
- **Left-Click Indicator:** Toggles the interactive companion popup window right below the indicator.
- **Right-Click Indicator:** Instantly toggles **Start / Pause** directly without opening the menu.

---

## 4. Interactive Companion Popup

Clicking the panel indicator opens a compact 4-tab control window:

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
   - Editable example subjects pre-configured:
     - `C++`
     - `Data Structures and Algorithms`
     - `Competitive Programming`
     - `Mathematics`
     - `Probability and Statistics`
     - `IIT Madras coursework`
     - `HFT preparation`
     - `Other`
   - Create new task with: Name, Subject, Target (e.g. *Solve 3 Codeforces problems*), and Notes.
   - `[ 🎯 Select for Timer ]` button to attribute focused study time to that task.
   - Mark complete or delete tasks.

3. **📊 Statistics Tab:**
   - Date navigation: *Previous Day*, *Today*, *Next Day*.
   - Real calculated metrics from SQLite:
     - Total focused study time today (e.g. `2h 30m`).
     - Completed focus sessions.
     - Completed tasks.
     - Top subject.
   - Subject breakdown: Detailed progress bars showing study minutes and percentages.
   - Recently completed tasks log.
   - Past 7 days history summary table.

4. **⚙ Settings Tab:**
   - Customizable durations:
     - Focus duration (default: 25 minutes).
     - Short break duration (default: 5 minutes).
     - Long break duration (default: 15 minutes).
     - Sessions before long break (default: 4 sessions).
   - Automation switches: Auto-start breaks, Auto-start focus sessions.
   - Alerts: Desktop notifications (`notify-send`) and audio alert chime toggle (`canberra-gtk-play` / `paplay`).
   - Panel Placement: Fine-tune horizontal offset in pixels (`+/- px`) with immediate live update.

---

## 5. Command-Line Interface (`pomodoroctl`)

You can control every aspect of the timer from any shell or terminal script:

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

## 6. Autostart Configuration

Per your instructions, **autostart is disabled by default**.

If you wish to have the Pomodoro Clock launch automatically upon login:

### To Enable Autostart:
```bash
mkdir -p ~/.config/autostart
cp ~/.local/share/applications/kali-pomodoro.desktop ~/.config/autostart/
```

### To Disable Autostart:
```bash
rm -f ~/.config/autostart/kali-pomodoro.desktop
```

---

## 7. Troubleshooting

- **Check if daemon is running:**
  ```bash
  pomodoro-app --status
  ```
- **Restart application:**
  ```bash
  pomodoro-app --restart
  ```
- **Inspect socket and database:**
  - Socket: `/run/user/1000/pomodoro/pomodoro.sock`
  - Database: `~/.local/share/pomodoro/pomodoro.db`
- **Adjust placement offset:**
  If you customize your GNOME date/time format (e.g., adding/removing weekday or seconds), open Settings in the popup and adjust `Horizontal offset adjustment` by a few pixels, or run:
  ```bash
  python3 -c "from pomodoro.ipc import IPCClient; IPCClient().send_command('update_settings', settings={'panel_x_offset': 10})"
  ```

---

## 8. Rollback & Uninstallation

To completely uninstall the application and restore your environment:
```bash
cd /home/kali/pomodoro-productivity-clock
./uninstall.sh
```

This will:
1. Terminate all running daemon and indicator processes.
2. Remove desktop shortcut and CLI symlinks from `~/.local/bin`.
3. Clean GNOME Shell extension files and unregister from `enabled-extensions`.
4. Clean runtime socket files.
5. Safely preserve your SQLite database at `~/.local/share/pomodoro/pomodoro.db` so your study history is never lost.
