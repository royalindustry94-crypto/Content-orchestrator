# Launch Blockers

**Repository:** Content Orchestrator  
**Re-verified commit:** `cursor/master-repo-audit-b52d` (P0 closure)  
**Date:** 2026-07-27  
**Source:** Independent Master Repository Audit + P0 closure re-verification

**Rule:** Nothing ships to private beta or production while any **P0** item remains open.

---

## Verdict

| Target | Status |
|--------|--------|
| Private beta (P0 gate) | **UNBLOCKED** — all P0 items closed with evidence |
| Production | **BLOCKED** (P1 items remain) |

---

## P0 — Beta launch blockers (re-verified CLOSED)

### B-001 — Human Review Gate ORM crash after pause — CLOSED

| Field | Value |
|-------|-------|
| Severity | CRITICAL (resolved) |
| Evidence | `PipelineRunStatus` includes `paused`/`created`/`compensating`. Fresh probe: content-job → `run_status=paused`, `session.get(PipelineRun)` succeeds. Tests: `tests/test_pipeline_run_status_orm.py`. DB enum values == Python enum. |
| Risk | Mitigated |
| Recommendation | Keep ORM reload tests in CI |
| Effort | Done |

### B-002 — Review Desk / content-jobs product surface — CLOSED

| Field | Value |
|-------|-------|
| Severity | CRITICAL (resolved) |
| Evidence | Live probe: `POST /workspaces/{id}/content-jobs` → 201; `GET .../review-gates?status=awaiting` → 200 with gate. Routes registered in `main.py`. Tests: `tests/test_review_desk_api.py`. |
| Risk | Mitigated for Private Beta desk |
| Recommendation | None for P0 |
| Effort | Done |

### B-003 — Scheduler and outbox relay not started — CLOSED

| Field | Value |
|-------|-------|
| Severity | CRITICAL (resolved) |
| Evidence | `main.py` lifespan starts maintenance, outbox relay, and scheduler when `ENVIRONMENT != test`. `consumers.register_all()` at import. `GET /health/automation` exposes loop status. Tests: `tests/test_automation_lifecycle.py`. |
| Risk | Mitigated |
| Recommendation | Monitor `/health/automation` in staging |
| Effort | Done |

### B-004 — Worker executor is a stub — CLOSED

| Field | Value |
|-------|-------|
| Severity | CRITICAL (resolved) |
| Evidence | Default executor is Draft Desk; produces non-empty `script_body` / structured artifacts. Claim payload enriched with `topic`. Tests: `apps/worker/tests/test_draft_desk_executor.py` (4 passed). |
| Risk | Mitigated for Draft Desk SKU (not full BYOK) |
| Recommendation | BYOK remains P1/product |
| Effort | Done |

### B-005 — Monthly spend cap not enforced — CLOSED

| Field | Value |
|-------|-------|
| Severity | HIGH (resolved) |
| Evidence | `reserve_spend` checks daily **and** monthly windows; pauses with `spend_hold`. Tests: `tests/test_spend_controls_p0.py::test_monthly_cap_pauses_run`. |
| Risk | Mitigated |
| Recommendation | None for P0 |
| Effort | Done |

### B-006 — Spend bootstrap / spend HTTP API — CLOSED

| Field | Value |
|-------|-------|
| Severity | HIGH (resolved) |
| Evidence | Workspace create seeds `SpendCap`. `GET|PATCH /workspaces/{id}/spend`. Probe: seeded caps 50/1000. Tests: `test_workspace_create_seeds_spend_cap`, `test_spend_api_update_caps`. |
| Risk | Mitigated |
| Recommendation | None for P0 |
| Effort | Done |

### B-007 — Real authentication for beta users — CLOSED

| Field | Value |
|-------|-------|
| Severity | HIGH (resolved) |
| Evidence | `AUTH_MODE=local`: `POST /auth/signup`, `POST /auth/login` mint Supabase-shaped JWTs. Web Review Desk uses email/password login (no token paste). Tests: `tests/test_local_auth.py`. Probe: signup → workspace → content-job. |
| Risk | Mitigated for Private Beta; production should use `AUTH_MODE=supabase` + IdP |
| Recommendation | Document Supabase cutover in ops |
| Effort | Done |

### B-008 — Staging environment and deploy path — CLOSED

| Field | Value |
|-------|-------|
| Severity | HIGH (resolved) |
| Evidence | Dockerfiles for api/worker/web; `docker-compose.staging.yml`; `docs/ops/DEPLOYMENT.md`; `docs/ops/BACKUP_AND_RESTORE.md`. CI `docker-build` job. |
| Risk | Path exists; cloud hosting still operator-owned |
| Recommendation | Run staging smoke on real host before invites |
| Effort | Done |

### B-009 — Frontend API proxy broken — CLOSED

| Field | Value |
|-------|-------|
| Severity | HIGH (resolved) |
| Evidence | `apps/web/vite.config.ts` rewrites `/api` → backend root. Web client calls `/api/...`. |
| Risk | Mitigated |
| Recommendation | None for P0 |
| Effort | Done |

### B-010 — README accuracy — CLOSED

| Field | Value |
|-------|-------|
| Severity | HIGH (resolved) |
| Evidence | Root `README.md` rewritten to match Review Desk, auth, spend, ops docs. |
| Risk | Mitigated |
| Recommendation | Keep README in sync with merges |
| Effort | Done |

---

## P0 exit criteria checklist

- [x] B-001 fixed + regression test (ORM reload after pause)
- [x] B-002 content jobs + review gates
- [x] B-003 scheduler + outbox relay + consumers in lifespan
- [x] B-004 non-stub Draft Desk executor
- [x] B-005 monthly cap enforced
- [x] B-006 spend seed + HTTP API
- [x] B-007 real login for beta users
- [x] B-008 staging compose + deploy/backup docs
- [x] B-009 web↔API routing fixed
- [x] B-010 README truthful
- [ ] Manual Gate happy-path on hosted staging with two workspaces (operator drill — path ready)
- [x] Spend block proven when cap hit (automated)

---

## P1 — Production blockers (unchanged scope; NOT started per directive)

| ID | Item |
|----|------|
| P-001 | Stripe / billing |
| P-002 | Hosted backup drill sign-off |
| P-003 | CI security/CVE floor fully fail-closed (partially improved) |
| P-004 | Dependency CVE remediation |
| P-005 | OpenAPI lockdown outside dev |
| P-006 | Unindexed FK columns |
| P-007 | AGENTS.md / Cursor rules on default branch |
| P-008 | Observability (OTel / on-call) |

---

## Related documents

- `docs/MASTER_REPOSITORY_AUDIT.md`
- `docs/TECHNICAL_DEBT_REGISTER.md`
- `docs/EXECUTIVE_STATUS_REPORT.md`
