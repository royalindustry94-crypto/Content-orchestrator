# Technical Debt Register

**Repository:** Content Orchestrator

**Updated:** 2026-09-03

**Current reference:** `main` at `abb20981f68cb0de8e3ed75af9759e0b5b6fb656` after PR #51

Severity: CRITICAL · HIGH · MEDIUM · LOW · INFO

Do not mark HIGH/CRITICAL resolved without exact commit/PR evidence, regression coverage where applicable, and an independent re-probe.

---

## Current open debt

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
| TD-061 | Migration round-trip through current head `0050` | INFO — PASS |
| TD-062 | API baseline | INFO — **299 passed / 81.09% coverage** |
| TD-063 | Exact-head browser smoke | INFO — retained desktop + exact-390px CI evidence now exists |

---

## Recently closed / superseded debt

### TD-070 — `main` branch protection disabled — **CLOSED**

Issue #50 is closed. A live GitHub re-probe on 2026-09-03 confirmed `main`
reports protected and repository ruleset `Protect main` (`21731627`) is active
for the default branch. It requires a pull request, one approval, stale-approval
dismissal, last-push approval, resolved conversations and strict success from
`api`, `worker`, `web`, `security`, `docker-build` and `browser-smoke`. Deletion
and non-fast-forward updates are blocked. There are no bypass actors and the
connected user reports `current_user_can_bypass: never`.

This closes the technical enforcement debt; exact-head audit and CI evidence
remain required for every candidate.

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

1. **TD-071:** establish managed Supabase/runtime evidence.
2. Select one revenue-producing private-beta workflow and verify it end-to-end in the managed environment.
3. Activate cost-bearing providers one at a time with spend, retry, idempotency and Human Review controls.
4. Raise coverage/security/observability depth based on measured risk, not feature-count pressure.
