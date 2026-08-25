# Locking, isolation & concurrency

## Defaults

- App uses PostgreSQL default **READ COMMITTED** unless an ADR says otherwise.
- Do not sprinkle `SERIALIZABLE` without measuring deadlocks and abort handling.

## Patterns used in this project

| Pattern | Use |
|---|---|
| `SELECT … FOR UPDATE` | Serialize check-then-act (spend caps, budgets, worker capacity) |
| `FOR UPDATE SKIP LOCKED` | Partition work across claimers/schedulers/reapers |
| Unique constraints | Idempotency under concurrent inserts |
| Same-TX outbox | Atomic state + event |

## Review questions

1. What rows are locked, in what order? (deadlock risk)
2. Is the lock held across external I/O? (**must not**)
3. Can two transactions both pass a read check and write? → need `FOR UPDATE` or unique conflict handling
4. On conflict, is the outcome explicit (409, capacity, pause) — not silent success?
5. Are advisory locks necessary? Prefer row locks on real entities; advisory locks only with documented keyspace

## Races to detect

- Double claim / double spend reservation
- Lost updates on status without version/lock
- Reaper vs submit/renew
- Concurrent DDL vs long transactions (ops concern)

## Idempotency & atomicity

- Natural keys + `UNIQUE` so concurrent retries collide safely
- One transaction for: domain mutation + outbox (+ ledger insert)
- Partial failure after external side effect → effect keys / compensating actions (orchestration concern, DB must provide uniqueness)

## Escalation

Unresolved races affecting money, tenant mix-ups, or irreversible migrations → **ESCALATE**.
