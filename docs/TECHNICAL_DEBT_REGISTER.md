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

### TD-016 — No Stripe / entitlements

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | No billing code |
| Risk | No revenue path |
| Recommendation | Stripe Checkout + webhooks |
| Effort | L |
| Also | P-001 |

### TD-017 — Hosted backup drill not signed off

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Docs exist; no signed restore drill artifact |
| Risk | Untested recovery in real hosting |
| Recommendation | Quarterly restore drill on managed Postgres |
| Effort | M |
| Also | P-002 |

### TD-018 — CI dependency audits not fail-closed

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | npm audit `continue-on-error`; pip-audit ignores vuln exit=1 |
| Risk | Known CVEs land unnoticed |
| Recommendation | Upgrade deps; fail on high+ |
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

### TD-021 — 33 unindexed FK columns

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Evidence | Prior catalog audit |
| Risk | Scale degradation |
| Recommendation | Index migration |
| Effort | M |
| Also | P-006 |

---

### MEDIUM

### TD-022 — Spend caps Numeric(10, 2)

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | PATCH `0.005` rounds to `0.01`; estimate also `0.01` so near-zero caps are coarse |
| Risk | Cannot express sub-cent policy precisely |
| Recommendation | Widen scale or document 2-decimal policy |
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

### TD-037 — Observability limited

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | structlog; no OTel exporters |
| Risk | Slow incidents |
| Recommendation | OTel + error tracking |
| Effort | L |
| Also | P-008 |

### TD-038 — AGENTS.md / Cursor rules absent on default branch

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Evidence | Not on `main` |
| Risk | Agent drift |
| Recommendation | Merge foundation docs |
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
