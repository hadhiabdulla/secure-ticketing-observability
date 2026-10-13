# Architecture

```text
Browser booking UI
  -> Flask route (root request trace/span)
     -> Inventory lookup/reservation (child span)
     -> Booking record (child persistence span)
     -> Structured JSON logs
     -> Failure detector (3 failures / 60 seconds)
        -> HIGH alert -> request trace -> spans -> matching logs
  -> Dashboard / trace explorer / security view
```

All components run in one process. `Ticketing.request()` creates a 32-character hexadecimal trace ID. `Ticketing.span()` creates 16-character span IDs and records parent relationships, status and measured elapsed milliseconds. Logs carry the currently active span ID.

An RLock protects seat validation and reservation as one atomic operation. The test suite submits eight concurrent booking attempts for the same seat and checks that exactly one succeeds. In-memory dictionaries are demonstration storage, not a production transaction database.

The source key is HMAC-SHA256 of synthetic user/source input under a random process-local key. Raw input is never written to logs or alerts. Only allowlisted structured fields are recorded. The application's messages are fixed strings, rather than arbitrary exception/request dumps. HTTP request input is length/type-checked before processing.

The dashboard's p95 is the nearest-rank 95th percentile of completed root request duration. Per-minute charts use actual UTC timestamps; they do not interpolate synthetic historical traffic. Error counts cover traced workflow failures, not malformed requests rejected before tracing. The HTTP-outcome chart uses those same completed workflow outcomes.

Future production work would require authenticated tenant context, persistent transactional inventory, genuine W3C propagation, OTel SDK instrumentation, a reviewed telemetry schema and managed Grafana Cloud exporters, plus alert review and deployment controls. No such migration is performed here.
