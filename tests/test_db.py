"""Unit tests for the SQLite database persistence module."""
import unittest
import tempfile
import datetime
from pathlib import Path
from pomodoro.db import Database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_pomodoro.db"
        self.db = Database(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_settings(self):
        settings = self.db.get_settings()
        self.assertEqual(settings["focus_duration"], 25)
        self.assertEqual(settings["short_break_duration"], 5)
        self.assertEqual(settings["long_break_duration"], 15)
        self.assertEqual(settings["sessions_before_long_break"], 4)
        self.assertEqual(settings["notifications_enabled"], True)
        self.assertEqual(settings["sound_enabled"], True)
        self.assertEqual(settings["autostart"], False)

    def test_update_settings(self):
        self.db.update_settings({"focus_duration": 30, "auto_start_breaks": True})
        settings = self.db.get_settings()
        self.assertEqual(settings["focus_duration"], 30)
        self.assertEqual(settings["auto_start_breaks"], True)

    def test_default_subjects(self):
        subjects = self.db.list_subjects()
        names = [s["name"] for s in subjects]
        self.assertIn("C++", names)
        self.assertIn("Competitive Programming", names)
        self.assertIn("Data Structures and Algorithms", names)
        self.assertIn("IIT Madras coursework", names)

    def test_task_crud(self):
        sub_id = self.db.list_subjects()[0]["id"]
        task_id = self.db.add_task(
            name="Solve 3 Codeforces problems",
            subject_id=sub_id,
            target="3 problems",
            notes="Div 2 Round",
        )
        self.assertGreater(task_id, 0)

        task = self.db.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task["name"], "Solve 3 Codeforces problems")
        self.assertEqual(task["target"], "3 problems")
        self.assertEqual(task["completed"], 0)

        # Complete task
        self.db.complete_task(task_id, True)
        task = self.db.get_task(task_id)
        self.assertEqual(task["completed"], 1)
        self.assertIsNotNone(task["completed_at"])

    def test_session_recording_and_stats(self):
        now = datetime.datetime.now()
        start = now - datetime.timedelta(minutes=25)
        sub_id = self.db.list_subjects()[0]["id"]

        # Record focus session of 25m (1500 seconds)
        sess_id = self.db.record_session(
            session_type="focus",
            start_time=start,
            end_time=now,
            duration_seconds=1500,
            subject_id=sub_id,
            completed_normally=True,
        )
        self.assertGreater(sess_id, 0)

        # Record break session of 5m (300 seconds) - should NOT count towards focus stats
        self.db.record_session(
            session_type="short_break",
            start_time=now,
            end_time=now + datetime.timedelta(minutes=5),
            duration_seconds=300,
            subject_id=sub_id,
            completed_normally=True,
        )

        stats = self.db.get_daily_stats(datetime.date.today())
        self.assertEqual(stats["total_focus_seconds"], 1500)
        self.assertEqual(stats["formatted_focus_time"], "25m")
        self.assertEqual(stats["completed_sessions"], 1)
        self.assertEqual(stats["top_subject"], "C++")
        self.assertEqual(len(stats["by_subject"]), 1)
        self.assertEqual(stats["by_subject"][0]["percentage"], 100.0)


if __name__ == "__main__":
    unittest.main()
