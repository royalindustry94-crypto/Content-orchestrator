# Milestone 4 — Workstream 3 Audit Report

**Branch:** `feature/milestone-4`  
**Scope:** Lease Management, Recovery, and Worker Reliability  
**Status:** VERIFIED (local gates) · CI pending on PR

## Invariants preserved

| Invariant | Evidence |
|---|---|
| Workspace isolation | Machine endpoints bind `workspace_id` from credential; assignment load filters by worker workspace; cross-workspace renew → 404 |
| RLS | `stage_recovery_audit` / `provider_effect_keys` FORCE RLS; SELECT-only for `app_runtime`; adversarial probes pass |
| Atomic claiming | WS2 SKIP LOCKED path unchanged except drain check + `lease_started_at` |
| Idempotency | claim_token (WS2); idempotency_key rewrite on requeue; provider_effect_keys unique |
| Audit logging | Recovery audit rows + `app.core.audit` on ack/renew/submit; immutable triggers |
| Cost controls | No spend path changes |
| Human Review Gate | Untouched |

## Security verification

| Check | Result |
|---|---|
| Revoked workers cannot renew leases | 401 at auth (`test_renew_rejects_revoked_credential`) |
| Stale workers lose leases | Offline sweep + `reap_worker_assignments` (`test_worker_crash_heartbeat_timeout_reaps`) |
| Cross-workspace access impossible | Workspace mismatch → 404; RLS probe empty for other user |
| Runtime users cannot bypass RLS | INSERT as `app_runtime` denied on recovery/effect tables |
| Audit logs immutable | `prevent_update` trigger on both new audit tables |

## Lease recovery verification

| Scenario | Result |
|---|---|
| Lease expiry → attempt+1 PENDING | Pass |
| Concurrent reapers (SKIP LOCKED) | Pass — no double bump |
| Renew wins vs reaper (live lease) | Pass |
| Reaper wins vs late renew | Pass — renew 403/409 |
| Worker restart reaps holdings | Pass (`worker_restart`) |
| Deregister reaps | Pass (`worker_deregistered`) |
| Max attempts → DLQ + FAILED | Pass |
| Provider effect key dedupe | Pass |
| Submit after reap rejected | Pass |
| Drain blocks claim | Pass |

## Defects found and fixed

1. **WS2 reaper return shape** — callers expected `StageAssignment`; now `RecoveryResult`. Updated WS2 test.
2. **`correlation_id` null on recovery fail** — `_fail_run` emit required correlation_id; recovery now backfills from assignment / generates UUID.
3. **Global cancel in WS3 fixture** — narrowed to current workspace to avoid shared-DB pollution.
4. **`mark_stale_workers_offline` return type** — now `list[uuid.UUID]` for same-tx reap; WS1 tests already discarded counts.

## Security findings

- No new SECURITY DEFINER functions.
- No secrets in audit events (credential material never logged).
- Revoke kill-switch now also reaps in-flight work (closes stranded-lease window).

## Blockers

None for WS3 scope. CI must confirm green on PR after push.

## Final status

**VERIFIED** (local PostgreSQL gates: API 116 passed `-W error`, worker 1 passed, ruff clean, migration up/down/fresh → `0027`, coverage ≈ 84%).
