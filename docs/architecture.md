# Architecture

```text
Browser booking site (/)            Browser observability dashboard (/dashboard)
  -> Flask routes (root request trace/span)
     -> Inventory lookup/reservation (child span)
     -> Booking record (child persistence span)
     -> Structured JSON logs
     -> Failure detector (3 failures / 60 seconds) -> HIGH alert
     -> Burst detector (8 attempts / 10 seconds)   -> MEDIUM alert
        -> alert -> request trace -> spans -> matching logs
  -> Client-side animated scenario runners send real requests
Dashboard -> read-only snapshot / trace detail APIs (auto-refresh)
```

Both browser apps are served by, and share, one backend: booking activity and client scenario runs produce the telemetry the dashboard renders. Dashboard refreshes are observation reads and do not generate workflow telemetry. The booking site never talks to the dashboard directly; the shared `Ticketing` core is the connection.

All components run in one process. `Ticketing.request()` creates a 32-character hexadecimal trace ID. `Ticketing.span()` creates 16-character span IDs and records parent relationships, status and measured elapsed milliseconds. Logs carry the currently active span ID.

An RLock protects seat validation and reservation as one atomic operation. The test suite submits eight concurrent booking attempts for the same seat and checks that exactly one succeeds. In-memory dictionaries are demonstration storage, not a production transaction database.

The source key is HMAC-SHA256 of demo user/source input under a random process-local key. Raw input is never written to logs or alerts. Only allowlisted structured fields are recorded. The application's messages are fixed strings, rather than arbitrary exception/request dumps. HTTP request input is length/type-checked before processing, and cross-origin POSTs are rejected with 403.

Three detection rules feed the alert list: repeated booking failures (3 in 60 seconds from one pseudonymous source, HIGH) and request bursts (8 booking attempts in 10 seconds, MEDIUM, a scalper-bot signal). Malformed input (3 invalid or oversized requests in 60 seconds, MEDIUM) is the third rule. All deduplicate per source per minute and neither blocks anything; a legitimate rush can trip them.

The dashboard's p95 is the nearest-rank 95th percentile of completed root request duration. Per-minute charts use actual UTC timestamps; they do not interpolate synthetic historical traffic. Error counts include rejected booking requests: JSON parsing, size/type/length validation and cross-origin checks run inside request.validate under the root trace. Every rejection returns its trace ID and writes a WARN log without the submitted payload. Each booking POST is counted once for burst detection. The HTTP-outcome chart uses those same completed workflow outcomes.

Both pages share one stylesheet with light and dark themes via CSS variables; the toggle persists in browser localStorage and defaults to the system preference.

Future production work would require authenticated tenant context, persistent transactional inventory, genuine W3C propagation, OTel SDK instrumentation, a reviewed telemetry schema and managed Grafana Cloud exporters, plus alert review and deployment controls. No such migration is performed here.
