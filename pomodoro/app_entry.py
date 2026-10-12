"""Entry point for pomodoro-app console script."""
import sys
from pathlib import Path

# Run launcher main
from pomodoro.config import PID_FILE, INDICATOR_PID_FILE, SOCKET_PATH, PORT_FILE, IS_WINDOWS
from pomodoro.ipc import IPCClient

def main():
    import subprocess
    import argparse

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DAEMON_BIN = PROJECT_ROOT / "bin" / "pomodoro-daemon"
    INDICATOR_BIN = PROJECT_ROOT / "bin" / "pomodoro-indicator"
    CTL_BIN = PROJECT_ROOT / "bin" / "pomodoroctl"

    parser = argparse.ArgumentParser(description="Pomodoro Productivity Clock")
    parser.add_argument("--stop", action="store_true", help="Stop Pomodoro clock and daemon")
    parser.add_argument("--restart", action="store_true", help="Restart Pomodoro clock")
    parser.add_argument("--status", action="store_true", help="Check status")
    parser.add_argument("--menu", action="store_true", help="Open controls popup")
    parser.add_argument("--daemon-only", action="store_true", help="Start only the background timer daemon")
    parser.add_argument("--qt", action="store_true", help="Force PyQt GUI on any platform")
    args, unknown = parser.parse_known_args()

    if args.stop:
        from pomodoro.daemon_entry import stop_daemon
        stop_daemon()
        return

    if args.status:
        from pomodoro.cli import main as cli_main
        sys.argv = [sys.argv[0], "status"]
        cli_main()
        return

    # Start background daemon if needed
    client = IPCClient()
    if not client.is_server_running():
        if IS_WINDOWS:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen([sys.executable, str(DAEMON_BIN)], creationflags=creationflags)
        else:
            subprocess.Popen([sys.executable, str(DAEMON_BIN)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        import time
        for _ in range(40):
            time.sleep(0.05)
            if client.is_server_running():
                break

    if args.daemon_only:
        print("Pomodoro daemon is running.")
        return

    # Launch indicator
    extra_flags = ["--qt"] if args.qt else []
    if IS_WINDOWS:
        subprocess.call([sys.executable, str(INDICATOR_BIN)] + extra_flags)
    else:
        import os
        os.execv(sys.executable, [sys.executable, str(INDICATOR_BIN)] + extra_flags)

if __name__ == "__main__":
    main()
