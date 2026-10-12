#!/bin/bash
# Uninstall script for Kali Pomodoro Productivity Clock
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
EXT_UUID="pomodoro@antigravity.org"
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"

echo "=== Uninstalling Kali Pomodoro Productivity Clock ==="

# 1. Stop any running instances
"$SCRIPT_DIR/bin/pomodoro-app" --stop 2>/dev/null || true
pkill -f "pomodoro-indicator" 2>/dev/null || true
pkill -f "pomodoro-daemon" 2>/dev/null || true

# 2. Remove desktop launcher
rm -f "$APPS_DIR/kali-pomodoro.desktop"
update-desktop-database "$APPS_DIR" 2>/dev/null || true
echo "✓ Removed desktop shortcut"

# 3. Remove symlinks
rm -f "$BIN_DIR/pomodoro-app"
rm -f "$BIN_DIR/pomodoroctl"
echo "✓ Removed symlinks from $BIN_DIR"

# 4. Remove GNOME Shell extension
if [ -d "$EXT_DIR" ]; then
    rm -rf "$EXT_DIR"
    CURRENT_EXTS=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "")
    if [[ "$CURRENT_EXTS" == *"$EXT_UUID"* ]]; then
        NEW_EXTS=$(python3 -c "
import ast
curr = ast.literal_eval('''$CURRENT_EXTS''')
if '$EXT_UUID' in curr:
    curr.remove('$EXT_UUID')
print(curr)
")
        gsettings set org.gnome.shell enabled-extensions "$NEW_EXTS" 2>/dev/null || true
    fi
    echo "✓ Removed GNOME Shell extension"
fi

# 5. Clean runtime files
rm -rf "$XDG_RUNTIME_DIR/pomodoro" 2>/dev/null || rm -rf "/run/user/$(id -u)/pomodoro" 2>/dev/null || true

echo ""
echo "=== Uninstallation Complete ==="
echo "Note: Your study history and tasks database (~/.local/share/pomodoro/pomodoro.db) was preserved."
echo "If you wish to remove it as well, run: rm -rf ~/.local/share/pomodoro"
