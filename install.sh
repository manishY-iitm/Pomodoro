#!/bin/bash
# Installation script for Pomodoro Productivity Clock (Linux & macOS)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"

echo "=== Installing Pomodoro Productivity Clock ==="

# 1. Ensure executable permissions
chmod +x "$SCRIPT_DIR/bin/"* 2>/dev/null || true
chmod +x "$SCRIPT_DIR/gnome-extension/install.sh" 2>/dev/null || true

# 2. Install icon (Linux)
if [ "$(uname)" = "Linux" ]; then
    ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
    mkdir -p "$ICON_DIR"
    cp "$SCRIPT_DIR/assets/icons/pomodoro.svg" "$ICON_DIR/" 2>/dev/null || true
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

    # Desktop shortcut
    mkdir -p "$APPS_DIR"
    if [ -f "$SCRIPT_DIR/assets/kali-pomodoro.desktop" ]; then
        cp "$SCRIPT_DIR/assets/kali-pomodoro.desktop" "$APPS_DIR/pomodoro.desktop"
        sed -i "s|/home/kali/pomodoro-productivity-clock|$SCRIPT_DIR|g" "$APPS_DIR/pomodoro.desktop" 2>/dev/null || true
        update-desktop-database "$APPS_DIR" 2>/dev/null || true
        echo "✓ Desktop launcher installed to $APPS_DIR/pomodoro.desktop"
    fi
fi

# 3. Create symlinks in ~/.local/bin
mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT_DIR/bin/pomodoro-app" "$BIN_DIR/pomodoro-app"
ln -sf "$SCRIPT_DIR/bin/pomodoroctl" "$BIN_DIR/pomodoroctl"
echo "✓ CLI commands symlinked to $BIN_DIR (pomodoro-app, pomodoroctl)"

# 4. Optional: Register with pip if available
if command -v pip3 >/dev/null 2>&1; then
    pip3 install -e "$SCRIPT_DIR" --quiet 2>/dev/null || true
fi

# 5. Install GNOME Shell extension (if running GNOME on Linux)
if [ "$XDG_CURRENT_DESKTOP" = "GNOME" ] || [ -d "/usr/share/gnome-shell" ]; then
    if [ -f "$SCRIPT_DIR/gnome-extension/install.sh" ]; then
        echo "Installing native GNOME Shell extension..."
        "$SCRIPT_DIR/gnome-extension/install.sh" || echo "Note: GNOME extension install skipped or warning."
    fi
fi

echo ""
echo "=== Installation Complete ==="
echo "Launch immediately with:  pomodoro-app"
echo "Or CLI status:            pomodoroctl status"
if [ "$(uname)" = "Darwin" ]; then
    echo "Menu bar indicator will appear beside the macOS top clock!"
else
    echo "Top panel indicator will appear beside the system clock / tray!"
fi
