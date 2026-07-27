# Milestone 4 — Workstream 2 Implementation: Job Queue & Atomic Claiming

Implements the design in `docs/M4_WS2_DESIGN.md`. Adds a pull-based atomic
claim path on top of the existing `stage_assignments` queue and WS1 worker
identity/auth.

## What was built

### Schema — migration `0026_stage_claiming_ws2` (head 0026)
- `stage_assignments` gains claim bookkeeping: `claimed_at`, `claimed_by`
  (FK `worker_registry`), `claim_count` (default 0), `claim_token`.
- Constraint `ck_stage_assignments_claimed_by_matches`
  (`claimed_by IS NULL OR claimed_by = worker_id`).
- Partial index `ix_stage_assignments_claim (workspace_id, stage, created_at)
  WHERE status='pending'` — matches the claim predicate/order.
- New enum `claim_outcome` (`granted|no_work|capacity|ineligible`).
- New append-only table `stage_claim_audit` (workspace-owned): ENABLE+FORCE
  RLS, `GRANT SELECT` to `app_runtime`, `policy_select_members(admin/editor/
  reviewer)`, **no** insert/update/delete grant or policy (service-role write,
  no permissive fallback). Indexes on `(workspace_id, created_at)` and
  `(worker_id, created_at)`.
- Full `downgrade()` (verified up→down→up round-trip).

### Models
- `app/models/assignments.py` — new columns, index, check constraint.
- `app/models/claim_audit.py` — `StageClaimAudit` (WorkspaceScopedMixin +
  CreatedAtMixin, append-only). Registered in `app/models/__init__.py`.
- `app/models/enums.py` — `ClaimOutcome`.

### Service — `app/orchestration/claiming.py`
`claim_assignment(session, *, worker_id, now=None, claim_token=None)
-> ClaimResult` runs inside the caller's transaction:
1. Lock the worker row `FOR UPDATE` (serializes capacity math).
2. `claim_token` idempotency short-circuit: return the assignment already held
   under this token (DISPATCHED, claimed by this worker) instead of a new one.
3. Eligibility: worker must be non-deregistered, `ONLINE`, heartbeat fresher
   than `CLAIM_HEARTBEAT_MAX_AGE_SECONDS` (90 s, server clock), and under
   `max_concurrency`. Capacity → `CAPACITY`; anything else → `INELIGIBLE`.
4. Select one eligible assignment (`workspace_id` match, supported `stage`,
   `status='pending'`), oldest first, `FOR UPDATE SKIP LOCKED LIMIT 1`.
5. Transition PENDING→DISPATCHED, set claim fields + lease, bump `claim_count`,
   increment worker load (flip `BUSY` at capacity), write a `stage_claim_audit`
   row, emit `STAGE_ASSIGNED` via the existing outbox — all one transaction.

Non-grants are audited and returned, never raised (no silent failures).

### API — `POST /workers/claim` (machine auth)
In `app/api/routes/workers.py` on `worker_router`. Body `{claim_token?}`.
Opens an `AsyncSessionLocal` transaction, calls the service, commits, and
shapes `ClaimOut`. Returns 200 with `assignment: null` + reason for non-grants;
401 (from `get_current_worker`) for revoked/expired/invalid credentials. Emits
a `worker_claim` structured audit line (never logs the credential/secret).
Schemas `ClaimIn` / `ClaimedAssignmentOut` / `ClaimOut` in
`app/schemas/workers.py`.

## Key invariants & how they hold
- **One job → one worker:** `FOR UPDATE SKIP LOCKED` on the candidate row; once
  DISPATCHED the `status='pending'` predicate hides it from all other claims.
- **Never exceed capacity:** worker-row `FOR UPDATE` serializes concurrent
  claims by the same worker; the second sees the incremented load.
- **Workspace isolation:** predicate hard-filters
  `assignment.workspace_id = worker.workspace_id`; audit ledger is FORCE-RLS.
- **No partial state:** assignment mutation and load increment share one
  transaction; any failure rolls back both.
- **Idempotent retries:** `claim_token` returns the same assignment.

## Coexistence with the push dispatcher
The push path (`dispatcher.dispatch_stage`) still works unchanged. Both create
`STAGE_ASSIGNED` events with the same envelope; the claim path adds `via:
"claim"` to the payload. The claim endpoint is opt-in — workers that never call
it are unaffected.

## Validation performed
- `ruff check app tests` — clean.
- Full suite `pytest -W error` (warnings promoted to errors) — 88 passed,
  deterministic across repeated runs; total coverage 84%,
  `claiming.py` 99%.
- Fresh-DB migration `upgrade head → downgrade base → upgrade head` — clean,
  head 0026; `claim_outcome` present; `stage_claim_audit` FORCE-RLS with one
  member-select policy and zero write policies.
