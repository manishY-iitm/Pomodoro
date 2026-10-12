@echo off
echo === Installing Pomodoro Productivity Clock (Windows) ===
python -m pip install PyQt6
python -m pip install -e "%~dp0"
echo.
echo === Installation Complete ===
echo Launch with: pomodoro-app
echo CLI status:  pomodoroctl status
pause
