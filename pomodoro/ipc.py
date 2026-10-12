"""Cross-platform IPC layer supporting Unix Domain Sockets and Localhost TCP Sockets.
Enables reliable communication across Linux, macOS, and Windows.
"""
import os
import sys
import json
import socket
import select
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

from pomodoro.config import SOCKET_PATH, PORT_FILE, DEFAULT_TCP_PORT, IS_WINDOWS


class IPCServer:
    def __init__(self, engine, socket_path: Optional[Path] = None, tcp_port: Optional[int] = None):
        self.engine = engine
        self.db = engine.db
        self.socket_path = socket_path or SOCKET_PATH
        self.requested_tcp_port = tcp_port
        self.tcp_port: Optional[int] = None

        self.running = False
        self.listen_sockets: List[socket.socket] = []
        self.unix_server_sock: Optional[socket.socket] = None
        self.tcp_server_sock: Optional[socket.socket] = None

        self.clients: List[socket.socket] = []
        self.subscribers: List[socket.socket] = []
        self.lock = threading.Lock()

        # Connect engine callbacks to broadcast
        self.engine.on_state_change = self._on_state_change
        self.engine.on_tick = self._on_tick

    def start(self):
        """Initializes sockets (Unix socket on POSIX, TCP localhost on all platforms)."""
        self.listen_sockets.clear()

        # 1. Start Unix Domain Socket (if on Unix / POSIX)
        if not IS_WINDOWS and hasattr(socket, "AF_UNIX"):
            if self.socket_path.exists():
                try:
                    test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    test_sock.connect(str(self.socket_path))
                    test_sock.close()
                    raise RuntimeError(f"Another instance is already running on {self.socket_path}")
                except (ConnectionRefusedError, FileNotFoundError):
                    self.socket_path.unlink(missing_ok=True)

            self.socket_path.parent.mkdir(parents=True, exist_ok=True)
            self.unix_server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.unix_server_sock.bind(str(self.socket_path))
            try:
                os.chmod(self.socket_path, 0o600)
            except Exception:
                pass
            self.unix_server_sock.listen(10)
            self.unix_server_sock.setblocking(False)
            self.listen_sockets.append(self.unix_server_sock)

        # 2. Start TCP Localhost Socket (for Windows and cross-platform clients)
        self.tcp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        ports_to_try = [self.requested_tcp_port] if self.requested_tcp_port else [DEFAULT_TCP_PORT, 0]
        bound = False
        for p in ports_to_try:
            try:
                self.tcp_server_sock.bind(("127.0.0.1", p))
                bound = True
                break
            except OSError:
                continue

        if bound:
            self.tcp_server_sock.listen(10)
            self.tcp_server_sock.setblocking(False)
            self.tcp_port = self.tcp_server_sock.getsockname()[1]
            try:
                PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
                PORT_FILE.write_text(str(self.tcp_port))
            except Exception:
                pass
            self.listen_sockets.append(self.tcp_server_sock)

        if not self.listen_sockets:
            raise RuntimeError("Failed to bind any IPC listening sockets (Unix or TCP).")

        self.running = True

    def stop(self):
        self.running = False
        with self.lock:
            for s in self.clients + self.subscribers:
                try:
                    s.close()
                except Exception:
                    pass
            self.clients.clear()
            self.subscribers.clear()

        for s in self.listen_sockets:
            try:
                s.close()
            except Exception:
                pass
        self.listen_sockets.clear()
        self.unix_server_sock = None
        self.tcp_server_sock = None

        if self.socket_path and self.socket_path.exists():
            try:
                self.socket_path.unlink(missing_ok=True)
            except Exception:
                pass

        if PORT_FILE.exists():
            try:
                PORT_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    def process_connections(self, timeout: float = 0.05):
        """Polls for new connections and incoming client commands."""
        if not self.running or not self.listen_sockets:
            return

        with self.lock:
            read_list = list(self.listen_sockets) + list(self.clients)

        try:
            readable, _, errored = select.select(read_list, [], read_list, timeout)
        except (ValueError, select.error):
            return

        for s in errored:
            self._disconnect(s)

        for s in readable:
            if s in self.listen_sockets:
                try:
                    client_sock, _ = s.accept()
                    client_sock.setblocking(False)
                    with self.lock:
                        self.clients.append(client_sock)
                except Exception:
                    pass
            else:
                try:
                    data = s.recv(4096)
                    if not data:
                        self._disconnect(s)
                        continue
                    self._handle_client_data(s, data.decode("utf-8"))
                except (ConnectionResetError, BrokenPipeError, OSError):
                    self._disconnect(s)
                except Exception:
                    pass

    def _disconnect(self, client_sock: socket.socket):
        with self.lock:
            if client_sock in self.clients:
                self.clients.remove(client_sock)
            if client_sock in self.subscribers:
                self.subscribers.remove(client_sock)
        try:
            client_sock.close()
        except Exception:
            pass

    def _handle_client_data(self, client_sock: socket.socket, raw_text: str):
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        for line in lines:
            try:
                msg = json.loads(line)
                response = self._dispatch_command(client_sock, msg)
                if response is not None:
                    resp_str = json.dumps(response) + "\n"
                    client_sock.sendall(resp_str.encode("utf-8"))
            except Exception as e:
                err_resp = {"ok": False, "error": str(e)}
                try:
                    client_sock.sendall((json.dumps(err_resp) + "\n").encode("utf-8"))
                except Exception:
                    pass

    def _dispatch_command(self, client_sock: socket.socket, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cmd = req.get("cmd")

        if cmd == "subscribe":
            with self.lock:
                if client_sock not in self.subscribers:
                    self.subscribers.append(client_sock)
            return {"ok": True, "event": "subscribed", "data": self.engine.get_status()}

        if cmd == "status":
            return {"ok": True, "data": self.engine.get_status()}

        if cmd == "start":
            self.engine.start()
            return {"ok": True, "data": self.engine.get_status()}

        if cmd == "pause":
            self.engine.pause()
            return {"ok": True, "data": self.engine.get_status()}

        if cmd == "resume":
            self.engine.resume()
            return {"ok": True, "data": self.engine.get_status()}

        if cmd == "toggle":
            self.engine.toggle()
            return {"ok": True, "data": self.engine.get_status()}

        if cmd == "reset":
            self.engine.reset()
            return {"ok": True, "data": self.engine.get_status()}

        if cmd == "skip":
            self.engine.skip()
            return {"ok": True, "data": self.engine.get_status()}

        if cmd == "set_task":
            task_id = req.get("task_id")
            self.engine.set_active_task(task_id)
            return {"ok": True, "data": self.engine.get_status()}

        if cmd == "list_tasks":
            inc = req.get("include_completed", True)
            tasks = self.db.list_tasks(include_completed=inc)
            return {"ok": True, "tasks": tasks}

        if cmd == "add_task":
            name = req.get("name", "")
            sub_id = req.get("subject_id")
            target = req.get("target")
            notes = req.get("notes")
            task_id = self.db.add_task(name, sub_id, target, notes)
            self._broadcast({"event": "tasks_changed"})
            return {"ok": True, "task_id": task_id}

        if cmd == "update_task":
            task_id = req.get("task_id")
            name = req.get("name")
            sub_id = req.get("subject_id")
            target = req.get("target")
            notes = req.get("notes")
            self.db.update_task(task_id, name, sub_id, target, notes)
            self._broadcast({"event": "tasks_changed"})
            return {"ok": True}

        if cmd == "complete_task":
            task_id = req.get("task_id")
            completed = req.get("completed", True)
            self.db.complete_task(task_id, completed)
            self._broadcast({"event": "tasks_changed"})
            return {"ok": True}

        if cmd == "delete_task":
            task_id = req.get("task_id")
            if self.engine.active_task_id == task_id:
                self.engine.set_active_task(None)
            self.db.delete_task(task_id)
            self._broadcast({"event": "tasks_changed"})
            return {"ok": True}

        if cmd == "list_subjects":
            subjects = self.db.list_subjects()
            return {"ok": True, "subjects": subjects}

        if cmd == "add_subject":
            name = req.get("name", "")
            color = req.get("color", "#61afef")
            sub_id = self.db.add_subject(name, color)
            self._broadcast({"event": "subjects_changed"})
            return {"ok": True, "subject_id": sub_id}

        if cmd == "delete_subject":
            sub_id = req.get("subject_id")
            self.db.delete_subject(sub_id)
            self._broadcast({"event": "subjects_changed"})
            return {"ok": True}

        if cmd == "get_stats":
            date_str = req.get("date")
            target_date = None
            if date_str:
                import datetime
                try:
                    target_date = datetime.date.fromisoformat(date_str)
                except ValueError:
                    pass
            stats = self.db.get_daily_stats(target_date)
            return {"ok": True, "stats": stats}

        if cmd == "get_history":
            days = req.get("days", 7)
            history = self.db.get_history(days)
            return {"ok": True, "history": history}

        if cmd == "get_settings":
            return {"ok": True, "settings": self.db.get_settings()}

        if cmd == "update_settings":
            updates = req.get("settings", {})
            self.db.update_settings(updates)
            self.engine.refresh_settings()
            self._broadcast({"event": "settings_changed", "settings": self.db.get_settings()})
            return {"ok": True, "settings": self.db.get_settings()}

        return {"ok": False, "error": f"Unknown command: {cmd}"}

    def _broadcast(self, msg: Dict[str, Any]):
        msg_str = json.dumps(msg) + "\n"
        encoded = msg_str.encode("utf-8")
        dead_socks = []

        with self.lock:
            subs = list(self.subscribers)

        for s in subs:
            try:
                s.sendall(encoded)
            except Exception:
                dead_socks.append(s)

        if dead_socks:
            with self.lock:
                for s in dead_socks:
                    if s in self.subscribers:
                        self.subscribers.remove(s)

    def _on_tick(self, status: Dict[str, Any]):
        self._broadcast({"event": "tick", "data": status})

    def _on_state_change(self, status: Dict[str, Any]):
        self._broadcast({"event": "state_change", "data": status})


class IPCClient:
    def __init__(self, socket_path: Optional[Path] = None, tcp_port: Optional[int] = None):
        self.socket_path = socket_path or SOCKET_PATH
        self.tcp_port = tcp_port
        self.sub_thread: Optional[threading.Thread] = None
        self.sub_running = False

    def _get_tcp_port(self) -> int:
        if self.tcp_port:
            return self.tcp_port
        if PORT_FILE.exists():
            try:
                return int(PORT_FILE.read_text().strip())
            except Exception:
                pass
        return DEFAULT_TCP_PORT

    def _connect(self, timeout: float = 2.0) -> socket.socket:
        """Connects via Unix socket (if on POSIX) or TCP localhost."""
        # 1. Try Unix domain socket first on POSIX platforms
        if not IS_WINDOWS and hasattr(socket, "AF_UNIX") and self.socket_path and self.socket_path.exists():
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect(str(self.socket_path))
                return s
            except Exception:
                try:
                    s.close()
                except Exception:
                    pass

        # 2. Try TCP Localhost
        port = self._get_tcp_port()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", port))
        return s

    def is_server_running(self) -> bool:
        try:
            with self._connect(timeout=0.5) as s:
                s.sendall(b'{"cmd": "status"}\n')
                data = s.recv(1024)
                return bool(data)
        except Exception:
            return False

    def send_command(self, cmd: str, timeout: float = 3.0, **kwargs) -> Dict[str, Any]:
        """Sends a single request command and returns parsed response."""
        payload = {"cmd": cmd, **kwargs}
        line = json.dumps(payload) + "\n"

        with self._connect(timeout=timeout) as s:
            s.sendall(line.encode("utf-8"))

            buffer = ""
            while True:
                chunk = s.recv(4096).decode("utf-8")
                if not chunk:
                    break
                buffer += chunk
                if "\n" in buffer:
                    first_line = buffer.split("\n")[0]
                    return json.loads(first_line)

        raise RuntimeError("No response received from Pomodoro service")

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> socket.socket:
        """Connects to socket and spawns background listener for pushed events."""
        sub_sock = self._connect(timeout=3.0)
        sub_sock.settimeout(None)
        sub_sock.sendall(b'{"cmd": "subscribe"}\n')

        def listener():
            self.sub_running = True
            buffer = ""
            while self.sub_running:
                try:
                    chunk = sub_sock.recv(4096).decode("utf-8")
                    if not chunk:
                        break
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line.strip():
                            try:
                                msg = json.loads(line)
                                callback(msg)
                            except Exception:
                                pass
                except Exception:
                    break
            self.sub_running = False

        self.sub_thread = threading.Thread(target=listener, daemon=True)
        self.sub_thread.start()
        return sub_sock
