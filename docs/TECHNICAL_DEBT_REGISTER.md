# Technical Debt Register

**Repository:** Content Orchestrator  
**Audited commit:** `248f69f` (`main`)  
**Date:** 2026-07-27  
**Source:** Independent Master Repository Audit  

**Severity scale:** CRITICAL · HIGH · MEDIUM · LOW · INFO  

Debt items are **not** automatically launch blockers. Cross-reference `docs/LAUNCH_BLOCKERS.md` when an item also blocks beta/production.

---

## Summary counts

| Severity | Count |
|----------|------:|
| CRITICAL | 4 |
| HIGH | 12 |
| MEDIUM | 14 |
| LOW | 8 |
| INFO | 5 |

---

## CRITICAL

### TD-001 — `PipelineRunStatus` missing `paused`

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| Evidence | DB enum has `paused` (Alembic `0014`); Python `PipelineRunStatus` lacks it; controller assigns `"paused"`; reload raises `LookupError`. Unused `PipelineRunStatusV2` contains `paused`. |
| Risk | Human Review Gate breaks after pause on any ORM reload. |
| Recommendation | Single enum source of truth; migration-aligned values; regression test reload-after-pause. |
| Effort | S |
| Also | Launch blocker B-001 |

### TD-002 — Background automation not wired in API lifespan

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| Evidence | `_scheduler_tick_once`, `_outbox_relay_loop` defined; lifespan only runs maintenance. `consumers.register_all()` unused. |
| Risk | Outbox and schedules inert in the running API. |
| Recommendation | Start tasks in lifespan; health shows loop liveness; integration test. |
| Effort | S–M |
| Also | Launch blocker B-003 |

### TD-003 — Worker default executor stub

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| Evidence | `_default_executor` returns canned success / `"stub-provider"`. |
| Risk | Silent fake completion; product appears to work. |
| Recommendation | Fail closed without configured provider; Draft Desk or BYOK implementation. |
| Effort | M |
| Also | Launch blocker B-004 |

### TD-004 — Product vertical (Review Desk) absent from `main`

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| Evidence | Content-jobs / review-gates routes 404; OpenAPI lacks paths; implementation on draft PR #23 only. |
| Risk | No shippable SKU on default branch. |
| Recommendation | Merge hardened Review Desk; keep architecture docs in sync. |
| Effort | M |
| Also | Launch blocker B-002 |

---

## HIGH

### TD-010 — Monthly spend cap unused

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | `monthly_cap_usd` column never read in spend service reserve/confirm/release. |
| Risk | Policy non-negotiable incomplete. |
| Recommendation | Enforce month window; tests for block/allow. |
| Effort | S–M |
| Also | B-005 |

### TD-011 — No spend seed / spend HTTP API

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Workspace create omits spend rows; no spend routes in OpenAPI. |
| Risk | Ops cannot manage caps without SQL. |
| Recommendation | Seed + REST + audit events. |
| Effort | M |
| Also | B-006 |

### TD-012 — Auth is token validation only

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | HS256 JWT verify; no IdP login, refresh, or web session. |
| Risk | Beta UX unsafe/unusable. |
| Recommendation | Supabase (or equiv.) end-to-end auth. |
| Effort | M–L |
| Also | B-007 |

### TD-013 — No CD / app container images

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Compose = Postgres; no API/worker/web Dockerfiles in deploy path; no deploy workflow. |
| Risk | Cannot run staging/production repeatably. |
| Recommendation | Multi-stage images + migrate job + CD. |
| Effort | L |
| Also | B-008 |

### TD-014 — Vite `/api` proxy mismatch

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Proxy to backend without rewrite; FastAPI has no `/api` prefix. |
| Risk | Frontend calls miss API. |
| Recommendation | Rewrite or mount under `/api`. |
| Effort | S |
| Also | B-009 |

### TD-015 — README inaccurate

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Claims auth/migrations not built; both exist on `main`. |
| Risk | Trust and onboarding failure. |
| Recommendation | Truthful capability matrix. |
| Effort | S |
| Also | B-010 |

### TD-016 — No Stripe / entitlements

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | No billing code. |
| Risk | No revenue path. |
| Recommendation | Stripe Checkout + webhooks. |
| Effort | L |
| Also | P-001 |

### TD-017 — No backup / DR

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | No backup automation or restore docs. |
| Risk | Irrecoverable data loss. |
| Recommendation | PITR + quarterly restore drill. |
| Effort | M |
| Also | P-002 |

### TD-018 — CI gaps (coverage, secrets, migration round-trip, audits)

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | `.github/workflows/ci.yml` runs migrate+pytest+ruff+web lint/build only. |
| Risk | Regressions and CVEs slip through. |
| Recommendation | Add coverage floor, gitleaks, alembic down/up, pip/npm audit. |
| Effort | M |
| Also | P-003 |

### TD-019 — Known dependency CVEs

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | npm audit 6 high; pip-audit flags starlette/jinja2/pyjwt/etc. |
| Risk | Exploitable supply chain. |
| Recommendation | Upgrade; gate CI. |
| Effort | S–M |
| Also | P-004 |

### TD-020 — OpenAPI unauthenticated

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | `/openapi.json` 200 without token. |
| Risk | API surface disclosure. |
| Recommendation | Disable outside dev or protect. |
| Effort | S |
| Also | P-005 |

### TD-021 — 33 unindexed FK columns

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Catalog query on fresh migrated DB. |
| Risk | Query plans degrade with volume. |
| Recommendation | Index migration after workload review. |
| Effort | M |
| Also | P-006 |

---

## MEDIUM

### TD-030 — Duplicate pipeline status enums

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | `PipelineRunStatus` vs `PipelineRunStatusV2`. |
| Risk | Drift (already caused TD-001). |
| Recommendation | Delete unused; one enum. |
| Effort | S |

### TD-031 — Local coverage ~83%, CI unenforced

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | API pytest coverage ~83% locally; no `--cov-fail-under` in CI. |
| Risk | Coverage can regress silently. |
| Recommendation | Fail under 80% (raise over time). |
| Effort | S |

### TD-032 — No web E2E tests

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Web CI = eslint + build only. |
| Risk | UI regressions undetected. |
| Recommendation | Playwright against staging/compose. |
| Effort | M |

### TD-033 — Worker test surface thin

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Worker suite: 1 passed at audit time. |
| Risk | Lease/claim/retry bugs undetected. |
| Recommendation | Expand claim/lease/retry/idempotency tests. |
| Effort | M |

### TD-034 — No rate limiting

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | No middleware/limiter in API. |
| Risk | Abuse / cost amplification. |
| Recommendation | Per-workspace and per-IP limits. |
| Effort | M |

### TD-035 — Incomplete idempotency on public mutations

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Outbox/job internals have idempotency patterns; not all public POSTs expose Idempotency-Key. |
| Risk | Double-submit duplicates. |
| Recommendation | Standard middleware for mutating routes. |
| Effort | M |

### TD-036 — CSRF not designed for future cookie auth

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Current Bearer model; no CSRF tokens planned in code. |
| Risk | When cookies land, CSRF exposure. |
| Recommendation | SameSite + CSRF for cookie sessions. |
| Effort | M |

### TD-037 — Observability limited to structlog

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | No metrics/tracing exporters. |
| Risk | Slow incident response. |
| Recommendation | OTel + error tracking. |
| Effort | L |
| Also | P-008 |

### TD-038 — Architecture/docs drift across draft PRs

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | AGENTS.md, business pack, PMF, launch plan only on draft PRs #20–#25. |
| Risk | Agents and humans follow conflicting sources. |
| Recommendation | Merge one coherent docs set to `main`. |
| Effort | M |

### TD-039 — Soft-delete / immutable table patterns uneven

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Audit/outbox immutability present in places; not uniformly documented or tested across all sensitive tables. |
| Risk | Accidental mutation of audit history. |
| Recommendation | Inventory + trigger tests per immutable table. |
| Effort | M |

### TD-040 — Optimistic locking coverage incomplete

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Version columns on some entities; not proven on all concurrent update paths. |
| Risk | Lost updates under contention. |
| Recommendation | Concurrent update tests for runs/jobs/spend. |
| Effort | M |

### TD-041 — Provider abstraction incomplete for production BYOK

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Provider interfaces exist; default path stubbed; no full secret vault integration proven on `main`. |
| Risk | Premature BYOK promises. |
| Recommendation | Explicit Draft Desk vs BYOK milestones. |
| Effort | L |

### TD-042 — Maintenance loop without peer automation

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Maintenance runs; scheduler/relay do not. |
| Risk | Partial “always-on” illusion. |
| Recommendation | Unified supervisor status endpoint. |
| Effort | S |

### TD-043 — Secret handling guidance missing on `main`

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Env-based JWT secret; no rotated-secrets runbook on `main`. |
| Risk | Long-lived weak secrets in staging. |
| Recommendation | Secrets runbook + rotation procedure. |
| Effort | S |

---

## LOW

### TD-050 — Ruff format not in CI

| Field | Value |
|-------|-------|
| Severity | LOW |
| Evidence | CI runs ruff check, not format --check. |
| Risk | Style drift. |
| Recommendation | Add format check. |
| Effort | S |

### TD-051 — Dead or unused helper modules

| Field | Value |
|-------|-------|
| Severity | LOW |
| Evidence | Status V2 and unwired loops indicate incomplete cleanup. |
| Risk | Confusion for new contributors. |
| Recommendation | Delete or wire; no half-states. |
| Effort | S |

### TD-052 — Web app still scaffold-level on `main`

| Field | Value |
|-------|-------|
| Severity | LOW |
| Evidence | Health-check oriented UI; Review Desk UI not on `main`. |
| Risk | Demo friction. |
| Recommendation | Accept until B-002 lands; then replace scaffold. |
| Effort | M |

### TD-053 — Test DB naming / local audit DB leftovers

| Field | Value |
|-------|-------|
| Severity | LOW |
| Evidence | Audit used `content_orchestrator_audit`; process docs don’t standardize ephemeral DB names. |
| Risk | Local collision. |
| Recommendation | Document `make audit-db` pattern. |
| Effort | S |

### TD-054 — Error responses may over-share in debug

| Field | Value |
|-------|-------|
| Severity | LOW |
| Evidence | FastAPI default error shapes; ensure prod disables debug. |
| Risk | Stack leakage if misconfigured. |
| Recommendation | Explicit prod exception handlers. |
| Effort | S |

### TD-055 — No CONTRIBUTING.md on `main`

| Field | Value |
|-------|-------|
| Severity | LOW |
| Evidence | File absent. |
| Risk | Slow onboarding. |
| Recommendation | Add after README rewrite. |
| Effort | S |

### TD-056 — Changelog absent on `main`

| Field | Value |
|-------|-------|
| Severity | LOW |
| Evidence | No `CHANGELOG.md` on audited `main`. |
| Risk | Release communication gap. |
| Recommendation | Keep a changelog from next merge train. |
| Effort | S |

### TD-057 — Performance tests absent

| Field | Value |
|-------|-------|
| Severity | LOW |
| Evidence | No load/benchmark suite in CI. |
| Risk | Unknown claim/lease limits. |
| Recommendation | k6/locust job contention scenario. |
| Effort | M |

---

## INFO

### TD-060 — FORCE RLS present on 36 tables

| Field | Value |
|-------|-------|
| Severity | INFO |
| Evidence | Catalog check: FORCE RLS enabled widely. |
| Risk | N/A (positive control). |
| Recommendation | Keep; add CI assertion. |
| Effort | S |

### TD-061 — Migration round-trip succeeded in audit

| Field | Value |
|-------|-------|
| Severity | INFO |
| Evidence | `upgrade head` → `downgrade base` → `upgrade head` to `0029` OK. |
| Risk | N/A until CI enforces. |
| Recommendation | Codify in CI (see TD-018). |
| Effort | S |

### TD-062 — API unit/integration tests 136 passed

| Field | Value |
|-------|-------|
| Severity | INFO |
| Evidence | Local pytest green at audit. |
| Risk | False confidence where tests mock away ORM/DB enum reality (see TD-001). |
| Recommendation | Prefer DB-backed tests for status transitions. |
| Effort | — |

### TD-063 — Many draft PRs ahead of `main`

| Field | Value |
|-------|-------|
| Severity | INFO |
| Evidence | Draft PRs #20–#25 (docs/product) and skill PRs #6–#19 not merged. |
| Risk | False sense that `main` includes that work. |
| Recommendation | Treat draft PRs as proposals only until merged. |
| Effort | — |

### TD-064 — Audit did not modify production application code

| Field | Value |
|-------|-------|
| Severity | INFO |
| Evidence | This audit ship is documentation-only by CEO directive. |
| Risk | Defects remain until engineering follow-up. |
| Recommendation | Execute `LAUNCH_BLOCKERS.md` P0 list next. |
| Effort | — |

---

## Debt burn-down guidance

1. **Week focus A:** TD-001, TD-002, TD-010, TD-011, TD-014, TD-015 (unblock Gate + spend + web).  
2. **Week focus B:** TD-004 + TD-003 (Review Desk + non-stub executor).  
3. **Week focus C:** TD-012 + TD-013 (auth + staging).  
4. **Ongoing:** TD-018/019 CI and CVEs; merge docs (TD-038).

Do not mark any CRITICAL/HIGH item **resolved** without: fix commit SHA, regression test, and re-run of the affected audit section.
