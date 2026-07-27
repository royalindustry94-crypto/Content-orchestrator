# Milestone 4 — Workstream 3 Implementation Report

**Branch:** `feature/milestone-4`  
**Migration head:** `0027`  
**Depends on:** WS1 (`0025`) · WS2 (`0026`)

## Delivered

| Area | Implementation |
|---|---|
| Design | `docs/M4_WS3_DESIGN.md` (landed before production code) |
| Schema | Migration `0027_lease_recovery_ws3` |
| Lease bounds | `lease_started_at`, `lease_extension_count` on `stage_assignments` |
| Recovery | `app/orchestration/recovery.py` — attempt bump, DLQ exhaustion, audit |
| Provider idempotency | `provider_effect_keys` + `ensure_provider_effect_key` |
| Recovery audit | `stage_recovery_audit` (FORCE RLS, immutable trigger) |
| HTTP lease API | `POST /workers/assignments/{id}/ack\|renew\|submit` |
| Dead-worker path | Offline sweep returns flipped ids; same-tx reap |
| Restart / shutdown | Reap on register, deregister, credential revoke |
| Drain enforcement | Claim returns `ineligible` when `drain=true` |
| Maintenance tick | `_orchestration_maintenance_loop` in `main.py` |
| Reference worker | HTTP claim/ack/renew/submit; run loop in `worker/main.py` |
| Config | `assignment_lease_seconds`, `assignment_max_lease_seconds`, reaper interval/batch, default max attempts |
| Tests | `tests/test_lease_recovery_ws3.py` (+ WS2 reaper assertion update) |
| Decisions | `docs/architecture-decisions.md` WS3 section |

## Files (primary)

- `apps/api/alembic/versions/0027_lease_recovery_ws3.py`
- `apps/api/app/orchestration/recovery.py`
- `apps/api/app/orchestration/provider_effects.py`
- `apps/api/app/orchestration/dispatcher.py` (bounds + re-export)
- `apps/api/app/orchestration/claiming.py` (lease_started_at, drain, config)
- `apps/api/app/api/routes/workers.py` (ack/renew/submit + reap hooks)
- `apps/api/app/services/workers.py` (returns flipped worker ids)
- `apps/api/app/main.py` (combined maintenance tick)
- `apps/api/app/models/{recovery_audit,provider_effects,assignments,enums}.py`
- `apps/worker/worker/{client,main,core/config}.py`
- `apps/api/tests/test_lease_recovery_ws3.py`

## Behaviour notes

1. **Same-row requeue:** recovery bumps `attempt_number`, rewrites `idempotency_key`, clears lease/claim fields; `claim_count` preserved.
2. **Bounded renew:** rejected with `409 max_lease_exceeded` when `now + lease > lease_started_at + max`.
3. **Revoked credentials:** cannot renew (401 at auth); revoke also reaps holdings (`worker_revoked`).
4. **Submit:** records provider effect key first; conflict on in-flight attempt → 409; terminal replay → idempotent 200.
5. **WS2 reaper callers:** `reap_expired_leases` now returns `list[RecoveryResult]` (`.assignment`); WS2 test updated.

## Out of scope (WS4+)

Priority queues, provider budgets, RECURRING jobs, DLQ replay endpoint, Prometheus `/metrics`, spend-cap locking.

## Validation performed

- `pytest -W error` (API full suite)
- Worker pytest + ruff
- `alembic upgrade head` / `downgrade 0026` / `upgrade head` / `downgrade base` / `upgrade head`
- Fresh database `alembic upgrade head` → `0027`
- `ruff check` clean
