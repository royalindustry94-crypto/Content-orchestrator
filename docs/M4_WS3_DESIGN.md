# Milestone 4 — Workstream 3 Design: Lease Management, Recovery & Worker Reliability

**Branch:** `feature/milestone-4` · **Status:** design complete · **Author:** Cursor Cloud Agent  
**Depends on:** WS1 (worker identity/heartbeats) · WS2 (atomic claiming)  
**Migration head before WS3:** `0026` · **WS3 revision:** `0027`

Workstream 1 delivered worker identity, credentials, heartbeats, and
server-driven offline detection. Workstream 2 delivered pull-based atomic
claiming with claim audit. Workstream 3 closes the **lease and recovery
plane**: workers must be able to renew leases over HTTP, expired or
orphaned leases must be recovered safely under concurrency, dead workers
must lose their work promptly, and every recovery action must be durable,
audited, and free of duplicate provider side-effects.

**In scope:** lease acquisition (existing claim/dispatch), lease renewal,
lease expiration, lease recovery, heartbeat monitoring integration,
stale-worker detection → lease reap, requeue of expired assignments,
crash recovery, worker shutdown/restart handling, duplicate-execution
prevention, lease extension bounds, retry scheduling on recovery,
dead-letter routing for exhausted recoveries, recovery audit logs.

**Out of scope (do not begin WS4):** priority queues, provider budgets,
RECURRING jobs, DLQ replay endpoint, Prometheus `/metrics`, spend-cap
locking, capability two-phase matching beyond what exists.

---

## 1. Lifecycle overview

```text
                    ┌─────────────────────────────────────────────────┐
                    │              ORCHESTRATION TICK                   │
                    │  (main.py: offline sweep + lease reaper)          │
                    └───────────────┬─────────────────┬─────────────────┘
                                    │                 │
                         mark_stale_workers_offline   reap_expired_leases
                         + reap_worker_assignments    (lease_expires_at < now)
                                    │                 │
                                    └────────┬────────┘
                                             ▼
                                   recovery algorithm (§6)
                                             │
                        ┌────────────────────┼────────────────────┐
                        ▼                    ▼                    ▼
                   requeue PENDING     route_to_dead_letter    no-op
                   attempt+1           (max attempts)          (already terminal)
                   audit + outbox      fail run                (SKIP LOCKED miss)

WORKER PROCESS
──────────────
 register ──► heartbeat loop ──► claim ──► ack ──► [renew…]* ──► submit
      │            │                │        │         │            │
      │            │                │        │         │            │
      │         last_hb_at       DISPATCHED  ACK      lease+        COMPLETED/
      │         ONLINE           + lease     +lease   bounded       FAILED
      │                                                         load--
 deregister / crash / revoke / stale heartbeat
      │
      ▼
  OFFLINE → holdings reaped (§7)
```

---

## 2. Lease state machine

Lease ownership is an attribute of a `stage_assignments` row, not a
separate entity. The lease is **held** only while status ∈
`{dispatched, acknowledged}` and `lease_expires_at IS NOT NULL`.

```text
                 claim / push-dispatch
  PENDING ──────────────────────────► DISPATCHED
    ▲                                    │
    │                                    │ ack (owner)
    │                                    ▼
    │                               ACKNOWLEDGED
    │                                    │
    │         renew (owner, lease live,  │  submit (owner)
    │         under max-total bound)     │
    │              ◄─────────────────────┤
    │              (status unchanged;    │
    │               lease_expires_at+)   ▼
    │                              COMPLETED | FAILED
    │
    │  recovery (lease expired | worker offline/deregistered)
    │  ── if attempt+1 ≤ max_attempts:
    │       clear lease/claim fields → PENDING (same row)
    │  ── else:
    │       FAILED + dead_letter_jobs + run failure path
    │
    └──────────────────────────────────────────────────────
```

**Invalid transitions (must reject loudly):**
- renew/ack/submit by non-owner worker → `403`
- renew/ack/submit when status not in allowed set → `409`
- renew when `lease_expires_at < now` → `409 lease_expired` (recovery owns it)
- renew when max total lease exceeded → `409 max_lease_exceeded`
- renew/ack/submit with revoked/expired credential → `401` (auth layer)
- renew by offline/deregistered worker → `403` / `410`

Terminal statuses (`completed`, `failed`, `cancelled`) never hold a lease.

---

## 3. Timeout strategy

All timers use the **API/database server clock**. Worker clocks are never
consulted (WS1 invariant).

| Timer | Default | Config key | Purpose |
|---|---|---|---|
| Claim / dispatch lease | 60s | `assignment_lease_seconds` | Time until first ack or renew must occur |
| Ack / renew extension | 60s | `assignment_lease_seconds` | Each successful renew/ack sets `lease_expires_at = now + N` |
| Max total lease | 900s (15m) | `assignment_max_lease_seconds` | Hard ceiling from `lease_started_at`; prevents immortal leases |
| Heartbeat healthy | < 30s | `worker_suspect_after_seconds` | Existing WS1 |
| Heartbeat suspect | 30–90s | between thresholds | Existing WS1 |
| Heartbeat dead / offline | ≥ 90s | `worker_offline_after_seconds` | Existing WS1; also claim eligibility |
| Offline sweep interval | 30s | `worker_offline_sweep_interval_seconds` | Existing WS1 |
| Lease reaper interval | 15s | `assignment_reaper_interval_seconds` | New; runs with offline sweep in one tick |
| Reaper batch size | 100 | `assignment_reaper_batch_size` | Bound lock duration |
| Claim heartbeat max age | 90s | reuse offline threshold | Already in claiming; move to config |
| Retry backoff | existing | workflow stage / retry.py | Used when recovery creates deferred retry jobs |

**Invariant:** `assignment_lease_seconds < worker_offline_after_seconds` is
recommended but not required. A live worker that stops renewing loses the
lease at `lease_expires_at`; a dead worker is flipped offline and its
holdings are reaped in the same tick without waiting for lease expiry.

**Bounded extension rule:**

```text
lease_started_at  set on first acquisition (claim or push-dispatch)
on renew/ack:
  if now + lease_seconds > lease_started_at + max_lease_seconds:
      reject (409 max_lease_exceeded) — reaper will reclaim when current
      lease_expires_at elapses (worker should checkpoint & stop)
  else:
      lease_expires_at = now + lease_seconds
      lease_extension_count += 1
```

---

## 4. Heartbeat timing

Unchanged thresholds from WS1. WS3 **integrates** heartbeats with leases:

1. Claim eligibility already requires fresh heartbeat (`CLAIM_HEARTBEAT_MAX_AGE_SECONDS`).
2. Lease renew requires the worker row to be non-deregistered and credential active;
   renew does **not** require a simultaneous heartbeat, but a worker that
   cannot heartbeat will be marked offline and lose leases via recovery.
3. Offline sweep (every 30s) + lease reaper (every 15s) share one
   `_orchestration_maintenance_loop` in `main.py`:
   - flip stale workers offline (zero load)
   - **immediately** reap assignments held by those workers
   - reap any other assignments with `lease_expires_at < now`

Heartbeat payload remains `{status, current_load}` in WS3 (in-flight
per-assignment count deferred; `current_load` already reflects holdings).

---

## 5. Lease renewal flow

```text
POST /workers/assignments/{assignment_id}/renew
Authorization: Bearer <credential_id>.<secret>
Body: {}   (optional: {"lease_seconds": N} ignored — server decides)

1. Authenticate worker (401 if revoked/expired/bad)
2. BEGIN
3. SELECT stage_assignments WHERE id=? FOR UPDATE
4. Assert workspace_id == worker.workspace_id (else 404 — no cross-tenant leak)
5. Assert worker_id == authenticated worker (else 403)
6. Assert status ∈ {dispatched, acknowledged} (else 409)
7. Assert lease_expires_at IS NOT NULL AND lease_expires_at >= now (else 409)
8. Assert under max-total bound (else 409)
9. Lock worker row FOR UPDATE; assert deregistered_at IS NULL (else 410)
10. lease_expires_at = now + assignment_lease_seconds
    lease_extension_count += 1
11. Append stage_recovery_audit? NO — renewals are normal; structured
    request audit via app.core.audit only
12. COMMIT
13. Return {assignment_id, lease_expires_at, lease_extension_count, status}
```

**Ack** (`POST .../ack`) is the first renew + status transition
`DISPATCHED → ACKNOWLEDGED`, setting `acknowledged_at`. Same ownership and
bound checks.

**Submit** (`POST .../submit`) finalizes COMPLETED/FAILED via existing
`dispatcher.submit_result`, after ownership checks. Clears lease fields.

---

## 6. Recovery algorithm

Single function family in `app/orchestration/recovery.py` (new module;
dispatcher reaper delegates here so claim and push paths share one path):

```text
recover_assignment(session, assignment, *, reason, now) -> RecoveryOutcome

Precondition: caller holds FOR UPDATE on the assignment row.
Statuses eligible: DISPATCHED | ACKNOWLEDGED.

1. previous_worker_id = assignment.worker_id
2. previous_attempt = assignment.attempt_number
3. previous_status = assignment.status
4. Decrement previous worker load (if any); flip BUSY→ONLINE if under cap
5. Determine max_attempts from WorkflowStage for (run.workflow, stage)
   — default 3 if stage def missing (fail-safe toward DLQ, never infinite)
6. next_attempt = previous_attempt + 1
7. if next_attempt > max_attempts:
      a. status = FAILED; completed_at = now; clear lease/claim fields
      b. route_to_dead_letter(related_table='stage_assignments', ...)
      c. controller path: fail the run (loud PIPELINE_FAILED)
      d. audit outcome=dead_lettered
      e. emit STAGE_REASSIGNED? No — emit STAGE_FAILED via controller
      f. return DEAD_LETTERED
8. else:
      a. status = PENDING
      b. attempt_number = next_attempt
      c. idempotency_key = f"{pipeline_run_id}:{stage}:{next_attempt}"
      d. clear: worker_id, lease_expires_at, lease_started_at,
         lease_extension_count→0, dispatched_at, acknowledged_at,
         claimed_by, claimed_at, claim_token
         (claim_count preserved — lifetime)
      e. emit STAGE_REASSIGNED {reason, previous_attempt, next_attempt}
      f. optionally schedule JobSchedule RETRY with backoff if reason
         warrants delay (lease_expired / worker_offline → immediate
         PENDING is enough; scheduler/claimers pick it up)
      g. audit outcome=requeued
      h. return REQUEUED
```

**Batch entry points:**

| Function | Selection predicate | Reason code |
|---|---|---|
| `reap_expired_leases` | status in (D,A) AND lease_expires_at < now | `lease_expired` |
| `reap_worker_assignments` | status in (D,A) AND worker_id = W | `worker_offline` / `worker_deregistered` / `worker_revoked` |
| `reap_max_lease_exceeded` | (optional) status in (D,A) AND lease_started_at + max < now — covered by lease_expires_at once renew is refused | n/a |

All use `FOR UPDATE SKIP LOCKED` + configurable `LIMIT`.

---

## 7. Crash recovery

| Failure | Detection | Recovery |
|---|---|---|
| Worker process crash mid-stage | Heartbeats stop → offline sweep; and/or lease expires | Reap holdings → PENDING attempt+1 |
| API process crash mid-claim | Transaction rolls back; row stays PENDING | No recovery needed |
| API process crash mid-reap | Transaction rolls back; next tick retries | Idempotent |
| DB restart | All state in Postgres | Tick resumes; leases may expire → reap |
| Network partition (worker alive, can't reach API) | Renew fails; lease expires | Reap; worker's late submit must fail ownership check (409) — **duplicate execution prevented at submit** |
| Worker restart | Soft: deregister old / register same credential; hard: new process same credential | On register, `current_load=0`; any stale holdings still on this worker_id are reaped by `reap_worker_assignments` called from register revival **or** by the next offline/reaper tick. Design choice: **on successful register, reap any DISPATCHED/ACKNOWLEDGED rows still pointing at this worker_id** (crash-before-offline race). |

**Duplicate execution prevention (critical):**

1. **Assignment uniqueness:** `(workspace_id, idempotency_key)` unique —
   requeue updates the key to the new attempt; two PENDING rows for the
   same attempt cannot exist.
2. **Provider effect key:** every provider-facing side effect must carry
   `provider_idempotency_key = f"{assignment_id}:{attempt_number}"`.
   Recorded in `provider_effect_keys` (new table) before the side effect;
   unique on `(workspace_id, effect_key)`. A recovered attempt has a
   **new** attempt_number → new key → allowed once. A crash that retries
   the **same** attempt with the same key is a no-op insert conflict.
3. **Submit ownership:** submit requires current `worker_id` match and
   non-terminal status; a reaped assignment cannot be completed by the
   crashed worker's late response.
4. **Claim token idempotency:** unchanged from WS2.

The reference worker executor records the provider effect key via the
service before "doing work" so tests can assert single side-effect under
simulated death.

---

## 8. Worker restart & shutdown flows

### 8.1 Graceful shutdown (drain)

```text
1. Admin sets drain=true OR worker calls local drain()
2. Worker stops claiming (client-side); WS3 also enforces drain in
   claim_assignment: if worker.drain → INELIGIBLE
3. In-flight: continue renew + submit until complete
4. deregister → OFFLINE, load=0; reap any remaining holdings
   (reason=worker_deregistered) — should be empty if graceful
```

### 8.2 Abrupt restart

```text
1. New process authenticates with same credential
2. POST /workers/register → status ONLINE, load=0, last_heartbeat_at=now
3. register handler calls reap_worker_assignments(worker_id,
   reason=worker_restart) for any stale DISPATCHED/ACKNOWLEDGED rows
4. Worker may claim fresh work (attempt+1 of recovered rows once PENDING)
```

### 8.3 Credential revoke

```text
1. Admin revokes → subsequent renew/ack/submit/claim → 401
2. Next maintenance tick: worker may still show ONLINE until heartbeat
   fails auth... actually revoke doesn't flip registry status.
3. WS3: after revoke, call reap_worker_assignments(reason=worker_revoked)
   in the same admin transaction (or immediately after) so work is not
   stranded until lease expiry.
```

---

## 9. Failure handling matrix

| Condition | HTTP / outcome | Durable effect |
|---|---|---|
| Lease expired at renew | 409 | Reaper requeues |
| Max total lease | 409 | Lease runs out → reaper |
| Non-owner renew | 403 | None |
| Cross-workspace assignment id | 404 | None (no existence leak across tenants beyond uuid guess) |
| Revoked credential | 401 | Holdings reaped on revoke path |
| Retryable stage failure | controller retry | New attempt via enqueue_stage |
| Lease recoveries exhaust max_attempts | DLQ + FAILED | `dead_letter_jobs` row |
| Permanent stage error | DLQ | existing |
| Concurrent reaper + renew | See §10 | One winner |

---

## 10. Race-condition analysis

| Race | Locking | Winner | Loser |
|---|---|---|---|
| Two workers claim same PENDING | `FOR UPDATE SKIP LOCKED` on assignment | One gets row | Other skips to next / no_work |
| Same worker two concurrent claims | `FOR UPDATE` on worker row | Serialized capacity | Second may CAPACITY |
| Renew vs reaper | Both `FOR UPDATE` assignment | Transaction order | If reaper commits first: renew sees PENDING/wrong owner → 409. If renew commits first: `lease_expires_at` in future → reaper predicate misses |
| Two reapers (multi-replica) | `SKIP LOCKED` | Partition rows | No double-requeue |
| Offline sweep vs heartbeat | Worker row lock | Heartbeat can revive | Sweep may flip then heartbeat flips back; holdings reaped only if still held after offline — **order in tick:** offline flip → reap by worker_id for flipped set **using the worker_ids returned/selected before flip**, or select assignments whose worker is offline/stale in one query |
| Submit vs reaper | Assignment `FOR UPDATE` | Same as renew | Late submit after requeue → 409 |
| Register (load=0) vs in-flight | Reap-on-register | Stale holdings requeued | — |
| Claim token replay | Lookup held DISPATCHED by token | Same assignment | — |
| Idempotency key update on reap | Unique index | Single row update | Conflict only if another row already has new key (should not happen) |

**Tick ordering (critical):**

```text
maintenance_tick:
  1. SELECT id FROM worker_registry WHERE stale ... FOR UPDATE SKIP LOCKED
  2. For each: status=OFFLINE, load=0; reap_worker_assignments(id, worker_offline)
  3. reap_expired_leases()  # catches holders that are still "online" but silent on renew
```

Doing reap in the same transaction as the offline flip prevents the window
where load=0 but assignments still say DISPATCHED for that worker.

---

## 11. PostgreSQL locking strategy

| Resource | Lock | Notes |
|---|---|---|
| `worker_registry` row | `FOR UPDATE` | Capacity, status, register, renew eligibility |
| `stage_assignments` row (mutate) | `FOR UPDATE` | ack/renew/submit/recover |
| Claim candidate | `FOR UPDATE SKIP LOCKED` | Multi-worker poll |
| Reaper candidates | `FOR UPDATE SKIP LOCKED LIMIT N` | Multi-replica safe |
| `provider_effect_keys` insert | Unique constraint | Conflict = duplicate suppressed |
| `stage_recovery_audit` insert | Append-only | No updates |
| No advisory locks | — | Row locks + SKIP LOCKED suffice |
| No Redis / in-memory lease map | — | All state in Postgres |

Partial index `ix_stage_assignments_lease` (existing) supports the expiry
scan. Add `ix_stage_assignments_worker_active` if needed:
`(worker_id) WHERE status IN ('dispatched','acknowledged')` — may already
be covered by `ix_stage_assignments_worker`.

---

## 12. Schema & migration plan (`0027_lease_recovery_ws3`)

**down_revision:** `0026`

### 12.1 Columns on `stage_assignments`

| Column | Type | Notes |
|---|---|---|
| `lease_started_at` | `timestamptz NULL` | Set on acquire; cleared on recover/complete |
| `lease_extension_count` | `integer NOT NULL DEFAULT 0` | Diagnostic / bound accounting |

### 12.2 Enum `recovery_outcome`

`requeued | dead_lettered | skipped`

### 12.3 Enum `recovery_reason`

`lease_expired | worker_offline | worker_deregistered | worker_revoked | worker_restart | max_lease_exceeded`

### 12.4 Table `stage_recovery_audit` (append-only)

| Column | Type |
|---|---|
| `id` | uuid PK |
| `workspace_id` | uuid NOT NULL FK workspaces |
| `assignment_id` | uuid NOT NULL |
| `previous_worker_id` | uuid NULL |
| `reason` | recovery_reason NOT NULL |
| `previous_status` | text NOT NULL |
| `previous_attempt` | int NOT NULL |
| `new_attempt` | int NULL |
| `outcome` | recovery_outcome NOT NULL |
| `detail` | text NULL |
| `correlation_id` | uuid NULL |
| `created_at` | timestamptz NOT NULL DEFAULT now() |

RLS: FORCE; `grant_runtime(SELECT)`; `policy_select_members` (admin/editor/reviewer);
no INSERT/UPDATE/DELETE for `app_runtime` — service-role writes only.
Indexes: `(workspace_id, created_at)`, `(assignment_id, created_at)`.

### 12.5 Table `provider_effect_keys`

| Column | Type |
|---|---|
| `id` | uuid PK |
| `workspace_id` | uuid NOT NULL |
| `assignment_id` | uuid NOT NULL |
| `attempt_number` | int NOT NULL |
| `effect_key` | text NOT NULL |
| `effect_kind` | text NOT NULL | e.g. `stage_execute` |
| `created_at` | timestamptz NOT NULL DEFAULT now() |

Unique: `(workspace_id, effect_key)`.
RLS: same append-only pattern as claim/recovery audit.

### 12.6 Downgrade

Drop tables, enums, columns, indexes. Full up→down→up gate.

---

## 13. API contracts

### Machine auth (`Authorization: Bearer <credential_id>.<secret>`)

#### `POST /workers/assignments/{assignment_id}/ack`

```json
// 200
{
  "assignment_id": "uuid",
  "status": "acknowledged",
  "lease_expires_at": "iso-8601",
  "lease_extension_count": 0,
  "attempt_number": 1
}
```

Errors: 401, 403, 404, 409, 410.

#### `POST /workers/assignments/{assignment_id}/renew`

```json
// 200
{
  "assignment_id": "uuid",
  "status": "acknowledged",
  "lease_expires_at": "iso-8601",
  "lease_extension_count": 3,
  "attempt_number": 1
}
```

#### `POST /workers/assignments/{assignment_id}/submit`

```json
// request
{
  "success": true,
  "result": {"...": "..."},
  "error_message": "",
  "provider_effect_key": "optional-override"  // default: "{id}:{attempt}"
}
// 200
{
  "assignment_id": "uuid",
  "status": "completed"
}
```

Submit records `provider_effect_keys` when `success` path executes side
effects; conflict on unique key → treat as idempotent success if the
assignment is already terminal for this worker/attempt, else 409.

### Admin (existing revoke/deregister paths)

- Credential revoke triggers `reap_worker_assignments(..., worker_revoked)`.
- Soft deregister triggers reap with `worker_deregistered`.

### Unchanged

- `POST /workers/claim`, register, heartbeat — preserved.
- Drain enforced in claim (INELIGIBLE when `drain=true`).

---

## 14. Config additions (`app/core/config.py`)

```text
assignment_lease_seconds: int = 60
assignment_max_lease_seconds: int = 900
assignment_reaper_interval_seconds: int = 15
assignment_reaper_batch_size: int = 100
assignment_default_max_attempts: int = 3
```

Move `CLAIM_LEASE_SECONDS` / `ACK_TIMEOUT_SECONDS` /
`CLAIM_HEARTBEAT_MAX_AGE_SECONDS` to read from settings (claiming +
dispatcher import settings; keep module-level aliases for back-compat in
tests if needed).

---

## 15. Module layout

| Module | Role |
|---|---|
| `app/orchestration/recovery.py` | **New.** recover_assignment, reap_expired_leases, reap_worker_assignments, record recovery audit |
| `app/orchestration/dispatcher.py` | acknowledge/renew_lease gain bound checks; reap delegates to recovery |
| `app/orchestration/claiming.py` | Set `lease_started_at`; enforce drain; read lease seconds from config |
| `app/orchestration/provider_effects.py` | **New.** ensure_provider_effect_key (insert-or-detect-duplicate) |
| `app/services/workers.py` | mark_stale_workers_offline returns flipped ids; optional combined helper |
| `app/api/routes/workers.py` | ack/renew/submit endpoints; revoke/deregister/register hooks |
| `app/schemas/workers.py` | LeaseOut, SubmitIn/Out |
| `app/main.py` | `_orchestration_maintenance_loop` replaces offline-only sweep |
| `apps/worker/worker/client.py` | HTTP claim/ack/renew/submit; drop direct-DB work path |
| `apps/worker/worker/main.py` | Minimal run loop: register → heartbeat task → claim/ack/execute/submit |

---

## 16. Compatibility invariants (must preserve)

| Invariant | How WS3 preserves it |
|---|---|
| Workspace isolation | All queries predicate `workspace_id`; machine auth binds workspace |
| RLS | New tables FORCE RLS; runtime SELECT-only; no runtime writes |
| Atomic claiming | Unchanged SKIP LOCKED path; drain check only |
| Idempotency | claim_token + idempotency_key update + provider_effect_keys |
| Audit logging | recovery audit table + `app.core.audit` on HTTP |
| Cost controls | No spend path changes; recoveries don't reserve spend |
| Human Review Gate | No changes to review_gates; recovery never bypasses gates |

---

## 17. Acceptance criteria

1. Design doc merged to branch before production code (this document).
2. Migration `0027` upgrades and downgrades; fresh-DB replay and
   up→down→up pass.
3. HTTP ack extends lease and sets ACKNOWLEDGED.
4. HTTP renew extends lease; rejects non-owner, wrong status, expired,
   max-total, revoked credential, deregistered worker.
5. Concurrent renewals serialize; final `lease_expires_at` is from the
   last commit; extension_count increases once per successful renew.
6. Lease expiry reaper: attempt+1, new idempotency_key, claim fields
   cleared, recovery audit row, STAGE_REASSIGNED emitted.
7. Dead worker: offline sweep + reap holdings without waiting for lease.
8. Worker crash mid-execution: after recovery + re-claim, provider effect
   key ensures single recorded side-effect per attempt.
9. Worker restart (re-register): stale holdings requeued.
10. Graceful drain: no new claims; in-flight completable.
11. Revoke: renew/claim 401; holdings reaped.
12. Max attempts on recovery → DLQ + assignment FAILED.
13. Adversarial RLS probes on `stage_recovery_audit` and
    `provider_effect_keys` (cross-workspace read denied; runtime write
    denied).
14. Reference worker uses HTTP claim/ack/renew/submit.
15. `pytest -W error` green for API + worker suites; ruff + typecheck
    clean; CI workflow green on the PR.
16. Docs: `M4_WS3_IMPLEMENTATION.md`, `M4_WS3_AUDIT.md`.

---

## 18. Test plan (PostgreSQL-backed)

| Test | Asserts |
|---|---|
| `test_ack_transitions_and_extends_lease` | status + lease |
| `test_renew_extends_lease` | lease_expires_at moved forward |
| `test_renew_rejects_non_owner` | 403 |
| `test_renew_rejects_expired` | 409 |
| `test_renew_rejects_max_total_lease` | 409 |
| `test_renew_rejects_revoked_credential` | 401 |
| `test_concurrent_renewals` | both succeed or one 409; count consistent |
| `test_duplicate_renew_after_reap` | 409 |
| `test_lease_expiry_requeues_with_attempt_bump` | attempt, key, audit |
| `test_lease_recovery_under_contention` | SKIP LOCKED, no double |
| `test_renew_wins_race_against_reaper` | stays with worker |
| `test_reaper_wins_race_against_late_renew` | renew 409 |
| `test_worker_crash_heartbeat_timeout` | offline + reap |
| `test_stale_worker_cleanup` | load 0, holdings PENDING |
| `test_worker_restart_reaps_stale_holdings` | register path |
| `test_shutdown_deregister_reaps` | worker_deregistered |
| `test_drain_blocks_claim` | INELIGIBLE |
| `test_recovery_exhaustion_routes_dlq` | DLQ row |
| `test_provider_effect_key_prevents_duplicate` | unique conflict |
| `test_submit_after_reap_rejected` | 409 |
| `test_recovery_audit_rls_adversarial` | cross-ws + write deny |
| `test_provider_effect_keys_rls_adversarial` | same |
| `test_migration_0027_upgrade_downgrade` | round-trip |
| `test_rollback_behaviour` | failed renew txn leaves lease unchanged |
| `test_reference_worker_http_e2e` | claim→ack→renew→submit |

Promote warnings to errors (`-W error`). No mocks of Postgres.

---

## 19. Architecture decisions (to append to `architecture-decisions.md`)

1. **Bounded leases with `lease_started_at`:** prevents heartbeat-extend
   from creating immortal assignments.
2. **Same-row requeue with attempt bump:** preserves assignment id for
   tracing; updates idempotency_key; claim_count is lifetime.
3. **Provider effect keys table:** durable duplicate-execution guard for
   provider side-effects across crash/requeue.
4. **Recovery audit ledger:** parallel to claim audit; append-only; RLS
   member-readable.
5. **Combined maintenance tick:** offline sweep and lease reaper in one
   loop with explicit ordering to close the load=0/still-DISPATCHED window.
6. **Reap on register/revoke/deregister:** do not wait for lease timeout
   when worker identity state changes.

---

## 20. Implementation order

1. Land this design doc (no production code in the same commit).
2. Migration `0027` + models + enums.
3. `recovery.py` + dispatcher/claiming/config updates.
4. HTTP ack/renew/submit + revoke/register/deregister hooks.
5. Maintenance loop in `main.py`.
6. Provider effect keys helper.
7. Reference worker HTTP migration + minimal run loop.
8. Comprehensive tests.
9. Implementation + audit docs; architecture-decisions update.
10. Push; update PR #2; run validation gates.

**Do not begin Workstream 4.**
