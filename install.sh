#!/bin/bash
# Installation script for Kali Pomodoro Productivity Clock
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"

echo "=== Installing Kali Pomodoro Productivity Clock ==="

# 1. Ensure executable permissions
chmod +x "$SCRIPT_DIR/bin/"*
chmod +x "$SCRIPT_DIR/gnome-extension/install.sh" 2>/dev/null || true

# 2. Install desktop shortcut
mkdir -p "$APPS_DIR"
cp "$SCRIPT_DIR/assets/kali-pomodoro.desktop" "$APPS_DIR/"
sed -i "s|/home/kali/pomodoro-productivity-clock|$SCRIPT_DIR|g" "$APPS_DIR/kali-pomodoro.desktop"
update-desktop-database "$APPS_DIR" 2>/dev/null || true
echo "✓ Desktop launcher installed to $APPS_DIR/kali-pomodoro.desktop"

# 3. Create convenient symlinks in ~/.local/bin
mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT_DIR/bin/pomodoro-app" "$BIN_DIR/pomodoro-app"
ln -sf "$SCRIPT_DIR/bin/pomodoroctl" "$BIN_DIR/pomodoroctl"
echo "✓ CLI commands symlinked to $BIN_DIR (pomodoro-app, pomodoroctl)"

# 4. Install GNOME Shell extension (if GNOME desktop)
if [ "$XDG_CURRENT_DESKTOP" = "GNOME" ] || [ -d "/usr/share/gnome-shell" ]; then
    echo "Installing native GNOME Shell extension..."
    "$SCRIPT_DIR/gnome-extension/install.sh" || echo "Note: GNOME extension install skipped or warning."
fi

echo ""
echo "=== Installation Complete ==="
echo "Launch immediately with:  pomodoro-app"
echo "Or CLI status:            pomodoroctl status"
echo "Top panel indicator appears immediately to the LEFT of the top clock!"
