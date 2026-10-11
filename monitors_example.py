"""An example monitor list. Copy it to monitors.py and make it yours.

provision.py reads monitors.py when it exists, which .gitignore keeps out of
the repository, and falls back to this file when it doesn't.
"""

from uptime_kuma_api import MonitorType

OK_CODES = ["200-299"]
OK_OR_REDIRECT = ["200-299", "300-399"]

# Groups render as collapsible headings in the Uptime Kuma UI.
GROUPS = ["Public sites", "Origins", "Homelab", "DNS"]

# Every monitor, keyed to the group it belongs under.
#
# Public sites are checked by KEYWORD rather than status code on purpose. The
# domains sit behind Cloudflare, so a 200 proves only that Cloudflare
# answered; a keyword unique to the rendered page also catches a bad deploy
# serving the wrong thing. The origin checks bypass Cloudflare entirely, which
# is what distinguishes "my app is down" from "Cloudflare is having a day".
MONITORS = [
    {
        "group": "Public sites",
        "type": MonitorType.KEYWORD,
        "name": "wjmaritz.dev",
        "url": "https://wjmaritz.dev",
        "keyword": "Wilhelm Maritz",
        "expiryNotification": True,
    },
    {
        "group": "Public sites",
        "type": MonitorType.KEYWORD,
        "name": "example.com",
        "url": "https://example.com",
        "keyword": "Example Domain",
        "expiryNotification": True,
    },
    {
        "group": "Origins",
        "type": MonitorType.JSON_QUERY,
        "name": "App origin",
        "url": "https://<app>.up.railway.app/health",
        "jsonPath": "$.status",
        "expectedValue": "ok",
        "expiryNotification": True,
    },
    {
        # Paperless redirects an anonymous request to its login page.
        "group": "Homelab",
        "type": MonitorType.HTTP,
        "name": "Paperless-ngx",
        "url": "http://192.168.1.10:8000",
        "accepted_statuscodes": OK_OR_REDIRECT,
    },
    {
        "group": "Homelab",
        "type": MonitorType.HTTP,
        "name": "Homepage",
        # Homepage has a login since v2; this path stays open without a session.
        "url": "http://192.168.1.10:3000/api/healthcheck",
    },
    {
        # Grafana's health endpoint also reports on its database, so this
        # catches "the UI loads but it cannot read its own storage".
        "group": "Homelab",
        "type": MonitorType.JSON_QUERY,
        "name": "Grafana",
        "url": "http://192.168.1.10:3003/api/health",
        "jsonPath": "$.database",
        "expectedValue": "ok",
    },
    {
        # A TCP check, not HTTP: the container's only service is sshd on 2222.
        "group": "Homelab",
        "type": MonitorType.PORT,
        "name": "Dev box (SSH)",
        "hostname": "192.168.1.10",
        "port": 2222,
    },
    {
        # Ping separates "the service died" from "the box or network died".
        "group": "Homelab",
        "type": MonitorType.PING,
        "name": "Server (ping)",
        "hostname": "192.168.1.10",
    },
    {
        # The server's own tailnet address. It only answers while tailscaled is
        # up and logged in, so this catches the container dying or the node key
        # expiring, which a check on the LAN address never would.
        "group": "Homelab",
        "type": MonitorType.PING,
        "name": "Tailscale (server)",
        "hostname": "100.64.0.1",
    },
    {
        # A Microsoft 365 tenant domain with no working web origin, so HTTP
        # checks would sit permanently red and teach nothing. Its DNS is the
        # part that actually matters.
        "group": "DNS",
        "type": MonitorType.DNS,
        "name": "example.org MX",
        "hostname": "example.org",
        "dns_resolve_server": "1.1.1.1",
        "dns_resolve_type": "MX",
    },
    {
        "group": "DNS",
        "type": MonitorType.DNS,
        # Apex TXT only, which is where SPF lives. DMARC is a separate record at
        # _dmarc.<domain>; add a monitor for it once it exists, not before, or
        # it will sit permanently red.
        "name": "example.org TXT (SPF)",
        "hostname": "example.org",
        "dns_resolve_server": "1.1.1.1",
        "dns_resolve_type": "TXT",
    },
]
