# Master Repository Audit — Content Orchestrator

**Audit date:** 2026-07-27  
**Audited commit:** `main` @ `248f69f` (Milestone 4 WS1–WS4)  
**Auditor stance:** Assume nothing is correct. Prove unreadiness where possible.  
**Code changes during audit:** None (documentation only). Defects recorded, not patched.

---

## Final Verdict

| Question | Verdict |
|----------|---------|
| Ready for Private Beta? | **NOT READY FOR BETA** |
| Ready for Production? | **NOT READY FOR PRODUCTION** |

**Overall completeness (product + ops for launch):** **~22%**  
**Engine completeness (orchestration library on Postgres):** **~75%**  
**Customer-reachable product completeness:** **~10%**

---

## Executive proof points (re-verified this run)

| Check | Result | Evidence |
|-------|--------|----------|
| Fresh migrate → head | **PASS** | `alembic upgrade head` → `0029` on empty DB `content_orchestrator_audit` |
| Downgrade → base | **PASS** | Full `alembic downgrade base` succeeded |
| Re-upgrade → head | **PASS** | Second `alembic upgrade head` → `0029` |
| API tests | **PASS** | `136 passed` in 45.62s |
| Coverage (local) | **83%** statements | `pytest --cov=app`; **CI does not enforce coverage** |
| Worker tests | **PASS** | 1 passed |
| Web lint + build | **PASS** | eslint + `tsc -b && vite build` |
| Ruff (api/worker) | **PASS** | `ruff check .` clean |
| Unauthenticated API | **PASS (secure)** | `GET /workspaces` → **401** |
| Garbage JWT | **PASS (secure)** | → **401** |
| Cross-workspace IDOR | **PASS (secure)** | Non-member `GET /workspaces/{id}` → **403** |
| Content jobs API | **FAIL (missing)** | `POST .../content-jobs` → **404** |
| Review gates API | **FAIL (missing)** | `GET .../review-gates` → **404** |
| ORM load after review pause | **FAIL (bug)** | `LookupError: 'paused' is not among the defined enum values` |
| Monthly spend cap | **FAIL (unused)** | `monthly_cap_usd` never referenced in `reserve_spend` |
| OpenAPI unauthenticated | **FAIL (exposure)** | `GET /openapi.json` → **200** |
| FORCE RLS tables | **PASS** | **36** public tables with `relforcerowsecurity` |
| Unindexed FK columns | **DEBT** | **33** FK columns without supporting index |
| Scheduler/relay in lifespan | **FAIL (inert engine)** | Only maintenance loop in `apps/api/app/main.py` |
| `consumers.register_all` at boot | **FAIL** | Never imported/called in `main.py` |
| Worker generation | **FAIL (stub)** | `_default_executor` returns empty success |
| Billing | **FAIL (absent)** | No Stripe/billing code on `main` |
| AGENTS.md / `.cursor/` | **FAIL (absent)** | Not on `main` (only on unmerged PRs) |
| Business/PMF/Launch docs | **FAIL (unmerged)** | Draft PRs #21–#25; **not on `main`** |
| README accuracy | **FAIL** | Claims auth/migrations “not yet built” — **false** |

---

## Product standing

### What works (engine / platform)

- Postgres schema through migration **0029** (identity, content, pipeline, spend, review gates, outbox, workers, claiming, leases, back-pressure).
- Supabase JWT verification + RLS-scoped sessions.
- Workspace/membership HTTP APIs with role guards.
- Worker machine + admin HTTP protocol (register, heartbeat, claim, ack, renew, submit, provision, drain, rotate, revoke).
- Orchestration **library**: controller, outbox, scheduler, dispatcher, claiming, recovery, relay, consumers (test-driven).
- Human Review Gate **logic** + spend **daily** reservation with row lock (WS4).
- Structured JSON logging + request IDs; worker ops audited.
- CI: migrate + ruff + pytest (api), ruff + pytest (worker), lint + build (web).

### Missing systems (customer / launch)

| System | Status on `main` |
|--------|------------------|
| Content job HTTP API | Missing (404) |
| Review Desk HTTP + UI | Missing |
| Real login UI | Missing (health-check page only) |
| Scheduler/relay production wiring | Missing |
| Real AI generation / BYOK crypto | Missing (stub + schema-only credentials) |
| Spend HTTP + monthly enforce + seed | Missing / incomplete |
| Stripe / entitlements | Missing |
| Notifications | Missing |
| Publish / analytics product code | Schema only |
| Deploy / Docker app images / CD | Missing |
| Backups / DR | Missing |
| Metrics export / alerting | Missing (`metrics.py` 0% coverage, unwired) |
| AGENTS.md, Cursor rules | Missing on `main` |
| Accurate operator docs | Missing (README stale) |

### Launch / Beta / Production blockers

See `docs/LAUNCH_BLOCKERS.md`.

---

## Area findings (severity · evidence · risk · recommendation · effort)

### Architecture

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| A1 | **Critical** | Orchestration engine not production-wired | `main.py` lifespan only runs maintenance; no `poll_and_lease` / `poll_and_dispatch` / `register_all` | Pipelines inert | Wire scheduler+relay+consumers (or dedicated process) | M |
| A2 | **High** | Product surface far behind engine | Routes: health/profiles/workspaces/memberships/concurrency/workers only | Cannot demo Gate | Land Review Desk + content APIs | L |
| A3 | **Medium** | Architecture drift vs README/M3 reports | README “not yet built: auth, migrations”; M3 report outdated | Wrong decisions | Rewrite status docs; archive stale reports | S |
| A4 | **Low** | Empty `n8n/`, `packages/`, placeholder READMEs | Directory stubs | Distraction | Delete or freeze until used | S |

### Backend

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| BE1 | **Critical** | No content/review product routes | Probe 404s | No beta | Ship L0-01 style APIs | L |
| BE2 | **High** | Route coverage uneven | workers 47%, memberships 44%, concurrency 51% cov | Regressions | Expand HTTP integration tests | M |
| BE3 | **Medium** | Admin mutations unaudited | workspace/membership routes lack `audit()` | Forensics gap | Wire audit helper | S |
| BE4 | **Medium** | OpenAPI public | `/openapi.json` 200 without auth | Recon | Disable in prod | S |

### Frontend

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| FE1 | **Critical** | No product UI | `App.tsx` health check only | No beta | Review Desk + login | L |
| FE2 | **High** | Vite `/api` proxy missing rewrite | `vite.config.ts` forwards `/api/health/ready` to FastAPI `/api/...` which does not exist | Broken local UX | Add rewrite strip `/api` | S |
| FE3 | **Medium** | npm audit: 6 high, 1 moderate | `npm audit` metadata | Supply chain | Update deps / audit fix | M |
| FE4 | **Low** | `npm test` not in CI web job | `ci.yml` web: lint+build only | Drift | Add vitest in CI when tests exist | S |

### Database / PostgreSQL / Alembic

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| DB1 | **Info/Pass** | Migrate/downgrade/replay works | This audit run on fresh DB | — | Keep replay in CI | — |
| DB2 | **Critical** | ORM enum missing `paused`/`created`/`compensating` | Probe `LookupError` on `session.get(PipelineRun)` after Gate pause; `PipelineRunStatus` vs DB ALTER in `0014` | Product APIs that reload runs break | Align model enum with DB (use V2 values) + regression test | S |
| DB3 | **High** | 33 unindexed FK columns | SQL catalog query this run | Write amplification / locks | Index hot FKs (`workspace_id`, run FKs) | M |
| DB4 | **Pass** | FORCE RLS on 36 domain tables | `pg_class.relforcerowsecurity` | — | Maintain | — |
| DB5 | **Info** | `event_consumers` / `consumer_checkpoints` no RLS | Intentional service tables | OK if no tenant data | Document | S |
| DB6 | **Pass** | Immutable triggers present | 14 immutable trigger names | — | Keep append-only | — |
| DB7 | **Medium** | CI lacks downgrade/replay | `.github/workflows/ci.yml` only `upgrade head` | Future breakages | Add up→down→up job | S |
| DB8 | **Medium** | Four “fix” membership RLS migrations (0021–0024) | Migration history | Policy complexity | Leave history; strengthen RLS tests | S |

### SQLAlchemy / models

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| SA1 | **Critical** | `PipelineRun.status` typed to incomplete enum | `models/pipeline.py` + `PipelineRunStatus`; V2 enum unused | Runtime load failures | Switch column enum to full set | S |
| SA2 | **Medium** | Soft deletes / version mixins exist; product paths unused | Models present; no content HTTP | Dead weight until product | OK | — |

### RLS / AuthZ / AuthN

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| SEC1 | **Pass** | JWT required | 401 probes | — | Keep | — |
| SEC2 | **Pass** | Cross-tenant deny at guard | 403 probe | — | Keep RLS tests | — |
| SEC3 | **High** | Invite by UUID only | `MembershipCreate.user_id` | Onboarding friction / mistakes | Email invites later | L |
| SEC4 | **High** | No app login | Web has no Supabase client | Beta blocker | Auth UI | M |
| SEC5 | **Medium** | OpenAPI exposed | Probe 200 | Recon | Lockdown | S |
| SEC6 | **Medium** | Dependency vulns (pip-audit / npm) | starlette/jinja2/pyjwt/etc.; npm 6 high | Supply chain | Patch policy + CI audit | M |
| SEC7 | **Pass (spot)** | No eval/exec/subprocess/pickle in apps | Grep clean | — | Keep | — |
| SEC8 | **Pass (spot)** | Workspace name SQLi treated as data | `'; DROP...` created as name 201 | ORM parameterization | Keep | — |
| SEC9 | **High** | BYOK encryption unimplemented | `encrypted_secret` column; no crypto module | Cannot store keys safely | Build crypto before any key UI | L |

### Human Review Gate

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| RG1 | **Critical** | Gate unreachable by customers | No HTTP/UI; 404 probes | No wedge | Product APIs + UI | L |
| RG2 | **Critical** | Review consumers not registered at boot | `consumers.register_all` unused in `main` | Approvals never resume in prod | Register + relay loop | M |
| RG3 | **High** | Pause breaks ORM reload | PAUSED_ENUM_LOAD FAIL | Blocks any Gate API | Fix enum | S |
| RG4 | **Pass (library)** | Gate logic tested | `test_orchestration_workflow.py` | — | Keep | — |

### Spend controls

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| SP1 | **Critical** | No customer spend API / no seed on create | `workspaces.py` create; no SpendCap insert | Caps unused | Seed + HTTP | M |
| SP2 | **High** | Monthly cap dead | `monthly_cap` not in `reserve_spend` source | False security | Enforce or remove promise | S |
| SP3 | **Pass (daily path)** | Daily + FOR UPDATE | controller + WS4 tests | — | Keep | — |

### Workers / queues / outbox / retry / idempotency

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| W1 | **Critical** | Generation stub | `_default_executor` | Empty product | Real executor or honest Draft SKU | XL / S |
| W2 | **Critical** | Scheduler not running | lifespan | No dispatch | Wire tick | M |
| W3 | **High** | Scheduler lease reaper not in maintenance | Only assignment reaper | Stuck LEASED jobs | Add reap | S |
| W4 | **Pass (library)** | Claim SKIP LOCKED, recovery, provider effect keys | M4 tests | — | Keep | — |
| W5 | **Medium** | DLQ no admin API | table only | Ops blind | Admin routes | M |
| W6 | **Info** | `RECURRING` loud `NotImplementedError` | scheduler.py | OK | Keep until producer | — |

### CI/CD / GitHub Actions

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| CI1 | **High** | No coverage gate, format, secret scan, CodeQL, migration replay | `ci.yml` minimal | Quality drift | Adopt strengthened CI (see unmerged #20 ideas) | M |
| CI2 | **Critical** | No CD / Docker app images | compose = Postgres only | Cannot host beta | Dockerize + deploy | L |
| CI3 | **Pass** | PR/main CI runs three jobs | workflow file | — | Keep | — |

### Tests

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| T1 | **Pass** | 136 API tests green | this run | — | Keep | — |
| T2 | **High** | No regression for paused ORM load | Probe failed; suite still green | False confidence | Add failing→fixed test | S |
| T3 | **Medium** | HTTP route coverage weak | cov missing lines on routes | Bugs in unused paths | Product tests when routes land | M |
| T4 | **Medium** | Worker suite tiny | 1 test | Stub confidence | Expand with executor | M |
| T5 | **High** | CI coverage not enforced | pytest without `--cov-fail-under` | Regressions | Gate ≥70% when stable | S |

### Documentation / business / agents

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| D1 | **Critical** | README false status | lines 68–78 | Mis-set expectations | Rewrite | S |
| D2 | **High** | Business/PMF/Launch plans not on `main` | PRs #21–#25 draft only | Strategy not SoT | Merge docs worth keeping | S |
| D3 | **High** | No AGENTS.md / rules on `main` | filesystem | AI/process drift | Merge foundation PR or recreate | M |
| D4 | **Medium** | Milestone doc sprawl vs launch | many `M4_WS*` | Noise | Archive to `docs/internal/` | S |

### Security / performance / recovery / env / docker / deps

| ID | Severity | Finding | Evidence | Risk | Recommendation | Effort |
|----|----------|---------|----------|------|----------------|--------|
| X1 | **Critical** | No backups/DR | no scripts/docs | Data loss | Backups before paid | M |
| X2 | **High** | Metrics unwired | `metrics.py` 0% cov | Blind ops | Export + alerts | M |
| X3 | **Medium** | No rate limits | routes open | Abuse | Gateway limits | M |
| X4 | **Medium** | `.env.example` incomplete for workers | missing `WORKER_CREDENTIAL` etc. | Misconfig | Complete | S |
| X5 | **High** | Dep vulnerabilities | pip-audit + npm audit this run | Known CVEs | Patch cadence | M |
| X6 | **Pass** | Assignment lease recovery wired | maintenance loop | — | Keep | — |

---

## Attempted bypass summary

| Control | Bypass attempted | Result |
|---------|------------------|--------|
| Authentication | No/garbage token | **Blocked** (401) |
| Authorization / IDOR | Other user’s workspace | **Blocked** (403) |
| RLS | Relies on guards + FORCE RLS (catalog verified) | **Strong** for existing routes |
| Human Review Gate | No HTTP surface | **N/A — missing product** (cannot bypass what customers cannot reach; also cannot use) |
| Spend controls | Monthly unused; no seed | **Partially ineffective** as product control |
| Provider permissions | No BYOK API | **N/A — missing** |

---

## Unmerged work (does not count as shipped)

Draft PRs exist for Review Desk (#23), audits (#24), launch plan (#25), business (#21), PMF (#22), Cursor foundation (#20), many skills (#6–#19). **`main` remains engine-only.** Merging docs/skills without P0 product wiring does **not** change the verdict.

---

## Completeness model

| Layer | % | Notes |
|-------|---|-------|
| Data model / migrations | 85 | Schema ahead of product |
| Identity / RLS | 90 | Strong |
| Worker protocol | 80 | Stub executor |
| Orchestration library | 75 | Not wired |
| Product APIs | 5 | Infra only |
| Frontend | 5 | Health check |
| Billing | 0 | — |
| Ops (CD/DR/obs) | 15 | CI only |
| **Weighted launch** | **~22** | Matches unreadiness |

---

*No finding marked VERIFIED without a command, probe, or file path from this audit run.*
