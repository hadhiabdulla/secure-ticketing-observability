# Mapping to the supplied academic report

| Report requirement | This implementation |
|---|---|
| Event discovery | Two synthetic events in Events & booking |
| Seat map and seat selection | Available/booked seats and selected-seat control |
| Booking confirmation | UUID booking confirmation; reserved seat becomes unavailable |
| Failure handling | Unknown event/seat and duplicate seat errors |
| Structured logging | JSON records and local logs.jsonl |
| Trace/span correlation | Manual identifiers, parent spans, matching log explorer |
| Repeated-failure detection | Same pseudonymous actor/source, 3 failures in 60 seconds |
| HIGH alert | Real alert record with linked request trace |
| Dashboard evidence | Actual browser captures, not static PDF images |
| Automated tests | Python unittest, 20 tests |
| Data minimization | No contact/payment fields, source address pseudonymization |
| Easy local setup | One dependency, run.bat/run.sh, no external services |
| OTel/Grafana | Future work only, matching the report's stated limits |

The UI follows the screenshot's green-and-white theme, top status header, left navigation, four summary cards, charts, logs, trace explorer and security investigation. It does not reuse the screenshot's numbers, logos as image assets, sample payment/auth logs or people/company documents. The fourth summary card shows measured p95 rather than a made-up active-user count. Services are represented as logical local components, not deployed microservices.

This repository was implemented anew from the report's described behaviour. It does not authenticate the report's claimed earlier execution, internship completion or dates, and does not contain original internship source code.
