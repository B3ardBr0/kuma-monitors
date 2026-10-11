"""Provision the ZimaBoard's Uptime Kuma instance from a single declaration.

Uptime Kuma has no configuration file: monitors are rows in its database,
created through a socket.io API. That makes a hand-built instance impossible to
review and tedious to rebuild. This script is the source of truth instead - the
monitor list in monitors.py is the configuration, and running it brings the
instance into line.

It is safe to re-run. Monitors, notifications and status pages are matched by
name and skipped if they already exist, so this adds what is missing rather than
duplicating what is there.

Credentials come from the environment:

    KUMA_URL     default http://localhost:3001
    KUMA_USER    the admin account created on first run
    KUMA_PASS    its password
    NTFY_TOPIC   ntfy.sh topic to publish alerts to
"""

from __future__ import annotations

import os
import sys

from uptime_kuma_api import MonitorType, NotificationType, UptimeKumaApi

KUMA_URL = os.environ.get("KUMA_URL", "http://localhost:3001")
KUMA_USER = os.environ.get("KUMA_USER", "")
KUMA_PASS = os.environ.get("KUMA_PASS", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")

# The monitor list lives in its own file. monitors.py holds the real one and is
# kept out of git; monitors_example.py shows the shape and is used without it.
try:
    from monitors import GROUPS, MONITORS
except ImportError:
    from monitors_example import GROUPS, MONITORS

STATUS_PAGE_SLUG = "home"
STATUS_PAGE_TITLE = "ZimaBoard 2"


def require_env() -> None:
    missing = [n for n, v in
               (("KUMA_USER", KUMA_USER), ("KUMA_PASS", KUMA_PASS),
                ("NTFY_TOPIC", NTFY_TOPIC)) if not v]
    if missing:
        raise SystemExit(f"set {', '.join(missing)} in the environment")


def ensure_notification(api: UptimeKumaApi) -> int:
    """Create the ntfy notification if it is not already there."""
    name = "ntfy"
    for existing in api.get_notifications():
        if existing["name"] == name:
            print(f"  notification '{name}' already exists")
            return existing["id"]
    created = api.add_notification(
        name=name,
        type=NotificationType.NTFY,
        isDefault=True,
        applyExisting=True,
        ntfyserverurl="https://ntfy.sh",
        ntfytopic=NTFY_TOPIC,
        ntfyPriority=5,
        ntfyAuthenticationMethod="none",
    )
    print(f"  created notification '{name}' -> {NTFY_TOPIC}")
    return created["id"]


def ensure_groups(api: UptimeKumaApi, existing: dict[str, int]) -> dict[str, int]:
    ids = {}
    for name in GROUPS:
        if name in existing:
            ids[name] = existing[name]
            print(f"  group '{name}' already exists")
            continue
        created = api.add_monitor(type=MonitorType.GROUP, name=name)
        ids[name] = created["monitorID"]
        print(f"  created group '{name}'")
    return ids


def ensure_monitors(api: UptimeKumaApi, groups: dict[str, int],
                    existing: dict[str, dict], notification_id: int) -> list[int]:
    """Create missing monitors, and make sure every one of them can alert.

    A notification marked as default is only pre-ticked in Uptime Kuma's web
    form. A monitor created over the API gets none unless it is attached here,
    and "apply to existing" only reaches monitors that exist at that moment.
    The first version of this script relied on both and alerted nobody for two
    days. Groups are left without one on purpose: a group goes down whenever a
    child does, so it would only ever send duplicates.
    """
    ids = []
    for spec in MONITORS:
        spec = dict(spec)
        name = spec["name"]
        if name in existing:
            monitor = existing[name]
            if notification_id not in (monitor.get("notificationIDList") or []):
                api.edit_monitor(monitor["id"], notificationIDList=[notification_id])
                print(f"  monitor '{name}' existed with no alerting - attached it")
            else:
                print(f"  monitor '{name}' already exists")
            if "url" in spec and monitor.get("url") != spec["url"]:
                api.edit_monitor(monitor["id"], url=spec["url"])
                print(f"  monitor '{name}' now checks {spec['url']}")
            ids.append(monitor["id"])
            continue
        spec["parent"] = groups[spec.pop("group")]
        spec["notificationIDList"] = [notification_id]
        created = api.add_monitor(**spec)
        ids.append(created["monitorID"])
        print(f"  created monitor '{name}'")
    return ids


def assert_alerting(api: UptimeKumaApi, notification_id: int) -> None:
    """Fail loudly if any real monitor still cannot alert."""
    silent = [m["name"] for m in api.get_monitors()
              if m["type"] != "group" and notification_id not in (m.get("notificationIDList") or [])]
    if silent:
        raise SystemExit(f"these monitors have no notification attached: {silent}")
    print("  every monitor has the notification attached")


def ensure_status_page(api: UptimeKumaApi, monitor_ids: list[int]) -> None:
    """Homepage's uptimekuma widget reads a status page, not the admin API."""
    slugs = {page["slug"] for page in api.get_status_pages()}
    if STATUS_PAGE_SLUG not in slugs:
        api.add_status_page(slug=STATUS_PAGE_SLUG, title=STATUS_PAGE_TITLE)
        print(f"  created status page '{STATUS_PAGE_SLUG}'")
    api.save_status_page(
        slug=STATUS_PAGE_SLUG,
        title=STATUS_PAGE_TITLE,
        description="Sites and homelab services",
        showTags=False,
        # Surfaces TLS expiry on the page itself; expiryNotification on each
        # monitor is what actually sends the warning.
        showCertificateExpiry=True,
        publicGroupList=[{
            "name": "All",
            "weight": 1,
            "monitorList": [{"id": i} for i in monitor_ids],
        }],
    )
    print(f"  status page holds {len(monitor_ids)} monitors")


def main() -> None:
    require_env()
    api = UptimeKumaApi(KUMA_URL)
    try:
        api.login(KUMA_USER, KUMA_PASS)
        print(f"connected to {KUMA_URL}")

        existing = {m["name"]: m for m in api.get_monitors()}
        notification_id = ensure_notification(api)
        groups = ensure_groups(api, {name: m["id"] for name, m in existing.items()})
        monitor_ids = ensure_monitors(api, groups, existing, notification_id)
        assert_alerting(api, notification_id)
        ensure_status_page(api, monitor_ids)

        print(f"\ndone: {len(monitor_ids)} monitors across {len(groups)} groups")
        print(f"status page: {KUMA_URL}/status/{STATUS_PAGE_SLUG}")
    finally:
        api.disconnect()


if __name__ == "__main__":
    sys.exit(main())
