# kuma-monitors

[Uptime Kuma](https://uptime.kuma.pet) monitors, declared in Python.

Uptime Kuma has no config file. Monitors are rows in a SQLite database created through a socket.io API, which means a hand-built instance can't be reviewed in a diff and can't be rebuilt without clicking it all in again. `provision.py` holds the monitor list as a declaration instead, and brings the instance into line with it.

Re-running is safe. Monitors, notifications and status pages are matched by name and skipped if they're there already.

## What a run looks like

A real run against a throwaway Uptime Kuma 1.23.16 in Docker, on port 3901, with the example list and a random topic. Trimmed where marked:

```
$ python provision.py
connected to http://localhost:3901
  created notification 'ntfy' -> demo-a159aa06803f5421
  created group 'Public sites'
  created group 'Origins'
  created group 'Homelab'
  created group 'DNS'
  created monitor 'wjmaritz.dev'
  created monitor 'example.com'
  created monitor 'App origin'
  ...
  created monitor 'example.org TXT (SPF)'
  every monitor has the notification attached
  created status page 'home'
  status page holds 11 monitors

done: 11 monitors across 4 groups
status page: http://localhost:3901/status/home
```

Run it again and every line says `already exists`; nothing is duplicated.

## Usage

```sh
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp monitors_example.py monitors.py      # then make it yours

KUMA_URL=http://localhost:3001 KUMA_USER=... KUMA_PASS=... NTFY_TOPIC=... ./.venv/bin/python provision.py
```

| Variable | Default | Meaning |
|---|---|---|
| `KUMA_URL` | `http://localhost:3001` | Uptime Kuma base URL |
| `KUMA_USER` | required | admin account |
| `KUMA_PASS` | required | its password |
| `NTFY_TOPIC` | required | ntfy.sh topic for alerts |

`monitors.py` is in `.gitignore`, so your real hostnames and addresses stay out of the repo. Without it, the script uses `monitors_example.py`.

## Every monitor has to be able to alert

The first version of this marked the ntfy notification as default and set "apply to existing", and I assumed that covered everything. It didn't. Default only pre-ticks a box in the web form, and "apply to existing" only reaches monitors that exist at that moment, which was none of them. Every monitor created over the API had no notification at all. For two days nothing could alert, and an outage at 03:35 on 20 September paged nobody.

So now the notification is attached to each monitor as it's created, existing monitors without it get repaired, and `assert_alerting` refuses to finish if any real monitor is still silent. Groups are left out on purpose: a group goes down whenever a child does, so it would only send duplicates.

The full story: [The 03:37 alert that was never sent](https://wjmaritz.dev/posts/alert-never-sent/).

## Why the sites are checked twice

Every public domain sits behind Cloudflare. An HTTP check against the domain proves Cloudflare answered, not that the app is alive: a dead origin can still return a Cloudflare error page. So each site is monitored at two levels.

- **At the edge**, by keyword. Matching a string only the real page renders catches a bad deploy serving the wrong content, which a status-code check never will.
- **At the origin**, against the hosting provider's domain directly, bypassing Cloudflare. That's what separates "my app is down" from "Cloudflare is having a day".

More on that: [Every site is monitored twice](https://wjmaritz.dev/posts/monitor-every-site-twice/).

## Why a tenant domain is DNS only

A Microsoft 365 tenant domain often has no working web origin. An HTTP monitor would sit permanently red and teach nothing. What matters for a tenant domain is DNS, so the example checks that MX resolves and that the SPF record is still there.

## Limitation worth remembering

Everything runs from inside the house. If the home connection drops, all the external monitors go red and none of those sites are actually down. There's no outside vantage point. A second Uptime Kuma somewhere external, or a push monitor, is the only real fix.

## Tests

```sh
./.venv/bin/python -m unittest test_provision
```

They run `provision.py` against a fake Uptime Kuma, so no server is needed.

Built by Wilhelm Maritz.
