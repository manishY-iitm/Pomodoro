import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

export class PomodoroIndicatorButton extends PanelMenu.Button {
    static {
        GObject.registerClass(this);
    }

    constructor() {
        super(0.0, "Pomodoro Timer", false);

        // Indicator button UI on the panel
        const box = new St.BoxLayout({
            vertical: false,
            style_class: 'pomodoro-panel-box',
            style: 'spacing: 4px; padding: 0 6px;',
        });

        this.iconLabel = new St.Label({
            y_align: Clutter.ActorAlign.CENTER,
            text: '◷',
            style: 'font-weight: bold; font-size: 11pt;',
        });

        this.textLabel = new St.Label({
            y_align: Clutter.ActorAlign.CENTER,
            text: 'FOCUS',
            style: 'font-weight: bold; font-size: 11pt;',
        });

        box.add_child(this.iconLabel);
        box.add_child(this.textLabel);
        this.add_child(box);

        // Build native GNOME Shell dropdown menu
        this._buildMenu();

        // Socket path for communication with Pomodoro daemon
        const uid = GLib.get_user_name();
        const runtimeDir = GLib.get_user_runtime_dir();
        this.socketPath = `${runtimeDir}/pomodoro/pomodoro.sock`;

        // Start periodic sync
        this._startSync();
    }

    _buildMenu() {
        // Status & Countdown Header item
        this.headerItem = new PopupMenu.PopupMenuItem("Pomodoro: IDLE", { reactive: false });
        this.headerItem.label.clutter_text.set_markup("<b>Pomodoro: IDLE (25:00)</b>");
        this.menu.addMenuItem(this.headerItem);

        // Task label
        this.taskItem = new PopupMenu.PopupMenuItem("No task selected", { reactive: false });
        this.menu.addMenuItem(this.taskItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Quick Controls
        this.toggleItem = new PopupMenu.PopupMenuItem("▶ Start Timer");
        this.toggleItem.connect('activate', () => this._sendCommand('toggle'));
        this.menu.addMenuItem(this.toggleItem);

        const resetItem = new PopupMenu.PopupMenuItem("⟲ Reset Interval");
        resetItem.connect('activate', () => this._sendCommand('reset'));
        this.menu.addMenuItem(resetItem);

        const skipItem = new PopupMenu.PopupMenuItem("⏭ Skip Session");
        skipItem.connect('activate', () => this._sendCommand('skip'));
        this.menu.addMenuItem(skipItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Open full management window
        const openAppItem = new PopupMenu.PopupMenuItem("📋 Open Tasks & Statistics...");
        openAppItem.connect('activate', () => {
            try {
                const home = GLib.get_home_dir();
                const appBin = `${home}/pomodoro-productivity-clock/bin/pomodoro-indicator`;
                GLib.spawn_command_line_async(appBin);
            } catch (e) {
                console.error(`Failed to launch pomodoro app: ${e.message}`);
            }
        });
        this.menu.addMenuItem(openAppItem);
    }

    _sendCommand(cmd) {
        try {
            const socketFile = Gio.File.new_for_path(this.socketPath);
            if (!socketFile.query_exists(null)) return;

            const client = new Gio.SocketClient();
            const address = new Gio.UnixSocketAddress({ path: this.socketPath });
            const conn = client.connect(address, null);
            const outStream = conn.get_output_stream();
            const payload = JSON.stringify({ cmd }) + "\n";
            outStream.write_all(new TextEncoder().encode(payload), null);
            conn.close(null);
        } catch (e) {
            console.warn(`Pomodoro socket error: ${e.message}`);
        }
    }

    _queryStatus() {
        try {
            const socketFile = Gio.File.new_for_path(this.socketPath);
            if (!socketFile.query_exists(null)) {
                this.iconLabel.set_text('◷');
                this.textLabel.set_text('FOCUS');
                return;
            }

            const client = new Gio.SocketClient();
            const address = new Gio.UnixSocketAddress({ path: this.socketPath });
            const conn = client.connect(address, null);

            const outStream = conn.get_output_stream();
            outStream.write_all(new TextEncoder().encode('{"cmd": "status"}\n'), null);

            const inStream = new Gio.DataInputStream({ base_stream: conn.get_input_stream() });
            const [line] = inStream.read_line_utf8(null);
            conn.close(null);

            if (line) {
                const resp = JSON.parse(line);
                if (resp && resp.ok && resp.data) {
                    this._updateUi(resp.data);
                }
            }
        } catch (e) {
            // Daemon not running or sleeping
        }
    }

    _updateUi(data) {
        const state = data.state || 'IDLE';
        const formatted = data.formatted_time || '25:00';
        const icon = data.panel_icon || '◷';
        const label = data.panel_label || 'FOCUS';

        this.iconLabel.set_text(icon);
        this.textLabel.set_text(label);

        // Update menu items
        this.headerItem.label.clutter_text.set_markup(`<b>Pomodoro: ${state} (${formatted})</b>`);
        if (state === 'FOCUS' || state === 'SHORT_BREAK' || state === 'LONG_BREAK') {
            this.toggleItem.label.set_text('⏸ Pause Timer');
        } else if (state === 'PAUSED') {
            this.toggleItem.label.set_text('▶ Resume Timer');
        } else {
            this.toggleItem.label.set_text('▶ Start Timer');
        }

        const task = data.active_task;
        if (task) {
            this.taskItem.label.set_text(`Task: ${task.name}`);
        } else {
            this.taskItem.label.set_text('No task selected');
        }
    }

    _startSync() {
        this._queryStatus();
        this._timeout = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            this._queryStatus();
            return GLib.SOURCE_CONTINUE;
        });
    }

    destroy() {
        if (this._timeout) {
            GLib.source_remove(this._timeout);
            this._timeout = null;
        }
        super.destroy();
    }
}

export default class PomodoroExtension extends Extension {
    enable() {
        this._indicator = new PomodoroIndicatorButton();

        // Exact placement: locate dateMenu in _centerBox and insert immediately before it!
        let dateMenuIndex = 0;
        if (Main.panel.statusArea['dateMenu']) {
            const dateContainer = Main.panel.statusArea['dateMenu'].container;
            const children = Main.panel._centerBox.get_children();
            const idx = children.indexOf(dateContainer);
            if (idx >= 0) {
                dateMenuIndex = idx;
            }
        }

        Main.panel.addToStatusArea('pomodoro-indicator', this._indicator, dateMenuIndex, 'center');
    }

    disable() {
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}
