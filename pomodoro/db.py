"""SQLite persistence layer for Pomodoro timer, tasks, subjects, sessions and statistics."""
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pomodoro.config import (
    DB_PATH,
    DEFAULT_FOCUS_MINUTES,
    DEFAULT_SHORT_BREAK_MINUTES,
    DEFAULT_LONG_BREAK_MINUTES,
    DEFAULT_SESSIONS_BEFORE_LONG_BREAK,
    DEFAULT_SUBJECTS,
)


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    import contextlib

    @contextlib.contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Creates tables and populates default settings and subjects if empty."""
        with self._connection() as conn:
            cur = conn.cursor()

            # Settings table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Subjects table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#61afef',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tasks table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
                    target TEXT,
                    notes TEXT,
                    completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            # Sessions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_type TEXT NOT NULL, -- 'focus', 'short_break', 'long_break'
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
                    completed_normally INTEGER DEFAULT 1,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Default settings
            defaults = {
                "focus_duration": str(DEFAULT_FOCUS_MINUTES),
                "short_break_duration": str(DEFAULT_SHORT_BREAK_MINUTES),
                "long_break_duration": str(DEFAULT_LONG_BREAK_MINUTES),
                "sessions_before_long_break": str(DEFAULT_SESSIONS_BEFORE_LONG_BREAK),
                "auto_start_breaks": "0",
                "auto_start_focus": "0",
                "notifications_enabled": "1",
                "sound_enabled": "1",
                "panel_x_offset": "0",
                "autostart": "0",
            }
            for k, v in defaults.items():
                cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

            # Default subjects
            for sub_name, color in DEFAULT_SUBJECTS:
                cur.execute(
                    "INSERT OR IGNORE INTO subjects (name, color) VALUES (?, ?)",
                    (sub_name, color),
                )

            conn.commit()

    # --- Settings ---
    def get_settings(self) -> Dict[str, Any]:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM settings")
            rows = cur.fetchall()
            settings = {}
            for r in rows:
                key, val = r["key"], r["value"]
                if key in (
                    "focus_duration",
                    "short_break_duration",
                    "long_break_duration",
                    "sessions_before_long_break",
                    "panel_x_offset",
                ):
                    try:
                        settings[key] = int(val)
                    except ValueError:
                        settings[key] = 0
                elif key in (
                    "auto_start_breaks",
                    "auto_start_focus",
                    "notifications_enabled",
                    "sound_enabled",
                    "autostart",
                ):
                    settings[key] = val == "1"
                else:
                    settings[key] = val
            return settings

    def update_settings(self, updates: Dict[str, Any]):
        with self._connection() as conn:
            cur = conn.cursor()
            for k, v in updates.items():
                if isinstance(v, bool):
                    str_v = "1" if v else "0"
                else:
                    str_v = str(v)
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?",
                    (k, str_v, str_v),
                )
            conn.commit()

    # --- Subjects ---
    def list_subjects(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, color, created_at FROM subjects ORDER BY id ASC")
            return [dict(r) for r in cur.fetchall()]

    def add_subject(self, name: str, color: str = "#61afef") -> int:
        name = name.strip()
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO subjects (name, color) VALUES (?, ?)", (name, color))
            conn.commit()
            return cur.lastrowid

    def delete_subject(self, subject_id: int):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
            conn.commit()

    # --- Tasks ---
    def add_task(
        self,
        name: str,
        subject_id: Optional[int] = None,
        target: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        name = name.strip()
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO tasks (name, subject_id, target, notes, completed)
                VALUES (?, ?, ?, ?, 0)
            """,
                (name, subject_id, target, notes),
            )
            conn.commit()
            return cur.lastrowid

    def update_task(
        self,
        task_id: int,
        name: Optional[str] = None,
        subject_id: Optional[int] = None,
        target: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        with self._connection() as conn:
            cur = conn.cursor()
            fields = []
            vals = []
            if name is not None:
                fields.append("name = ?")
                vals.append(name.strip())
            if subject_id is not None:
                fields.append("subject_id = ?")
                vals.append(subject_id if subject_id > 0 else None)
            if target is not None:
                fields.append("target = ?")
                vals.append(target)
            if notes is not None:
                fields.append("notes = ?")
                vals.append(notes)
            if fields:
                vals.append(task_id)
                cur.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", vals)
                conn.commit()

    def complete_task(self, task_id: int, completed: bool = True):
        now = datetime.datetime.now().isoformat() if completed else None
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE tasks SET completed = ?, completed_at = ? WHERE id = ?",
                (1 if completed else 0, now, task_id),
            )
            conn.commit()

    def delete_task(self, task_id: int):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

    def list_tasks(self, include_completed: bool = True) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cur = conn.cursor()
            query = """
                SELECT t.id, t.name, t.subject_id, s.name as subject_name, s.color as subject_color,
                       t.target, t.notes, t.completed, t.created_at, t.completed_at
                FROM tasks t
                LEFT JOIN subjects s ON t.subject_id = s.id
            """
            if not include_completed:
                query += " WHERE t.completed = 0"
            query += " ORDER BY t.completed ASC, t.id DESC"
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT t.id, t.name, t.subject_id, s.name as subject_name, s.color as subject_color,
                       t.target, t.notes, t.completed, t.created_at, t.completed_at
                FROM tasks t
                LEFT JOIN subjects s ON t.subject_id = s.id
                WHERE t.id = ?
            """,
                (task_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    # --- Sessions & History ---
    def record_session(
        self,
        session_type: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        duration_seconds: int,
        task_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        completed_normally: bool = True,
    ) -> int:
        """Records a completed or stopped session in the database."""
        # Auto-resolve subject from task if not explicitly passed
        if task_id and not subject_id:
            task = self.get_task(task_id)
            if task and task.get("subject_id"):
                subject_id = task["subject_id"]

        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sessions (
                    session_type, start_time, end_time, duration_seconds,
                    task_id, subject_id, completed_normally
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_type,
                    start_time.isoformat(),
                    end_time.isoformat(),
                    duration_seconds,
                    task_id,
                    subject_id,
                    1 if completed_normally else 0,
                ),
            )
            conn.commit()
            return cur.lastrowid

    # --- Statistics ---
    def get_daily_stats(self, target_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """Calculates accurate daily statistics for the specified date (defaults to today)."""
        target = target_date or datetime.date.today()
        day_start = f"{target.isoformat()} 00:00:00"
        day_end = f"{target.isoformat()} 23:59:59"

        with self._connection() as conn:
            cur = conn.cursor()

            # 1. Focus time & completed focus sessions
            # Only count 'focus' session types
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(duration_seconds), 0) as total_seconds,
                    COUNT(CASE WHEN completed_normally = 1 THEN 1 END) as completed_sessions
                FROM sessions
                WHERE session_type = 'focus'
                  AND datetime(end_time) >= datetime(?)
                  AND datetime(end_time) <= datetime(?)
            """,
                (day_start, day_end),
            )
            focus_row = cur.fetchone()
            total_focus_seconds = focus_row["total_seconds"]
            completed_sessions = focus_row["completed_sessions"]

            # 2. Completed tasks on this day
            cur.execute(
                """
                SELECT COUNT(*) as completed_tasks
                FROM tasks
                WHERE completed = 1
                  AND completed_at IS NOT NULL
                  AND datetime(completed_at) >= datetime(?)
                  AND datetime(completed_at) <= datetime(?)
            """,
                (day_start, day_end),
            )
            task_row = cur.fetchone()
            completed_tasks = task_row["completed_tasks"]

            # 3. Focus time by subject
            cur.execute(
                """
                SELECT
                    COALESCE(s.name, 'Unassigned') as subject_name,
                    COALESCE(s.color, '#abb2bf') as color,
                    SUM(sess.duration_seconds) as subject_seconds
                FROM sessions sess
                LEFT JOIN subjects s ON sess.subject_id = s.id
                WHERE sess.session_type = 'focus'
                  AND datetime(sess.end_time) >= datetime(?)
                  AND datetime(sess.end_time) <= datetime(?)
                GROUP BY subject_name
                ORDER BY subject_seconds DESC
            """,
                (day_start, day_end),
            )
            subject_rows = cur.fetchall()
            by_subject = []
            top_subject = "None"
            if subject_rows:
                top_subject = subject_rows[0]["subject_name"]
                for r in subject_rows:
                    sec = r["subject_seconds"]
                    pct = round((sec / total_focus_seconds * 100), 1) if total_focus_seconds > 0 else 0
                    by_subject.append({
                        "name": r["subject_name"],
                        "color": r["color"],
                        "seconds": sec,
                        "formatted": self.format_duration(sec),
                        "percentage": pct,
                    })

            # 4. Recently completed tasks
            cur.execute(
                """
                SELECT t.id, t.name, COALESCE(s.name, 'Other') as subject_name, t.completed_at
                FROM tasks t
                LEFT JOIN subjects s ON t.subject_id = s.id
                WHERE t.completed = 1
                ORDER BY t.completed_at DESC
                LIMIT 5
            """
            )
            recent_tasks = [dict(r) for r in cur.fetchall()]

            return {
                "date": target.isoformat(),
                "total_focus_seconds": total_focus_seconds,
                "formatted_focus_time": self.format_duration(total_focus_seconds),
                "completed_sessions": completed_sessions,
                "completed_tasks": completed_tasks,
                "top_subject": top_subject,
                "by_subject": by_subject,
                "recent_tasks": recent_tasks,
            }

    def get_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Returns statistics summary for the past N days."""
        today = datetime.date.today()
        history = []
        for i in range(days):
            d = today - datetime.timedelta(days=i)
            stats = self.get_daily_stats(d)
            history.append(stats)
        return history

    @staticmethod
    def format_duration(seconds: int) -> str:
        """Formats seconds into human readable '2h 30m' or '25m'."""
        if seconds <= 0:
            return "0m"
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        if hours > 0:
            if mins > 0:
                return f"{hours}h {mins}m"
            return f"{hours}h"
        return f"{mins}m"
