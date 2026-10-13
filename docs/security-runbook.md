# Booking security signals

## Signals

HIGH (repeated_booking_failures): at least three booking failures from the same pseudonymous source key within 60 seconds.

MEDIUM (request_burst): eight or more booking attempts from the same pseudonymous source key within 10 seconds, a scalper-bot pattern.

Both deduplicate per source key per 60-second cooldown. Scenario buttons deliberately trigger each rule. Alerts indicate a pattern requiring review, not a confirmed attacker.

## Investigate

1. Open Security and select Investigate trace.
2. Check the failed root span and its error child span.
3. Read correlated logs for EVENT_NOT_FOUND, SEAT_NOT_FOUND or SEAT_UNAVAILABLE.
4. Search the source pseudonym in Logs to compare the nearby pattern.
5. Determine whether this was the demo button, ordinary retries or a suspicious sequence.
6. Record your findings. Do not auto-block based on these demo rules.

## Recovery and limitations

For a legitimate seat conflict, choose an available seat. For a missing event/seat, refresh the event/seat selection. Restarting the server resets inventory, alerts and source keys, while artifacts/ retains append-only evidence. Stop the process before deleting artifacts/ to clear disk evidence.

Do not attempt real IP blocking, account suspension or production containment from this local demo. Those require authenticated production identity, approved controls, a reviewed policy and operator authority.
