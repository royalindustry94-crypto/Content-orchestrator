# Technical Debt Register

**Repository:** Content Orchestrator  
**Updated:** 2026-09-07  
**Current reference:** `claude/project-builder-handover-k95wpm` (unmerged; base `main` remains PR #49)

Severity: CRITICAL · HIGH · MEDIUM · LOW · INFO

Do not mark HIGH/CRITICAL resolved without exact commit/PR evidence, regression coverage where applicable, and an independent re-probe.

---

## Current open debt

### HIGH

### TD-070 — `main` branch protection disabled — **OPEN**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | GitHub reports `main` unprotected with no required status checks enforced; tracked by issue #50 |
| Risk | Direct push or unverified merge can bypass the audited workflow |
| Recommendation | Require PRs, relevant CI gates, block force push/deletion, tightly control emergency bypass, then independently re-read protection/ruleset state |
| Effort | S |

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

### TD-034 — No explicit application rate limiting — **OPEN**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | Existing baseline does not establish a dedicated per-workspace/IP rate limiter |
| Risk | Abuse and cost amplification, particularly when live providers are enabled |
| Recommendation | Add bounded per-workspace/IP/provider limits before broad live-provider exposure |
| Effort | M |

### TD-041 — BYOK / live-provider activation incomplete — **OPEN**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | Preview departments remain explicitly unconfigured; live provider/runtime evidence is not part of the merged preview certification |
| Risk | Overstating AI/media execution capability or enabling cost-bearing calls without full accounting |
| Recommendation | Activate one provider at a time behind provider abstraction, spend reserve/commit controls, retries/backoff/timeouts, idempotency and supervised failure tests |
| Effort | L |

### TD-071 — Managed Supabase/runtime evidence unavailable — **OPEN**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | Supabase connector is installed but has not exposed a project to the current audit session |
| Risk | Production auth/database/PITR/deployment facts cannot be independently verified |
| Recommendation | Establish connector visibility and perform a read-only runtime audit before any deployment/live-auth certification |
| Effort | S-M |

---

### LOW / INFO

| ID | Item | Severity / state |
|---|---|---|
| TD-050 | Ruff format is not a distinct CI gate | LOW |
| TD-060 | FORCE RLS remains a positive architectural control | INFO — exact current table count should be derived from live/current migration evidence when needed |
| TD-061 | Migration round-trip through current head `0052` | INFO — PASS (branch `claude/project-builder-handover-k95wpm`; not yet on `main`) |
| TD-062 | API baseline | INFO — **321 passed / 81.03% coverage** on the same branch (was 299/81.09% on `main`) |
| TD-063 | Exact-head browser smoke | INFO — retained desktop + exact-390px CI evidence now exists on `main`; not re-run for this unmerged branch |

---

## Fix pushed, pending independent re-audit (2026-09-07 Claude cross-check, issue #91)

Per this register's own rule, the builder who found these is also the one who
fixed them — **none of the following are self-certified closed.** Each needs
an independent re-probe against `claude/project-builder-handover-k95wpm`
(head at time of writing) before being marked CLOSED.

### TD-072 — `content_jobs.py` / `review_gates.py` had no RLS backstop — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | Both routes used the owner DB connection (`AsyncSessionLocal`) instead of the RLS-scoped session every other tenant route uses. A follow-up write-surface audit traced the full call graph of `create_content_job()`/`decide_review_gate()` and found 9 tables (`pipeline_runs`, `spend_reservations`, `spend_logs`, `job_schedule`, `review_gates`, `outbox_events`, `workflow_definitions`, `workflow_stages`, `workflow_transitions`) missing INSERT/UPDATE RLS policies or grants for `app_runtime`, plus `dead_letter_jobs`/`event_consumers` missing grants outright. Riskiest: `review_gates` had no UPDATE policy at all, and `spend_caps` restricted UPDATE to admin-only — both tables are read with `SELECT ... FOR UPDATE` in this call graph, which Postgres RLS requires to satisfy *both* the SELECT and UPDATE policy; either gap alone would have silently zero-rowed `decide_review_gate` (every call) or `create_content_job` (every editor-authored call) had the naive swap been done without this fix. |
| Fix | Migration `0052_orchestration_runtime_write_policies.py` adds/widens the policies and grants per the write-surface audit (kept as `docs/audit/td072_write_surface_map.md`-equivalent evidence in the migration's own docstring). `content_jobs.py` and `review_gates.py` now use `Depends(get_current_session)`. No other route touches these tables (research/strategy/content_department/production/compliance each use their own separate run tables), so this cannot regress those. Full existing test suite (312 tests, including `test_editor_cannot_decide_review_gate` which creates a content job as an editor — exercising exactly the riskiest `spend_caps`/`review_gates` FOR UPDATE path — and `test_approve_advances_to_published` which exercises the full `decide_review_gate` fan-out) passes unmodified against the new session, plus the existing `tests/test_content_desk_workspace_scoping.py` service-layer isolation tests. |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

### TD-073 — `profiles` RLS SELECT policy leaked PII across tenants — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | `profiles_select_authenticated` (migration 0001) only checked "is any authenticated user," not shared workspace — any user could read every other user's email/full_name platform-wide via the `app_runtime` role. `FORCE ROW LEVEL SECURITY` was enabled; the policy itself provided no isolation. No live exploit found (no route reads `profiles` beyond `GET /me`). |
| Fix | Migration `0051_profiles_workspace_scoped_select.py` scopes SELECT to self-or-shared-workspace. Regression test in `tests/test_cross_workspace_isolation.py::test_rls_blocks_reading_a_stranger_profile_across_workspaces`. |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

### TD-074 — Zero audit trail on workspace-membership/role changes — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | `memberships.py` invite/role-update/remove called neither `audit()` nor any event log, unlike the identical pattern in `spend.py`/`review_gates.py`/`workers.py`/`billing.py`. |
| Fix | All three endpoints now call `audit()` with actor/target/role fields. Regression test `tests/test_workspaces.py::test_membership_mutations_are_audit_logged`. |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

### TD-075 — Hardcoded `app_runtime` migration password, no production guard — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | Migration 0001 creates the `app_runtime` role with the literal password `app_runtime` unconditionally; no code-level check analogous to the `AUTH_MODE=local` production guard existed. |
| Fix | `app/core/config.py::_validate_app_runtime_password` fails startup closed when `ENVIRONMENT=production` and `APP_DATABASE_URL` still carries the default password. Tests in `tests/test_pr34_high_fixes.py` (`test_c2_*`). |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

### TD-077 — Provider-effect idempotency didn't survive a crash-driven retry — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | `default_effect_key()` derived the dedup key from `(assignment_id, attempt_number)`. `recovery.py`'s crash/lease-expiry path always bumps `attempt_number` before re-queuing the *same* assignment, so a re-claimed attempt got a *new* effect key and would re-execute a real, billable provider call — up to `assignment_default_max_attempts` (3) times. Separately, the reference worker (`apps/worker/worker/client.py`) synthesized its own `{assignment_id}:{attempt}` key and passed it as an explicit override to `submit`, which would have defeated even a correct server-side fix by never letting ack's and submit's keys agree. Currently zero live exposure — no real provider is wired in anywhere in this repo. |
| Fix | `default_effect_key()` now derives the key from `assignment_id` alone (attempt-independent); `attempt_number` is still stored on the row for audit but no longer part of the dedup key. `ack_assignment` now surfaces `LeaseOut.provider_effect_created` (previously computed and silently discarded) so a caller learns *before* performing the side effect that a prior attempt already reserved it. The reference worker client no longer synthesizes or overrides the key, and now refuses to invoke the executor when `provider_effect_created` is `False` — it submits an explicit failure ("provider effect already reserved by a prior attempt...") rather than silently re-running or fabricating an unverifiable success. Regression tests: `tests/test_lease_recovery_ws3.py::test_effect_key_survives_crash_recovery_attempt_bump` (server-side key stability) and `tests/test_reference_worker_client.py::test_reference_worker_client_refuses_to_reexecute_after_crash_recovery` (full client+server path, proves the executor is never called). |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

### TD-078 — Reference worker never exercised the server's idempotent claim replay — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | LOW/MEDIUM |
| Evidence | `claim_assignment` has a full idempotent-replay path keyed on `claim_token` (a retried claim with the same token returns the assignment already held, rather than granting a second one), but `ReferenceWorkerClient.claim_next` never sent one. A lost HTTP response (timeout/connection reset) left the server holding a granted assignment the worker didn't know about, stranding that capacity slot until the ~60s lease expiry — bounded and self-healing, but the one shipped worker implementation never actually exercised the mechanism designed for this. |
| Fix | `claim_next()` now generates one `claim_token` per claim attempt and retries up to 3 times with the *same* token on a transport-level failure only (`httpx.TransportError` — timeouts/connection resets), leaving HTTP error statuses (4xx/5xx) to propagate immediately, unretried. Regression tests: `apps/worker/tests/test_reference_worker_client_claim_retry.py` (mocked-transport unit tests: retry reuses the token, gives up after the bound, doesn't retry HTTP error statuses) plus the existing full-suite claim/lease/recovery tests (54 tests) confirming no regression to the claim/ack/renew/submit protocol. |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

### TD-079 — API/worker Draft Desk generators had silently drifted — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | LOW |
| Evidence | `app/services/draft_desk.py` and `worker/executors/draft_desk.py` are independently-maintained, duplicate generators (the worker can't import the API package) whose own docstrings say "keep outputs aligned" as a manually-maintained invariant with no test enforcing it. Adding a parity test proved the invariant had already broken: on a topic with irregular internal whitespace (e.g. `"  extra   whitespace   topic  "`), the API returned the result dict's `topic` field only `.strip()`'d (`"extra   whitespace   topic"`), while the worker returned it fully whitespace-collapsed (`"extra whitespace topic"`) — the generated hook/body/cta text agreed (both use the collapsed form internally), but the `topic` field a caller might display or store did not. |
| Fix | `app/services/draft_desk.py::execute_stage` now returns the same whitespace-collapsed `topic` the worker already did. New test `tests/test_draft_desk_worker_parity.py` runs both generators against the same inputs (scripting/idea/review/other stages, whitespace, empty/missing topic) and asserts identical output, so a future edit to one without the other now fails CI instead of silently drifting. |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

### TD-076 — `reserve_spend()` fails open with no `SpendCap` row — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | If no `SpendCap` row exists for a workspace, the cap-check block was skipped entirely and the reservation proceeded unconditionally — contrary to "spend caps fail closed." Mitigated in practice since `POST /workspaces` always seeds a cap and there's no delete endpoint. |
| Fix | `reserve_spend()` now treats a missing cap the same as an exceeded cap (pause + `spend_hold` + emit event). Regression test `tests/test_spend_controls_p0.py::test_reserve_spend_fails_closed_without_cap_row`. Required updating 5 unrelated test files (`test_open_finding_closure.py`, `test_orchestration_scheduler_dispatcher.py`, `test_orchestration_workflow.py`, `test_reference_worker_client.py`, `test_regression_defects.py`) that deliberately created workspaces with no cap to isolate orchestration-mechanic testing — they now seed a permissive cap instead. |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

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

1. Independently re-audit TD-072…TD-079 (2026-09-07 fixes on `claude/project-builder-handover-k95wpm`) before merge.
2. **TD-070 / issue #50:** technically protect `main`.
3. **TD-071:** establish managed Supabase/runtime evidence.
4. Select one revenue-producing private-beta workflow and verify it end-to-end in the managed environment.
5. Activate cost-bearing providers one at a time with spend, retry, idempotency and Human Review controls.
6. Raise coverage/security/observability depth based on measured risk, not feature-count pressure.
