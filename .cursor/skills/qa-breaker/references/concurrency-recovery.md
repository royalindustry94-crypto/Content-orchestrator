# Concurrency & recovery QA

## Concurrency

Use separate asyncpg connections / `AsyncSessionLocal` sessions:

- Dual claim on one assignment
- Dual `reserve_spend` under cap
- Claim vs reaper around lease expiry
- Provider budget saturation vs other-provider claim

Assert single-winner semantics and durable counters (`current_load`, reservation rows).

## Recovery

- Lease expiry → PENDING attempt bump or DLQ — never silent drop
- Worker offline/deregister/revoke → holdings reaped
- Restart register → prior DISPATCHED not stranded
- Recovery does not skip Human Review Gate
- Re-run recovery twice → idempotent / safe

## Partial failure

- Abort mid-transaction → no half-written outbox+state pairs
- Failed commit → counters unchanged
- Duplicate submit with effect key → no double provider effect

Coordinate security framing of auth bypass with `/security-auditor`.
