# Architecture invariants — CEO reference

Authoritative narrative also lives in `docs/architecture-decisions.md`,
`docs/milestone-2-identity-and-access.md`, and M4 design docs. This file is
the CEO’s checklist form.

---

## Data & runtime

| # | Invariant | Enforcement |
|---|---|---|
| D1 | PostgreSQL is the sole source of truth for orchestration state | Reject Redis/Kafka/etc. as SoT; queues may be derived later, never authoritative |
| D2 | Alembic migrations own schema | No manual prod DDL; every table change is a revision with downgrade |
| D3 | `WorkspaceScopedMixin` / `workspace_id` on tenant tables | Code review + schema tests |
| D4 | FORCE RLS on tenant tables | Migration helpers + adversarial `app_runtime` probes |
| D5 | Runtime role ≠ table owner | `APP_DATABASE_URL` / `app_runtime`; service-role only where policies deny writes |

## Security & identity

| # | Invariant | Enforcement |
|---|---|---|
| S1 | Supabase issues JWTs; API verifies only | No local password auth / token minting for users |
| S2 | Workers use per-worker credentials | Hash-at-rest; constant-time compare; rotate/revoke |
| S3 | Uniform 401 on credential failure modes | Prevent enumeration |
| S4 | No secrets in audit logs or outbox payloads | Audit helper denylist / review |
| S5 | Admin mutations that bypass RLS go through service-role **after** explicit authz guards | Pattern in `workers` / concurrency admin routes |

## Orchestration correctness

| # | Invariant | Enforcement |
|---|---|---|
| O1 | Atomic claiming via `FOR UPDATE SKIP LOCKED` | WS2+ tests; never claim without row lock |
| O2 | Leases bounded; recovery never drops work silently | WS3 recovery → PENDING bump or DLQ |
| O3 | Provider effect keys prevent duplicate side effects | Unique `(workspace_id, effect_key)` |
| O4 | Outbox is the event bus foundation | Emit in same transaction as state change |
| O5 | Idempotent retries (claim tokens, submit, cancel) | Dedicated tests |

## Product controls

| # | Invariant | Enforcement |
|---|---|---|
| P1 | Human Review Gate is mandatory for gated stages | Controller + review_gates; recovery must not skip |
| P2 | Spend reservation before costly dispatch | `reserve_spend`; pause/`SPEND_HOLD` when over cap |
| P3 | Spend races serialize on `spend_caps` | `SELECT … FOR UPDATE` |
| P4 | Back-pressure never deletes PENDING work | WS4 state machine |

## Engineering hygiene

| # | Invariant | Enforcement |
|---|---|---|
| E1 | No placeholders / silent failures | CEO gate + grep audits |
| E2 | Warnings are errors in tests | `pytest -W error` |
| E3 | New RLS ⇒ adversarial tests in same PR | M4 plan rule |
| E4 | Design before production code for workstreams | `docs/M*_WS*_DESIGN.md` |
| E5 | Deterministic clocks in lease/liveness tests | Injectable `now=` |

## Explicit non-goals (until a CEO decision reopens)

- Rejected 369 numerology product caps
- Second datastore without a scale proof
- Real AI provider executors before abstraction + budgets/spend are ready
- Merging cloud-agent PRs without human order
