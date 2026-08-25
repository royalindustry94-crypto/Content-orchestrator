# Attack matrix guide

Build the matrix **before** adding tests. Every in-scope row needs at least one
deterministic attempt.

## Columns

| Field | Meaning |
|---|---|
| Surface | Claiming, RLS, spend, review, migration, UI, … |
| Attack | Concrete hostile or failure scenario |
| Expectation | Exact status/DB outcome |
| Evidence | Test name or command |
| Result | Pass/Fail |

## Minimum rows (when surface touched)

1. Happy path (still verify **DB effects**, not status alone)
2. Unauthorized / cross-workspace
3. Validation / boundary (empty, max, invalid enum)
4. Idempotent replay
5. Concurrent double-submit / double-claim / double-reserve
6. Crash/timeout/restart recovery
7. Illegal state transition
8. Rollback / failed TX leaves no partial rows or corrupted counters
9. Migration replay (if schema touched)

## Examples

| Surface | Attack | Expectation |
|---|---|---|
| Claim | Two workers claim one PENDING | Exactly one GRANTED |
| Spend | Two TX reserve last dollar | Exactly one reservation |
| Lease | Submit after expiry | 409 lease_expired; reaper owns row |
| RLS | Outsider SELECT | Zero rows |
| Review | Worker completes gated stage without approval | Blocked / no advance |
| Outbox | Retry after success | No duplicate side effect / safe replay |

Prefer injectable clocks over `sleep` for leases/heartbeats.
