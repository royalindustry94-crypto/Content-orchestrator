# Milestone 4 — Workstream 1 Design: Worker Registry, Heartbeats, Capability Model

**Status:** APPROVED WITH AMENDMENTS — implemented (see "Amendments" below).

## Amendments (approved 2026-07-26, as built)

The implementation diverges from this design where the approval mandated changes:

1. **No global `WORKER_AUTH_TOKEN`.** Replaced by a `worker_credentials` table (per-worker `credential_id` + SHA-256-hashed secret, workspace-pinned, `active|revoked` status, `expires_at`, `rotated_at`). Bearer format `<credential_id>.<secret>`; constant-time comparison; identical 401 for every failure mode. Admin endpoints: provision (secret shown once), rotate (zero-downtime — old credential gets a grace `expires_at`), revoke (immediate kill switch).
2. **Heartbeat telemetry is admin/operator-visible**, not hidden: `GET /workspaces/{id}/workers/{worker_id}/heartbeats` (workspace admin) with a matching admin-only RLS policy on `worker_heartbeats`.
3. Registration is idempotent (row created at provisioning; register updates it, revives soft-deregistered rows, never clears admin `drain`). Heartbeats are duplicate/replay-tolerant with server-assigned timestamps. Offline detection is server-driven (`mark_stale_workers_offline`, background sweep). Structured audit events with request IDs on every endpoint. Capabilities are versioned with protocol negotiation (accepted set `[1]`; server echoes accepted version). Clock skew: only the server clock is used anywhere — worker clocks are never consulted.
4. `worker_credentials` is service-role-only: FORCE RLS, zero policies, zero grants for app roles.

> **Operator note:** `drain` is currently an administrative *intent* flag on the registry row only. Dispatcher enforcement (excluding drained workers from new assignments) is deliberately out of WS1 scope and lands with the scheduling workstream.
**Scope:** registry, heartbeats, capabilities only. Explicitly excluded: scheduling, claiming, leases, queues, back-pressure, DLQ, execution.

## 0. What already exists (M3) vs. what WS1 adds

M3 shipped `worker_registry` + `worker_heartbeats` (migration 0017), a `worker_status` enum (`online|busy|draining|offline`), GIN-indexed `supported_stages`, and a reference client that registers/heartbeats **directly against the database** with the service role.

WS1 gaps to close:

| Capability | M3 state | WS1 change |
|---|---|---|
| Registration | direct DB insert, not idempotent | HTTP endpoint, idempotent upsert on `(name, instance_key)` |
| Deregistration | none | HTTP endpoint → `draining`/`offline` (soft; row retained for audit) |
| Version | none | `worker_version text` column |
| Capabilities | free-form JSONB, unused | validated schema: providers, model families, per-provider max concurrency |
| Offline detection | none (status only changes via dispatcher) | liveness thresholds + `mark_stale_workers_offline()` maintenance function |
| Worker auth | implicit (DB role) | dedicated worker bearer token (Replit secret) |
| Observability | none | admin `GET /workers`, `GET /workers/{id}` with computed liveness |
| Workspace isolation | nullable `workspace_id` pin, no RLS | RLS added for workspace-pinned reads (see §5) |

## 1. Database Schema (migration `0025`)

Additive `ALTER`s on `worker_registry` (no new tables; `worker_heartbeats` unchanged):

```sql
ALTER TABLE worker_registry
  ADD COLUMN instance_key   text NOT NULL DEFAULT gen_random_uuid()::text,
  ADD COLUMN worker_version text,
  ADD COLUMN drain          boolean NOT NULL DEFAULT false,
  ADD COLUMN deregistered_at timestamptz;
CREATE UNIQUE INDEX uq_worker_registry_name_instance
  ON worker_registry (name, instance_key);
ALTER TABLE worker_registry
  ADD CONSTRAINT ck_worker_registry_load_nonneg CHECK (current_load >= 0),
  ADD CONSTRAINT ck_worker_registry_load_capacity CHECK (current_load <= max_concurrency),
  ADD CONSTRAINT ck_worker_registry_max_concurrency CHECK (max_concurrency >= 1);
```

- `instance_key`: client-supplied stable identity per process instance → idempotent re-registration after crash/restart (same name+key = same row updated, not duplicated).
- `drain`: graceful decommission flag; a draining worker keeps heartbeating but (in later workstreams) receives no new work. Kept separate from `status` because drain is an *intent*, status is an *observation*.
- `deregistered_at`: soft deregistration timestamp; rows are never hard-deleted (audit trail; heartbeat history FK stays valid).
- Capabilities JSONB validated at the API layer (Pydantic), not by DB constraint — shape:
  `{"providers": [{"name": "openai", "models": ["gpt-*"], "max_concurrency": 2}], "features": ["script","voice"]}`.

Downgrade: drop the columns/constraints/index (no data loss for M3 columns).

## 2. SQLAlchemy Models

`app/models/workers.py`:
- `WorkerRegistration`: add `instance_key`, `worker_version`, `drain`, `deregistered_at` mapped columns (native enum pattern with `values_callable`, per project rule).
- `WorkerHeartbeat`: unchanged.
- New Pydantic schemas in `app/schemas/workers.py`: `WorkerRegisterIn`, `WorkerHeartbeatIn`, `WorkerOut` (includes computed `liveness`), `CapabilitySpec` (validated capabilities shape).

## 3. Alembic Migration

- Single revision `0025_worker_registry_ws1`, revises `0024`, linear chain preserved.
- Pure SQL `op.execute` style (project convention), upgrade + full downgrade, replayable from base (CI-verified).

## 4. Index Strategy

Existing indexes retained (GIN on `supported_stages`; partial on active status). New:
- `uq_worker_registry_name_instance` — idempotent upsert target.
- Partial index `ix_worker_registry_live ON worker_registry (last_heartbeat_at) WHERE deregistered_at IS NULL AND drain = false` — offline-detection scan touches only active rows.
- No index on `worker_version` or `drain` alone (low cardinality, never a leading predicate).

## 5. RLS Policies

`worker_registry` / `worker_heartbeats` are currently RLS-exempt infra tables (documented M3 decision). WS1 refines this because workspace-pinned workers are tenant-relevant:

- Enable `FORCE ROW LEVEL SECURITY` on `worker_registry` with policies:
  - `workers_select`: `USING (workspace_id IS NULL OR is_workspace_member(workspace_id, app_current_user_id()))` — global workers visible to any authenticated user (operational metadata, no tenant data); pinned workers visible only to their workspace's members.
  - **No INSERT/UPDATE/DELETE policies for `app_runtime`** — worker lifecycle writes go through the service role (RLS-bypassing `postgres`-owned session used by the worker endpoints), so end-user JWTs can never mutate the registry.
- `worker_heartbeats`: stays service-role-only (no user-facing reads in WS1; admin endpoint reads registry summary, not raw heartbeats). FORCE RLS with **no policies** for `app_runtime` = deny-all, which is stricter than M3's grant.
  - Requires revoking the M3 `GRANT SELECT ON worker_heartbeats TO app_runtime` (tightening, no functional loss).
- Adversarial probes (per project rule): pinned-worker invisibility across workspaces; user-JWT INSERT/UPDATE rejection; heartbeat table fully invisible to `app_runtime`.

## 6. Authentication & Authorization

Two principals:

1. **Workers** — machine auth via `WORKER_AUTH_TOKEN` (new Replit secret, no default; app refuses worker routes if unset). `Authorization: Bearer <token>` checked by a dedicated dependency with constant-time comparison. Worker routes use the service-role DB session (workers are not tenants). Token grants access **only** to `/workers/register`, `/workers/{id}/heartbeat`, `/workers/{id}/deregister` — nothing else.
2. **Users** — existing JWT auth for read endpoints; `GET /workers` list obeys RLS (§5). Drain toggle (`POST /workers/{id}/drain`) requires workspace admin for pinned workers; global workers' drain is service/ops-only in WS1 (no user role can set it) — revisit when an ops role exists.

Explicitly rejected alternative: per-worker issued tokens with rotation — deferred; single shared secret is acceptable while all workers are first-party, and the schema (`instance_key`) doesn't preclude upgrading later.

## 7. FastAPI Endpoints

| Method & path | Auth | Behavior |
|---|---|---|
| `POST /workers/register` | worker token | Idempotent upsert on `(name, instance_key)`; sets status `online`, clears `deregistered_at`/`drain` on re-register; validates capabilities schema; returns worker id + effective record. 409 if name+instance is deregistering elsewhere concurrently (see §9). |
| `POST /workers/{id}/heartbeat` | worker token | Updates `last_heartbeat_at`, `current_load`, `status` (worker-reported `online|busy|draining`), appends `worker_heartbeats` row. 404 unknown id; 410 if deregistered. Load > max_concurrency → 422 (constraint mirror). |
| `POST /workers/{id}/deregister` | worker token | Sets `deregistered_at = now()`, status `offline`, load 0. Idempotent (repeat → 200 same state). |
| `GET /workers` | user JWT | List with computed `liveness` (`healthy` <30s, `suspect` 30–90s, `dead` >90s or never; thresholds from config); RLS filters pinned workers. Filterable by `status`, `stage`. |
| `GET /workers/{id}` | user JWT | Single worker detail (RLS applies). |
| `POST /workers/{id}/drain` | user JWT (workspace admin, pinned only) | Sets `drain=true`; body `{drain: bool}` to undo. |

Reference worker client (`apps/worker`) is migrated from direct-DB registration/heartbeat to these HTTP endpoints (single lifecycle path; claim/execute stays DB-native until later workstreams).

## 8. Worker State Transitions

```
(unregistered) --register--> online
online  <--heartbeat(load<max)--   busy
online  --heartbeat(load>0, ==max)--> busy
online|busy --drain=true--> (status unchanged; scheduling-visible intent)
online|busy --deregister--> offline (deregistered_at set, terminal until re-register)
online|busy --no heartbeat > offline_after (config, default 90s)--> offline   [mark_stale_workers_offline()]
offline --register (same name+instance_key)--> online (row reused)
```

Invariants: `deregistered_at IS NOT NULL ⇒ status = offline ∧ current_load = 0`; `0 ≤ current_load ≤ max_concurrency` (DB checks). Status is never trusted blindly: liveness is always recomputed from `last_heartbeat_at` at read time; `mark_stale_workers_offline()` merely persists the observation (idempotent `UPDATE ... WHERE last_heartbeat_at < now() - interval AND status <> 'offline' AND deregistered_at IS NULL`). In WS1 it is invoked by tests and exposed as an internal function only — wiring into the scheduler tick is Workstream 3 (scheduling) scope.

## 9. Race Conditions & Mitigations

| Race | Mitigation |
|---|---|
| Two instances register with same `(name, instance_key)` concurrently | `INSERT ... ON CONFLICT (name, instance_key) DO UPDATE` — single row, last writer wins on metadata; no duplicates possible (unique index). |
| Heartbeat vs. deregister interleaving | Heartbeat `UPDATE ... WHERE deregistered_at IS NULL` → 0 rows → 410 to the worker; deregister wins deterministically. |
| Heartbeat vs. `mark_stale_workers_offline()` | Both are single-statement UPDATEs; row-level locking serializes them. A heartbeat landing just after mark-offline flips status back on the next heartbeat write (self-healing; no lost updates because heartbeat sets status explicitly). |
| Concurrent heartbeats from a confused duplicate process | Same row, serialized by row lock; append-only history records both (flapping is diagnosable, not corrupting). |
| Load counter drift (worker crashes between claim and heartbeat) | Out of WS1 scope (claiming untouched); DB check constraints keep values sane; offline detection zeroes stale workers' effective capacity at read time. |
| Version-counter lost update on registry row | Existing `set_version_and_updated_at` trigger + row locks; no read-modify-write cycles in endpoint SQL (single-statement upserts/updates). |

## 10. Acceptance Tests (all against real PostgreSQL)

1. Register: creates row, status online; response echoes capabilities.
2. Register idempotency: same `(name, instance_key)` twice → one row, updated metadata (version bump), 200 both times.
3. Register conflict-free concurrency: two parallel registers, same key → exactly one row.
4. Capabilities validation: malformed capabilities (unknown top-level key, negative concurrency) → 422, no row.
5. Heartbeat: updates `last_heartbeat_at`/load/status; appends history row.
6. Heartbeat guards: unknown id → 404; deregistered → 410; load > max → 422.
7. Deregister: sets terminal state; idempotent repeat; subsequent heartbeat → 410; re-register revives the same row.
8. Offline detection: clock-controlled `mark_stale_workers_offline()` — 89s silent worker stays as-is, 91s flips offline; deregistered/drained rows untouched; idempotent second run.
9. Liveness computation: healthy/suspect/dead thresholds at 29/31/91s.
10. Drain: admin sets/unsets on pinned worker; non-admin → 403; drain does not change status.
11. Auth: worker routes reject missing/wrong token (401); user JWT on worker routes → 401; worker token on user routes → 401.
12. RLS probes: pinned worker invisible to non-member (HTTP + direct SQL as `app_runtime`); global worker visible to all members; `app_runtime` cannot INSERT/UPDATE registry or SELECT heartbeats.
13. Migration: fresh-DB replay to `0025`, downgrade→upgrade round trip.
14. Reference client end-to-end: register → N heartbeats → deregister over HTTP against the app.
15. Regression: full existing suite stays green (dispatcher still selects workers correctly with new columns present).

**CI:** no new jobs required; existing api/worker jobs cover the new tests. (Plan §16's migration-replay-from-base CI job can ride along if desired — flagged as optional in this WS.)

**Documentation:** update `docs/architecture-decisions.md` (worker auth model, soft deregistration, RLS refinement) and `replit.md` current-state line.

---

**Decision requested:** approve this design (including the two opinionated calls: ① worker lifecycle moves to HTTP with a shared machine token; ② `worker_registry`/`worker_heartbeats` gain FORCE RLS with deny-all writes for user roles, tightening the M3 grants).
