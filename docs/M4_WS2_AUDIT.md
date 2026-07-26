# Milestone 4 — Workstream 2 Audit: Job Queue & Atomic Claiming

**Date:** 2026-07-26 · **Branch:** `feature/milestone-4` · **Stance:**
adversarial — every claim guarantee was attacked with real PostgreSQL until it
held. All evidence is real-DB (no mocks).

## Required proofs (directive §Required Proof)

| Claim | Proof | Result |
|---|---|---|
| Two workers cannot claim one job | `test_two_workers_cannot_claim_one_job`: 5 workers race 1 pending row via concurrent `POST /workers/claim` | exactly **1** `granted`, `claim_count == 1` ✅ |
| Worker cannot exceed max concurrency | `test_worker_cannot_exceed_max_concurrency_under_load`: 1 worker (max 2), 6 assignments, 6 concurrent claims | exactly **2** granted, `current_load == 2`, status `BUSY` ✅ |
| Incompatible worker gets no work | `test_capability_mismatch` (worker supports `scripting`, work is `voiceover`) | `no_work` ✅ |
| Revoked worker gets no work | `test_revoked_worker_cannot_claim` | **401** ✅ |
| Expired credential gets no work | `test_expired_credential_cannot_claim` | **401** ✅ |
| Stale worker gets no work | `test_stale_heartbeat_ineligible` (heartbeat 200 s old) | `ineligible`, reason "stale" ✅ |
| Offline worker gets no work | `test_offline_worker_ineligible` | `ineligible` ✅ |
| Cross-workspace worker gets no work | `test_workspace_mismatch` (pending row in another workspace) | `no_work` ✅ |
| Duplicate/concurrent claims are safe | `test_duplicate_claim_token_returns_same_assignment` + the two concurrency tests | same assignment returned, one row consumed ✅ |
| Rollback restores state | `test_rollback_restores_assignment_and_load` | assignment back to PENDING, `worker_id/claimed_by` NULL, `current_load == 0` ✅ |
| Claim ordering documented, starvation considered | FIFO `created_at ASC` (design §19) | oldest-first, no in-stage starvation ✅ |

## Directive test matrix (§Tests)
All present and passing: successful claim; no eligible assignment; capability
mismatch; workspace mismatch; revoked worker; expired credential; stale
heartbeat; offline worker; worker at capacity; concurrent workers claiming one
assignment; duplicate request; rollback after failure; invalid transition
(claim of a non-pending row → skipped); RLS adversarial probes; migration
upgrade/downgrade/upgrade. **Warnings are promoted to errors** in the final run
(`pytest -W error`).

## RLS results
- `stage_claim_audit`: ENABLE + FORCE RLS, one `SELECT` policy
  (`app_user_has_workspace_role`), **zero** insert/update/delete policies or
  grants. `test_claim_audit_rls_blocks_cross_workspace_and_writes`:
  - an admin of workspace B sees **0** rows of workspace A's ledger (RLS), and
  - an `app_runtime` `INSERT` into the ledger is **denied** (no grant/policy) —
    writes are service-role only.
- `stage_assignments`: unchanged RLS (member SELECT only, no runtime write
  policy); new columns inherit it. Claims mutate via the service role.

## Concurrency results
Both concurrency tests exercise genuine parallel transactions (separate
asyncpg connections through the ASGI transport), not simulated ordering:
- 5-workers-vs-1-job → 1 winner, 4 `no_work`; `claim_count == 1`.
- 1-worker-vs-6-jobs (6 concurrent claims, max 2) → 2 grants, load exactly 2.
The mechanism: worker-row `FOR UPDATE` serializes capacity math; candidate row
`FOR UPDATE SKIP LOCKED` guarantees distinct rows per claimer.

## Security review
- No shared global worker credential — claims authenticate per-worker (WS1).
- No secrets/authorization headers logged — the `worker_claim` audit line
  carries only `worker_id`, `outcome`, `assignment_id`.
- No direct writes to `main`; no force-push; PR open, not merged.
- No placeholders/silent failures — every non-grant is an explicit, audited
  outcome with a reason.
- No mocked PostgreSQL evidence; no in-memory queue; no external broker.

## Defects fixed during implementation
- Initial `_bring_online` test helper hardcoded `max_concurrency=2` in the
  register body, masking the capacity path; fixed to honor the provisioned
  value (test-only).
- No product defects found in the claim path under the attack battery.

## Final state
| Item | Value |
|---|---|
| Migration head | 0026 (up/down/up round-trip verified) |
| Test totals | 88 passed / 0 failed (deterministic; `-W error`) |
| WS2 tests | 19 |
| Coverage | 84% total; `claiming.py` 99% |
| Lint | `ruff check app tests` clean |

## Verdict
**VERIFIED** once pushed with green GitHub Actions and the open PR — atomic
claiming is proven safe under concurrency, RLS blocks cross-workspace reads and
tenant writes, and all directive proofs pass on real PostgreSQL. Out-of-scope
items (lease renewal, advanced scheduling, worker execution, extra
back-pressure) were intentionally not touched.
