# Launch Blockers

**Repository:** Content Orchestrator  
**Re-verified:** 2026-07-27 — fresh adversarial audit on `cursor/master-repo-audit-b52d`  
**Source of truth:** Independent probes + regression suite (not prior reports)

**Rule:** Nothing ships to private beta or production while any **P0** item remains open.

---

## Verdict

| Target | Status |
|--------|--------|
| Private beta (P0 gate) | **UNBLOCKED — P0 COMPLETE** |
| Production | **BLOCKED** (P1 remains) |

---

## P0 defects found in re-audit (now closed)

| ID | Severity | Finding | Resolution | Evidence |
|----|----------|---------|------------|----------|
| D-P0-1 | CRITICAL | Workspace-wide spend cap bypassed via cross-provider reservations | Aggregate all providers when `SpendCap.provider IS NULL` | `test_workspace_cap_counts_all_providers`; live attack BLOCKED |
| D-P0-2 | CRITICAL | Review Desk content-jobs skipped spend entirely | Reserve/commit on desk path; HTTP 402 on hold | `test_content_job_blocked_when_monthly_cap_exceeded` |
| D-P0-3 | HIGH | Shutdown cancelled loops without awaiting | `asyncio.gather` after cancel | `test_lifespan_starts_and_stops_automation_loops` |
| D-P0-4 | MEDIUM | Ops doc wrong on AUTH_MODE | Corrected `docs/ops/DEPLOYMENT.md` | Doc review |

---

## P0 checklist (all CLOSED with fresh evidence)

| ID | Item | Status | Evidence |
|----|------|--------|----------|
| B-001 | PipelineRunStatus / Gate ORM reload | CLOSED | Enum parity + `test_pipeline_run_status_orm.py` |
| B-002 | content-jobs + review-gates | CLOSED | Live APIs + `test_review_desk_api.py` |
| B-003 | Scheduler + outbox startup | CLOSED | Lifespan starts both; ticks observed |
| B-004 | Worker real execution | CLOSED | Draft Desk non-empty artifacts |
| B-005 | Monthly cap enforcement | CLOSED | Daily+monthly; cross-provider fix |
| B-006 | Spend seed + API | CLOSED | Workspace create + GET/PATCH `/spend` |
| B-007 | Real login | CLOSED | Local signup/login + web UI |
| B-008 | Staging/deploy/backup path | CLOSED | Dockerfiles, staging compose, ops docs; CI docker-build green |
| B-009 | Vite `/api` rewrite | CLOSED | `vite.config.ts` |
| B-010 | README truthful | CLOSED | Rewritten README |
| P0-3 shutdown | Shutdown lifecycle | CLOSED | Await cancelled tasks |
| P0-4 auto-pause | Spend auto-pause on product path | CLOSED | Desk path + dispatcher |

---

## P1 — Production blockers

| ID | Item | Status | Evidence |
|----|------|--------|----------|
| P-001 | Stripe / billing | In progress on PR #27 | Separate branch |
| P-002 | Hosted backup restore drill sign-off | OPEN | Needs human / hosted credentials |
| P-003 | CI CVE fail-closed | **CLOSED** | `pip-audit` + `npm audit --audit-level=high` fail CI |
| P-004 | Dependency CVE remediation | **CLOSED** | PyJWT swap; FastAPI/Starlette/Vite upgrades; isolated audits clean |
| P-005 | OpenAPI lockdown outside dev | In progress on PR #28 | Separate branch |
| P-006 | Unindexed FK columns | OPEN | |
| P-007 | AGENTS.md / Cursor rules on default branch | OPEN | |
| P-008 | Observability / on-call | OPEN | |
| P-009 | Spend Numeric(10,2) precision vs sub-cent estimates | OPEN | |

---

## Related

- `docs/MASTER_REPOSITORY_AUDIT.md`
- `docs/TECHNICAL_DEBT_REGISTER.md`
- `docs/EXECUTIVE_STATUS_REPORT.md`
