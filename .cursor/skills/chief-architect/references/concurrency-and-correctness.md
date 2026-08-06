# Concurrency, idempotency & retry hazards

Chief Architect must surface these **before** implementation, not after incidents.

## Common hazard catalog

| Hazard | Typical location | Required mitigation |
|---|---|---|
| Double claim | Pull claim / push dispatch | `FOR UPDATE SKIP LOCKED` on assignment; worker capacity lock |
| Lost update | Status transitions | Row lock or version check; single writer path |
| Check-then-act spend | `reserve_spend` | `FOR UPDATE` on `spend_caps`; recompute under lock |
| Provider double spend / double side effect | Worker submit / crash-retry | `provider_effect_keys` (or equivalent) unique per attempt |
| Lease extend forever | renew/ack | Max lease from `lease_started_at` |
| Reaper vs submit race | expiry | Submit rejects expired lease; reaper owns recovery |
| Concurrent migration + code | deploys | Expand/contract; order migrations before code that requires columns |
| Outbox dual-write drift | domain events | Emit outbox in **same transaction** as state change |
| Idempotent HTTP retry | claim/submit | claim_token / effect key / natural idempotency_key |
| Fairness starvation | scheduler/claim | Document ordering (priority, age boost); prove with tests |

## Review questions (must answer)

1. What is the **unit of atomicity** (one DB transaction)?
2. What rows are locked, in what order?
3. What happens if the process dies after commit? after side effect but before commit?
4. What makes a retry safe (key, status guard, unique constraint)?
5. What is the user/operator-visible outcome on contention (error code, pause, capacity)?
6. Can two replicas run this loop safely?

## Idempotency requirements

Production paths that clients or workers may retry **must** define:

- Idempotency key or natural unique key
- Replay behavior (return prior result vs conflict)
- Persistence of the key (DB unique constraint, not memory)

## Retry requirements

- Bounded retries with documented backoff for transient cases
- Exhaustion → DLQ / failed run / explicit pause — **never silent drop**
- Distinguishing retryable vs permanent errors (`is_retryable` policies)

## Human Review Gate & spend under concurrency

- Recovery/requeue must not auto-approve or skip review
- Spend holds must remain effective under concurrent reservations
- Financial and review invariants outrank throughput optimizations

## Tests the Architect requires

For architectural concurrency changes, require at least one of:

- Parallel async sessions / connections proving single-winner semantics
- Clock-injected lease/reaper races
- Adversarial duplicate submit/claim retries

No “looks fine in single-threaded test” for lock-sensitive paths.
