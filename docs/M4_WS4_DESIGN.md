# Milestone 4 — Workstream 4 Design: Priority Queue, Back-pressure & Resource Protection

**Branch:** `feature/milestone-4` · **Status:** design complete · **Author:** Cursor Cloud Agent  
**Depends on:** WS1–WS3 (worker identity, atomic claiming, lease recovery)  
**Migration head before WS4:** `0028` · **WS4 revisions:** `0029`, `0030` (if split)

WS1–WS3 delivered the worker plane. Workstream 4 hardens **who gets work
next** and **how hard the system pushes**, closing plan §§4, 9 and the
baseline spend-cap race (§14 / missing test #1).

**In scope:**
- Assignment priority column + claim/dispatch ordering
- Age-based anti-starvation boost (deterministic, server-clock)
- Per-workspace queue-depth accounting and thresholds
- `BACKPRESSURE_ENTERED` / `BACKPRESSURE_CLEARED` outbox events
- Provider concurrency budgets enforced at claim and push-dispatch
- Spend-cap `SELECT … FOR UPDATE` hardening + concurrency regression test
- Admin APIs to read/update concurrency limits and provider budgets
- Comprehensive PostgreSQL-backed + adversarial RLS tests

**Out of scope (later WS):**
- `JobType.RECURRING` implementation
- DLQ replay endpoint / retention archival job
- Prometheus `/metrics` HTTP endpoint (table-derived collectors already exist)
- Real AI provider executors / provider abstraction beyond budgets
- Web UI

---

## 1. Architecture overview

```text
                    ┌─────────────────────────────────────────┐
                    │         PENDING stage_assignments         │
                    │  ordered by effective_priority DESC,      │
                    │            created_at ASC                 │
                    └──────────────────┬──────────────────────┘
                                       │
              claim / push-dispatch    │
                                       ▼
              ┌────────────────────────────────────────┐
              │  Eligibility gates (all must pass)      │
              │  1. workspace concurrency cap (exists)  │
              │  2. provider budget remaining (NEW)     │
              │  3. worker capacity / drain / heartbeat │
              │  4. capability / stage match            │
              └──────────────────┬─────────────────────┘
                                 │
                                 ▼
                         DISPATCHED + lease
                                 │
         queue depth ────────────┼──────────── spend reserve
         (PENDING count)         │            (FOR UPDATE cap)
                 │               │
                 ▼               ▼
        BACKPRESSURE_*     SPEND_HOLD / proceed
```

PostgreSQL remains the sole source of truth. No Redis, no in-memory
queues. All priority, budget, and cap decisions are transactional.

---

## 2. Priority model

### 2.1 Columns on `stage_assignments`

| Column | Type | Meaning |
|---|---|---|
| `priority` | `integer NOT NULL DEFAULT 0` | Base priority set at enqueue (workspace tier + caller hint) |
| *(computed)* | — | `effective_priority = priority + age_boost(created_at, now)` |

No separate `effective_priority` column: age boost is computed at selection
time from `created_at` and the server clock so it cannot drift stale and
needs no background refresher.

### 2.2 Age boost (anti-starvation)

```text
age_seconds = max(0, extract(epoch from (now - created_at)))
boost = min(floor(age_seconds / age_boost_interval_seconds) * age_boost_per_interval,
            age_boost_max)
effective_priority = priority + boost
```

Defaults (config):
- `assignment_age_boost_interval_seconds = 60`
- `assignment_age_boost_per_interval = 1`
- `assignment_age_boost_max = 100`

Invariant: any PENDING row eventually outranks any finite static priority
(bounded only by `age_boost_max`, which is intentionally high enough that
a 100-minute-old default-priority job beats a priority-99 brand-new job).

### 2.3 Workspace tier → base priority

Add optional `priority_tier` on `workspaces` (`smallint NOT NULL DEFAULT 0`,
range 0–10). When creating a PENDING assignment (controller enqueue /
dispatch_stage leaving PENDING / claim seed paths that set attempt),
base priority defaults to `workspace.priority_tier * tier_priority_weight`
(config default weight = 10). Callers may still set an explicit higher
`priority` on the assignment row later via admin tools; WS4 does not add
a public “bump priority” API beyond workspace tier.

### 2.4 Selection order

**Pull claim** and any “pick next PENDING” query:

```sql
ORDER BY
  (priority + LEAST(
      age_boost_max,
      FLOOR(EXTRACT(EPOCH FROM (now() - created_at)) / interval_s) * per_interval
  )) DESC,
  created_at ASC
```

Implemented in SQL (expression in `ORDER BY`) so SKIP LOCKED still
partitions correctly under concurrency. Config values are bound as
query parameters.

**Push dispatch** (`dispatch_stage`) does not pick among PENDING rows
today — it creates a new assignment. When it leaves work PENDING (no
worker), the row gets `priority` from the workspace tier. Claimers then
order correctly.

**Scheduler `job_schedule`** already orders by `priority DESC, run_after ASC`
— unchanged. WS4 may set job priority from the same workspace tier when
enqueueing stage jobs (controller `enqueue_stage`).

---

## 3. Back-pressure state machine

```text
                  queue_depth < soft_limit
         ┌──────────────────────────────────┐
         │                                  │
         ▼                                  │
   ┌───────────┐   depth >= soft_limit   ┌──────────────┐
   │  NORMAL   │ ───────────────────────► │  PRESSURED  │
   └───────────┘   emit ENTERED           └──────────────┘
         ▲                                  │
         │     depth < soft_limit           │ depth >= hard_limit
         │     emit CLEARED                 ▼
         │                            ┌──────────────┐
         └────────────────────────────│  THROTTLED   │
              depth < soft_limit      └──────────────┘
              emit CLEARED                  │
                                            │ claim/dispatch still
                                            │ allowed up to workspace
                                            │ max_concurrent_assignments
                                            │ but scheduler tick
                                            │ allowance reduced
```

| State | Meaning | Scheduling effect |
|---|---|---|
| NORMAL | depth < soft | Full fairness allowances |
| PRESSURED | soft ≤ depth < hard | Emit observability event; claim still FIFO+priority |
| THROTTLED | depth ≥ hard | Scheduler `max_per_scheduler_tick` halved (min 1); **work is never dropped** |

Depth = count of `stage_assignments` with `status = 'pending'` for the workspace.

Thresholds live on `workspace_concurrency_limits`:
- `queue_soft_limit integer NOT NULL DEFAULT 50`
- `queue_hard_limit integer NOT NULL DEFAULT 200`
- check: `queue_soft_limit > 0 AND queue_hard_limit >= queue_soft_limit`

Back-pressure signal rows (dedup) — table `workspace_backpressure_state`:
- `workspace_id` PK/FK
- `state` enum `normal|pressured|throttled`
- `pending_depth integer NOT NULL`
- `entered_at timestamptz`
- `updated_at timestamptz`
- FORCE RLS, member SELECT, service-role write

Transitions emit outbox events (at most one ENTERED/CLEARED per actual
state change per tick).

---

## 4. Provider concurrency budgets

### 4.1 Table `provider_concurrency_budgets`

| Column | Type |
|---|---|
| `id` | uuid PK |
| `workspace_id` | uuid NOT NULL FK |
| `provider` | text NOT NULL |
| `max_concurrent` | integer NOT NULL CHECK (> 0) |
| `version`, timestamps | standard |

Unique `(workspace_id, provider)`. FORCE RLS; admin write via service
role after guard; member SELECT.

### 4.2 In-flight accounting

A provider slot is consumed when a stage assignment is DISPATCHED or
ACKNOWLEDGED and the assignment's stage maps to a provider. WS4 uses an
explicit nullable column:

`stage_assignments.provider text NULL`

Set at claim/dispatch when the workflow stage (or worker capability)
declares a provider; otherwise NULL → budget check skipped (stage has no
provider cost surface).

Count query:

```sql
SELECT count(*) FROM stage_assignments
 WHERE workspace_id = $ws
   AND provider = $provider
   AND status IN ('dispatched','acknowledged')
```

### 4.3 Enforcement points

1. **Pull claim** — after locking worker, before locking assignment: if
   candidate has `provider` set, check budget; if at cap, skip that row
   (`SKIP LOCKED` next) or return CAPACITY with reason
   `provider budget exhausted` (prefer skip to next eligible row so one
   saturated provider cannot block another stage).
2. **Push `dispatch_stage`** — before attaching a worker; if over budget,
   leave assignment PENDING (same as “no worker”).
3. **Never drop** work — PENDING remains claimable when a slot frees.

Partial index:

```sql
CREATE INDEX ix_stage_assignments_provider_inflight
  ON stage_assignments (workspace_id, provider)
  WHERE status IN ('dispatched','acknowledged') AND provider IS NOT NULL;
```

---

## 5. Spend-cap locking (§14)

`reserve_spend` today reads the cap without locking. WS4 change:

```python
select(SpendCap).where(...).with_for_update()
```

Both concurrent reservations serialize on the cap row; the second sees
the first's reservation in `_spend_committed_plus_reserved` (same
snapshot after lock). No schema change required.

Test: two concurrent `reserve_spend` calls for the last remaining dollar
→ exactly one reservation, one `SPEND_HOLD`.

---

## 6. Failure & concurrency analysis

| Race | Locking | Outcome |
|---|---|---|
| N claimers, priority order | `FOR UPDATE SKIP LOCKED` on ordered candidates | Highest effective priority claimed first among unlocked rows; no double claim |
| Claim vs age boost boundary | Boost computed in SELECT expression with `now()` | Deterministic within a statement; slight cross-statement drift acceptable |
| Budget check vs concurrent claim | Worker row lock + assignment lock; budget count is committed in-flight | Two claimers for same provider: second may observe count including first after first commits; within one txn, count is snapshot — **mitigation:** take `FOR UPDATE` on the budget row before counting/assigning |
| Back-pressure tick vs claim | State table upsert under workspace advisory or row lock | At-most-one ENTERED/CLEARED per transition |
| Dual `reserve_spend` | `FOR UPDATE` on `spend_caps` | Serialized; second fails closed |
| Throttled scheduler vs claim | Independent | Claim still works; only scheduler tick intake slows |

**Budget row locking strategy:** on claim/dispatch when `provider` is set,
`SELECT … FROM provider_concurrency_budgets WHERE workspace_id=? AND provider=? FOR UPDATE`
then count in-flight. Missing budget row → no limit (fail-open for
unset providers; admin must insert a budget to constrain).

---

## 7. Migration plan

### `0029_priority_backpressure_ws4`

1. `workspaces.priority_tier smallint NOT NULL DEFAULT 0` + check 0–10
2. `stage_assignments.priority integer NOT NULL DEFAULT 0`
3. `stage_assignments.provider text NULL`
4. Replace/augment claim index:
   `ix_stage_assignments_claim_priority ON (workspace_id, priority DESC, created_at) WHERE pending`
   (keep old claim index or drop if redundant)
5. `ix_stage_assignments_provider_inflight` partial index
6. Extend `workspace_concurrency_limits` with `queue_soft_limit`, `queue_hard_limit`
7. Enum `backpressure_state`
8. Table `workspace_backpressure_state` + FORCE RLS + member SELECT
9. Table `provider_concurrency_budgets` + FORCE RLS + member SELECT;
   admin mutations via service role
10. Full downgrade

### Spend locking

No migration — code-only change in `reserve_spend`.

---

## 8. API contracts

### Admin (JWT + workspace admin)

#### `GET /workspaces/{id}/concurrency`
Returns limits + current pending depth + back-pressure state + in-flight counts.

#### `PUT /workspaces/{id}/concurrency`
Body: `{ max_concurrent_assignments?, max_per_scheduler_tick?, queue_soft_limit?, queue_hard_limit? }`  
Upserts `workspace_concurrency_limits`.

#### `GET /workspaces/{id}/provider-budgets`
List budgets.

#### `PUT /workspaces/{id}/provider-budgets/{provider}`
Body: `{ max_concurrent: int }` upsert.

#### `DELETE /workspaces/{id}/provider-budgets/{provider}`
Remove budget (unlimited again).

#### `PATCH /workspaces/{id}` (extend)
Optional `priority_tier` field (admin).

### Machine claim (unchanged path, new ordering/gates)

`POST /workers/claim` — response unchanged; selection uses priority +
provider budget skip.

### Events

```text
BACKPRESSURE_ENTERED = "backpressure.entered"
BACKPRESSURE_CLEARED = "backpressure.cleared"
```

Payload: `{ "state": "pressured"|"throttled"|"normal", "pending_depth": N, "soft_limit": S, "hard_limit": H }`

---

## 9. Module layout

| Module | Change |
|---|---|
| `orchestration/priority.py` | **New.** `effective_priority_sql()` / `compute_age_boost()` |
| `orchestration/backpressure.py` | **New.** depth query, state transition, emit events, tick helper |
| `orchestration/provider_budgets.py` | **New.** lock budget, count in-flight, `has_capacity()` |
| `orchestration/claiming.py` | Order by effective priority; skip over-budget providers |
| `orchestration/dispatcher.py` | Set priority/provider on create; budget gate |
| `orchestration/scheduler.py` | Apply throttle when THROTTLED; set job priority from tier |
| `orchestration/controller.py` | `reserve_spend` FOR UPDATE; enqueue priority from tier |
| `api/routes/concurrency.py` | **New.** admin limit/budget endpoints |
| `main.py` | Maintenance tick also runs `evaluate_backpressure()` |
| `core/config.py` | Age-boost + default soft/hard limits |
| `models/assignments.py`, `workspace.py`, `scheduling.py` | New columns/tables |
| `events/types.py` | BACKPRESSURE_* constants |

---

## 10. Compatibility invariants

| Invariant | Preservation |
|---|---|
| Workspace isolation | All new tables workspace-scoped + RLS |
| RLS | FORCE + adversarial probes |
| Atomic claiming | SKIP LOCKED retained; only ORDER BY / filters change |
| Idempotency | Claim token + effect keys untouched |
| Audit logging | Admin mutations emit `audit()`; back-pressure via outbox |
| Human Review Gate | Untouched |
| Spend controls | Strengthened (row lock); reservation semantics unchanged |
| Lease recovery (WS3) | Untouched |

---

## 11. Acceptance criteria

1. Design doc landed before production code.
2. Migrations `0029` (+ spend code) upgrade/downgrade; fresh replay; up→down→up.
3. Higher-priority PENDING claimed before lower-priority (same workspace).
4. Aged low-priority eventually precedes fresh high-priority (boost).
5. Provider budget: N+1st concurrent claim for same provider denied/skipped; other providers unaffected.
6. Queue soft/hard transitions emit exactly one ENTERED/CLEARED per change.
7. THROTTLED halves scheduler tick allowance; PENDING never deleted by back-pressure.
8. Concurrent `reserve_spend` cannot exceed daily cap.
9. Adversarial RLS on new tables; non-admin cannot PUT budgets.
10. WS1–WS3 suites remain green; `pytest -W error`; ruff; CI green.
11. Docs: `M4_WS4_IMPLEMENTATION.md`, `M4_WS4_AUDIT.md`.

---

## 12. Testing strategy

| Test | Asserts |
|---|---|
| `test_claim_respects_priority_order` | High priority claimed first |
| `test_age_boost_prevents_starvation` | Clock-injected; old low-pri wins |
| `test_provider_budget_blocks_excess` | Cap enforced under burst |
| `test_provider_budget_does_not_block_other_provider` | Isolation |
| `test_concurrent_claims_priority_skip_locked` | No double claim |
| `test_backpressure_entered_and_cleared` | Events + state row |
| `test_throttled_scheduler_reduces_tick` | Allowance halved |
| `test_backpressure_never_drops_pending` | Count preserved |
| `test_spend_cap_concurrent_reservations` | Exactly one wins |
| `test_admin_concurrency_api_authz` | Non-admin 403 |
| `test_provider_budgets_rls_adversarial` | Cross-ws / write deny |
| `test_backpressure_state_rls_adversarial` | Same |
| `test_migration_0029_roundtrip` | Columns/tables present |
| Regression: full WS1–WS3 suites | No regressions |

---

## 13. Config additions

```text
assignment_age_boost_interval_seconds: int = 60
assignment_age_boost_per_interval: int = 1
assignment_age_boost_max: int = 100
workspace_tier_priority_weight: int = 10
queue_soft_limit_default: int = 50
queue_hard_limit_default: int = 200
backpressure_eval_interval_seconds: int = 15  # share maintenance tick
```

---

## 14. Implementation order

1. Land this design (no production code in same commit).
2. Migration `0029` + models + enums + event types.
3. `priority.py`, `provider_budgets.py`, `backpressure.py`.
4. Wire claiming + dispatcher + scheduler + controller spend lock.
5. Admin API routes + workspace `priority_tier`.
6. Maintenance tick back-pressure evaluation.
7. Tests (priority, budget, back-pressure, spend race, RLS).
8. Implementation + audit docs; push; update PR.

**Do not begin Workstream 5 (RECURRING / DLQ replay / metrics HTTP).**
