# Installation script for Pomodoro Productivity Clock on Windows
# Run with: powershell -ExecutionPolicy Bypass -File install.ps1

Write-Host "=== Installing Pomodoro Productivity Clock (Windows) ===" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# 1. Install dependencies
Write-Host "Checking / Installing dependencies..." -ForegroundColor Yellow
python -m pip install --quiet PyQt6

# 2. Install package in editable mode so CLI commands are globally available
Write-Host "Registering commands (pomodoroctl, pomodoro-app)..." -ForegroundColor Yellow
python -m pip install --quiet -e $ScriptDir

# 3. Create Windows Desktop Shortcut
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
    $ShortcutPath = Join-Path $DesktopPath "Pomodoro Clock.lnk"
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = (Join-Path $ScriptDir "bin\pomodoro-app.bat")
    $Shortcut.WorkingDirectory = $ScriptDir
    $Shortcut.Description = "Pomodoro Productivity Clock"
    $Shortcut.Save()
    Write-Host "✓ Desktop shortcut created: $ShortcutPath" -ForegroundColor Green
} catch {
    Write-Host "Note: Could not create desktop shortcut automatically." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host "Launch immediately with:  pomodoro-app" -ForegroundColor Cyan
Write-Host "Or check status with:     pomodoroctl status" -ForegroundColor Cyan
Write-Host "System tray indicator will appear beside your Windows taskbar clock!" -ForegroundColor Yellow
