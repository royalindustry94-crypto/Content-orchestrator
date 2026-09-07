# Technical Debt Register

**Repository:** Content Orchestrator  
**Updated:** 2026-09-07  
**Current reference:** `claude/project-builder-handover-k95wpm` @ `7a814db` (unmerged; base `main` remains PR #49)

Severity: CRITICAL · HIGH · MEDIUM · LOW · INFO

Do not mark HIGH/CRITICAL resolved without exact commit/PR evidence, regression coverage where applicable, and an independent re-probe.

---

## Current open debt

### HIGH

### TD-072 — `content_jobs.py` / `review_gates.py` have no RLS backstop — **OPEN**

| Field | Value |
|---|---|
| Severity | HIGH |
| Evidence | 2026-09-07 independent Claude audit (issue #91 Section 1/3 cross-check). Both routes use the owner DB connection (`AsyncSessionLocal`) instead of the RLS-scoped session every other tenant route uses, because the shared orchestration engine (`app/orchestration/controller.py`) is also driven by the connectionless background scheduler with no per-request JWT context. `pipeline_runs` has no INSERT/UPDATE RLS policy at all; `review_gates` has no UPDATE policy — a naive session swap would break content-job creation and review decisions, not just tighten security. |
| Risk | No database-level backstop on the two routes that create content and decide Human Review outcomes; isolation depends entirely on the FastAPI guard plus every downstream query staying correctly workspace-scoped. No live exploit found — every sampled query was correctly filtered. |
| Mitigation shipped | `claude/project-builder-handover-k95wpm` @ `7a814db` documents the architectural reason in both route files and adds `tests/test_content_desk_workspace_scoping.py` (direct service-layer isolation tests, no FastAPI guard in the loop) alongside the existing `tests/test_review_desk_api.py::test_cross_workspace_review_gate_is_hidden`. |
| Recommendation | Design and independently audit a correct INSERT/UPDATE RLS write-policy matrix for `pipeline_runs`, `review_gates`, and the other orchestration tables these two routes touch, then migrate the routes to `Depends(get_current_session)`. This is a separate, scoped migration project — not a quick fix. |
| Effort | L |

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
| TD-061 | Migration round-trip through current head `0051` | INFO — PASS (branch `claude/project-builder-handover-k95wpm`; not yet on `main`) |
| TD-062 | API baseline | INFO — **307 passed / 81.16% coverage** on the same branch (was 299/81.09% on `main`) |
| TD-063 | Exact-head browser smoke | INFO — retained desktop + exact-390px CI evidence now exists on `main`; not re-run for this unmerged branch |

---

## Fix pushed, pending independent re-audit (2026-09-07 Claude cross-check, issue #91)

Per this register's own rule, the builder who found these is also the one who
fixed them — **none of the following are self-certified closed.** Each needs
an independent re-probe against `claude/project-builder-handover-k95wpm` @
`7a814db` before being marked CLOSED.

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

### TD-076 — `reserve_spend()` fails open with no `SpendCap` row — **FIX PUSHED**

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Evidence | If no `SpendCap` row exists for a workspace, the cap-check block was skipped entirely and the reservation proceeded unconditionally — contrary to "spend caps fail closed." Mitigated in practice since `POST /workspaces` always seeds a cap and there's no delete endpoint. |
| Fix | `reserve_spend()` now treats a missing cap the same as an exceeded cap (pause + `spend_hold` + emit event). Regression test `tests/test_spend_controls_p0.py::test_reserve_spend_fails_closed_without_cap_row`. Required updating 5 unrelated test files (`test_open_finding_closure.py`, `test_orchestration_scheduler_dispatcher.py`, `test_orchestration_workflow.py`, `test_reference_worker_client.py`, `test_regression_defects.py`) that deliberately created workspaces with no cap to isolate orchestration-mechanic testing — they now seed a permissive cap instead. |
| Status | Fix pushed; pending independent re-audit before CLOSED. |

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

1. Independently re-audit TD-073…TD-076 (2026-09-07 fixes on `claude/project-builder-handover-k95wpm`) before merge.
2. **TD-070 / issue #50:** technically protect `main`.
3. **TD-071:** establish managed Supabase/runtime evidence.
4. **TD-072:** design and independently audit a correct RLS write-policy matrix for `pipeline_runs`/`review_gates` before switching those two routes off the owner connection.
5. Select one revenue-producing private-beta workflow and verify it end-to-end in the managed environment.
6. Activate cost-bearing providers one at a time with spend, retry, idempotency and Human Review controls.
7. Raise coverage/security/observability depth based on measured risk, not feature-count pressure.
