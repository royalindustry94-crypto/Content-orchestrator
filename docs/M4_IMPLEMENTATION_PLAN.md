# Milestone 4 — Implementation Plan

**Baseline:** `feature/milestone-4` cut from `main` @ `ca857ef` (M3 release `v0.3.0-milestone-3`).
**Status:** Planning only — no implementation authorized yet.

M3 delivered the orchestration core (outbox, relay, state machine, scheduler/dispatcher, review gates, spend reservations, reference worker). M4 hardens the execution plane and makes workers real. Each section below states what exists, what changes, and how it is verified.

---

## 1. Worker Registry

**Exists:** `worker_registry` table (id, name, `supported_stages` array + GIN index, status, capacity fields); registration in the reference client.

**M4 changes:**
- Add `capabilities JSONB` (provider types, model families, max concurrency per provider) alongside `supported_stages` for finer matching.
- Add `version` and `drain` flag (graceful decommission: drain → finish leases → retire).
- Registration becomes idempotent upsert keyed on worker name + instance id.

**Verify:** registration/upsert tests; drain test proving no new claims while existing leases finish.

## 2. Heartbeats

**Exists:** `worker_heartbeats` table; client sends periodic heartbeats; dispatcher filters by heartbeat freshness.

**M4 changes:**
- Heartbeat payload gains in-flight assignment count and per-provider saturation.
- Server-side liveness policy: `healthy` (< 30s), `suspect` (30–90s), `dead` (> 90s) — thresholds in config, not hardcoded.
- Dead workers: leases reaped, assignments requeued (idempotency keys prevent double side-effects, §7).

**Verify:** clock-controlled tests for each liveness transition; reap-on-dead test.

## 3. Capability Matching

**Exists:** stage-based matching via `supported_stages @>` containment.

**M4 changes:**
- Two-phase match: stage containment (GIN, cheap) → capability predicate on JSONB (provider/model requirements from the workflow stage definition).
- Deterministic tie-break: least-loaded, then oldest heartbeat-refreshed worker, to spread load.

**Verify:** matrix test (stage × capability × load) asserting selected worker; property test that no unqualified worker is ever selected.

## 4. Assignment Queue

**Exists:** `stage_assignments` with PENDING partial index (`ix_stage_assignments_pending_stage`).

**M4 changes:**
- Priority column (workspace tier + age-based anti-starvation boost).
- Explicit queue-depth accounting per workspace to feed back-pressure (§9).

**Verify:** ordering tests (priority respected, starvation impossible past a bounded age).

## 5. Atomic Claiming

**Exists:** claim via `FOR UPDATE SKIP LOCKED` in the reference client.

**M4 changes:** none to the mechanism — it is correct. Add claim-time capability re-check (worker may have drained since match) and record `claimed_by`/`claimed_at` for audit.

**Verify:** N-workers × M-assignments concurrency test asserting exactly-once claims (extends existing test with contention).

## 6. Lease Management & 7. Recovery

**Exists:** lease expiry + reaping (`ix_stage_assignments_lease` partial index); reap requeues expired assignments.

**M4 changes:**
- **Lease extension**: long provider calls heartbeat-extend their lease (bounded max total lease) instead of racing the reaper.
- **Idempotency keys**: every provider-side effect carries `assignment_id + attempt` as an idempotency key so a reaped-then-requeued assignment cannot double-execute or double-spend. This is the critical recovery invariant for real AI providers.
- Recovery ladder: lease expiry → requeue (attempt+1) → retry policy (§backoff, existing) → exhaustion → DLQ (§10) → run marked FAILED with loud event.

**Verify:** simulated worker death mid-execution; assert single provider side-effect via recorded idempotency keys; lease-extension race test.

## 8. Scheduling

**Exists:** scheduler tick with `FOR UPDATE SKIP LOCKED`; job types START_STAGE, STAGE_TIMEOUT, REVIEW_TIMEOUT, COMPENSATION; RECURRING raises `NotImplementedError`.

**M4 changes:**
- Implement `JobType.RECURRING`: cron-like `schedule_spec` column, next-fire computation on completion, jitter to avoid thundering herd. Removes the M3 loud-fail guard *with* a policy, per the guard's own instruction.
- Multi-replica safety statement: already safe via SKIP LOCKED; add a two-scheduler test to prove it.

**Verify:** recurring fire/refire tests with controlled clock; duplicate-fire impossibility under two concurrent schedulers.

## 9. Back-pressure

**Exists:** per-workspace fair caps and max-concurrent-assignment limits.

**M4 changes:**
- Provider-level concurrency budgets (e.g. max N concurrent calls per provider account) enforced at dispatch.
- Queue-depth thresholds emit `BACKPRESSURE_*` events for observability; over-threshold workspaces get scheduling deprioritized, never dropped.

**Verify:** dispatch test proving provider budget is never exceeded under a burst of eligible assignments.

## 10. Dead-letter Handling

**Exists:** DLQ table; poison outbox events and retry-exhausted work route to it.

**M4 changes:**
- DLQ replay endpoint (admin-only, §13) with per-item audit of who replayed and outcome.
- Retention policy: resolved DLQ items archived after a configurable window.

**Verify:** poison-event → DLQ test (closes M3 gap); replay round-trip test; RLS/authz test that non-admins cannot see or replay.

## 11. Metrics

**Exists:** `orchestration/metrics.py` counters, unwired.

**M4 changes:**
- Wire counters (claims, completions, failures, retries, DLQ arrivals, spend reserved/committed/released, queue depth, lease reaps) to a `/metrics` Prometheus-format endpoint (unauthenticated-safe: no workspace data, aggregate only).
- Add tick-duration histograms for scheduler/relay/dispatcher.

**Verify:** scrape-format test; counter-increment assertions inside existing flow tests.

## 12. PostgreSQL Migrations

- New revisions continue the single linear chain from `0024` (no branches).
- Each migration ships upgrade + working downgrade, replayed from base in CI (§16).
- Expected new migrations: worker capabilities/drain (§1), assignment priority (§4), recurring schedule spec (§8), spend-cap locking support if schema change needed (§14), DLQ retention fields (§10).
- Rule from M3 history (4 fix-migrations): **every migration touching a policy or table ships with adversarial RLS tests in the same PR.**

## 13. RLS

- Every new table: `FORCE ROW LEVEL SECURITY` + explicit policies before first data write; infra-only tables documented as service-role-only (existing pattern).
- New policy tests follow the M3 adversarial probe pattern (cross-workspace read/write/insert/delete as `app_runtime`).
- No new `SECURITY DEFINER` functions unless recursion demands it; each must be minimal and reviewed.

## 14. Spend Hardening (prerequisite #1, before any real provider)

- `reserve_spend` takes `SELECT ... FOR UPDATE` on the cap row; concurrent reservations serialize.
- Provider usage reconciliation: actual cost written back to `provider_usage` on completion; reservation adjusted (release delta or flag overrun).

**Verify:** two-transaction race test proving the M3 race is closed (this is Missing Test #1 in the baseline).

## 15. API Endpoints

New (all JWT + RLS, following existing route patterns):
- `GET /workspaces/{id}/runs`, `GET /runs/{id}` — run status + stage history.
- `POST /runs/{id}/review` — approve/reject a pending gate (editor/admin).
- `GET /workspaces/{id}/spend` — caps, reserved, committed.
- `GET /workers` (admin) — registry + liveness.
- `POST /dlq/{id}/replay` (admin) — §10.
- OpenAPI regenerated; contract test asserting the path inventory (extends M3 audit check).

## 16. PostgreSQL Tests & CI

- All tests run against real PostgreSQL (existing pattern); no mocks of the database.
- Close the six baseline "Missing Tests" (spend race, poison DLQ, review timeout, lease contention, retry exhaustion, HTTP negative paths).
- CI additions: migration replay from base on fresh PG service container; dead-code scan job; coverage gate raised only after new code lands (keep ≥ 70%, target ≥ 85%).

## 17. Documentation

- Update `docs/architecture-decisions.md` per new decision (idempotency keys, lease extension, recurring policy).
- `docs/M4_RELEASE_REPORT.md` at milestone end, mirroring the M3 release package (metrics, checksums, audit).
- `replit.md` kept current at each merge.

---

## Implementation Order (dependency-driven)

1. Spend hardening (§14) — money safety first.
2. Worker registry/heartbeat/capability upgrades (§1–3) + idempotency keys (§7).
3. Assignment priority + back-pressure (§4, §9).
4. Recurring jobs (§8).
5. DLQ replay + retention (§10).
6. Metrics endpoint (§11).
7. API endpoints (§15).
8. Missing-test closure + CI additions (§16) — continuous, merged with each item above.

## Exit Criteria

- All six baseline missing tests implemented and green.
- Fresh-DB migration replay green in CI.
- Adversarial RLS probes green for every new table/policy.
- No `NotImplementedError` remaining in scheduled paths.
- Release package + audit equivalent to M3's before merge.
