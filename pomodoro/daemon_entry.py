"""Entry point for pomodoro-daemon console script."""
import os
import sys
import time
import signal
from pathlib import Path

from pomodoro.config import PID_FILE, SOCKET_PATH, PORT_FILE, INDICATOR_PID_FILE, IS_WINDOWS
from pomodoro.db import Database
from pomodoro.notify import Notifier
from pomodoro.engine import TimerEngine
from pomodoro.ipc import IPCServer


def stop_daemon():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        PID_FILE.unlink(missing_ok=True)

    if INDICATOR_PID_FILE.exists():
        try:
            pid = int(INDICATOR_PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        INDICATOR_PID_FILE.unlink(missing_ok=True)

    SOCKET_PATH.unlink(missing_ok=True)
    PORT_FILE.unlink(missing_ok=True)
    print("Pomodoro Clock stopped.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pomodoro Timer Daemon")
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--restart", action="store_true", help="Restart running daemon")
    parser.add_argument("--status", action="store_true", help="Check daemon running status")
    args = parser.parse_args()

    running_pid = None
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            running_pid = pid
        except (ValueError, OSError):
            PID_FILE.unlink(missing_ok=True)

    if args.status:
        if running_pid:
            print(f"Pomodoro daemon is running (PID {running_pid})")
            sys.exit(0)
        else:
            print("Pomodoro daemon is stopped")
            sys.exit(1)

    if args.stop or args.restart:
        stop_daemon()
        if args.stop:
            sys.exit(0)

    db = Database()
    notifier = Notifier()
    engine = TimerEngine(db=db, notifier=notifier)
    server = IPCServer(engine=engine)

    try:
        server.start()
    except Exception as e:
        print(f"Failed to start IPC server: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))
    except Exception:
        pass

    def handle_exit(signum, frame):
        server.stop()
        PID_FILE.unlink(missing_ok=True)
        PORT_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_exit)

    last_tick = time.monotonic()
    try:
        while server.running:
            server.process_connections(timeout=0.05)
            now = time.monotonic()
            if now - last_tick >= 1.0:
                engine.tick()
                last_tick = now
    finally:
        server.stop()
        PID_FILE.unlink(missing_ok=True)
        PORT_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
