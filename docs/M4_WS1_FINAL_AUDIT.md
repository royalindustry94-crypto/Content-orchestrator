# Milestone 4 — Workstream 1 Final Audit (2026-07-26)

**Auditor stance:** external, adversarial — the implementation was assumed
flawed until every attack failed. Branch `feature/milestone-4`.

**Verdict: ✅ VERIFIED** — after fixing two issues found during the audit,
every attack below fails and the implementation is correct and
deterministic.

---

## 1. Attacks performed and evidence

### Worker registration
- Duplicate registration (sequential + 5× concurrent): converges to **one**
  row, last write wins, no unique-constraint blow-up. ✅
- Register with unsupported `protocol_version` (99) → **422**. ✅
- Register with unknown capability fields (`extra="forbid"`) → **422**. ✅
- Register revives a soft-deregistered row without clearing admin `drain`. ✅

### Worker authentication
- Missing / empty / malformed (`abc.def`, `.`, `..`) tokens → uniform **401**. ✅
- Unknown credential id, wrong secret → **401** (constant-time compare with
  dummy-hash path for unknown ids; no state enumeration). ✅
- SQL injection in the bearer token (`' OR '1'='1`,
  `'; DROP TABLE worker_credentials;--.x`) → **401**; `worker_credentials`
  table confirmed intact afterwards (parameterized queries + UUID parse). ✅
- User JWT presented to a worker route → **401**. ✅
- Worker credential presented to an admin route → **401**. ✅

### Credential rotation
- Zero-downtime: both old and new credentials authenticate during the grace
  window; old credential dies exactly at its grace `expires_at`, new keeps
  working. ✅

### Credential revocation
- Kill switch revokes **all** active credentials → subsequent auth **401**. ✅
- **Race (rotate vs revoke) — FIXED (see §3).** Revoke now serializes behind
  an in-flight rotate via the worker row lock and kills the
  concurrently-created credential too; regression test proves it.

### Heartbeats
- Server-assigned timestamps; client clocks never consulted. ✅
- Replay / duplicate delivery (4× concurrent identical) → all **200**, state
  converges, history appends harmlessly. ✅
- `current_load > max_concurrency` → **422**. ✅
- Heartbeat reporting `offline` → **422**. ✅
- Heartbeat against a deregistered worker → **410**. ✅

### Offline detection
- 89 s silent (below threshold) → stays online; 91 s → flipped `offline`,
  load zeroed; second sweep idempotent. ✅
- Liveness thresholds (healthy < 30 s ≤ suspect < 90 s ≤ dead; `None` → dead). ✅

### Capability matching / negotiation
- Versioned spec validated; server rejects unsupported versions and echoes
  the accepted version — no silent downgrade. ✅

### RLS (direct SQL as `app_runtime` with `request.jwt.claim.sub` set)
- `worker_credentials` SELECT → **permission denied** (zero grants/policies,
  service-role only); secret hashes unreadable by any user role. ✅
- `worker_registry` UPDATE by a workspace admin → **0 rows** touched
  (FORCE RLS, no write policy); row unchanged. ✅
- `worker_heartbeats` SELECT: workspace **admin** sees telemetry; a normal
  member (reviewer) sees **0** rows; member still sees the registry row. ✅

### Cross-workspace isolation
- Outsider GET list/detail/heartbeats → **403** (guard) and RLS hides the
  pinned worker row entirely (count 0) at the SQL layer. ✅
- Admin of workspace A cannot reach a worker of workspace B (path-scoped
  query → 404; not-admin-of-B → 403). ✅

### Replay attacks
- Captured heartbeat replayed → idempotent, no corruption; possession of the
  bearer credential is already full worker authority, so replay grants
  nothing extra. ✅

### Race conditions
- Concurrent registration (5×) → one row. ✅
- Concurrent heartbeats (4×) → converges. ✅
- Rotate vs revoke → serialized after fix (§3). ✅

### Duplicate registration / duplicate heartbeat
- Both idempotent (see above). ✅

### Migration upgrade/downgrade
- Fresh DB `upgrade head` → `downgrade base` → `upgrade head`: clean,
  head `0025`. ✅

### PostgreSQL constraints (as superuser — all correctly REJECTED)
- `current_load < 0` → `ck_worker_registry_load_nonneg`. ✅
- `current_load > max_concurrency` → `ck_worker_registry_load_capacity`. ✅
- `max_concurrency < 1` → `ck_worker_registry_max_concurrency`. ✅
- deregistered but not offline → `ck_worker_registry_deregistered_offline`. ✅
- duplicate `(name, instance_key)` → `uq_worker_registry_name_instance`. ✅
- invalid credential status enum → rejected by `worker_credential_status`. ✅

### API authorization
- Provision/rotate/revoke/drain/heartbeat-list require workspace **admin**;
  list/detail require **member**; non-members → 403; wrong principal → 401. ✅

### Audit logging
- Audit helper **refuses** sensitive keys (`secret`, `worker_secret`,
  `secret_hash`, `token`, `authorization`, case-insensitive) → `ValueError`. ✅
- Every endpoint emits a structured event correlated by `X-Request-ID`;
  the provisioning secret is never logged (only ids). ✅

---

## 2. Test isolation / determinism
Discovered the suite was **non-deterministic** (2/1/0 failures across runs) —
the scheduler `poll_and_lease` over-fetch window and `reap_expired_leases`
batch were being crowded out by PENDING/LEASED `job_schedule` rows
accumulated from earlier suite runs on the shared DB (204 due-pending + 374
leased leftovers observed). **Not a WS1 product defect** (the WS1 tests
create zero job_schedule rows) but it blocked a trustworthy verdict.
**Fixed** (§3). Suite now: **6/6 consecutive clean runs**.

## 3. Fixes made during the audit

1. **Credential rotate/revoke concurrency race (product code).**
   `rotate` and `revoke` now both acquire the `worker_registry` row lock
   (`SELECT … FOR UPDATE`) before mutating credentials, serializing them.
   Previously a kill-switch `revoke` could read the active set before a
   concurrent `rotate` inserted its new credential, then leave that new
   credential ACTIVE after the admin believed everything was killed.
   Added deterministic regression test
   `test_rotate_revoke_serialized_kill_switch` (holds the worker lock with
   an uncommitted new credential, proves revoke blocks then kills it).

2. **Scheduler test isolation (test-only).**
   `test_scheduler_fairness_caps_per_workspace_per_tick` and
   `test_reap_expired_scheduler_leases_returns_to_pending` now retire
   pre-existing pending/leased `job_schedule` rows at test start, matching
   the existing "park leftover state" pattern.

Both committed as `9a1e9c1` and pushed; CI green on that SHA.

## 4. Final state

| Item | Value |
|---|---|
| Final code commit | `9a1e9c1` (fixes) — this audit doc committed on top |
| Test totals | **69 passed / 0 failed** (6/6 deterministic runs) |
| Coverage | **84%** (`app` package); WS1 modules: `worker_auth` 98%, `services/workers` 100%, `audit` 100% |
| CI status | **success** (GitHub Actions `CI` on `9a1e9c1`) |
| Migration head | **0025** (fresh-DB up/down/up verified) |
| FORCE-RLS tables | **31** |
| RLS policies | **56** (`worker_credentials` deliberately has zero) |
| Open PR | #2 → base `main` |

## 5. Final verdict

**VERIFIED.** Every enumerated attack fails; the two issues found during the
audit were fixed, regression-tested, committed, and pushed; CI is green and
the suite is deterministic. No known security or correctness defects remain
in Workstream 1 scope. Workstream 2 remains not started, per instructions.
