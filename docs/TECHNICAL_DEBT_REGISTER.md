# Technical Debt Register

**Repository:** Content Orchestrator  
**Updated:** 2026-09-09 (Phase 0/1 recovery audit — reconciled against merged `main`)  
**Current reference:** `main` @ `2ca92f8` (PR #94 and PR #95 merged 2026-09-09T13:19 UTC; superseded the prior unmerged `claude/project-builder-handover-k95wpm` reference below)

Severity: CRITICAL · HIGH · MEDIUM · LOW · INFO

Do not mark HIGH/CRITICAL resolved without exact commit/PR evidence, regression coverage where applicable, and an independent re-probe.

---

## Current open debt

### HIGH

None currently open. TD-070 (below) closed 2026-09-09.

---

### MEDIUM

### TD-031 — Coverage floor trails observed coverage — **OPEN**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | Current API suite: **299 passed, 81.09% coverage**; CI floor remains 75% |
| Risk | Future code can regress materially while still passing the configured floor |
| Recommendation | Raise the floor deliberately after measuring module-specific gaps; do not game coverage |
| Effort | S |

### TD-034 — No explicit application rate limiting — **CLOSED (2026-09-09)**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | No request had ever been rate-limited; a single client could flood the API or credential-stuff across many emails (the existing lockout in `local_auth.py` is per-*credential*, not per-IP, so it only engages once a specific known email is targeted). |
| Fix | `app/core/rate_limit.py`: dependency-free, in-process, per-IP fixed-window limiter (`InMemoryRateLimiter` + `RateLimitMiddleware`). A global limit (default 300 req/60s per IP) applies to every route except `/health/*` and `/metrics`; a stricter dedicated limit (default 10 req/60s per IP) applies to `/auth/signup` and `/auth/login`. Rejections return `429` with `Retry-After` and are audit-logged (`rate_limit_exceeded`). Keys on `request.client.host`, not `X-Forwarded-For` (a client-supplied header would let any caller bypass the limit by varying it). New settings: `RATE_LIMIT_ENABLED` (default `true`), `RATE_LIMIT_WINDOW_SECONDS`, `RATE_LIMIT_REQUESTS_PER_WINDOW`, `AUTH_RATE_LIMIT_REQUESTS_PER_WINDOW`. See `docs/work-packages/WP-P1-010-rate-limiting.md` for the full design, including why this is deliberately in-process (single-container deployment topology today — no Redis dependency added without its own work package) and per-workspace/per-provider limits are deferred (tied to TD-041 live-provider activation, which isn't built yet). |
| Tests | `tests/test_rate_limit.py`: limiter unit tests (window rollover, key isolation, invalid construction) plus a standalone-app integration suite (429 + `Retry-After`, auth paths use the stricter limiter independently of the global budget, exempt paths never limited, distinct client IPs have independent budgets) — 10 new tests, `app/core/rate_limit.py` at 100% coverage. Also asserts the shared `app` singleton does **not** attach the middleware under `ENVIRONMENT=test` — the full pytest session imports that module once and shares its state across ~340 unrelated tests, so enforcing it there would produce cross-test flakiness rather than signal; this mirrors the existing precedent in `app/main.py` for other interval/background behavior. Full suite: 349 passed (was 339), 81.23% coverage, verified from a clean install before closing this finding. |
| Status | **CLOSED.** Self-implemented and self-tested in this pass (Phase 3 forward delivery, not a milestone-audit closure) — flagging per this register's own rule that the builder isn't the sole certifier of milestone-level work; this is a bounded P1 addition, not a milestone, so it doesn't require a separate independent audit before merge, but an independent read is still welcome. |

### TD-041 — BYOK / live-provider activation incomplete — **OPEN**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | Every department's `create_manual_run`/`create_production_run`/`create_compliance_run` (`apps/api/app/services/{research,strategy,content_department,production,compliance}.py`) hardcodes `status="provider_not_configured"`/`"blocked_provider_not_configured"` and returns without calling anything external — no cost, no live output, matching the product's own truthful-unconfigured-state convention. The only worker executor that exists at all is `apps/worker/worker/executors/draft_desk.py` (mirrored API-side by `app/services/draft_desk.py`), which is pure deterministic string templating with `estimated_cost_usd` hardcoded to `"0.01"` — no provider, no I/O. `ProviderCredential` (BYOK secret storage, `apps/api/app/models/config.py`, migrated since Milestone 3) is inert schema: grepped for all usages across `apps/api/app` and it appears only in the model files — no service, no route, no encryption helper, nothing reads or writes it. `.env.example`'s provider key lines (`OPENAI_API_KEY` etc.) are comments only; `Settings`/`WorkerSettings` have no corresponding fields in code. |
| Risk | Overstating AI/media execution capability; enabling cost-bearing calls without full accounting if built carelessly |
| 2026-09-08 reconnaissance (read-only, no code changed) | A dedicated gap-mapping pass found the orchestration substrate is **already fully built and reusable** for this: idempotent effect dedup (`orchestration/provider_effects.py`, keyed on `assignment_id` alone, survives attempt bumps — TD-077's fix), the full spend reserve→commit→release lifecycle with fail-closed cap enforcement and commit-clamped-to-reserved semantics (`orchestration/controller.py:725-965`, already wired into `dispatcher.py`'s dispatch/submit path), stage-level retry/backoff/dead-letter (`orchestration/retry.py` + `controller.handle_stage_failure`), and the worker's lease/claim/ack/renew/submit protocol with a pluggable `StageExecutor` injection point (`worker/client.py`). None of that needs to be rebuilt or redesigned. |
| What's actually missing, in build order | (1) Real provider API key config — either plain `Settings`/`WorkerSettings` fields, or wiring up the already-migrated but entirely-unused `ProviderCredential` BYOK table (needs an encryption helper + CRUD route + decrypt-at-call lookup built from scratch — none exists today). (2) A minimal provider abstraction/registry — none exists; the only extension point today is the single hardwired `StageExecutor` callable. (3) One new worker executor modeled on `draft_desk.py`'s `execute_stage(context) -> (bool, dict|None, str)` contract, wrapping a real HTTP call. (4) Call-level retry/backoff/timeout around that HTTP call — the existing retry machinery is stage-level only; no HTTP-call-level retry library (e.g. `tenacity`) is a dependency yet. (5) A real per-request cost estimator (token/character-based) to replace the flat `default_stage_estimate_usd=0.01` fed into `reserve_spend`/`commit_spend` — the hook points already exist (`dispatcher.py:270,497`), only the estimator function is missing. (6) Flipping each department's hardcoded `provider_not_configured` short-circuit to a real dispatch branch. (7) New test infrastructure — zero HTTP-mocking scaffolding exists anywhere in the repo (`respx`/`vcr`/`tenacity` are not dependencies); needs a mocked-provider contract-test suite covering the reserve→call(success/429/5xx/timeout)→commit/release/idempotency matrix. (8) `orchestration/retry.py`'s retryable-error marker list may need provider-specific transient-error strings added. |
| Recommendation | Text-generation is the fastest realistic first path — Draft Desk already proves the exact worker I/O contract a real single-shot LLM call needs; production/media and compliance require multi-step external calls and are architecturally harder, so defer those. Activate one provider at a time, not built here — needs a Founder decision on which provider, a real API key, and a spend-cap figure the Founder is comfortable with before any cost-bearing call is made. |
| Effort | L |

### TD-085 — No reconciliation against Stripe's source of truth for a permanently-lost webhook — **OPEN**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | 2026-09-08 billing audit. `is_entitled()`/`_apply_subscription()` are driven exclusively by inbound webhook delivery; nothing in the repo ever calls the Stripe API to re-fetch current subscription state. If a `customer.subscription.deleted`/`updated(canceled)` webhook is never successfully delivered (endpoint outage spanning Stripe's retry window, a `STRIPE_WEBHOOK_SECRET` rotation misconfiguration, etc.), `WorkspaceBilling.plan/status` never changes and `is_entitled()` keeps returning `True` indefinitely. Not live-exploitable today — `BILLING_ENABLED=false` makes `is_entitled()` unconditionally `True` for everyone regardless of this path — but must be closed before BILLING-001 go-live (`docs/LAUNCH_BLOCKERS.md`). |
| Risk | A workspace can stay entitled indefinitely after Stripe has actually cancelled/downgraded it, with no self-healing path short of another unrelated webhook happening to arrive for the same subscription. |
| Recommendation | A periodic reconciliation job calling `stripe.Subscription.list`/`retrieve` per workspace with a stale `stripe_subscription_id`, or at minimum an ops alert on `billing_webhook_events` gaps vs. Stripe's own dashboard delivery log. Deliberately not built as part of this pass — this is new scheduled infrastructure, not a bug fix, and belongs on the BILLING-001 go-live checklist rather than shipped unprompted against a currently-disabled feature. |
| Effort | M |

---

### LOW / INFO

| ID | Item | Severity / state |
|---|---|---|
| TD-050 | Ruff format is not a distinct CI gate | LOW |
| TD-060 | FORCE RLS remains a positive architectural control | INFO — exact current table count should be derived from live/current migration evidence when needed |
| TD-061 | Migration round-trip through current head `0054` | INFO — PASS (branch `claude/project-builder-handover-k95wpm`; not yet on `main`) |
| TD-062 | API baseline | INFO — **333 passed / 81% coverage** on the pre-merge branch (was 299/81.09% on `main`); **339 passed / 80.82% coverage** independently reproduced on merged `main` @ `2ca92f8` (2026-09-09 recovery audit, fresh install/venv, full pytest+coverage run) |
| TD-063 | Exact-head browser smoke | INFO — retained desktop + exact-390px CI evidence now exists on `main`; not re-run for this unmerged branch |

---

## Closed — 2026-09-09 Phase 0/1 recovery audit

### TD-070 — `main` branch protection disabled — **CLOSED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | Issue #50 was closed 2026-08-28 as "completed," but its only linked implementation, PR #59 (a `workflow_dispatch` job to `PUT` protection via the REST API), was left **open and draft** — never merged — because it depended on a Founder-supplied `ADMIN_PAT` secret and a manual run. That left the register unable to tell, from the PR trail alone, whether protection was ever actually turned on. Re-probed live via `mcp__github__list_branches` during this recovery audit (2026-09-09): `main` now reports `"protected": true`. Protection was evidently applied directly (GitHub UI or equivalent), not through PR #59's workflow — PR #59 itself is stale/superseded and safe to close without merging, at the Founder's discretion, since the control it exists to add is already live by another path. |
| Verification | Live GitHub API read this session: `{"name":"main","sha":"2ca92f8...","protected":true}`. Ruleset detail (required-checks list, force-push/deletion block, admin-enforcement) was not individually re-read in this pass — the connected tool surface exposes only the `protected` boolean, not the full ruleset payload; re-open narrowly if per-check enforcement detail is ever needed as evidence for an external audit. |
| Status | **CLOSED.** `main` is protected as of this verification. Issue #50's closure is corroborated, not just trusted. |

---

## Closed — independently re-audited (2026-09-07 Claude cross-check batch, issue #91)

**2026-09-09 update:** PR #94 (TD-072 through TD-088, all 15 findings below) and PR #95
(Operations Dashboard frontend hardening) are now **merged to `main`** (head `2ca92f8`).
The independent re-audit (issue #91) that had already passed all 15 findings on the
pre-merge branch was re-verified against `main` itself in this recovery audit: API suite
reproduced clean from a fresh install — **339 passed, 80.82% coverage** (75% floor),
migration upgrade → downgrade-to-base → re-upgrade clean through head `0054`, `ruff check`
clean; worker suite reproduced clean — 7 passed, lint clean; web suite reproduced clean —
lint clean, `tsc -b && vite build` clean, 31 tests passed, `npm audit --audit-level=high`
clean (2 pre-existing moderate `@vitest/mocker` advisories in a dev-only test-runner
dependency, not shipped, not high/critical, matching CI's own `--audit-level=high` gate).
Codex's Section 1 gate on protected `main` (issue #91, 2026-09-08) should now be re-checked
against this merged head — the coupling and evidence trail below remains the authoritative
per-finding record.

Per this register's own rule, the builder who found these is also the one who
fixed them, so none were self-certified closed. A separate Claude session,
with no access to this builder's reasoning beyond the pushed code and this
register's evidence claims, independently re-probed all 15 findings against
`claude/project-builder-handover-k95wpm` (head `27627a0` at time of
re-audit) on 2026-09-09 — reproducing the full test suite from scratch,
replaying three of the riskiest fixes via revert-and-confirm-failure, and
reading the remainder in full rather than trusting this register's prose.
**Verdict: PASS on all 15, no FAIL or CONDITIONAL findings.** Full comment:
issue #91. This closes the finding as a defect; it does not authorize merge
to `main` — that remains a Founder decision per `docs/MILESTONE_AUDIT_STANDARD.md`,
and Codex's separate Section 1 gate on protected `main` (issue #91,
2026-09-08) stays FAIL until these land there and are re-verified in place.
One coupling to note: TD-082 and TD-088 were verified together and must not
be merged independently of each other (TD-082's RLS widening alone, without
TD-088's app-layer fix, would reintroduce the exact gap TD-088 closes) —
see issue #91 for the full reasoning.

### TD-082 — Operations Dashboard routes bypass RLS (21 of 28 handlers) — **CLOSED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | `apps/api/app/api/routes/operations_dashboard.py` opened the owner/superuser `AsyncSessionLocal()` connection instead of the RLS-scoped `Depends(get_current_session)` in 21 of its handlers (all five `actions/*` mutation endpoints included — pause/resume workers, emergency-stop, retry-failed-jobs, clear-dead-letter), matching the same architectural pattern TD-072 fixed for `content_jobs.py`/`review_gates.py`. (A full re-read found 28 handlers total, not the originally-estimated 24 — 5 already compliant, 2 have no DB session at all — but the 21 non-compliant count was correct.) A dedicated write-surface audit (same methodology as TD-072) found this was not a simple session swap: `billing_webhook_events` and `worker_credentials` had **zero `app_runtime` grant at all** (hard permission-denied under RLS, not just zero rows) — reached by 9 of the 21 handlers and by `action_emergency_stop` respectively; `worker_registry` had a write grant but no UPDATE policy, and `stage_assignments` had no UPDATE policy either, while `action_emergency_stop`'s underlying `reap_worker_assignments()` locks `stage_assignments` with `SELECT ... FOR UPDATE` — the exact TD-072-class trap where a missing policy means the lock silently matches zero rows instead of erroring; `stage_recovery_audit`'s grant explicitly excluded INSERT; `dead_letter_jobs` had SELECT+INSERT (from 0052) but no UPDATE, needed by the two DLQ-management actions. |
| Fix | Migration `0054_operations_dashboard_admin_rls.py` adds the minimal admin-scoped grants/policies for each gap (all 21 handlers gate on `require_workspace_admin` only, narrower than 0052's editor/reviewer-inclusive lists). `worker_registry`/`worker_credentials` needed an explicit architecture decision, documented in the migration itself: the three Quick Actions are already shipped and reachable via HTTP today over the owner connection — widening RLS to allow admin-scoped, workspace-pinned writes grants no new capability, it only makes that already-permitted write pass through the database's own tenant boundary instead of relying solely on the route's query. Global (`workspace_id IS NULL`) workers stay untouchable by any workspace admin, preserving migration 0025's original protection — enforced by a `workspace_id IS NOT NULL` guard on the new policy. `stage_recovery_audit`'s INSERT policy goes beyond the standard `policy_insert_roles()` helper: it requires `assignment_id` to reference a real `stage_assignments` row in the same workspace (an `EXISTS` subquery), not just "an admin of some workspace," since this is an audit/compliance trail — a plain admin-scoped policy would have let an admin insert fabricated recovery-audit rows for nonexistent assignments (caught by an existing adversarial test, `test_recovery_audit_rls_adversarial`, which the stricter policy keeps passing unmodified). All 21 handlers in `operations_dashboard.py` now use `Depends(get_current_session)`. |
| Tests | Two existing tests in `test_worker_registry_ws1.py` asserted the now-deliberately-changed "no user role can ever write `worker_registry`" invariant; updated (not weakened) to assert the new one — admin + workspace-pinned = allowed, non-admin and global workers = still denied, verified via direct RLS-session SQL. New test `tests/test_lease_recovery_ws3.py::test_emergency_stop_over_rls_session_actually_persists_all_writes` is a full HTTP-level regression proving every write in the emergency-stop path actually persists under RLS — not just returns 200, since a silently no-op'd UPDATE would have passed the pre-existing status-code-only integration test (`test_operations_dashboard_v3.py::test_mission_control_modules_and_actions`, which never asserted the target worker's final state) — verified to actually fail with `permission denied for table worker_credentials` when migration 0054 is downgraded, before trusting it. Full suite: 330 passed, 81% coverage, migration round-trip (upgrade→downgrade→upgrade) clean through head `0054`. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-083 — Workspace deletion silently left `job_schedule` rows in place — **CLOSED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | `job_schedule` is classified in `HARD_DELETABLE_TABLES` as "removed outright," but no migration ever created an RLS DELETE policy for it (only `policy_select_members`, 0016, and later INSERT/UPDATE for the scheduler's own writes, 0052). Under FORCE RLS, a command with no matching policy silently matches zero rows rather than erroring. Reproduced live end-to-end before the fix: seeded a `job_schedule` row, called the real deletion endpoint as a real admin, got HTTP 200 with `erased_counts: {"job_schedule": 0}`, and the row was still in the database. A control probe with `leads` on the same code path deleted correctly, isolating this to `job_schedule` specifically. |
| Fix | Migration `0053_job_schedule_delete_policy.py` adds the missing admin-only DELETE policy, matching the pattern already used for the other two `HARD_DELETABLE_TABLES` entries (`leads`, `publication_eligibility`). Regression test `tests/test_data_governance_closure.py::test_deletion_actually_removes_hard_deletable_job_schedule_rows` seeds a row and asserts it's actually gone after deletion, not just reported as erased. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-084 — `worker_heartbeats` silently dropped from data exports — **CLOSED**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | `worker_heartbeats` was listed in `EXPORTABLE_TABLES`, but has no `workspace_id` column — the export loop's own `else: continue` skipped it via the same code path as "this table doesn't exist," making the omission indistinguishable from either case and contradicting the module's own stated guarantee that "the bundle names every omission." Not a cross-tenant leak (the query never ran), a completeness defect for a compliance feature. |
| Fix | Moved `worker_heartbeats` to a new, explicit `STRUCTURALLY_UNEXPORTABLE_TABLES` list (documented reason: no `workspace_id` column, and `worker_registry.workspace_id` is itself nullable so a join wouldn't reliably scope it either); the export response now includes `unattributable_tables`/`unattributable_reason` alongside the existing credential `excluded_tables`/`exclusion_reason`, so the omission is named rather than silent. Regression test `tests/test_data_governance_closure.py::test_export_names_structurally_unattributable_tables`. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-081 — Founder dashboards blended billing/revenue/customer data across workspaces — **CLOSED**

| Field | Value |
|---|---|
| Severity | CRITICAL |
| Evidence | `operations_dashboard.customers()` takes no `workspace_id` — it aggregates billing/revenue/member data across *every workspace the calling admin administers*. Three reports that each present themselves as scoped to one `workspace_id` in their URL path reused it unscoped: `GET /operations/insights` (`most_active_customer` could name a different workspace), `GET /operations/executive-mode` (`revenue_mtd_usd` was the sum across every workspace the caller admins, sitting in the same response next to `spend_today_usd`, which *was* correctly scoped — so a Founder comparing the two numbers on one screen was comparing one tenant's spend to N tenants' revenue), and `GET /operations/search` (a "customer" search hit could return another workspace's name/id). This was **live and currently exploitable by design**, not a theoretical risk — any admin of 2+ workspaces (the exact shape of an agency running multiple clients, this product's own stated target market) triggers it immediately, no misconfiguration or edge case required. `GET /operations/customers` itself is an intentional cross-workspace "portfolio" view (explicit code comment: `del workspace_id  # authz scoped; customers are admin-owned workspaces`) and was correctly left unscoped. |
| Fix | `operations_dashboard.customers()` gained an optional `workspace_id` filter; the three consuming reports now pass their own `workspace_id` so each returns only that one workspace's data, while `/operations/customers` itself is unchanged (still the intentional portfolio view). Regression test `tests/test_operations_dashboard_v4.py::test_single_workspace_reports_never_blend_another_admined_workspace` seeds two workspaces under one admin with very different revenue/member counts, verifies all three single-workspace reports stay scoped, and separately verifies `/customers` still correctly sees both — verified to actually fail without the fix (reverted the fix, confirmed the test fails with the exact blended number, restored it) before trusting it as a real regression test. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-072 — `content_jobs.py` / `review_gates.py` had no RLS backstop — **CLOSED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | Both routes used the owner DB connection (`AsyncSessionLocal`) instead of the RLS-scoped session every other tenant route uses. A follow-up write-surface audit traced the full call graph of `create_content_job()`/`decide_review_gate()` and found 9 tables (`pipeline_runs`, `spend_reservations`, `spend_logs`, `job_schedule`, `review_gates`, `outbox_events`, `workflow_definitions`, `workflow_stages`, `workflow_transitions`) missing INSERT/UPDATE RLS policies or grants for `app_runtime`, plus `dead_letter_jobs`/`event_consumers` missing grants outright. Riskiest: `review_gates` had no UPDATE policy at all, and `spend_caps` restricted UPDATE to admin-only — both tables are read with `SELECT ... FOR UPDATE` in this call graph, which Postgres RLS requires to satisfy *both* the SELECT and UPDATE policy; either gap alone would have silently zero-rowed `decide_review_gate` (every call) or `create_content_job` (every editor-authored call) had the naive swap been done without this fix. |
| Fix | Migration `0052_orchestration_runtime_write_policies.py` adds/widens the policies and grants per the write-surface audit (kept as `docs/audit/td072_write_surface_map.md`-equivalent evidence in the migration's own docstring). `content_jobs.py` and `review_gates.py` now use `Depends(get_current_session)`. No other route touches these tables (research/strategy/content_department/production/compliance each use their own separate run tables), so this cannot regress those. Full existing test suite (312 tests, including `test_editor_cannot_decide_review_gate` which creates a content job as an editor — exercising exactly the riskiest `spend_caps`/`review_gates` FOR UPDATE path — and `test_approve_advances_to_published` which exercises the full `decide_review_gate` fan-out) passes unmodified against the new session, plus the existing `tests/test_content_desk_workspace_scoping.py` service-layer isolation tests. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-073 — `profiles` RLS SELECT policy leaked PII across tenants — **CLOSED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | `profiles_select_authenticated` (migration 0001) only checked "is any authenticated user," not shared workspace — any user could read every other user's email/full_name platform-wide via the `app_runtime` role. `FORCE ROW LEVEL SECURITY` was enabled; the policy itself provided no isolation. No live exploit found (no route reads `profiles` beyond `GET /me`). |
| Fix | Migration `0051_profiles_workspace_scoped_select.py` scopes SELECT to self-or-shared-workspace. Regression test in `tests/test_cross_workspace_isolation.py::test_rls_blocks_reading_a_stranger_profile_across_workspaces`. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-074 — Zero audit trail on workspace-membership/role changes — **CLOSED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | `memberships.py` invite/role-update/remove called neither `audit()` nor any event log, unlike the identical pattern in `spend.py`/`review_gates.py`/`workers.py`/`billing.py`. |
| Fix | All three endpoints now call `audit()` with actor/target/role fields. Regression test `tests/test_workspaces.py::test_membership_mutations_are_audit_logged`. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-075 — Hardcoded `app_runtime` migration password, no production guard — **CLOSED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | Migration 0001 creates the `app_runtime` role with the literal password `app_runtime` unconditionally; no code-level check analogous to the `AUTH_MODE=local` production guard existed. |
| Fix | `app/core/config.py::_validate_app_runtime_password` fails startup closed when `ENVIRONMENT=production` and `APP_DATABASE_URL` still carries the default password. Tests in `tests/test_pr34_high_fixes.py` (`test_c2_*`). |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-077 — Provider-effect idempotency didn't survive a crash-driven retry — **CLOSED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | `default_effect_key()` derived the dedup key from `(assignment_id, attempt_number)`. `recovery.py`'s crash/lease-expiry path always bumps `attempt_number` before re-queuing the *same* assignment, so a re-claimed attempt got a *new* effect key and would re-execute a real, billable provider call — up to `assignment_default_max_attempts` (3) times. Separately, the reference worker (`apps/worker/worker/client.py`) synthesized its own `{assignment_id}:{attempt}` key and passed it as an explicit override to `submit`, which would have defeated even a correct server-side fix by never letting ack's and submit's keys agree. Currently zero live exposure — no real provider is wired in anywhere in this repo. |
| Fix | `default_effect_key()` now derives the key from `assignment_id` alone (attempt-independent); `attempt_number` is still stored on the row for audit but no longer part of the dedup key. `ack_assignment` now surfaces `LeaseOut.provider_effect_created` (previously computed and silently discarded) so a caller learns *before* performing the side effect that a prior attempt already reserved it. The reference worker client no longer synthesizes or overrides the key, and now refuses to invoke the executor when `provider_effect_created` is `False` — it submits an explicit failure ("provider effect already reserved by a prior attempt...") rather than silently re-running or fabricating an unverifiable success. Regression tests: `tests/test_lease_recovery_ws3.py::test_effect_key_survives_crash_recovery_attempt_bump` (server-side key stability) and `tests/test_reference_worker_client.py::test_reference_worker_client_refuses_to_reexecute_after_crash_recovery` (full client+server path, proves the executor is never called). |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |
| Follow-up finding | Codex (PR #94, 2026-09-09): a future rollback to a version predating this fix, after this version has run in production, could leave `{assignment_id}:{attempt_number}`-format keys in the database that a subsequent re-upgrade's attempt-independent lookup wouldn't recognize, allowing one more re-execution than intended. **Accepted, not built defensively**: as the Evidence row above already establishes, no real provider has ever been wired into this repo, so no legacy-format key can exist anywhere yet — there is nothing to migrate. Building dual-format lookup logic now would be defending against a rollback of a deploy that hasn't happened, for a code path with zero live callers. Re-evaluate if/when a real provider integration ships and this code has actually run against production traffic. |

### TD-078 — Reference worker never exercised the server's idempotent claim replay — **CLOSED**

| Field | Value |
|---|---|
| Severity | LOW/MEDIUM |
| Evidence | `claim_assignment` has a full idempotent-replay path keyed on `claim_token` (a retried claim with the same token returns the assignment already held, rather than granting a second one), but `ReferenceWorkerClient.claim_next` never sent one. A lost HTTP response (timeout/connection reset) left the server holding a granted assignment the worker didn't know about, stranding that capacity slot until the ~60s lease expiry — bounded and self-healing, but the one shipped worker implementation never actually exercised the mechanism designed for this. |
| Fix | `claim_next()` now generates one `claim_token` per claim attempt and retries up to 3 times with the *same* token on a transport-level failure only (`httpx.TransportError` — timeouts/connection resets), leaving HTTP error statuses (4xx/5xx) to propagate immediately, unretried. Regression tests: `apps/worker/tests/test_reference_worker_client_claim_retry.py` (mocked-transport unit tests: retry reuses the token, gives up after the bound, doesn't retry HTTP error statuses) plus the existing full-suite claim/lease/recovery tests (54 tests) confirming no regression to the claim/ack/renew/submit protocol. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-079 — API/worker Draft Desk generators had silently drifted — **CLOSED**

| Field | Value |
|---|---|
| Severity | LOW |
| Evidence | `app/services/draft_desk.py` and `worker/executors/draft_desk.py` are independently-maintained, duplicate generators (the worker can't import the API package) whose own docstrings say "keep outputs aligned" as a manually-maintained invariant with no test enforcing it. Adding a parity test proved the invariant had already broken: on a topic with irregular internal whitespace (e.g. `"  extra   whitespace   topic  "`), the API returned the result dict's `topic` field only `.strip()`'d (`"extra   whitespace   topic"`), while the worker returned it fully whitespace-collapsed (`"extra whitespace topic"`) — the generated hook/body/cta text agreed (both use the collapsed form internally), but the `topic` field a caller might display or store did not. |
| Fix | `app/services/draft_desk.py::execute_stage` now returns the same whitespace-collapsed `topic` the worker already did. New test `tests/test_draft_desk_worker_parity.py` runs both generators against the same inputs (scripting/idea/review/other stages, whitespace, empty/missing topic) and asserts identical output, so a future edit to one without the other now fails CI instead of silently drifting. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-076 — `reserve_spend()` fails open with no `SpendCap` row — **CLOSED**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | If no `SpendCap` row exists for a workspace, the cap-check block was skipped entirely and the reservation proceeded unconditionally — contrary to "spend caps fail closed." Mitigated in practice since `POST /workspaces` always seeds a cap and there's no delete endpoint. |
| Fix | `reserve_spend()` now treats a missing cap the same as an exceeded cap (pause + `spend_hold` + emit event). Regression test `tests/test_spend_controls_p0.py::test_reserve_spend_fails_closed_without_cap_row`. Required updating 5 unrelated test files (`test_open_finding_closure.py`, `test_orchestration_scheduler_dispatcher.py`, `test_orchestration_workflow.py`, `test_reference_worker_client.py`, `test_regression_defects.py`) that deliberately created workspaces with no cap to isolate orchestration-mechanic testing — they now seed a permissive cap instead. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-086 — Concurrent (not merely out-of-order) webhook delivery could leave a stale "active" billing state after a later cancellation — **CLOSED**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | 2026-09-08 billing audit. `_apply_subscription()` unconditionally overwrote `billing.status`/`billing.plan` from whatever `subscription` dict it was handed, with no row lock taken before the read-modify-write, and `ensure_workspace_billing()` used a plain `session.get()`. Stripe explicitly does not guarantee ordered *or* single-threaded delivery: two distinct events for the same subscription (e.g. an older `active` update and a newer `canceled` deletion) can arrive as two genuinely concurrent HTTP requests, each in its own transaction. The existing `test_out_of_order_events_converge_on_latest_delivered_state` test proves the *sequential* replay case is safe but cannot exercise true concurrent/racing transactions. |
| Fix | `ensure_workspace_billing()` gained a `for_update: bool = False` parameter that locks the row (`session.get(..., with_for_update=...)`) for the rest of the transaction; `_apply_subscription()` — the only caller that mutates entitlement-bearing fields from webhook data — now passes `for_update=True`, so a second concurrent webhook transaction touching the same workspace's billing row blocks until the first commits instead of racing an unlocked read. Regression test `tests/test_billing_webhook_ordering.py::test_ensure_workspace_billing_for_update_locks_concurrent_readers` opens two real concurrent `AsyncSessionLocal()` sessions against live Postgres, holds the lock in one uncommitted transaction, and asserts the second transaction's `for_update=True` call genuinely blocks (does not complete within 0.2s) until the first commits — verified to actually fail (`TypeError: unexpected keyword argument 'for_update'`) against the pre-fix code via `git stash` before trusting it. |
| Status | **CLOSED** for the concurrent-transaction race this entry was scoped to (re-audited 2026-09-09, issue #91: PASS, verified via a real concurrent-Postgres-session revert-test). A **separate** gap was found 2026-09-09 by Codex's PR review, after this entry's initial closure: the row lock alone does not stop a genuinely distinct, older webhook event (different event id — not caught by the duplicate-receipt guard) from overwriting a newer state once delivered late, since `_apply_subscription` applied every distinct event unconditionally. Fixed the same day: it now compares the incoming event's own `created` timestamp against the max `created` already stored for the workspace's subscription-lifecycle receipts, and skips the entitlement-affecting mutation (receipt is still recorded) if the incoming event is older than one already applied. See `test_delayed_older_event_does_not_resurrect_a_newer_cancellation` — verified to actually fail against the pre-fix code (`'active' == 'canceled'`) before trusting it. Reconciliation against Stripe's own source of truth for a *permanently*-lost webhook remains separately tracked as TD-085 (not fixed here — new scheduled infrastructure, out of scope for a bug-fix pass). |

### TD-087 — Unhandled Stripe API failure between `Customer.create` and `Session.create` could orphan/duplicate Stripe Customer objects; rejected webhooks were not audit-logged — **CLOSED**

| Field | Value |
|---|---|
| Severity | LOW / INFO |
| Evidence | 2026-09-08 billing audit. (a) Neither Stripe call in `create_checkout_session` was wrapped in `try/except`; if `stripe.checkout.Session.create` raised after `stripe.Customer.create` already succeeded, the DB rolled back cleanly but the live Stripe Customer object was left orphaned, and a retry created a *second* orphaned Customer since the DB no longer remembered the first — also, the raw `stripe.error.StripeError` was not caught by the route's `except billing_service.BillingError`, so it surfaced as an unhandled 500 rather than a clean 4xx/503. (b) A rejected webhook (bad signature/payload) was logged via `logger.warning` only, with no `audit()` call, unlike a successfully processed webhook — meaning a potential attack/misconfiguration signal wouldn't show up wherever the audit trail specifically is monitored. Neither was live-exploitable (billing gated off / not security-critical), but both were recommended pre-go-live hardening. |
| Fix | Both Stripe calls in `create_checkout_session` are now wrapped in `try/except stripe.error.StripeError`, raising a clean `BillingError("stripe_unavailable", ...)` that the route maps to 503; `Customer.create` also now passes a deterministic per-workspace `idempotency_key` so a retry after a network-ambiguous failure reuses the same Customer instead of risking a duplicate at the Stripe API layer itself. `apps/api/app/api/routes/webhooks.py`'s rejection path now also calls `audit(request, "stripe_webhook_rejected", code=exc.code)` alongside the existing `logger.warning`. Regression tests: `tests/test_billing_p1.py::test_checkout_customer_create_failure_raises_clean_billing_error`, `::test_checkout_session_create_failure_does_not_persist_customer_id` (also covers the previously-untested existing-customer-reuse branch via the new `::test_checkout_reuses_existing_stripe_customer_id`), and `::test_webhook_rejection_is_audit_logged` — all four verified to actually fail against the pre-fix code via `git stash` before trusting them. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

### TD-088 — Two Quick Action functions had a defense-in-depth workspace-scoping gap; the assistant's generic "idle worker" question answered about the wrong worker — **CLOSED**

| Field | Value |
|---|---|
| Severity | LOW (the two scoping gaps) / MEDIUM (the assistant logic bug — wrong data presented as fact, not a security issue) |
| Evidence | 2026-09-08 targeted audit of the two lowest-coverage Operations Dashboard service modules (`operations_mission.py` 30%, `operations_v4.py` 50%), the same heuristic that found the CRITICAL TD-081 blended-dashboard bug. No new cross-tenant data leak of that shape was found — both already-fixed `customers()` call sites and all seven `global_search` branches were re-verified correctly scoped. Three smaller genuine issues were found: (1) `retry_failed_jobs`'s DLQ-replay loop (`operations_mission.py`) resolves a `PipelineRun` via a related id and explicitly re-checks `run.workspace_id == workspace_id` before touching it; its second loop (assignments that failed without ever reaching the DLQ) resolves a `PipelineRun` the same way via `assignment.pipeline_run_id` but was missing the identical guard — nothing in the schema ties a `StageAssignment`'s `workspace_id` to its `pipeline_run`'s `workspace_id`, so if that invariant were ever violated upstream, one workspace's admin could flip another workspace's pipeline run to `RUNNING` and enqueue work against it. (2) `emergency_stop`'s credential-revocation query filtered `WorkerCredential` by `worker_id` only, not also `workspace_id`, on a table that is FORCE RLS with zero policies for non-admin app-level access (post-TD-082, admin-scoped RLS policies now exist too, but the app-layer query itself had no independent check) — safe today only because every credential-creation path always stamps `credential.workspace_id = registration.workspace_id`. (3) `assistant_answer`'s "idle worker" branch (`operations_v4.py`): a generic question with no worker name ("are any workers idle?") left its name-matching `needle` empty, and `needle in row.name.lower()` is `True` for every worker since an empty string is a substring of anything — the assistant silently answered about whichever worker sorted first alphabetically, regardless of whether it was actually idle. This is a real logic bug, not a tenant-isolation issue. |
| Fix | (1) Added `if run is None or run.workspace_id != workspace_id: continue` to the second loop in `retry_failed_jobs`, matching the guard already present in the first loop. (2) Added `WorkerCredential.workspace_id == workspace_id` to the revocation query's filter in `emergency_stop`. (3) `assistant_answer`'s idle-worker branch now only does named-worker lookup when a name was actually captured; with no name, it reports the real set of workers whose `current_task is None`, or that none are idle. |
| Tests | Two new adversarial regression tests in `tests/test_operations_dashboard_v3.py` (`test_retry_failed_jobs_never_mutates_a_foreign_workspaces_pipeline_run`, `test_emergency_stop_never_revokes_a_foreign_workspaces_credential`) directly simulate the upstream invariant being violated (a mismatched-workspace `stage_assignments` row; a `worker_credentials` row stamped with a different workspace than its worker) and assert the foreign workspace's data is untouched. One new test in `tests/test_operations_dashboard_v4.py` (`test_assistant_generic_idle_question_reports_the_actually_idle_worker`) seeds one busy and one genuinely idle worker, names the busy one so it sorts first alphabetically, and asserts a generic "are any workers idle?" question reports the actually-idle worker, not the busy one. All three verified to actually fail against the pre-fix code via `git stash` before being trusted. Full suite: 333 passed, 81% coverage. |
| Status | **CLOSED.** Independently re-audited 2026-09-09 (issue #91): PASS. See issue #91 for the full independent audit comment. |

---

## Reviewed and accepted (not a defect)

### TD-080 — Solo Admin can author and approve their own content — **ACCEPTED, DOCUMENTED**

| Field | Value |
|---|---|
| Severity | MEDIUM (as originally flagged) |
| Evidence | `WorkspaceRole.ADMIN` is in both the content-author role set and the Human Review Gate decision-maker role set — nothing stops a solo Admin from approving a draft they authored themselves. The 2026-09-07 audit flagged this as weakening "independent Human Review" for single-admin workspaces, and noted it wasn't documented as an intentional tradeoff anywhere. |
| Decision (2026-09-08) | **Kept as current behavior, now explicitly documented as intentional** — see `apps/api/app/core/authorization.py`. This product's Private Beta target market (`docs/ROADMAP.md`: solo operators / small agencies) is exactly the case where requiring a second human reviewer would break the primary use case rather than add safety. The Human Review Gate's non-negotiable guarantee (AGENTS.md: "content never auto-publishes past review") is preserved — it does not require the reviewer to be a person distinct from the author, only that a review step exists and cannot be bypassed. A workspace wanting maker-checker separation today can enforce it operationally (don't grant one person both roles' worth of trust). |
| Revisit when | The product moves toward larger teams/agencies where this guarantee needs to be structural (e.g. `reviewer_id != content.created_by`, or a workspace-level "require independent review" setting) rather than operational. Not blocking for the current Private Beta baseline. |

---

## Recently closed / superseded debt

### TD-071 — Managed Supabase/runtime evidence unavailable — **CLOSED**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence (2026-09-08) | Founder connected the Supabase MCP connector this session, exposing project `content-orchestrator-test` (ref `vagfnbcnvtojljggxvxr`, region ap-southeast-2, Postgres 17.6.1, `ACTIVE_HEALTHY`, created 2026-08-28). Performed a read-only audit: (1) Supabase's automated security advisor flagged 4 tables (`alembic_version`, `event_consumers`, `consumer_checkpoints`, `local_auth_credentials` — the last holds password hashes) as "RLS disabled," which reads as alarming in isolation; verified directly against `information_schema.role_table_grants` that **zero privileges are granted to `anon`/`authenticated`/`PUBLIC` on any table in the public schema** — someone had already run hardening migrations (`contain_managed_public_api_default_grants`, `managed_supabase_public_acl_hardening_0051`, visible in `supabase_migrations.schema_migrations`) stripping Supabase's default Data-API access entirely, so the advisor finding is not a live exposure (Supabase's own automated REST/GraphQL layer cannot read a row on this project regardless of RLS state). (2) `worker_credentials`/`billing_webhook_events` show "RLS enabled, no policy" — confirmed intentional (deny-all for `app_runtime`; both are only ever written by the owner connection, matching `apps/api/app/api/routes/webhooks.py`'s own "owner-session writes" docstring and TD-039's original hardening). (3) Found genuine drift: `public.alembic_version` was stamped `0051`, two migrations behind the branch's `0053` head — meaning TD-072's RLS write-policy fix and TD-083's `job_schedule` DELETE policy were **not yet live** on the managed database. |
| Fix | Applied migrations `0052` and `0053` directly to the managed project (via `apply_migration`, SQL mirrored exactly from `apps/api/alembic/versions/0052_orchestration_runtime_write_policies.py` and `0053_job_schedule_delete_policy.py`, cross-checked against the project's actual pre-migration policy/grant state via `pg_policies`/`information_schema.role_table_grants` before applying). `alembic_version` now reads `0053`. Re-ran the security advisor post-migration: same 2 pre-existing intentional findings only, nothing new, nothing regressed. |
| Status | **CLOSED** — production auth/database facts are now independently verified rather than taken on faith, and the managed instance matched the branch's migration head at the time of this verification (`0053`). This branch has since advanced to `0054` via TD-082 (same PR); that migration has **not** been applied to or verified against the managed database — only `0053` is confirmed live there. PITR/backup-policy verification specifically was not part of this pass (no PITR-inspection tool was exercised) — reopen narrowly for that if needed before a real go-live certification. |

### TD-032 — No web E2E — **CLOSED / SUPERSEDED**

The old record said the web had Vitest-only coverage. That is no longer accurate.

Current CI includes an exact-head browser-smoke job that:

- explicitly verifies the checked-out candidate SHA,
- starts the migrated API and web application,
- exercises representative desktop routes and exact 390px mobile states,
- checks console/exception/blank-state/unlabeled-control/overflow failures,
- validates truthful `NOT CONFIGURED` states,
- records candidate identity, results and logs,
- retains screenshots and machine-readable evidence as a GitHub Actions artifact.

This closes the specific “no browser E2E evidence” debt. A future Playwright/staging suite may still add value, but it is not accurate to describe the repository as Vitest-only.

### TD-038 — Agent rules absent — **CLOSED / STRENGTHENED**

Root `AGENTS.md` exists and PR #49 adds the independent milestone PASS/CONDITIONAL/FAIL governance standard plus `docs/MILESTONE_AUDIT_STANDARD.md`.

---

## Historical resolved controls

The following previously resolved controls remain closed unless new evidence shows regression:

| ID | Historical issue | Resolution state |
|---|---|---|
| TD-001 | Missing `paused` enum | CLOSED |
| TD-002 | Automation unwired | CLOSED |
| TD-003 | Worker stub | CLOSED |
| TD-004 | Product APIs missing | CLOSED |
| TD-010 | Monthly cap unused | CLOSED |
| TD-011 | No spend seed/API | CLOSED |
| TD-012 | No real login | CLOSED |
| TD-013 | No Docker/CD path | CLOSED |
| TD-014 | Vite proxy | CLOSED |
| TD-015 | README false | CLOSED |
| TD-016 | No Stripe/entitlements | CLOSED in-repo; production go-live remains separate |
| TD-017 | Hosted backup drill unsigned | CLOSED for historical drill; current managed runtime/PITR still needs live verification |
| TD-018 | CI dependency audits soft-fail | CLOSED |
| TD-020 | OpenAPI unauthenticated | CLOSED |
| TD-021 | Unindexed FK baseline | CLOSED; later department migrations include additional index migrations through `0050` |
| TD-022 | Spend cap precision | CLOSED |
| TD-037 | Observability baseline absent | CLOSED for in-repo metrics/on-call baseline |

---

## Current burn-down priority

1. ~~TD-072…TD-082, TD-085…TD-088 through PR #94; get it merged to `main`~~ — **DONE.** PR #94 and PR #95 merged 2026-09-09; re-verified against merged `main` in this recovery audit (see evidence above). Codex's Section 1 gate should be re-run against `main` @ `2ca92f8` to close the loop formally.
2. ~~**TD-070 / issue #50:** technically protect `main`~~ — **DONE.** `main` verified `protected: true` live.
3. Select one revenue-producing private-beta workflow and verify it end-to-end in the managed environment.
4. Activate cost-bearing providers one at a time with spend, retry, idempotency and Human Review controls — see TD-041's build-order gap list.
5. Raise coverage/security/observability depth based on measured risk, not feature-count pressure.
6. Housekeeping (low priority, not blocking): ~30 open PRs and dozens of stale branches remain from earlier multi-agent lanes, mostly superseded by the now-merged audited baseline (`main` @ `2ca92f8`). Per `coordination hub #90`, none should be closed/merged/absorbed without an explicit Founder decision — flagged here for Founder triage, not acted on unilaterally.
