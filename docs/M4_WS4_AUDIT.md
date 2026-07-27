# Milestone 4 — Workstream 4 Audit Report

**Branch:** `feature/milestone-4`  
**Scope:** Priority Queue, Back-pressure & Resource Protection  
**Status:** VERIFIED · CI green on `3c365b5`

## Invariants preserved

| Invariant | Evidence |
|---|---|
| Workspace isolation | Budgets/limits/back-pressure state are workspace-scoped; claim filters by worker workspace |
| RLS | New tables FORCE RLS; member SELECT; runtime write denied (adversarial probes) |
| Atomic claiming | `FOR UPDATE SKIP LOCKED` retained; ORDER BY effective priority; savepoint skip for budgets |
| Idempotency | claim_token + assignment idempotency keys unchanged |
| Audit logging | Admin concurrency/budget mutations via `audit()`; back-pressure via outbox |
| Human Review Gate | Untouched |
| Spend controls | Strengthened with row lock; reservation semantics unchanged |
| Lease recovery (WS3) | Untouched |

## Security verification

| Check | Result |
|---|---|
| Non-admin cannot PUT concurrency / budgets | 403 |
| Cross-workspace SELECT of budgets/state | Empty under outsider JWT |
| Runtime INSERT/UPDATE on new tables | Denied (no grant / no write policy) |
| No secrets in audit events | Only ids / limits logged |

## Functional verification

| Scenario | Result |
|---|---|
| Higher priority claimed first | Pass |
| Age boost prevents starvation | Pass |
| Provider budget blocks excess | Pass (`capacity`) |
| Other providers unaffected | Pass |
| Concurrent claims no double-grant | Pass |
| BACKPRESSURE ENTERED/CLEARED once per transition | Pass |
| THROTTLED halves scheduler tick | Pass |
| Back-pressure never drops PENDING | Pass |
| Concurrent `reserve_spend` last dollar | Exactly one reservation |
| Migration 0029 columns/tables + FORCE RLS | Pass |
| WS1–WS3 regression suite | Green (full API suite) |

## Defects found and fixed

1. **Claim batch lock starvation** — locking a batch of PENDING candidates with `FOR UPDATE` held sibling rows until commit, so a concurrent claimer saw `no_work`. Fixed with per-candidate `SAVEPOINT` + skip list so over-budget (and non-chosen) locks release.
2. **HTTP 204 delete response body** — FastAPI rejected `DELETE …/provider-budgets/{provider}` with a typed `None` body; switched to `Response(status_code=204)`.
3. **Ruff** — import sort on `backpressure.py`; line length on `workspace.priority_tier`.

## Security findings

- No new SECURITY DEFINER functions.
- Admin budget mutations use service-role session only after `require_workspace_admin` (same pattern as worker credential writes).
- Missing budgets remain fail-open by design (documented); operators must configure budgets to constrain providers.

## Remaining risks

- Age boost is bounded by `assignment_age_boost_max` (default 100); extreme static priorities above that ceiling can still starve until boost saturates.
- Provider budget accounting depends on `stage_assignments.provider` being set; stages without a provider skip the budget gate.
- Legacy in-process claim paths that omit provider still behave as unlimited for that row.

## Blockers

None for WS4 scope.

## Final status

**VERIFIED**

- Local: API `136 passed` (`pytest -W error`), worker `1 passed`, `ruff` clean, migration `0029` up/down/fresh, coverage **83%**
- CI: https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/30276059715 (api/worker/web success on `bfb7f49`)
