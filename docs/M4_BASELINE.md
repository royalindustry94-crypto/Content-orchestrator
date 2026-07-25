# Milestone 4 Baseline — Milestone 3 Freeze

**Date:** 2026-07-25
**Baseline branch:** `feature/milestone-4` (cut from `origin/main` @ `ca857ef`)
**Frozen release:** `v0.3.0-milestone-3` → `3bc4f3e` (squash-merged into main as `c03af2b`)

---

## 1. Repository State

- `origin/main` = `ca857ef17e47d301ab0281ed7791722f0616b94e` (merge commit `c03af2b` + merge-record doc note).
- Tree diff between `main` and tag `v0.3.0-milestone-3` under `apps/` is **empty** — main carries exactly the audited M3 code.
- Release tag verified on GitHub (annotated tag → `3bc4f3e`).
- CI green on the merge commit: run 30174413167 (api / web / worker).
- Feature branch `feature/milestone-3` deleted post-merge.
- Layout: `apps/api` (FastAPI + Alembic), `apps/worker` (reference worker client), `apps/web` (React/Vite scaffold), `docs/`.

## 2. Architecture Summary

- **Transactional outbox** — events emitted inside the caller's transaction; per-aggregate monotonic sequences via `pg_advisory_xact_lock` + unique index.
- **Relay** — polls PENDING events with `FOR UPDATE SKIP LOCKED`; per-consumer checkpoints; poison events → dead-letter queue.
- **Declarative workflow state machine** — `workflow_definitions`/`stages`/`transitions` with `on_success`, `on_review_approved`, `on_review_rejected` triggers.
- **Scheduler / dispatcher** — fair per-workspace caps, lease-based assignments with expiry reaping, worker matching by health + supported stages (GIN array index).
- **Human review gate** — pause/approve/reject with loud timeout failure.
- **Spend controls** — reservation against daily/monthly caps before dispatch; over-cap → `SPEND_HOLD`; release on failure/cancel.
- **Retry** — exponential backoff with full jitter (5s base, ×2, 300s cap, 3 attempts); unknown errors non-retryable; exhaustion → DLQ.

## 3. Database Summary

| Metric | Value |
|---|---|
| Migration head | `0024` (single linear head, `alembic heads` verified) |
| Migrations | 24 |
| Tables | 33 (28 user-data + 5 infrastructure) |
| FORCE RLS tables | 28 |
| RLS policies | 54 |
| SQLAlchemy models | 32 |
| Indexes / FKs / checks | 103 / 74 / 271 |
| SECURITY DEFINER helpers | 4 (RLS recursion breakers) |

Fresh-database replay and downgrade/upgrade round-trip verified during the M3 final audit.

## 4. API Inventory (11 endpoints)

- `GET /health/live`, `GET /health/ready`
- `GET /me` (profile), `PATCH` profile update
- `GET /workspaces`, `POST /workspaces`, `GET /workspaces/{id}`, `PATCH /workspaces/{id}`
- `GET /workspaces/{id}/memberships`, `POST` add member, `PATCH /{user_id}` role change, `DELETE /{user_id}` remove/self-leave

All protected routes require a valid JWT (aud/sub/exp enforced); RLS is the second enforcement layer.

## 5. Worker Inventory

`apps/worker/worker/`: `client.py` (register → heartbeat → claim → execute → submit protocol), `core/` (config, DB session), `main.py` (loop entrypoint). Executor is a documented stub returning canned success — real AI execution is M4 scope.

## 6. Security Inventory

- JWT: `python-jose`, secret required at startup (no default), 401 on missing/garbage/expired tokens.
- RLS: adversarially verified (cross-workspace read/update → 0 rows; non-member insert → policy violation; self-leave only own row; no claim → no rows).
- No raw SQL string interpolation, no `verify=False`/`debug=True`/wildcard CORS, zero PUBLIC grants, zero hardcoded secrets.
- Infra tables (`consumer_checkpoints`, `event_consumers`, `worker_heartbeats`, `worker_registry`) are service-role-only by design.

## 7. RLS Inventory

28/28 user-data tables FORCE RLS; 54 policies; helper functions `app_current_user_id()`, `is_workspace_member()`, `is_workspace_admin()` (+1 membership-insert definer). Policy history: 0021 fixed recursion, 0022 insert policy, 0023 security-definer insert, 0024 self-leave delete.

## 8. Outstanding Technical Debt (health-audit findings)

1. **Spend-cap race** — `reserve_spend` does not lock the cap row (`SELECT FOR UPDATE`); concurrent reservations can both pass. *Highest-priority M4 fix.*
2. **4 "fix" migrations** (0021–0024) — all RLS-policy corrections on `workspace_memberships`; acceptable history, but signals that new policies need adversarial tests before merge (pattern now established).
3. **Duplicated helpers** — `_utcnow` and `reap_expired_leases` defined in two modules each; candidates for a shared `orchestration/util` module. Minor.
4. **Stale historical docs** — `docs/phase-1-removal-*.md` reference deleted Node-era files (`app.ts`, `db/schema.ts`); intentional as historical record, but should be marked "historical" or archived.
5. **Dead-code scan tooling** — `vulture` is not installable in this venv (no pip; Nix store); ruff's unused-code rules pass clean, but a dedicated dead-code pass should run in CI in M4.
6. **Metrics unwired** — `orchestration/metrics.py` counters exist but are not exported anywhere.

No production-code defects found; per instructions, no code was modified.

## 9. Known Limitations (carried from M3)

- `JobType.RECURRING` raises `NotImplementedError` (intentional loud guard).
- Worker executor stub; web app scaffold-only (no product UI).
- Local workspace has no Node runtime — frontend verification relies on CI.
- Local PG occasionally emits Replit-internal "heliumdb" errors; clean-clone validation relies on CI.

## 10. Risks for Milestone 4

| Risk | Impact | Mitigation |
|---|---|---|
| Spend race under real provider costs | Financial overrun | Fix cap-row locking **before** wiring real providers |
| AI provider latency/failures vs lease expiry | Duplicate execution after lease reap | Idempotency keys on provider calls; lease heartbeat extension |
| RLS policy changes for new tables | Data leak regression | Mandatory adversarial RLS probes per new table (M3 audit pattern) |
| Outbox growth under real volume | Relay lag | Retention/archival job; index-only scans already in place |
| Secrets for AI providers | Leakage | Replit secrets manager only; never in config defaults |

## 11. Milestone 4 Prerequisites

1. Spend-cap `SELECT FOR UPDATE` hardening + concurrency test.
2. Provider abstraction interface in worker (idempotent, cost-reporting).
3. Provider API secrets provisioned (secrets manager).
4. CI job for dead-code scan and (optionally) migration replay from base.
5. Decision: recurring-job policy design for `JobType.RECURRING`.

## 12. Recommended Implementation Order

1. **Harden spend reservation** (cap-row locking, concurrency regression test) — protects money before anything spends it.
2. **Provider abstraction + usage reconciliation** in the worker (idempotency keys, cost write-back to `provider_usage`).
3. **First real executor** (script generation) end-to-end behind a review gate.
4. **Remaining executors** (voice, video) reusing the abstraction.
5. **Recurring producer** + implement `JobType.RECURRING` policy.
6. **Metrics export + tracing** (wire `metrics.py`).
7. **Web UI**: run dashboard → review-gate approvals → spend monitoring.
8. **Load/multi-replica validation** of relay + dispatcher.

---

*Baseline frozen. Milestone 4 implementation must not begin until explicitly instructed.*
