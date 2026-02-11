import json
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

import pystray
import tkinter as tk
from PIL import Image, ImageDraw
from tkinter import simpledialog


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

RECEIVER_CONFIG_PATH = BASE_DIR / "receivers.json"

POLL_INTERVAL_MS = 90_000
OFFLINE_FAILURE_THRESHOLD = 2

DEFAULT_RECEIVERS = [
    ("주민자치", "109.3.124.39"),
    ("총무", "109.3.124.17"),
    ("복지계장", "109.3.124.35"),
    ("총무계장", "109.3.124.13"),
    ("7번창구", "109.3.124.41"),
    ("김정화", "109.3.124.32"),
    ("맞춤형복지1", "109.3.124.24"),
    ("산업", "109.3.124.16"),
    ("6번창구", "109.3.124.21"),
    ("5번창구", "109.3.124.30"),
    ("4번창구", "109.3.124.23"),
    ("맞춤형복지2", "109.3.124.22"),
    ("1번창구", "109.3.124.28"),
    ("2번창구", "109.3.124.15"),
    ("3번창구", "109.3.124.25"),
    ("9번창구", "109.3.124.20"),
    ("연우", "109.3.124.42"),
]


def get_today_log_path() -> Path:
    return LOG_DIR / f"scan_log_{datetime.now():%Y-%m-%d}.json"


class ScanMonitorFinal:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Scan Monitor")
        self.root.resizable(False, False)

        self.receivers = self.load_receivers()
        self.current_log_path = get_today_log_path()
        self.history = self.load_data(self.current_log_path)
        self.last_status = {ip: None for _, ip in self.receivers}
        self.failure_counts = {ip: 0 for _, ip in self.receivers}
        self.labels: dict[str, dict[str, tk.Label]] = {}

        self.setup_ui()
        self.create_tray()

        # X 버튼은 종료, 최소화는 트레이 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Unmap>", self.on_window_unmap)

        self.poll_status()
        self.root.mainloop()

    def load_receivers(self) -> list[tuple[str, str]]:
        if RECEIVER_CONFIG_PATH.exists():
            try:
                data = json.loads(RECEIVER_CONFIG_PATH.read_text(encoding="utf-8"))
                receivers = []
                for item in data:
                    name = item.get("name")
                    ip = item.get("ip")
                    if isinstance(name, str) and isinstance(ip, str):
                        receivers.append((name, ip))
                if receivers:
                    return receivers
            except json.JSONDecodeError:
                pass

        self.save_receivers(DEFAULT_RECEIVERS)
        return list(DEFAULT_RECEIVERS)

    def save_receivers(self, receivers: list[tuple[str, str]] | None = None) -> None:
        if receivers is None:
            receivers = self.receivers

        payload = [{"name": name, "ip": ip} for name, ip in receivers]
        RECEIVER_CONFIG_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def setup_ui(self) -> None:
        f_small = ("Malgun Gothic", 9)
        f_bold = ("Malgun Gothic", 9, "bold")

        h_frame = tk.Frame(self.root, bg="#eeeeee")
        h_frame.pack(fill="x")
        headers = [("수신처", 10), ("상태", 8), ("최초ON", 8), ("최종OFF", 8)]
        for i, (text, width) in enumerate(headers):
            tk.Label(h_frame, text=text, width=width, font=f_bold, bg="#eeeeee").grid(
                row=0, column=i
            )

        for name, ip in self.receivers:
            row = tk.Frame(self.root)
            row.pack(fill="x")

            name_lbl = tk.Label(
                row, text=name, width=10, anchor="w", font=f_small, cursor="hand2"
            )
            name_lbl.grid(row=0, column=0)
            name_lbl.bind(
                "<Double-Button-1>",
                lambda _e, target_ip=ip: self.edit_receiver_name(target_ip),
            )

            st_lbl = tk.Label(row, text="-", width=8, font=f_small)
            st_lbl.grid(row=0, column=1)

            on_val = self.history.get(ip, {}).get("on", "-")
            on_lbl = tk.Label(row, text=on_val, width=8, font=f_small, fg="blue")
            on_lbl.grid(row=0, column=2)

            off_val = self.history.get(ip, {}).get("off", "-")
            off_lbl = tk.Label(row, text=off_val, width=8, font=f_small, fg="red")
            off_lbl.grid(row=0, column=3)

            self.labels[ip] = {
                "name": name_lbl,
                "st": st_lbl,
                "on": on_lbl,
                "off": off_lbl,
            }

    def edit_receiver_name(self, ip: str) -> None:
        current_name = next((name for name, target_ip in self.receivers if target_ip == ip), "")
        new_name = simpledialog.askstring(
            "수신처 이름 변경", f"{ip} 이름", initialvalue=current_name, parent=self.root
        )

        if new_name is None:
            return

        new_name = new_name.strip()
        if not new_name:
            return

        self.receivers = [
            (new_name, target_ip) if target_ip == ip else (name, target_ip)
            for name, target_ip in self.receivers
        ]
        self.labels[ip]["name"].config(text=new_name)
        self.save_receivers()

    def load_data(self, log_path: Path) -> dict[str, dict[str, str]]:
        default_data = {ip: {"on": "-", "off": "-"} for _, ip in self.receivers}
        if log_path.exists():
            try:
                loaded = json.loads(log_path.read_text(encoding="utf-8"))
                for ip in default_data:
                    if ip in loaded and isinstance(loaded[ip], dict):
                        default_data[ip]["on"] = loaded[ip].get("on", "-")
                        default_data[ip]["off"] = loaded[ip].get("off", "-")
            except json.JSONDecodeError:
                pass

        return default_data

    def save_data(self) -> None:
        self.current_log_path.write_text(
            json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def maybe_rollover_day(self) -> None:
        today_path = get_today_log_path()
        if today_path != self.current_log_path:
            self.current_log_path = today_path
            self.history = self.load_data(today_path)
            self.last_status = {ip: None for _, ip in self.receivers}
            self.failure_counts = {ip: 0 for _, ip in self.receivers}

            for ip, label_set in self.labels.items():
                label_set["on"].config(text=self.history[ip]["on"])
                label_set["off"].config(text=self.history[ip]["off"])
                label_set["st"].config(text="-", fg="#999999")

    def check_status(self, ip: str, timeout_s: float = 0.8) -> bool:
        try:
            with socket.create_connection((ip, 21), timeout=timeout_s):
                return True
        except (TimeoutError, OSError):
            return False

    def poll_status(self) -> None:
        self.maybe_rollover_day()

        changed = False
        now = datetime.now().strftime("%H:%M")

        for _, ip in self.receivers:
            connected = self.check_status(ip)

            if connected:
                self.failure_counts[ip] = 0
                is_on = True
            else:
                self.failure_counts[ip] += 1
                is_on = self.failure_counts[ip] < OFFLINE_FAILURE_THRESHOLD

            if connected or is_on:
                state_text = "Ready"
                state_fg = "green"
            else:
                state_text = "Offline"
                state_fg = "#999999"

            self.labels[ip]["st"].config(text=state_text, fg=state_fg)

            if connected and self.history[ip]["on"] == "-":
                self.history[ip]["on"] = now
                self.labels[ip]["on"].config(text=now)
                changed = True

            if self.last_status[ip] is True and is_on is False:
                self.history[ip]["off"] = now
                self.labels[ip]["off"].config(text=now)
                changed = True

            self.last_status[ip] = is_on

        if changed:
            self.save_data()

        self.root.after(POLL_INTERVAL_MS, self.poll_status)

    def on_window_unmap(self, _event=None) -> None:
        if self.root.state() == "iconic":
            self.root.after(0, self.hide_window)

    def hide_window(self) -> None:
        self.root.withdraw()

    def show_window(self, icon=None, item=None) -> None:
        self.root.after(0, self._show_window_main_thread)

    def _show_window_main_thread(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def on_close(self, icon=None, item=None) -> None:
        self.root.after(0, self._close_main_thread)

    def _close_main_thread(self) -> None:
        try:
            self.icon.stop()
        except Exception:
            pass
        self.root.destroy()

    def create_tray(self) -> None:
        img = Image.new("RGB", (64, 64), (240, 240, 240))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 10, 54, 54), fill=(0, 120, 215))

        menu = pystray.Menu(
            pystray.MenuItem("열기", self.show_window, default=True),
            pystray.MenuItem("종료", self.on_close),
        )
        self.icon = pystray.Icon("ScanMonitor", img, "Scan Monitor", menu)
        self.icon.run_detached()


if __name__ == "__main__":
    ScanMonitorFinal()
