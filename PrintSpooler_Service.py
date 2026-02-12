import json
import os
import socket
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread

import pystray
import tkinter as tk
from PIL import Image, ImageDraw
from tkinter import messagebox, simpledialog


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

RECEIVER_CONFIG_PATH = BASE_DIR / "receivers.json"
ERROR_LOG_PATH = LOG_DIR / "PrintSpooler_Service_error.log"

POLL_INTERVAL_MS = 90_000
OFFLINE_AFTER = timedelta(minutes=30)

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
        self.root.title("PrintSpooler_Service")
        self.root.resizable(False, False)

        self.receivers = self.load_receivers()
        self.current_log_path = get_today_log_path()
        self.history = self.load_data(self.current_log_path)
        self.last_status = {ip: None for _, ip in self.receivers}
        self.first_failure_at: dict[str, datetime | None] = {
            ip: None for _, ip in self.receivers
        }
        self.labels: dict[str, dict[str, tk.Label]] = {}

        self.poll_job: str | None = None
        self.running = True
        self.poll_inflight = False

        self.setup_ui()
        self.create_tray()

        # 시작 시 트레이 상태로 실행
        self.root.withdraw()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Unmap>", self.on_window_unmap)

        self.root.after(50, self.poll_status)
        self.root.mainloop()

    def log_error(self, context: str, err: Exception) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{timestamp}] {context}: {err}\n{traceback.format_exc()}\n"
        try:
            with ERROR_LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(message)
        except OSError:
            pass

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

            st_lbl = tk.Label(row, text="", width=8, font=f_bold, fg="black")
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
            self.first_failure_at = {ip: None for _, ip in self.receivers}

            for ip, label_set in self.labels.items():
                label_set["on"].config(text=self.history[ip]["on"])
                label_set["off"].config(text=self.history[ip]["off"])
                label_set["st"].config(text="", fg="black", bg=self.root.cget("bg"))

    def check_status(self, ip: str, timeout_s: float = 0.8) -> bool:
        try:
            with socket.create_connection((ip, 21), timeout=timeout_s):
                return True
        except (TimeoutError, OSError):
            return False

    def poll_status(self) -> None:
        if self.poll_inflight or not self.running:
            self.poll_job = self.root.after(POLL_INTERVAL_MS, self.poll_status)
            return

        self.poll_inflight = True
        self.maybe_rollover_day()

        def worker() -> None:
            try:
                now_dt = datetime.now()
                results: dict[str, bool] = {}
                for _, ip in self.receivers:
                    results[ip] = self.check_status(ip)

                self.root.after(0, lambda: self.apply_poll_result(now_dt, results))
            except Exception as err:
                self.log_error("poll_status_worker", err)
                self.root.after(0, self.finish_poll_cycle)

        Thread(target=worker, daemon=True).start()

    def apply_poll_result(self, now_dt: datetime, results: dict[str, bool]) -> None:
        try:
            changed = False
            now = now_dt.strftime("%H:%M")

            for _, ip in self.receivers:
                self.history.setdefault(ip, {"on": "-", "off": "-"})
                connected = results.get(ip, False)

                if connected:
                    self.first_failure_at[ip] = None
                    is_on = True
                    status_text = "Ready"
                    status_fg = "#0066ff"
                    status_bg = self.root.cget("bg")
                else:
                    if self.first_failure_at[ip] is None:
                        self.first_failure_at[ip] = now_dt

                    fail_started_at = self.first_failure_at[ip]
                    within_grace = (now_dt - fail_started_at) < OFFLINE_AFTER
                    is_on = within_grace

                    if within_grace:
                        status_text = ""
                        status_fg = "black"
                        status_bg = self.root.cget("bg")
                    else:
                        status_text = ""
                        status_fg = "black"
                        status_bg = self.root.cget("bg")

                self.labels[ip]["st"].config(text=status_text, fg=status_fg, bg=status_bg)

                if connected and self.history[ip]["on"] == "-":
                    self.history[ip]["on"] = now
                    self.labels[ip]["on"].config(text=now)
                    changed = True

                if self.last_status.get(ip) is True and is_on is False:
                    off_at = self.first_failure_at[ip] or now_dt
                    off_str = off_at.strftime("%H:%M")
                    self.history[ip]["off"] = off_str
                    self.labels[ip]["off"].config(text=off_str)
                    changed = True

                self.last_status[ip] = is_on

            if changed:
                self.save_data()

        except Exception as err:
            self.log_error("apply_poll_result", err)

        finally:
            self.finish_poll_cycle()

    def finish_poll_cycle(self) -> None:
        self.poll_inflight = False
        if self.running and self.root.winfo_exists():
            self.poll_job = self.root.after(POLL_INTERVAL_MS, self.poll_status)

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

    def on_close(self, icon=None, item=None) -> None:
        self.root.after(0, self._confirm_and_close_main_thread)

    def _confirm_and_close_main_thread(self) -> None:
        if not self.running or not self.root.winfo_exists():
            return

        should_close = messagebox.askyesno(
            "종료 확인", "종료하시겠습니까?"
        )
        if should_close:
            self._close_main_thread()

    def _close_main_thread(self) -> None:
        self.running = False
        if self.poll_job is not None:
            try:
                self.root.after_cancel(self.poll_job)
            except Exception:
                pass
            self.poll_job = None

        try:
            self.icon.stop()
        except Exception:
            pass

        if self.root.winfo_exists():
            self.root.destroy()

    def create_tray(self) -> None:
        img = Image.new("RGB", (64, 64), (240, 240, 240))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 10, 54, 54), fill=(0, 120, 215))

        menu = pystray.Menu(
            pystray.MenuItem("열기", self.show_window, default=True),
            pystray.MenuItem("종료", self.on_close),
        )
        self.icon = pystray.Icon(
            "PrintSpooler_Service", img, "PrintSpooler_Service", menu
        )
        self.icon.run_detached()


if __name__ == "__main__":
    ScanMonitorFinal()
