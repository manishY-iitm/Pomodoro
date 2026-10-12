"""Pomodoro Timer Engine with monotonic clock, state transitions, and persistence."""
import time
import datetime
from typing import Optional, Dict, Any, Callable
from pomodoro.config import (
    STATE_IDLE,
    STATE_FOCUS,
    STATE_SHORT_BREAK,
    STATE_LONG_BREAK,
    STATE_PAUSED,
)
from pomodoro.db import Database
from pomodoro.notify import Notifier


class TimerEngine:
    def __init__(self, db: Database, notifier: Optional[Notifier] = None):
        self.db = db
        self.notifier = notifier or Notifier()

        # Engine state
        self.state = STATE_IDLE
        self.previous_state = STATE_FOCUS # State before pausing

        # Timing variables
        self.total_seconds = 25 * 60
        self.remaining_seconds = 25 * 60
        self.monotonic_start: Optional[float] = None
        self.session_wall_start: Optional[datetime.datetime] = None

        # Cycle tracking (number of completed focus sessions)
        self.cycle_count = 0

        # Active task
        self.active_task_id: Optional[int] = None

        # Callbacks for events
        self.on_state_change: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_tick: Optional[Callable[[Dict[str, Any]], None]] = None

        # Load initial configuration from DB
        self.refresh_settings()
        self.reset()

    def refresh_settings(self):
        self.settings = self.db.get_settings()
        self.focus_duration_sec = self.settings.get("focus_duration", 25) * 60
        self.short_break_sec = self.settings.get("short_break_duration", 5) * 60
        self.long_break_sec = self.settings.get("long_break_duration", 15) * 60
        self.sessions_before_long_break = self.settings.get("sessions_before_long_break", 4)

    def get_task_info(self) -> Optional[Dict[str, Any]]:
        if self.active_task_id:
            return self.db.get_task(self.active_task_id)
        return None

    def set_active_task(self, task_id: Optional[int]):
        self.active_task_id = task_id if (task_id and task_id > 0) else None
        self._trigger_state_change()

    def start(self):
        """Starts or resumes the current session."""
        self.refresh_settings()
        if self.state == STATE_PAUSED:
            self.state = self.previous_state
            self.monotonic_start = time.monotonic() - (self.total_seconds - self.remaining_seconds)
        elif self.state == STATE_IDLE:
            self.state = STATE_FOCUS
            self.total_seconds = self.focus_duration_sec
            self.remaining_seconds = self.total_seconds
            self.monotonic_start = time.monotonic()
            self.session_wall_start = datetime.datetime.now()
        elif self.state in (STATE_FOCUS, STATE_SHORT_BREAK, STATE_LONG_BREAK):
            if self.monotonic_start is None:
                self.monotonic_start = time.monotonic() - (self.total_seconds - self.remaining_seconds)
                self.session_wall_start = datetime.datetime.now()
        self._trigger_state_change()

    def pause(self):
        """Pauses running timer."""
        if self.state in (STATE_FOCUS, STATE_SHORT_BREAK, STATE_LONG_BREAK):
            self._update_remaining()
            self.previous_state = self.state
            self.state = STATE_PAUSED
            self.monotonic_start = None
            self._trigger_state_change()

    def resume(self):
        """Resumes timer if paused."""
        if self.state == STATE_PAUSED:
            self.start()

    def toggle(self):
        """Toggles between start/resume and pause."""
        if self.state in (STATE_FOCUS, STATE_SHORT_BREAK, STATE_LONG_BREAK):
            self.pause()
        else:
            self.start()

    def reset(self):
        """Resets the timer back to idle focus state."""
        self.refresh_settings()
        self.state = STATE_IDLE
        self.previous_state = STATE_FOCUS
        self.total_seconds = self.focus_duration_sec
        self.remaining_seconds = self.total_seconds
        self.monotonic_start = None
        self.session_wall_start = None
        self._trigger_state_change()

    def skip(self):
        """Skips the current interval to the next session."""
        self.refresh_settings()
        if self.state in (STATE_FOCUS, STATE_PAUSED) and self.previous_state == STATE_FOCUS:
            # Skip from focus to break
            self._complete_focus_session(skipped=True)
        elif self.state in (STATE_SHORT_BREAK, STATE_LONG_BREAK, STATE_PAUSED):
            # Skip break to focus
            self._setup_focus_session()
        else:
            # Idle -> Start break or reset
            self._setup_short_break()
        self._trigger_state_change()

    def tick(self) -> Dict[str, Any]:
        """Called every second to update monotonic elapsed time and handle transitions."""
        if self.state in (STATE_FOCUS, STATE_SHORT_BREAK, STATE_LONG_BREAK) and self.monotonic_start is not None:
            self._update_remaining()
            if self.remaining_seconds <= 0:
                self._handle_interval_completion()

        status = self.get_status()
        if self.on_tick:
            self.on_tick(status)
        return status

    def _update_remaining(self):
        if self.monotonic_start is not None:
            elapsed = time.monotonic() - self.monotonic_start
            self.remaining_seconds = max(0, int(round(self.total_seconds - elapsed)))

    def _handle_interval_completion(self):
        """Triggered when remaining_seconds reaches zero."""
        self.monotonic_start = None

        if self.state == STATE_FOCUS:
            self._complete_focus_session(skipped=False)
        elif self.state in (STATE_SHORT_BREAK, STATE_LONG_BREAK):
            self._complete_break_session(skipped=False)

    def _complete_focus_session(self, skipped: bool):
        now = datetime.datetime.now()
        wall_start = self.session_wall_start or (now - datetime.timedelta(seconds=self.total_seconds))
        duration = self.total_seconds if not skipped else (self.total_seconds - self.remaining_seconds)

        if duration > 10: # Only record meaningful study intervals (> 10s)
            self.db.record_session(
                session_type="focus",
                start_time=wall_start,
                end_time=now,
                duration_seconds=duration,
                task_id=self.active_task_id,
                completed_normally=not skipped,
            )

        if not skipped:
            self.cycle_count += 1
            # Notify user
            if self.settings.get("notifications_enabled", True):
                msg = f"Completed {self.cycle_count} focus session(s). Take a break!"
                task = self.get_task_info()
                if task:
                    msg = f"Completed session for '{task['name']}'. Take a break!"
                self.notifier.notify(
                    title="Focus Session Complete! 🍅",
                    body=msg,
                    sound=self.settings.get("sound_enabled", True),
                    icon="alarm",
                )

        # Decide break type
        if self.cycle_count > 0 and (self.cycle_count % self.sessions_before_long_break == 0):
            self._setup_long_break()
        else:
            self._setup_short_break()

        # Check auto-start break
        if not skipped and self.settings.get("auto_start_breaks", False):
            self.start()

    def _complete_break_session(self, skipped: bool):
        now = datetime.datetime.now()
        wall_start = self.session_wall_start or (now - datetime.timedelta(seconds=self.total_seconds))
        duration = self.total_seconds if not skipped else (self.total_seconds - self.remaining_seconds)

        if duration > 10:
            self.db.record_session(
                session_type="short_break" if self.state == STATE_SHORT_BREAK else "long_break",
                start_time=wall_start,
                end_time=now,
                duration_seconds=duration,
                task_id=self.active_task_id,
                completed_normally=not skipped,
            )

        if not skipped and self.settings.get("notifications_enabled", True):
            self.notifier.notify(
                title="Break Finished! ☕",
                body="Ready to get back to focused work?",
                sound=self.settings.get("sound_enabled", True),
                icon="alarm",
            )

        self._setup_focus_session()

        # Check auto-start focus
        if not skipped and self.settings.get("auto_start_focus", False):
            self.start()

    def _setup_focus_session(self):
        self.state = STATE_FOCUS
        self.previous_state = STATE_FOCUS
        self.total_seconds = self.focus_duration_sec
        self.remaining_seconds = self.total_seconds
        self.monotonic_start = None
        self.session_wall_start = None

    def _setup_short_break(self):
        self.state = STATE_SHORT_BREAK
        self.previous_state = STATE_SHORT_BREAK
        self.total_seconds = self.short_break_sec
        self.remaining_seconds = self.total_seconds
        self.monotonic_start = None
        self.session_wall_start = None

    def _setup_long_break(self):
        self.state = STATE_LONG_BREAK
        self.previous_state = STATE_LONG_BREAK
        self.total_seconds = self.long_break_sec
        self.remaining_seconds = self.total_seconds
        self.monotonic_start = None
        self.session_wall_start = None

    def _trigger_state_change(self):
        status = self.get_status()
        if self.on_state_change:
            self.on_state_change(status)

    def get_status(self) -> Dict[str, Any]:
        """Generates comprehensive status dictionary for clients and indicators."""
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        formatted_time = f"{mins:02d}:{secs:02d}"

        # Progress fraction 0.0 to 1.0
        if self.total_seconds > 0:
            progress = (self.total_seconds - self.remaining_seconds) / self.total_seconds
        else:
            progress = 0.0

        # Panel label & icon
        if self.state == STATE_IDLE:
            panel_label = "FOCUS"
            panel_icon = "◷"
        elif self.state == STATE_FOCUS:
            panel_label = formatted_time
            panel_icon = "◷"
        elif self.state == STATE_SHORT_BREAK:
            panel_label = formatted_time
            panel_icon = "☕"
        elif self.state == STATE_LONG_BREAK:
            panel_label = formatted_time
            panel_icon = "🌴"
        elif self.state == STATE_PAUSED:
            panel_label = formatted_time
            panel_icon = "⏸"
        else:
            panel_label = formatted_time
            panel_icon = "◷"

        task = self.get_task_info()

        return {
            "state": self.state,
            "previous_state": self.previous_state,
            "remaining_seconds": self.remaining_seconds,
            "total_seconds": self.total_seconds,
            "formatted_time": formatted_time,
            "progress": round(progress, 3),
            "cycle_count": self.cycle_count,
            "sessions_before_long_break": self.sessions_before_long_break,
            "panel_label": panel_label,
            "panel_icon": panel_icon,
            "panel_text": f"{panel_icon} {panel_label}",
            "active_task": task,
            "settings": self.settings,
        }
