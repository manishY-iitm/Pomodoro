"""Cross-platform desktop notifications and audio alert delivery for Windows, macOS, and Linux."""
import os
import sys
import shutil
import subprocess
from typing import Optional
from pomodoro.config import IS_WINDOWS, IS_MACOS, IS_LINUX


class Notifier:
    def __init__(self):
        self.notify_send_bin = shutil.which("notify-send")
        self.canberra_bin = shutil.which("canberra-gtk-play")
        self.paplay_bin = shutil.which("paplay")
        self.afplay_bin = shutil.which("afplay")

    def notify(
        self,
        title: str,
        body: str,
        urgency: str = "normal",
        sound: bool = True,
        icon: Optional[str] = "alarm",
    ):
        """Sends a desktop notification and plays an optional audio chime."""
        if IS_WINDOWS:
            self._notify_windows(title, body)
        elif IS_MACOS:
            self._notify_macos(title, body)
        else:
            self._notify_linux(title, body, urgency, icon)

        if sound:
            self.play_chime()

    def _notify_linux(self, title: str, body: str, urgency: str, icon: Optional[str]):
        if self.notify_send_bin:
            cmd = [
                self.notify_send_bin,
                "-a", "Pomodoro Clock",
                "-u", urgency,
                "-t", "8000",
            ]
            if icon:
                cmd.extend(["-i", icon])
            cmd.extend([title, body])
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def _notify_macos(self, title: str, body: str):
        # Escape quotes for AppleScript
        safe_title = title.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')
        script = f'display notification "{safe_body}" with title "{safe_title}"'
        try:
            subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _notify_windows(self, title: str, body: str):
        safe_title = title.replace("'", "''")
        safe_body = body.replace("'", "''")
        ps_cmd = (
            f"[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null; "
            f"[reflection.assembly]::loadwithpartialname('System.Drawing') | Out-Null; "
            f"$notify = new-object system.windows.forms.notifyicon; "
            f"$notify.icon = [system.drawing.systemicons]::information; "
            f"$notify.visible = $true; "
            f"$notify.showballoontip(8000, '{safe_title}', '{safe_body}', [system.windows.forms.tooltipicon]::info)"
        )
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except Exception:
            pass

    def play_chime(self):
        """Plays a system alert chime asynchronously."""
        if IS_WINDOWS:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                return
            except Exception:
                pass

        if IS_MACOS and self.afplay_bin:
            for sound_path in [
                "/System/Library/Sounds/Glass.aiff",
                "/System/Library/Sounds/Ping.aiff",
                "/System/Library/Sounds/Tink.aiff",
            ]:
                if os.path.exists(sound_path):
                    try:
                        subprocess.Popen([self.afplay_bin, sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return
                    except Exception:
                        continue

        if IS_LINUX:
            if self.canberra_bin:
                try:
                    subprocess.Popen(
                        [self.canberra_bin, "-i", "complete"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
                except Exception:
                    pass

            if self.paplay_bin:
                for sound_path in [
                    "/usr/share/sounds/gnome/default/alerts/string.ogg",
                    "/usr/share/sounds/gnome/default/alerts/swing.ogg",
                    "/usr/share/sounds/oxygen/stereo/message-new-email.ogg",
                    "/usr/share/sounds/freedesktop/stereo/complete.oga",
                ]:
                    if os.path.exists(sound_path):
                        try:
                            subprocess.Popen(
                                [self.paplay_bin, sound_path],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            return
                        except Exception:
                            continue

        # Terminal bell fallback
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass
