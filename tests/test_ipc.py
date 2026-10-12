"""Unit tests for the IPC server and client module."""
import unittest
import tempfile
import time
import threading
from pathlib import Path
from pomodoro.db import Database
from pomodoro.engine import TimerEngine
from pomodoro.ipc import IPCServer, IPCClient


class TestIPC(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_ipc.db"
        self.socket_path = Path(self.temp_dir.name) / "test_ipc.sock"
        self.db = Database(self.db_path)
        self.engine = TimerEngine(self.db)
        self.server = IPCServer(self.engine, self.socket_path)
        self.server.start()

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        time.sleep(0.05) # Allow socket to initialize

    def _run_server(self):
        while self.server.running:
            self.server.process_connections(0.02)
            time.sleep(0.01)

    def tearDown(self):
        self.server.stop()
        self.temp_dir.cleanup()

    def test_client_status_and_commands(self):
        client = IPCClient(self.socket_path)
        self.assertTrue(client.is_server_running())

        resp = client.send_command("status")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["data"]["state"], "IDLE")

        # Start timer
        resp = client.send_command("start")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["data"]["state"], "FOCUS")

        # Pause timer
        resp = client.send_command("pause")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["data"]["state"], "PAUSED")

        # Reset timer
        resp = client.send_command("reset")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["data"]["state"], "IDLE")

    def test_client_subscription(self):
        client = IPCClient(self.socket_path)
        received_events = []

        def on_event(event):
            received_events.append(event)

        sub_sock = client.subscribe(on_event)
        time.sleep(0.05)

        # Trigger tick
        self.engine.start()
        self.engine.tick()

        # Give small moment for broadcast
        time.sleep(0.1)
        sub_sock.close()

        self.assertGreater(len(received_events), 0)


if __name__ == "__main__":
    unittest.main()
