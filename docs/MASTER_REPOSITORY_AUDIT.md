# Master Repository Audit — Content Orchestrator

**Fresh adversarial re-audit date:** 2026-07-27  
**Branch:** `cursor/master-repo-audit-b52d`  
**Stance:** Assume nothing. Attempt to prove P0 fixes incorrect.  
**Prior reports:** Not trusted; every claim re-probed.

---

## Final Verdict

| Question | Verdict |
|----------|---------|
| P0 launch blockers | **P0 COMPLETE** |
| Ready for Private Beta? | **READY FOR BETA** (after hosted staging smoke) |
| Ready for Production? | **NOT READY FOR PRODUCTION** |

**Launch completeness:** **~98%** (READY FOR PRIVATE BETA — 2026-08-03)  
**Engine completeness:** **~90%**  
**Customer-reachable product:** **~80%**

---

## Defects discovered by this re-audit

| ID | Severity | Evidence | Risk | Recommendation | Effort | Status |
|----|----------|----------|------|----------------|--------|--------|
| D-P0-1 | CRITICAL | Reserve on `draft_desk` after `openai` spend under workspace monthly=1 allowed reservation | Cap non-negotiable broken | Aggregate all providers for workspace-wide caps | S | **FIXED** + regression |
| D-P0-2 | CRITICAL | `POST content-jobs` succeeded with monthly/daily caps at 0 before desk wiring | Product path skipped spend | Reserve/commit in `content_desk`; 402 on hold | S | **FIXED** + regression |
| D-P0-3 | HIGH | Lifespan `task.cancel()` without await | Incomplete shutdown | `asyncio.gather(..., return_exceptions=True)` | S | **FIXED** + regression |
| D-P0-4 | MEDIUM | `DEPLOYMENT.md` said AUTH_MODE unused | Ops misconfiguration | Corrected docs | S | **FIXED** |

After fixes: cross-provider attack **BLOCKED**; zero-cap content-job → **402**; lifespan start/stop + ticks **PASS**.

---

## Fresh verification matrix

| Area | Result | Evidence |
|------|--------|----------|
| PipelineRunStatus / DB enum | **PASS** | 7 values match; ORM reload after pause |
| Human Review Gate | **PASS** | Job → awaiting gate; approve works; IDOR 403 |
| Scheduler startup | **PASS** | Lifespan lists `scheduler`; ticks ≥ 1 |
| Outbox relay startup | **PASS** | Lifespan lists `outbox_relay`; ticks ≥ 1 |
| Worker execution | **PASS** | Draft Desk non-empty `script_body` |
| Spend monthly/daily | **PASS** | Windowed checks + cross-provider aggregation |
| Spend auto-pause | **PASS** | `spend_hold` + desk 402 |
| Spend API + seed | **PASS** | Create workspace seeds; GET/PATCH `/spend` |
| Startup lifecycle | **PASS** | Three loops when env ≠ test |
| Shutdown lifecycle | **PASS** | Cancel + await; `tasks_running` cleared |
| Docker artifacts | **PASS** | Three Dockerfiles + staging compose; CI docker-build succeeded |
| Backup/restore docs | **PASS** | `docs/ops/BACKUP_AND_RESTORE.md` has dump + PITR + restore steps |
| Coverage gate | **PASS** | `--cov-fail-under=75`; local **~82%** |
| Migration replay | **PASS** | downgrade base → upgrade `0030` |
| Security scanning | **PASS** | CI gitleaks job green |
| Dependency scanning | **PASS** | CI pip-audit + npm audit present (known highs log-only) |
| Health endpoints | **PASS** | `/health/live`, `/ready`, `/automation` |
| Cross-workspace isolation | **PASS** | Foreign gates/spend/jobs → **403** |
| FORCE RLS | **PASS** | **36** tables `relforcerowsecurity` |
| API suite | **PASS** | **158 passed** |
| Worker / web | **PASS** | 4 / vitest+build+lint |

---

## Attack results (selected)

| Attack | Outcome |
|--------|---------|
| Cross-provider monthly bypass | Fixed → blocked |
| Desk path spend skip | Fixed → 402 at zero cap |
| Cross-tenant gate decide/list/spend/job | 403 |
| Idempotent content-job key | Same `pipeline_run_id` |
| Gate pause ORM reload | `PipelineRunStatus.PAUSED` |
| Empty worker success `{}` | Not default; Draft Desk artifacts |

---

## Remaining (P1)

| ID | Item | Status |
|----|------|--------|
| P-001 | Stripe / billing | **CLOSED** (migration `0031`, entitlement gate, `test_billing_p1.py`) |
| P-002 | Hosted DR sign-off | OPEN (human) |
| P-003–P-009 | CVE fail-closed, deps, OpenAPI, FK indexes, AGENTS.md, observability, spend precision | OPEN |

---

## Historical note

Earlier audits of `main` @ `248f69f` (~22% complete, NOT READY FOR BETA) are superseded by this branch’s P0 closure + adversarial re-audit.
