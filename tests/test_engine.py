"""Unit tests for the Pomodoro Timer Engine."""
import unittest
import tempfile
import time
from pathlib import Path
from pomodoro.db import Database
from pomodoro.engine import TimerEngine
from pomodoro.config import (
    STATE_IDLE,
    STATE_FOCUS,
    STATE_SHORT_BREAK,
    STATE_LONG_BREAK,
    STATE_PAUSED,
)


class DummyNotifier:
    def __init__(self):
        self.notifications = []

    def notify(self, title, body, urgency="normal", sound=True, icon=None):
        self.notifications.append((title, body))


class TestTimerEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_engine.db"
        self.db = Database(self.db_path)
        self.notifier = DummyNotifier()
        self.engine = TimerEngine(self.db, self.notifier)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_state(self):
        status = self.engine.get_status()
        self.assertEqual(status["state"], STATE_IDLE)
        self.assertEqual(status["remaining_seconds"], 25 * 60)
        self.assertEqual(status["panel_label"], "FOCUS")
        self.assertEqual(status["panel_icon"], "◷")

    def test_start_and_pause_and_resume(self):
        self.engine.start()
        status = self.engine.get_status()
        self.assertEqual(status["state"], STATE_FOCUS)

        # Pause
        self.engine.pause()
        status = self.engine.get_status()
        self.assertEqual(status["state"], STATE_PAUSED)
        self.assertEqual(status["panel_icon"], "⏸")

        # Resume
        self.engine.resume()
        status = self.engine.get_status()
        self.assertEqual(status["state"], STATE_FOCUS)

    def test_monotonic_tick(self):
        self.engine.start()
        # Mock monotonic start back 5 seconds
        self.engine.monotonic_start -= 5.0
        status = self.engine.tick()
        self.assertEqual(status["remaining_seconds"], (25 * 60) - 5)
        self.assertEqual(status["formatted_time"], "24:55")

    def test_reset(self):
        self.engine.start()
        self.engine.monotonic_start -= 100.0
        self.engine.tick()
        self.engine.reset()
        status = self.engine.get_status()
        self.assertEqual(status["state"], STATE_IDLE)
        self.assertEqual(status["remaining_seconds"], 25 * 60)

    def test_session_transition_to_short_break(self):
        self.engine.start()
        # Fast forward to end of focus session
        self.engine.monotonic_start -= (25 * 60 + 1)
        status = self.engine.tick()

        # Should transition to SHORT_BREAK (ready)
        self.assertEqual(status["state"], STATE_SHORT_BREAK)
        self.assertEqual(status["cycle_count"], 1)
        self.assertEqual(status["remaining_seconds"], 5 * 60)
        self.assertEqual(status["panel_icon"], "☕")
        self.assertEqual(len(self.notifier.notifications), 1)

    def test_transition_to_long_break_after_4_sessions(self):
        self.engine.sessions_before_long_break = 4
        self.engine.cycle_count = 3 # 3 completed so far

        self.engine.start()
        # Complete 4th session
        self.engine.monotonic_start -= (25 * 60 + 1)
        status = self.engine.tick()

        self.assertEqual(status["state"], STATE_LONG_BREAK)
        self.assertEqual(status["cycle_count"], 4)
        self.assertEqual(status["remaining_seconds"], 15 * 60)
        self.assertEqual(status["panel_icon"], "🌴")

    def test_skip(self):
        self.engine.start()
        self.engine.skip() # Skip focus
        status = self.engine.get_status()
        self.assertEqual(status["state"], STATE_SHORT_BREAK)

        self.engine.skip() # Skip break
        status = self.engine.get_status()
        self.assertEqual(status["state"], STATE_FOCUS)

    def test_active_task_association(self):
        task_id = self.db.add_task(name="Test Task", target="1")
        self.engine.set_active_task(task_id)

        status = self.engine.get_status()
        self.assertIsNotNone(status["active_task"])
        self.assertEqual(status["active_task"]["name"], "Test Task")


if __name__ == "__main__":
    unittest.main()
