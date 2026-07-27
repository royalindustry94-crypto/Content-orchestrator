# Launch Blockers

**Repository:** Content Orchestrator  
**Audited commit:** `248f69f` (`main`)  
**Date:** 2026-07-27  
**Source:** Independent Master Repository Audit

**Rule:** Nothing ships to private beta or production while any **P0** item remains open.

---

## Verdict

| Target | Status |
|--------|--------|
| Private beta | **BLOCKED** |
| Production | **BLOCKED** |

---

## P0 — Beta launch blockers

These must be closed before inviting any external workspace.

### B-001 — Human Review Gate ORM crash after pause

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| Evidence | After `request_human_review`, `session.get(PipelineRun, id)` raises `LookupError: 'paused' is not among the defined enum values`. DB enum includes `paused` (migration `0014`); `PipelineRunStatus` does not. |
| Risk | Gate appears to work in unit tests; production path breaks on next ORM load of a paused run. |
| Recommendation | Add `PAUSED = "paused"` to `PipelineRunStatus` (or unify with `PipelineRunStatusV2`). Add integration test that reloads after pause. |
| Effort | S (0.5 day) |
| Owner | Platform |
| Blocks | Private beta, any workflow using the Gate |

### B-002 — No Review Desk / content-jobs product surface on `main`

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| Evidence | `POST /v1/workspaces/{id}/content-jobs` → 404; `GET .../review-gates` → 404; OpenAPI has no content-job paths. Product code exists only on unmerged draft PR #23. |
| Risk | Nothing to sell or demo as Agency Content Desk. |
| Recommendation | Land WP-PB-001 (or equivalent) on `main` with CI green. |
| Effort | M (merge + harden; 2–4 days if PR #23 is base) |
| Owner | Product + Platform |
| Blocks | Private beta |

### B-003 — Scheduler and outbox relay not started

| Field | Value |
|-------|-------|
| Evidence | `apps/api/src/content_orchestrator_api/main.py` lifespan starts only `_maintenance_loop`. `_scheduler_tick_once` and `_outbox_relay_loop` exist but are unused. `consumers.register_all()` never called. |
| Risk | Schedules and outbox events never drive work in a running API process. |
| Recommendation | Start both loops in lifespan; call `register_all()` at startup; add lifecycle integration test. |
| Effort | S–M (1–2 days) |
| Owner | Platform |
| Blocks | Private beta automation |

### B-004 — Worker executor is a stub

| Field | Value |
|-------|-------|
| Evidence | `apps/worker/src/content_orchestrator_worker/worker.py` `_default_executor` returns fixed `"ok"` / `"stub-provider"`. |
| Risk | Jobs “succeed” without real generation; false confidence in ops. |
| Recommendation | Ship Draft Desk SKU (template/canned copy) or real BYOK provider path; remove stub as default. |
| Effort | M (3–5 days Draft Desk; larger for BYOK) |
| Owner | Platform |
| Blocks | Meaningful private beta |

### B-005 — Monthly spend cap not enforced

| Field | Value |
|-------|-------|
| Evidence | `SpendLimit.monthly_cap_usd` never referenced in `reserve_spend` / `confirm_spend` / `release_reservation`. |
| Risk | Non-negotiable spend control incomplete; overspend possible within reserved budget. |
| Recommendation | Enforce calendar-month confirmed+reserved spend against `monthly_cap_usd`. |
| Effort | S–M (1–2 days + tests) |
| Owner | Platform |
| Blocks | Private beta (policy) |

### B-006 — No spend bootstrap or spend HTTP API

| Field | Value |
|-------|-------|
| Evidence | Workspace create does not seed `SpendLimit` / `SpendLedger`. No `/spend` routes in OpenAPI. |
| Risk | Operators cannot configure or observe spend without DB access. |
| Recommendation | Seed defaults on workspace create; expose get/update spend endpoints with audit events. |
| Effort | M (2–3 days) |
| Owner | Platform |
| Blocks | Private beta ops |

### B-007 — No real authentication for beta users

| Field | Value |
|-------|-------|
| Evidence | Auth is JWT HS256 validation only; no signup/login/session UI; web Review Desk (on PR #23) pastes token + workspace id. |
| Risk | Unusable and unsafe for non-engineers; secret handling errors likely. |
| Recommendation | Supabase Auth (or equivalent) + session cookie/Bearer; workspace membership from claims. |
| Effort | M–L (1 week) |
| Owner | Platform + Web |
| Blocks | Private beta |

### B-008 — Staging environment and deploy path missing

| Field | Value |
|-------|-------|
| Evidence | No CD workflow; no production Docker images for API/worker/web; compose is local Postgres only. |
| Risk | No place to run private beta tenants. |
| Recommendation | Staging compose/K8s + migrate job + secrets + health checks. |
| Effort | L (1–2 weeks) |
| Owner | Ops |
| Blocks | Private beta |

### B-009 — Frontend API proxy broken for FastAPI routes

| Field | Value |
|-------|-------|
| Evidence | Vite proxies `/api` → backend without stripping prefix; FastAPI routes are `/health/*` and `/v1/*`, not `/api/*`. |
| Risk | Web health/product calls fail unless every client rewrites paths. |
| Recommendation | Add proxy rewrite or mount API under `/api`. |
| Effort | S (hours) |
| Owner | Web |
| Blocks | Web-based beta |

### B-010 — README / product claims contradict reality

| Field | Value |
|-------|-------|
| Evidence | README says auth and migrations “not yet built” while both exist; overstates product completeness. |
| Risk | Investors/customers misled; engineers onboard to wrong mental model. |
| Recommendation | Rewrite README to match `main` capabilities and explicit non-goals. |
| Effort | S (0.5 day) |
| Owner | Product |
| Blocks | Honest beta messaging (soft P0) |

---

## P1 — Production blockers (also severe for scaled beta)

### P-001 — No Stripe / billing

| Field | Value |
|-------|-------|
| Evidence | No Stripe SDK or webhook handlers in repo. |
| Risk | Cannot charge; no paid conversion path. |
| Recommendation | Checkout + customer portal + webhook → workspace entitlement. |
| Effort | L |
| Owner | Platform |
| Blocks | Production |

### P-002 — No backup / PITR / DR runbook

| Field | Value |
|-------|-------|
| Evidence | No ops docs or automation for backups. |
| Risk | Data loss; unrecoverable tenant outage. |
| Recommendation | Managed Postgres PITR + restore drill documented. |
| Effort | M |
| Owner | Ops |
| Blocks | Production |

### P-003 — CI security and migration replay gaps

| Field | Value |
|-------|-------|
| Evidence | CI: no coverage gate, no secret scan, no CodeQL, no alembic downgrade/re-upgrade, no npm/pip audit in CI. |
| Risk | Regressions and vulns land unnoticed. |
| Recommendation | Add jobs for coverage floor, gitleaks, migration round-trip, dependency audit. |
| Effort | M |
| Owner | Platform |
| Blocks | Production (P1 for beta) |

### P-004 — Dependency vulnerabilities

| Field | Value |
|-------|-------|
| Evidence | `npm audit`: 6 high (vite/esbuild); `pip-audit`: starlette, jinja2, pyjwt, etc. |
| Risk | Known CVEs in runtime/tooling. |
| Recommendation | Upgrade and pin; fail CI on high+. |
| Effort | S–M |
| Owner | Platform |
| Blocks | Production |

### P-005 — OpenAPI publicly readable

| Field | Value |
|-------|-------|
| Evidence | `GET /openapi.json` → 200 without auth. |
| Risk | Attack surface enumeration. |
| Recommendation | Disable docs in non-dev or require auth. |
| Effort | S |
| Owner | Platform |
| Blocks | Production hardening |

### P-006 — Unindexed foreign keys (33)

| Field | Value |
|-------|-------|
| Evidence | Postgres: 33 FK columns without supporting indexes (e.g. `pipeline_runs.workspace_id`, `jobs.workspace_id`). |
| Risk | Cross-tenant admin queries and joins degrade under load. |
| Recommendation | Add indexes in a dedicated migration after EXPLAIN review. |
| Effort | M |
| Owner | Platform |
| Blocks | Production scale |

### P-007 — No AGENTS.md / Cursor rules / company docs on `main`

| Field | Value |
|-------|-------|
| Evidence | Absent on `main`; present only as draft PRs. |
| Risk | Agent/human drift; repeated architecture violations. |
| Recommendation | Merge foundation docs after conflict resolution. |
| Effort | S–M |
| Owner | Eng management |
| Blocks | Sustainable production engineering (process) |

### P-008 — No observability stack

| Field | Value |
|-------|-------|
| Evidence | structlog only; no metrics/tracing exporters or alert runbooks. |
| Risk | Silent production failures. |
| Recommendation | OTel + error tracking + uptime checks. |
| Effort | L |
| Owner | Ops |
| Blocks | Production |

---

## P2 — Should not block first private beta invite (track explicitly)

| ID | Item | Effort |
|----|------|--------|
| T-001 | Dead `PipelineRunStatusV2` enum duplication | S |
| T-002 | CSRF strategy for cookie auth (when login lands) | M |
| T-003 | Rate limiting / abuse controls | M |
| T-004 | Idempotency keys on all mutating public APIs | M |
| T-005 | Web E2E (Playwright) in CI | M |
| T-006 | Business docs pack on `main` | S |
| T-007 | Load test for claim/lease under contention | M |

---

## Exit criteria checklist

### Private beta exit (all required)

- [ ] B-001 fixed + regression test (ORM reload after pause)
- [ ] B-002 content jobs + review gates on `main`
- [ ] B-003 scheduler + outbox relay + consumers in lifespan
- [ ] B-004 non-stub generation path (Draft Desk minimum)
- [ ] B-005 monthly cap enforced
- [ ] B-006 spend seed + HTTP API
- [ ] B-007 real login for beta users
- [ ] B-008 staging deployed with migrations
- [ ] B-009 web↔API routing fixed
- [ ] B-010 README truthful
- [ ] Manual Gate happy-path on staging with two workspaces (RLS proof)
- [ ] Spend block proven when cap hit

### Production exit (all required in addition)

- [ ] All P1 items closed
- [ ] Stripe live mode + dunning
- [ ] Backup restore drill signed off
- [ ] Security review + dependency CVE floor
- [ ] On-call + incident runbook
- [ ] Load test pass criteria met

---

## Related documents

- `docs/MASTER_REPOSITORY_AUDIT.md`
- `docs/TECHNICAL_DEBT_REGISTER.md`
- `docs/EXECUTIVE_STATUS_REPORT.md`
- Draft PR #23 (Review Desk) — candidate implementation for B-002 (not on `main`)
- Draft PR #25 (Launch Execution Plan) — sequencing guidance (not on `main`)
