"""Desktop notification and audio alert delivery."""
import shutil
import subprocess
from typing import Optional


class Notifier:
    def __init__(self):
        self.notify_send_bin = shutil.which("notify-send")
        self.canberra_bin = shutil.which("canberra-gtk-play")
        self.paplay_bin = shutil.which("paplay")

    def notify(
        self,
        title: str,
        body: str,
        urgency: str = "normal",
        sound: bool = True,
        icon: Optional[str] = "alarm",
    ):
        """Sends a desktop notification and plays an optional audio chime."""
        if self.notify_send_bin:
            cmd = [
                self.notify_send_bin,
                "-a", "Pomodoro Clock",
                "-u", urgency,
                "-t", "8000", # 8 seconds
            ]
            if icon:
                cmd.extend(["-i", icon])
            cmd.extend([title, body])
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        if sound:
            self.play_chime()

    def play_chime(self):
        """Plays a system alert chime asynchronously."""
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

        # Fallback to paplay with standard GNOME sound
        if self.paplay_bin:
            for sound_path in [
                "/usr/share/sounds/gnome/default/alerts/string.ogg",
                "/usr/share/sounds/gnome/default/alerts/swing.ogg",
                "/usr/share/sounds/oxygen/stereo/message-new-email.ogg",
            ]:
                try:
                    subprocess.Popen(
                        [self.paplay_bin, sound_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
                except Exception:
                    continue
