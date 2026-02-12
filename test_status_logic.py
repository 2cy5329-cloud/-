import socket
import sys
import threading
import types
import unittest
from datetime import datetime, timedelta


# Stub optional runtime deps before module import
sys.modules.setdefault(
    "pystray",
    types.SimpleNamespace(
        Menu=lambda *a, **k: None,
        MenuItem=lambda *a, **k: None,
        Icon=lambda *a, **k: None,
    ),
)
if "PIL" not in sys.modules:
    pil = types.ModuleType("PIL")
    pil.Image = types.SimpleNamespace(new=lambda *a, **k: None)
    pil.ImageDraw = types.SimpleNamespace(Draw=lambda *a, **k: None)
    sys.modules["PIL"] = pil
    sys.modules["PIL.Image"] = pil.Image
    sys.modules["PIL.ImageDraw"] = pil.ImageDraw

import PrintSpooler_Service as app


class FakeLabel:
    def __init__(self, text=""):
        self.props = {"text": text, "fg": "", "bg": "#fff"}

    def config(self, **kwargs):
        self.props.update(kwargs)

    def cget(self, key):
        return self.props.get(key)


class StatusLogicTests(unittest.TestCase):
    def make_obj(self, history=None, first_failure_at=None, last_status=None):
        ip = "1.1.1.1"
        obj = app.ScanMonitorFinal.__new__(app.ScanMonitorFinal)
        obj.receivers = [("A", ip)]
        obj.history = history or {ip: {"on": "-", "off": "-"}}
        obj.first_failure_at = first_failure_at or {ip: None}
        obj.last_status = last_status or {ip: None}
        obj.labels = {
            ip: {
                "st": FakeLabel(),
                "on": FakeLabel(obj.history[ip]["on"]),
                "off": FakeLabel(obj.history[ip]["off"]),
            }
        }
        obj.set_row_visibility = lambda _ip, _visible: None
        obj.save_data = lambda: None
        obj.finish_poll_cycle = lambda: None
        obj.log_error = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("unexpected error path")
        )
        return obj, ip

    def test_success_sets_ready_and_first_on(self):
        obj, ip = self.make_obj()
        obj.apply_poll_result(datetime(2026, 1, 1, 9, 0), {ip: True})
        self.assertEqual(obj.history[ip]["on"], "09:00")
        self.assertEqual(obj.labels[ip]["st"].cget("text"), "Ready")

    def test_first_failure_within_grace_not_offline(self):
        ip = "1.1.1.1"
        obj, ip = self.make_obj(
            history={ip: {"on": "08:00", "off": "-"}},
            last_status={ip: True},
        )
        t0 = datetime(2026, 1, 1, 9, 0)
        obj.apply_poll_result(t0, {ip: False})
        self.assertEqual(obj.first_failure_at[ip], t0)
        self.assertEqual(obj.history[ip]["off"], "-")
        self.assertIs(obj.last_status[ip], True)

    def test_offline_after_10_minutes_uses_first_failure_time(self):
        ip = "1.1.1.1"
        first_fail = datetime(2026, 1, 1, 9, 0)
        obj, ip = self.make_obj(
            history={ip: {"on": "08:00", "off": "-"}},
            first_failure_at={ip: first_fail},
            last_status={ip: True},
        )
        obj.apply_poll_result(first_fail + timedelta(minutes=11), {ip: False})
        self.assertEqual(obj.history[ip]["off"], "09:00")
        self.assertIs(obj.last_status[ip], False)

    def test_recovery_resets_failure_and_sets_ready(self):
        ip = "1.1.1.1"
        obj, ip = self.make_obj(
            history={ip: {"on": "08:00", "off": "09:00"}},
            first_failure_at={ip: datetime(2026, 1, 1, 9, 0)},
            last_status={ip: False},
        )
        obj.apply_poll_result(datetime(2026, 1, 1, 9, 12), {ip: True})
        self.assertIsNone(obj.first_failure_at[ip])
        self.assertIs(obj.last_status[ip], True)
        self.assertEqual(obj.labels[ip]["st"].cget("text"), "Ready")

    def test_check_status_success_and_failure(self):
        obj, _ = self.make_obj()

        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)

        def accept_once():
            try:
                conn, _addr = srv.accept()
                conn.close()
            except OSError:
                pass

        threading.Thread(target=accept_once, daemon=True).start()

        original = app.socket.create_connection
        app.socket.create_connection = lambda addr, timeout=0.8: original(
            ("127.0.0.1", port), timeout
        )
        try:
            self.assertTrue(obj.check_status("dummy", 0.8))
        finally:
            srv.close()

        app.socket.create_connection = lambda addr, timeout=0.8: (_ for _ in ()).throw(
            OSError("closed")
        )
        try:
            self.assertFalse(obj.check_status("dummy", 0.8))
        finally:
            app.socket.create_connection = original


if __name__ == "__main__":
    unittest.main()
