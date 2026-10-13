# Secure ticketing observability

An easy-to-run Python prototype of a ticket-booking workflow with structured logs, trace/span correlation and cybersecurity alerts. The green-and-white dashboard follows the supplied internship report's visual layout, with working views and real local values instead of fixed screenshot numbers.

This is a **fresh reference implementation**, not recovered internship source code or Ticmint production software. It uses synthetic events only. No company document, certificate, personal details, payment data or real customer traffic is included.

![Dashboard from an actual local run](https://github.com/user-attachments/assets/c3777f99-bdc4-46ae-9b53-6d1d9a0c9b1b)

## Quick start

Requirements: Python 3.10 or newer. Internet is needed once to install Flask. No Docker, Node.js, cloud account, database or API key is required.

1. Download the repository ZIP from GitHub's **Code → Download ZIP**, then extract it.
2. On Windows, double-click **run.bat**. This creates a virtual environment, installs Flask and opens the dashboard. If `py` is missing, install Python from https://www.python.org/downloads/ and enable the launcher.
3. On macOS/Linux, run `sh run.sh`, then open **http://127.0.0.1:5000**.

Manual setup:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Keep the terminal open. Press Ctrl+C to stop. If port 5000 is already in use, set `PORT` before starting app.py and open that port instead. The server binds to loopback only.

## Demo in two minutes

1. Open **Events & booking**, choose an event and an available seat, then confirm.
2. Go to **Dashboard** for counts, request charts and recent logs.
3. Open **Traces**, select a booking and inspect its spans and matching JSON logs.
4. In **Events & booking**, click **Send 3 invalid bookings**. These are real local HTTP requests, not injected alert records.
5. Open **Security**, then **Investigate trace** to follow the alert into its failed request.
6. Search **Logs** by message, level or trace ID.

Refreshing dashboard views does not create ticketing requests. Loading events/seats and submitting bookings does. Charts aggregate actual requests per UTC minute; a single minute appears as a dot, not a fabricated trend.

## Features

- Two synthetic events, each with 12 seats.
- Seat reservation protected by a lock: concurrent requests cannot book the same seat twice.
- Explicit EVENT_NOT_FOUND, SEAT_NOT_FOUND and SEAT_UNAVAILABLE responses.
- Structured JSON logs with timestamp, level, service, region, partner_id, trace_id and span_id.
- Root request spans and child inventory/persistence spans with measured durations.
- Dashboard, logs, traces, metrics, security, services and booking views.
- HIGH alert after 3 booking failures from the same pseudonymous actor/source pair in 60 seconds, with alert deduplication.
- Privacy-focused field allowlist, process-local HMAC source pseudonyms, cross-origin POST checks and restrictive browser headers.
- Mobile layout, Windows launcher, repeatable demo and automated tests.

## Real run evidence

Run the tests and regenerate the deterministic scenario:

```sh
python -m unittest discover -s tests -v
python demo.py
```

The included test run passed **20 tests**. `demo.py` actually executed 7 requests: event discovery, seat lookup, 2 successful bookings and 3 failures, creating 1 HIGH alert. The demo counts differ from the UI screenshot scenario, which made 1 booking and then 3 invalid bookings. Trace IDs, timestamps and timings change every run.

Evidence files:

- `evidence/test-results.txt`: captured unittest output.
- `evidence/demo-responses.json`: actual request results.
- `evidence/observability.json`: correlated traces, logs and alert from demo.py.
- `evidence/screenshots.md`: GitHub-hosted dashboard, trace and security screenshots from the running browser application.
- The companion source ZIP also includes JSON-log and 390px mobile captures.
- `evidence/ui-results.json`: completed browser checks, no JavaScript errors and no mobile horizontal overflow.

The browser screenshots were captured after real booking/alert actions, not copied from the supplied PDF. The UI structure and theme are recreated; it is not a pixel-for-pixel copy. Unimplemented payment/authentication services and the PDF's static volumes are deliberately not presented as live features.

## Files and API

```text
app.py          Flask routes and local server
core.py         ticketing, trace/span model, logger and security monitor
demo.py         executable evidence scenario
templates/      dashboard HTML
static/         local CSS and JavaScript (no CDNs)
tests/          unittest suite
docs/           architecture, report mapping and incident runbook
evidence/       captured outputs from actual runs
artifacts/      runtime JSONL logs/traces/alerts (git-ignored)
```

| Endpoint | Purpose |
|---|---|
| GET /api/events | Discover synthetic events |
| GET /api/events/{event_id}/seats | Read seat availability |
| POST /api/bookings | Submit JSON event_id and seat |
| GET /api/observability | Current dashboard snapshot |
| GET /api/traces/{trace_id} | Trace and correlated logs |

## Important limits

- This models correlation in one process. It is **not distributed tracing**, W3C trace context propagation, OpenTelemetry or Grafana Cloud integration.
- Inventory and dashboard state are in memory and reset when the server restarts. JSONL evidence files append across runs; deleting artifacts/ clears saved evidence. They are not replayed into state.
- There is one fixed synthetic actor/partner. No real multi-tenant isolation, login, authorization, payment, email or SMS is implemented.
- The failure rule is a demo signal, not a proven intrusion detector. A legitimate customer can trigger it. It does not block IPs or users.
- No raw IP, email, phone, address or payment field is logged. Source pseudonyms are keyed per process and cannot correlate across restarts. Do not enter real personal data into this demo.
- Memory and JSONL files are not bounded; keep runs short. Do not deploy publicly, reverse-proxy or expose this Flask development server to a network.
- The source plan's cloud rollout, senior reviews, Jira/Slack setup and production definition of done are not claimed complete.

See [architecture](docs/architecture.md), [report mapping](docs/report-mapping.md) and [security runbook](docs/security-runbook.md).
