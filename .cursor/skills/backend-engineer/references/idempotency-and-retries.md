# Idempotency & retries

## Idempotent APIs & worker ops

Every client/worker-retried mutation needs a defined replay policy:

| Mechanism | Example |
|---|---|
| Natural unique key | `idempotency_key` on `stage_assignments` (`run:stage:attempt`) |
| Client token | `claim_token` returns the same granted assignment |
| Effect key | `provider_effect_keys` unique `(workspace_id, effect_key)` |
| HTTP upsert | `PUT` budget/limit rows by natural key |

On replay:

- Return the original successful result when safe, **or**
- Return `409` with stable code when the state conflicts

Never create a second side effect because the client timed out.

## Retry with exponential backoff

Use existing helpers where present (`app.orchestration.retry.compute_backoff_seconds`).

Rules:

1. Retry **transient** failures only (worker unavailable, lock contention you requeue, network blips to your own API).
2. Do **not** blind-retry non-idempotent external provider calls without an effect key.
3. Bound attempts; on exhaustion route to DLQ / fail run / pause — **never silent drop**.
4. Backoff: base * multiplier^attempt, capped at max; add jitter only if the codebase already standardizes it.
5. Scheduler “no worker” loops must be bounded (`NO_WORKER_MAX_RETRIES` pattern).

## Outbox & at-least-once

- Consumers must be idempotent; relays may deliver more than once.
- Persist consumer checkpoints; poison messages → DLQ per design.

## Spend & review

- Retries of `reserve_spend` must not double-reserve beyond caps (row lock + status).
- Review decisions are durable; do not “retry approve” by creating duplicate gates without uniqueness guards.
