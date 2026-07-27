# Milestone 4 — Workstream 2 Design: Job Queue & Atomic Claiming

**Branch:** `feature/milestone-4` · **Status:** design phase · **Author:** Replit

Workstream 1 shipped worker identity, per-worker credentials, machine auth,
heartbeats, server-driven offline detection, and RLS for `worker_registry` /
`worker_credentials` / `worker_heartbeats`. Workstream 2 adds the **pull-based
atomic claim path**: an authenticated worker asks the API for work, and the
server hands out at most one eligible `stage_assignment` per claim under
concurrency, transactionally coupling the assignment state change to the
worker's load accounting.

Scope is deliberately narrow (per directive): claiming only. **Out of scope:**
lease renewal beyond what already exists, advanced scheduling, worker
execution, and back-pressure beyond the existing per-workspace concurrency cap.

---

## 1. Tables and models

No new table is strictly required — `stage_assignments` (migration 0018)
already models the queue. WS2 **reuses** it and adds claim bookkeeping:

Existing `stage_assignments` columns of interest: `id`, `workspace_id`,
`pipeline_run_id`, `stage` (`content_stage`), `attempt_number`, `worker_id`
(FK `worker_registry`), `status` (`stage_assignment_status`),
`idempotency_key` (unique per workspace), `lease_expires_at`, `dispatched_at`,
`acknowledged_at`, `completed_at`, `result`, `correlation_id`, `trace_id`,
`version` (optimistic-lock trigger).

**New columns (migration 0026):**
- `claimed_at timestamptz NULL` — server clock at successful claim.
- `claimed_by uuid NULL REFERENCES worker_registry(id)` — the claiming worker
  (kept distinct from `worker_id` only for audit clarity; both are set to the
  same worker on claim, so a check enforces `claimed_by = worker_id` when
  `claimed_by IS NOT NULL`).
- `claim_count integer NOT NULL DEFAULT 0` — number of times this row has been
  claimed (diagnostic for reclaim-after-lease-expiry).

**New table (migration 0026): `stage_claim_audit`** — an append-only,
workspace-owned claim ledger (every claim attempt outcome), FORCE-RLS,
member-readable, service-role-writable. Columns: `id`, `workspace_id`,
`assignment_id NULL`, `worker_id NOT NULL`, `outcome` (new enum
`claim_outcome`: `granted`, `no_work`, `capacity`, `ineligible`), `stage NULL`,
`detail text NULL`, `correlation_id NULL`, `created_at`.

## 2. Migration plan

Single migration `0026_stage_claiming_ws2` (down_revision `0025`):
1. `ALTER TABLE stage_assignments ADD COLUMN claimed_at`, `claimed_by`,
   `claim_count`.
2. `ADD CONSTRAINT ck_stage_assignments_claimed_by_matches
   CHECK (claimed_by IS NULL OR claimed_by = worker_id)`.
3. Partial index `ix_stage_assignments_claimable ON (stage, created_at)
   WHERE status = 'pending'` already exists as
   `ix_stage_assignments_pending_stage`; add a covering composite
   `ix_stage_assignments_claim ON (workspace_id, stage, created_at)
   WHERE status = 'pending'` for the workspace-scoped claim poll.
4. `CREATE TYPE claim_outcome AS ENUM (...)`.
5. `CREATE TABLE stage_claim_audit (...)`; `enable_rls` (ENABLE + FORCE),
   `grant_runtime(select-only)`, `policy_select_members(admin/editor/reviewer)`.
   No INSERT/UPDATE/DELETE grant to `app_runtime` — writes are service-role
   only (mirrors WS1 audit-write pattern).
6. Full `downgrade()`: drop table, drop enum, drop constraint/index/columns.
Round-trip (up → down → up) is an acceptance gate.

## 3. Queue states and transitions

Reuse `stage_assignment_status`. Claim-relevant transitions:

```
PENDING --claim--> DISPATCHED        (worker pulls; worker_id+claimed_by set)
DISPATCHED --ack--> ACKNOWLEDGED     (existing; unchanged)
DISPATCHED/ACKNOWLEDGED --lease expiry--> PENDING (existing reaper; frees load, worker_id=NULL)
ACKNOWLEDGED --submit--> COMPLETED | FAILED (existing)
PENDING/DISPATCHED/ACKNOWLEDGED --cancel--> CANCELLED (existing)
```

A claim only ever consumes a `PENDING` row and moves it to `DISPATCHED`. No new
status value is introduced (a "claimed" row is a `DISPATCHED` row with
`claimed_by` set). Any other source state is an **invalid claim target** and is
skipped by the query (never an error — the row simply isn't eligible).

## 4. Claim eligibility (of an assignment)

A `stage_assignments` row is claimable by worker `W` iff **all** hold:
- `status = 'pending'`,
- `workspace_id = W.workspace_id` (strict workspace scoping),
- `stage = ANY(W.supported_stages)` (capability match),
- not already leased (guaranteed by `status = 'pending'`).
Ordering: `created_at ASC` (FIFO within a stage) → oldest work first, which
bounds starvation (see §19). Selection uses `FOR UPDATE SKIP LOCKED LIMIT 1`.

## 5. Capability matching

The worker's `supported_stages text[]` must contain the assignment's `stage`.
Enforced **in the SQL predicate** (`stage = ANY(supported_stages)` via the
worker's row, resolved before the assignment query) so an incompatible worker's
claim never even locks a row. A worker that supports zero matching stages gets
`no_work`.

## 6. Worker status & capacity rules

Before any assignment row is locked, the claiming worker's own
`worker_registry` row is loaded `FOR UPDATE` and must satisfy:
- `status = 'online'` (NOT `busy`/`draining`/`offline`),
- credential valid (enforced by machine auth before the handler runs —
  `get_current_worker`; revoked/expired credential ⇒ 401, never reaches claim),
- heartbeat fresh: `now - last_heartbeat_at < CLAIM_HEARTBEAT_MAX_AGE`
  (server clock only; default 90 s, matching the offline threshold),
- capacity available: `current_load < max_concurrency`.
On success `current_load += 1`; if it reaches `max_concurrency`, status flips to
`BUSY` (same rule the push dispatcher uses). A worker already at capacity gets
`capacity` outcome (HTTP 200 with `assignment: null` + reason, **not** an
error — capacity is normal back-pressure).

## 7. Transaction boundaries

The entire claim is **one transaction** on the **service-role session**
(`AsyncSessionLocal`; workers authenticate via machine auth, not user JWT, so
RLS user-scoping does not apply — workspace scoping is enforced in the query
predicate). Sequence inside the txn:
1. `SELECT ... FOR UPDATE` the worker row (locks capacity accounting).
2. Validate status / heartbeat / capacity. If invalid → write audit row
   (`capacity` or `ineligible`) and **commit only the audit** (see §14).
3. `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1` an eligible assignment.
4. If none → write `no_work` audit, commit.
5. Mutate assignment (→ DISPATCHED, set worker_id/claimed_by/claimed_at/
   dispatched_at/lease_expires_at, `claim_count += 1`) **and** worker load in
   the same txn; write `granted` audit; emit `STAGE_ASSIGNED` via the existing
   outbox; commit.
Any exception → full rollback: neither the assignment nor the load moves, no
partial state (§14).

## 8. Locking & `FOR UPDATE SKIP LOCKED`

- Worker row: plain `FOR UPDATE` (we *must* serialize capacity math for that
  worker; two concurrent claims by the same worker cannot both see load=N).
- Assignment row: `FOR UPDATE SKIP LOCKED` so N workers polling concurrently
  each lock a **different** pending row — no two workers block on or win the
  same row. This is the core of "two workers cannot claim one job."
- Lock order is always worker-row-then-assignment-row to avoid deadlock; a
  claim never locks two worker rows.

## 9. Idempotency

Assignment creation is already idempotent via
`uq_stage_assignments_workspace_idem (workspace_id, idempotency_key)`
(`{run}:{stage}:{attempt}`). For the **claim** itself, an optional
client-supplied `claim_token` (UUID) makes retbirth safe: if the worker
re-sends the same `claim_token`, and it already holds an assignment claimed
under that token (DISPATCHED, `claimed_by = worker`), the API returns that same
assignment instead of claiming a second one. Without a token, a claim is a
fresh pull each time (at-least-once semantics, safe because each pull consumes a
distinct row).

## 10. Duplicate-claim prevention

Two layers: (a) `SKIP LOCKED` + `status='pending'` predicate means once a row
is DISPATCHED it is invisible to every other claim; (b) the `claim_token`
idempotency short-circuit prevents a single worker's retried request from
consuming a second row. A worker cannot hold the same assignment twice because
the row leaves `pending` on first claim.

## 11. Workspace isolation

- Query predicate hard-filters `assignment.workspace_id = worker.workspace_id`.
- A worker whose `workspace_id` differs from an assignment can never lock it.
- `stage_claim_audit` is FORCE-RLS + member-select, so one workspace's admins
  cannot read another's claim ledger.
- Cross-workspace probe (worker of A, assignment of B) ⇒ `no_work`, and a
  direct SQL attempt as `app_runtime` returns zero rows (RLS).

## 12. RLS policies

- `stage_assignments`: unchanged — already ENABLE+FORCE RLS, member SELECT
  only, no runtime write policy (claims mutate via service role). New columns
  inherit the table's RLS automatically.
- `stage_claim_audit`: ENABLE + FORCE RLS; `GRANT SELECT` to `app_runtime`;
  `policy_select_members(['admin','editor','reviewer'])`; **no** insert/update/
  delete policy or grant → append-only, service-role-written, member-readable,
  cross-workspace-blocked. No permissive fallback policy anywhere.

## 13. Indexes

- Reuse `ix_stage_assignments_pending_stage (stage, created_at) WHERE
  status='pending'`.
- Add `ix_stage_assignments_claim (workspace_id, stage, created_at) WHERE
  status='pending'` — matches the exact claim predicate/order for index-only
  candidate scans.
- `stage_claim_audit`: `ix_stage_claim_audit_ws_created (workspace_id,
  created_at DESC)` for admin telemetry; `ix_stage_claim_audit_worker
  (worker_id, created_at DESC)`.

## 14. Failure behavior

- Ineligible worker (offline/stale/at-capacity): **HTTP 200** with
  `{assignment: null, reason: "..."}` — not an error; capacity/liveness are
  normal states. An audit row records the reason. (Revoked/expired credential
  is the exception: 401 from auth, before the handler.)
- No eligible work: HTTP 200, `assignment: null`, reason `no_work`.
- DB error mid-claim: transaction rolls back entirely (assignment stays
  pending, worker load unchanged); handler returns 500; **no partial state**.
- No silent fallbacks: every non-grant path names its reason and is audited.

## 15. Audit events

- Structured log line per claim (existing audit logger), `X-Request-ID`
  correlated, **never** logging the credential/secret/authorization header.
- Durable `stage_claim_audit` row per attempt with `outcome`.
- Domain event `STAGE_ASSIGNED` emitted through the existing transactional
  outbox on `granted` (same envelope the push dispatcher uses), so downstream
  consumers see push- and pull-assigned work identically.

## 16. Service / API contracts

**Service** `app/orchestration/claiming.py`:
```
async def claim_assignment(session, *, worker: WorkerRegistration,
    now: datetime | None = None, claim_token: uuid.UUID | None = None
) -> ClaimResult
```
`ClaimResult` = `{assignment: StageAssignment | None, outcome: ClaimOutcome,
reason: str}`. Pure DB logic, injectable `now` for clock-controlled tests,
no HTTP concerns. Runs inside a caller-provided txn.

**API** (machine auth, `worker_router`, prefix `/workers`):
```
POST /workers/claim
  auth: Bearer <credential_id>.<secret>
  body: { "claim_token"?: uuid }
  200: { "assignment": {id, stage, pipeline_run_id, attempt_number,
                        lease_expires_at, correlation_id, trace_id} | null,
         "outcome": "granted|no_work|capacity|ineligible",
         "reason": "<human text>" }
  401: invalid/revoked/expired credential
```
Reuses `get_current_worker`. The route opens an `AsyncSessionLocal`
transaction, calls the service, commits, and shapes the response.

## 17. Acceptance tests (real PostgreSQL)

Enumerated in §Tests of the directive; each is a real-DB test (no mocks):
successful claim; no eligible assignment; capability mismatch; workspace
mismatch; revoked worker; expired credential; stale heartbeat; offline worker;
worker at capacity; **N concurrent workers vs 1 assignment → exactly 1 winner**;
**1 worker vs M assignments respecting max_concurrency**; duplicate request
(same `claim_token`) → same assignment; rollback after injected failure →
assignment + load restored; invalid transition (claim of a non-pending row) →
skipped; RLS adversarial probes on `stage_claim_audit` and `stage_assignments`;
migration up/down/up. Warnings promoted to errors (`-W error`) in the final run.

## 18. Rollback strategy

- Code: revert on `feature/milestone-4`; no direct writes to `main`, no
  force-push, PR stays open (no auto-merge).
- Schema: `alembic downgrade 0025` drops the new table/enum/columns/indexes
  cleanly (verified by round-trip). The claim path is additive — reverting it
  leaves the existing push dispatcher fully functional.
- Runtime: the claim endpoint is opt-in (workers must call it); disabling it
  has no effect on push-based dispatch.

## 19. Race conditions & mitigations

| Race | Mitigation |
|---|---|
| Two workers claim one assignment | `FOR UPDATE SKIP LOCKED` + `status='pending'` predicate → each locks a distinct row; loser sees it gone |
| One worker's concurrent claims exceed capacity | Worker row `FOR UPDATE` serializes capacity math; second claim sees updated `current_load` |
| Claim races the offline sweep | Both lock the worker row `FOR UPDATE`; sweep-then-claim ⇒ claim sees offline ⇒ `ineligible`; claim-then-sweep ⇒ load already incremented, consistent |
| Claim races lease reaper | Reaper only touches DISPATCHED/ACKNOWLEDGED rows; a PENDING row being claimed is invisible to the reaper until DISPATCHED, and both use row locks |
| Claim races credential rotate/revoke | Auth resolves the credential before the txn; a revoke committed first ⇒ 401; committed after ⇒ this claim already authenticated (bounded by the request), next claim 401 |
| Starvation of old work | FIFO `created_at ASC` ordering ⇒ oldest pending row in a stage is always the next candidate; no priority inversion within a stage |
| Duplicate delivery of claim request | `claim_token` idempotency short-circuit returns the same assignment |

**Claim ordering (documented):** within a `(workspace, stage)`, strictly FIFO by
`created_at`. Across stages a worker supporting several stages takes whichever
compatible row is oldest overall (single ordered query, no per-stage
round-robin). This favors latency-bounded fairness and cannot starve any single
job because the oldest always sorts first.
