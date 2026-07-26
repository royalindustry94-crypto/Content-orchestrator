# Milestone 4 — Workstream 1 Audit (2026-07-26)

Scope audited: worker registry hardening as approved with amendments in
`docs/M4_WS1_DESIGN.md`. Branch `feature/milestone-4`.

## Verification results

| Check | Result |
|---|---|
| Test suite | **68 passed / 0 failed** (was 39 at M4 baseline; +21 WS1 acceptance tests, +8 audit-logging tests) |
| Coverage | 84% (`app` package; baseline 85.45% — new HTTP/auth surface area, all critical paths covered) |
| Lint (ruff) | clean — `app`, `tests`, `apps/worker/worker` |
| Migration head | `0025` (baseline `0024`) |
| Fresh-DB replay | `upgrade head` on empty DB ✓; `downgrade 0024` ✓; re-`upgrade head` ✓ |
| FORCE-RLS tables | 31 (baseline 28: +`worker_registry`, +`worker_heartbeats`, +`worker_credentials`) |
| RLS policies | 56 (baseline 54: +registry select, +heartbeats admin select; `worker_credentials` deliberately has **zero** policies/grants — service-role only) |
| HTTP endpoints | 21 (baseline 11: +3 machine worker endpoints, +7 admin worker endpoints) |

## Mandated acceptance tests — all present and passing

Duplicate registration (idempotent, single row) · concurrent registration ·
stale heartbeat → server-driven offline (89s/91s boundary + idempotent
re-sweep) · heartbeat replay/duplicate delivery · secret rotation
(zero-downtime grace, old credential dies at expiry) · revoked worker → 401 ·
expired credential → 401 · cross-workspace worker invisible (HTTP 403 + RLS
row-hidden) · adversarial RLS probes as `app_runtime` (heartbeats admin-only,
registry read-only — UPDATE touches 0 rows, credentials permission-denied) ·
uniform 401 across all auth failure modes · drain admin-only and preserved
across re-registration · protocol-version negotiation/rejection · audit
logger refuses sensitive fields.

## Code review (architect pass)

Verdict: no severe security or correctness findings. Minor suggestions
addressed: audit-logging regression tests added
(`tests/test_audit_logging.py`); drain-is-intent-only operator note added to
the design doc. Rotate-vs-revoke concurrency test deferred (revoke is a
status flip on the same rows rotation grace-expires; both paths are
individually tested and the kill switch wins by construction — revoked
status is checked before expiry).

## Out of scope (unchanged, per approval)

No scheduling, claiming, lease, queue, back-pressure, or DLQ work.
Workstream 2 has NOT been started.
