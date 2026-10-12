#!/bin/bash
# Install native GNOME Shell extension for Kali Pomodoro Clock
set -e

EXT_UUID="pomodoro@antigravity.org"
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing Pomodoro GNOME Shell Extension to $EXT_DIR..."
mkdir -p "$EXT_DIR"

cp "$SCRIPT_DIR/metadata.json" "$EXT_DIR/"
cp "$SCRIPT_DIR/extension.js" "$EXT_DIR/"
cp "$SCRIPT_DIR/stylesheet.css" "$EXT_DIR/"

echo "Enabling extension in GNOME settings..."
CURRENT_EXTS=$(gsettings get org.gnome.shell enabled-extensions)
if [[ "$CURRENT_EXTS" != *"$EXT_UUID"* ]]; then
    NEW_EXTS=$(python3 -c "
import ast
curr = ast.literal_eval('''$CURRENT_EXTS''')
if '$EXT_UUID' not in curr:
    curr.append('$EXT_UUID')
print(curr)
")
    gsettings set org.gnome.shell enabled-extensions "$NEW_EXTS"
fi

echo "✓ Extension installed and enabled in GNOME Shell preferences!"
echo "Note: Under GNOME Wayland, newly registered extensions load when starting a GNOME Shell session."
