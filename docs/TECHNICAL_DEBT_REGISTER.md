# Technical Debt Register

**Repository:** Content Orchestrator  
**Updated:** 2026-07-27 (post adversarial P0 re-audit)  
**Audited branch:** `cursor/master-repo-audit-b52d`

Severity: CRITICAL · HIGH · MEDIUM · LOW · INFO

---

## Resolved in P0 closure / re-audit (do not reopen without evidence)

| ID | Was | Resolution |
|----|-----|------------|
| TD-001 | CRITICAL missing `paused` enum | `PipelineRunStatus` aligned; ORM reload tests |
| TD-002 | CRITICAL automation unwired | Lifespan starts scheduler/outbox/maintenance; shutdown awaits |
| TD-003 | CRITICAL worker stub | Draft Desk executor |
| TD-004 | CRITICAL product APIs missing | content-jobs + review-gates |
| TD-010 | HIGH monthly cap unused | Enforced + cross-provider aggregation fix |
| TD-011 | HIGH no spend seed/API | Seed + GET/PATCH |
| TD-012 | HIGH no real login | Local auth + web login |
| TD-013 | HIGH no Docker/CD path | Dockerfiles + staging compose + CI docker-build |
| TD-014 | HIGH vite proxy | Rewrite present |
| TD-015 | HIGH README false | Rewritten |
| D-P0-1/2/3 | CRITICAL/HIGH found in re-audit | Fixed with regressions |

---

## Open debt

### HIGH

### TD-016 — No Stripe / entitlements — **CLOSED (P-001)**

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Was: no billing code. Now: `workspace_billing` + Stripe Checkout/webhooks + entitlement gate |
| Risk | Was: no revenue path |
| Resolution | WP-PB-004 / P-001 on `cursor/p1-stripe-billing-b52d`; `BILLING_ENABLED` default false |
| Effort | L |
| Also | P-001 |

### TD-017 — Hosted backup drill not signed off — **CLOSED (P-002)**

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Was: docs only. Now: signed drill in `docs/DISASTER_RECOVERY_REPORT.md` (dump 0.084s, restore 0.263s, isolated DB, Gate/spend/RLS verified) |
| Risk | Was: untested recovery |
| Resolution | Staging DB pair restore on Postgres 16.14; quarterly managed PITR still recommended when cloud credentials exist |
| Effort | M |
| Also | P-002 |

### TD-018 — CI dependency audits not fail-closed — **CLOSED (P-003/P-004)**

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Was: soft-fail audits. Now: `pip-audit` + `npm audit --audit-level=high` fail the job; API/web/worker trees clean in isolated audit |
| Risk | Was: known CVEs land unnoticed |
| Resolution | Dep upgrades (FastAPI/Starlette/PyJWT/cryptography/Vite/ESLint floors) + fail-closed CI |
| Effort | M |
| Also | P-003/P-004 |

### TD-020 — OpenAPI unauthenticated — **CLOSED (P-005)**

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Was: `/openapi.json` public. Now: docs/OpenAPI only when `ENVIRONMENT` is `development`/`dev` |
| Risk | Was: surface disclosure in staging/prod |
| Resolution | `openapi_route_kwargs` + FastAPI docs URLs None outside dev; `test_openapi_lockdown_p1.py` |
| Effort | S |
| Also | P-005 |

### TD-021 — 33 unindexed FK columns — **CLOSED (P-006)**

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Was: 35 FKs without leading-column index. Now: migration `0031_fk` + `test_fk_indexes_p1.py` asserts zero |
| Risk | Was: scale degradation on deletes/joins |
| Resolution | Covering btree indexes via Alembic; probe regression test |
| Effort | M |
| Also | P-006 |

---

### MEDIUM

### TD-022 — Spend caps Numeric(10, 2) — **CLOSED (P-009)**

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Was: PATCH `0.005` rounded to `0.01`. Now: `spend_caps` are `numeric(12,4)`; API accepts 4 decimal places |
| Risk | Was: cannot express sub-cent policy |
| Resolution | Migration `0031_spend_precision` + schema Decimal validation; `test_spend_precision_p1.py` |
| Effort | S |
| Also | P-009 |

### TD-031 — Local coverage ~82%, floor 75%

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | CI `--cov-fail-under=75` |
| Risk | Soft floor |
| Recommendation | Raise to 80+ over time |
| Effort | S |

### TD-032 — No web E2E

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Vitest unit only |
| Risk | UI regressions |
| Recommendation | Playwright against staging |
| Effort | M |

### TD-034 — No rate limiting

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | No limiter middleware |
| Risk | Abuse / cost amplification |
| Recommendation | Per-workspace + IP limits |
| Effort | M |

### TD-037 — Observability limited — **CLOSED (P-008 in-repo baseline)**

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Was: collectors unwired. Now: `GET /metrics` Prometheus export + `docs/ops/ON_CALL.md` |
| Risk | Was: slow incidents |
| Resolution | Wire table-derived collectors; on-call runbook. Optional OTel/Sentry still needs vendor credentials |
| Effort | L |
| Also | P-008 |

### TD-038 — AGENTS.md / Cursor rules absent on default branch — **CLOSED (P-007)**

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Was: absent on `main`. Now: root `AGENTS.md` + `.cursor/rules/content-orchestrator.mdc` |
| Risk | Was: agent drift |
| Resolution | Foundation agent docs with non-negotiables and working rules |
| Effort | M |
| Also | P-007 |

### TD-041 — BYOK incomplete

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Draft Desk only |
| Risk | Over-promised AI generation |
| Recommendation | Explicit BYOK milestone |
| Effort | L |

---

### LOW / INFO

| ID | Item | Severity |
|----|------|----------|
| TD-050 | Ruff format not in CI | LOW |
| TD-060 | FORCE RLS on 36 tables | INFO (positive) |
| TD-061 | Migration round-trip OK | INFO |
| TD-062 | API 158 tests / ~82% cov | INFO |

---

## Burn-down after P0

1. P1: Stripe + hosted DR drill  
2. Harden CI CVE fail-closed + upgrade deps  
3. OpenAPI lockdown + FK indexes  
4. Observability  

Do not mark HIGH/CRITICAL resolved without: commit SHA, regression test, re-probe.
