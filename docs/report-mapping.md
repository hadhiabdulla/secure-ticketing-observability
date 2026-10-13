# Mapping to the supplied academic report

| Report requirement | This implementation |
|---|---|
| Event discovery | Six sample events with categories, venues, dates and prices on the booking site |
| Seat map and seat selection | Fifty seats per event with multi-seat selection and an order summary |
| Booking confirmation | UUID booking references; reserved seats become unavailable |
| Failure handling | Unknown event/seat, duplicate seat and malformed-input errors |
| Structured logging | JSON records and local logs.jsonl |
| Trace/span correlation | Manual identifiers, parent spans, matching log explorer |
| Repeated-failure detection | Same pseudonymous source, 3 failures in 60 seconds, HIGH alert |
| Bot-burst detection | 8 booking attempts in 10 seconds from one source, MEDIUM alert |
| Dashboard evidence | Actual browser captures, not static PDF images |
| Automated tests | Python unittest, 24 tests |
| Data minimization | No contact/payment fields, source address pseudonymization |
| Easy local setup | One dependency, run.bat/run.sh or git clone, no external services |
| OTel/Grafana | Future work only, matching the report's stated limits |

The UI follows the report's green-and-white theme, left navigation, summary cards, charts, logs, trace explorer and security investigation, with the booking flow promoted to its own customer-facing website. It does not reuse the report's numbers, logos as image assets, sample payment/auth logs or people/company documents. The fourth summary card shows measured p95 rather than a made-up active-user count. Services are represented as logical local components, not deployed microservices.

This repository was implemented anew from the report's described behaviour. It does not authenticate the report's claimed earlier execution, internship completion or dates, and does not contain original internship source code.
