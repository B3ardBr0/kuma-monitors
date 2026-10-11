"""Tests for provision.py against a fake Uptime Kuma. No server needed.

    python -m unittest test_provision
"""

import contextlib
import io
import unittest

import monitors_example
import provision


class FakeKuma:
    """Keeps monitors in a list. Like the real API, a monitor gets a
    notification only when it is passed one; isDefault does nothing here."""

    def __init__(self, monitors=None):
        self.monitors = list(monitors or [])
        self.notifications = []

    def login(self, user, password): pass
    def disconnect(self): pass
    def get_monitors(self): return self.monitors
    def get_notifications(self): return self.notifications
    def get_status_pages(self): return []
    def add_status_page(self, **kwargs): pass
    def save_status_page(self, **kwargs): pass

    def add_notification(self, **kwargs):
        self.notifications.append({"id": 1, **kwargs})
        return {"id": 1}

    def add_monitor(self, **kwargs):
        monitor = {"id": len(self.monitors) + 1, "notificationIDList": [], **kwargs}
        monitor["type"] = str(getattr(monitor["type"], "value", monitor["type"]))
        self.monitors.append(monitor)
        return {"monitorID": monitor["id"]}

    def edit_monitor(self, monitor_id, **kwargs):
        next(m for m in self.monitors if m["id"] == monitor_id).update(kwargs)


def provision_against(api):
    provision.UptimeKumaApi = lambda url: api
    provision.KUMA_USER = provision.KUMA_PASS = provision.NTFY_TOPIC = "x"
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        provision.main()
    return out.getvalue()


class Provision(unittest.TestCase):
    def setUp(self):
        provision.GROUPS = monitors_example.GROUPS
        provision.MONITORS = monitors_example.MONITORS

    def test_every_created_monitor_can_alert(self):
        api = FakeKuma()
        out = provision_against(api)
        self.assertIn("every monitor has the notification attached", out)
        real = [m for m in api.monitors if m["type"] != "group"]
        self.assertEqual(len(real), len(monitors_example.MONITORS))
        self.assertTrue(all(m["notificationIDList"] == [1] for m in real))

    def test_an_existing_silent_monitor_is_repaired(self):
        api = FakeKuma([{"id": 99, "type": "http", "name": "Grafana", "notificationIDList": []}])
        api.notifications.append({"id": 1, "name": "ntfy"})
        out = provision_against(api)
        self.assertIn("monitor 'Grafana' existed with no alerting - attached it", out)

    def test_the_guard_refuses_a_silent_monitor(self):
        api = FakeKuma([{"id": 5, "type": "http", "name": "Forgotten", "notificationIDList": []}])
        with self.assertRaises(SystemExit):
            provision.assert_alerting(api, notification_id=1)

    def test_groups_are_allowed_to_stay_silent(self):
        api = FakeKuma([{"id": 5, "type": "group", "name": "Homelab", "notificationIDList": []}])
        with contextlib.redirect_stdout(io.StringIO()):
            provision.assert_alerting(api, notification_id=1)


if __name__ == "__main__":
    unittest.main()
