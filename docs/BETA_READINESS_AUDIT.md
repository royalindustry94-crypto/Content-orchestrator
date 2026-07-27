# Beta Readiness Audit — Content Orchestrator

**Audit date:** 2026-07-27  
**Source of truth:** `main` @ `248f69f` (Milestone 4 WS1–WS4 merged)  
**Question answered:** Could we onboard our first paying customer **today**?  
**Method:** Repository verification (routes, lifespan, workers, schema, CI, docs). Unmerged draft PRs noted separately — they do **not** count as shipped.

---

## Executive Summary

**No. We could not onboard a first paying customer today.**

Content Orchestrator on `main` is a **strong multi-tenant orchestration engine** with identity, FORCE RLS, worker protocol, review-gate *library* logic, and spend *library* logic. It is **not a product**.

A paying customer cannot today:

1. Sign up and log in through our app  
2. Submit content into a pipeline through a supported UI/API product path  
3. Approve work in a Review Desk on `main`  
4. Get real AI generation (worker executor is a canned-success stub)  
5. Have scheduled jobs advance (scheduler + outbox relay are **not** started in the API process)  
6. Pay us (zero Stripe/billing code)  
7. See spend caps they control (no spend HTTP API; caps not seeded on workspace create)  
8. Publish or view analytics (schema-only)  
9. Rely on a deploy/backup story (CI only; no CD; no DR)

**Final verdict:** **NOT READY**

| Score | Value |
|-------|-------|
| **Launch Score** | **28 / 100** |

Unmerged draft PR [#23](https://github.com/royalindustry94-crypto/Content-orchestrator/pull/23) (`cursor/private-beta-mvp-b52d`) would raise the score to ~**42** if merged (Review Desk API/UI + outbox relay). It still would **not** make the product beta-ready without scheduler wiring, real generation, spend surface, billing, auth UI, and ops basics.

---

## Launch Score (0–100)

| Dimension | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Customer-reachable core loop | 25 | 2 | Engine exists; no product path on `main` |
| Human Review Gate (sellable) | 15 | 6 | Library + tests; no HTTP/UI on `main` |
| Spend controls (sellable) | 10 | 4 | Daily reserve + lock; no API; monthly unused |
| Auth / tenancy / RLS | 15 | 13 | JWT + roles + FORCE RLS + isolation tests |
| Real generation / providers | 10 | 1 | Stub executor only |
| Billing | 10 | 0 | Absent |
| Frontend / onboarding | 5 | 1 | Health check only |
| Ops (CI/CD, backups, observability) | 5 | 2 | CI yes; CD/DR/metrics no |
| Docs for customers/operators | 5 | 1 | Stale README; no onboarding runbook |
| **Total** | **100** | **28** | |

**Score bands:** 0–39 not beta · 40–59 private beta (invite-only, founder-assisted) · 60–79 first 10 paid with care · 80+ public launch posture.

---

## Area-by-area audit

Legend: **Complete** · **Production Ready** · **Beta Ready** · **Missing** · risk **High / Medium / Low**

### Backend

| Verdict | **Beta Ready** (infra APIs) / **Missing** (product APIs) | Risk: **High** |
|---------|----------------------------------------------------------|----------------|

**Evidence (`apps/api/app/main.py`):** routers = health, profiles, workspaces, memberships, concurrency, workers only.

| Exists | Missing for customer |
|--------|----------------------|
| Workspace/membership CRUD | Content jobs create/list |
| Worker fleet admin + machine protocol | Review gate list/decide |
| Concurrency / provider budgets | Spend cap CRUD + ledger |
| `/me` profile | BYOK provider credentials API |
| | Billing, publish, analytics, notifications, DLQ admin |

**Unmerged:** PR #23 adds content-jobs + review-gates routes — still not on `main`.

---

### Frontend

| Verdict | **Missing** | Risk: **High** |
|---------|-------------|----------------|

**Evidence:** `apps/web/src/App.tsx` — Milestone-1 health check only (`/api/health/ready`). No login, no review desk, no onboarding.

**Vite proxy on `main`:** `apps/web/vite.config.ts` proxies `/api` **without** stripping the prefix → health check is broken against FastAPI `/health/ready` unless something else rewrites.

**Unmerged:** PR #23 Review Desk UI (token paste + workspace id) — still not real Supabase login.

---

### Database

| Verdict | **Production Ready** (schema/migrations) | Risk: **Low** (schema) / **High** (ops) |
|---------|------------------------------------------|------------------------------------------|

- Alembic linear head **`0029`** (`apps/api/alembic/versions/`).  
- Domain tables + FORCE RLS verified in `apps/api/tests/test_schema_migrations.py`.  
- Models exist for content, pipeline, spend, publish, analytics, provider credentials.  
- **Ops gap:** no backup/restore automation; `docker-compose.yml` is Postgres-only.

---

### Workers

| Verdict | **Production Ready** (protocol) / **Missing** (generation) | Risk: **High** |
|---------|------------------------------------------------------------|----------------|

**Evidence:** `apps/worker/worker/client.py` — `_default_executor` returns `(True, {}, "")` with explicit “generation excluded” docstring.  
Register / heartbeat / claim / ack / renew / submit protocol is real and tested.

---

### AI orchestration

| Verdict | **Beta Ready** (library) / **Missing** (runtime wiring) | Risk: **High** |
|---------|---------------------------------------------------------|----------------|

**Exists:** outbox, workflow controller, claiming, recovery, back-pressure (`apps/api/app/orchestration/`).  
**Not in API lifespan on `main`:**

- `scheduler.poll_and_lease` / `process_leased_job` — tests only  
- `relay.poll_and_dispatch` — tests only  
- `consumers.register_all()` — **never called** on `main`

**Evidence:** `apps/api/app/main.py` maintenance loop = offline sweep + assignment lease reap + backpressure only.

Even if content APIs were merged, **jobs would not advance** without scheduler + relay wiring.

---

### Human Review Gate

| Verdict | **Beta Ready** (engine) / **Missing** (product surface on `main`) | Risk: **High** |
|---------|-------------------------------------------------------------------|----------------|

**Engine:** `pause_for_review`, `submit_review_decision`, timeout/escalation in `apps/api/app/orchestration/controller.py`; migration `0019_review_gates.py`; workflow tests.  
**Product:** no review HTTP/UI on `main`. Consumers that resume runs are unregistered at boot.

---

### Spend controls

| Verdict | **Beta Ready** (daily reserve) / **Missing** (product + monthly) | Risk: **High** |
|---------|------------------------------------------------------------------|----------------|

| Present | Gap |
|---------|-----|
| `reserve_spend` with `FOR UPDATE` on cap row | Monthly cap column **never checked** |
| Fail-closed `SPEND_HOLD` + event | No HTTP for caps/ledger |
| Config defaults in settings | **Not seeded** on `POST /workspaces` |
| Concurrency race test (WS4) | Customer cannot see or set caps |

---

### Authentication

| Verdict | **Production Ready** (API JWT) / **Missing** (app login) | Risk: **Medium** |
|---------|----------------------------------------------------------|------------------|

- Supabase JWT verify: `apps/api/app/core/security.py`  
- Fail-fast `SUPABASE_JWT_SECRET` in settings  
- No in-app signup/login; customer must use Supabase elsewhere  
- README incorrectly references `JWT_SECRET_KEY`

---

### Authorization

| Verdict | **Production Ready** | Risk: **Low–Medium** |
|---------|----------------------|----------------------|

- Roles: admin / editor / reviewer (`workspace_membership.py`)  
- Guards: `require_workspace_member` / `admin` (`authorization.py`)  
- Invite API takes **`user_id`**, not email — founder friction for beta

---

### Multi-tenancy / RLS

| Verdict | **Production Ready** | Risk: **Low** |
|---------|----------------------|---------------|

- FORCE RLS on domain tables; isolation tests (`test_cross_workspace_isolation.py`)  
- Worker/credential tables intentionally service-role scoped (documented in M4 migrations)  
- This is the strongest production-grade area in the repo

---

### Provider abstraction / BYOK

| Verdict | **Missing** | Risk: **High** |
|---------|-------------|----------------|

- `ProviderCredential` model with `encrypted_secret` / `encryption_key_id` (`models/config.py`)  
- **No** encrypt/decrypt service, **no** credential routes, **no** encryption key env  
- Worker never reads provider credentials

---

### Audit logging

| Verdict | **Beta Ready** (partial) | Risk: **Medium** |
|---------|--------------------------|------------------|

- Request ID middleware + structured JSON logs (`core/audit.py`, `core/logging.py`)  
- Worker/concurrency mutations audited  
- **Not audited:** workspace create/update, membership invite/role/remove  
- No customer-exportable audit trail API

---

### CI/CD

| Verdict | **Beta Ready** (CI) / **Missing** (CD) | Risk: **Medium–High** |
|---------|----------------------------------------|------------------------|

**CI (`.github/workflows/ci.yml`):** API (migrate + ruff + pytest), worker, web lint/build.  
**CD:** none. No Dockerfile for API/worker. Compose = Postgres only. No staging/prod promote.

---

### Documentation

| Verdict | **Missing** (customer/operator) / **Complete** (internal M4) | Risk: **High** |
|---------|-------------------------------------------------------------|----------------|

| Good | Bad |
|------|-----|
| M2 identity doc, M4 workstream designs | README claims auth/data model “not yet built” — **false** |
| Architecture decisions (partial) | No customer onboarding runbook |
| | `database/README.md` / `n8n/README.md` placeholders |
| | Business/PMF docs exist only on **unmerged** branches |

---

### Error handling

| Verdict | **Beta Ready** (orchestration style) | Risk: **Medium** |
|---------|--------------------------------------|------------------|

- Fail-loud patterns in scheduler (`NotImplementedError` for RECURRING), config fail-fast  
- Maintenance/relay ticks catch and log (when wired)  
- No global API error envelope; review consumers silently no-op if gate missing

---

### Observability

| Verdict | **Missing** (metrics/alerts) / **Beta Ready** (logs) | Risk: **Medium** |
|---------|------------------------------------------------------|------------------|

- JSON logs yes  
- `orchestration/metrics.py` unwired; no `/metrics`, no Sentry/PagerDuty/Slack alerts  
- Trace IDs on events without OpenTelemetry export

---

### Billing readiness

| Verdict | **Missing** | Risk: **High** |
|---------|-------------|----------------|

Zero Stripe (or any payment) code, tables, webhooks, or entitlement checks. Cannot charge a customer in-product.

---

### Customer onboarding

| Verdict | **Missing** | Risk: **High** |
|---------|-------------|----------------|

No guided flow. Manual: Supabase user → JWT → `POST /workspaces` → UUID membership invites → provision worker secret → (no content path on `main`).

---

### Settings / user management

| Verdict | **Beta Ready** (minimal) | Risk: **Medium** |
|---------|--------------------------|------------------|

Workspace name + priority tier + memberships. No brand kit, notification prefs, spend settings UI, email invites.

---

### Publishing pipeline

| Verdict | **Missing** (app) / schema present | Risk: **High** for “full product”; **Medium** if beta = review-only |
|---------|-------------------------------------|----------------------------------------------------------------------|

`PublishJob` model + migration `0007`; no routes/workers/n8n workflows.

---

### Analytics

| Verdict | **Missing** | Risk: **Low** for beta (defer) |
|---------|-------------|-------------------------------|

`AnalyticsSnapshot` schema only. Not needed for first paid beta if positioning is Review Desk + spend.

---

### Security

| Verdict | **Beta Ready** (identity/workers) / **High Risk** (product gaps) | Risk: **High** overall for paid data |
|---------|------------------------------------------------------------------|--------------------------------------|

Strengths: JWT, RLS, worker secret hashing, audit refuse-secrets.  
Gaps: no BYOK crypto, OpenAPI `/docs` unauthenticated by default, no rate limits, no entitlement layer, secrets story incomplete for providers.

---

### Performance

| Verdict | **Beta Ready** (design) | Risk: **Medium** |
|---------|-------------------------|------------------|

SKIP LOCKED, fairness caps, back-pressure exist. Untested under real multi-tenant load. No rate limits. Advisory locks on outbox emit may contend at scale.

---

### Recovery

| Verdict | **Beta Ready** (assignment leases) / **Missing** (scheduler leases + DLQ ops) | Risk: **High** |
|---------|------------------------------------------------------------------------------|----------------|

Assignment lease reaper + dead-worker recovery **wired** in lifespan.  
Scheduler job-lease reaper **not** wired. DLQ table exists; **no** admin/replay API. Outbox never relays in prod on `main`.

---

### Disaster recovery

| Verdict | **Missing** | Risk: **High** |
|---------|-------------|----------------|

No backup jobs, PITR docs, restore drills, or runbooks. Local Docker volume only.

---

### Secrets management

| Verdict | **Beta Ready** (app/JWT/DB) / **Missing** (BYOK) | Risk: **High** |
|---------|--------------------------------------------------|----------------|

Worker credentials: generate/hash/rotate done right.  
Provider BYOK: schema fantasy until encrypt service exists.  
`.env.example` omits worker runtime vars (`API_BASE_URL`, `WORKER_CREDENTIAL`, etc.).

---

### Environment configuration

| Verdict | **Beta Ready** for local API | Risk: **Medium** |
|---------|------------------------------|------------------|

Required DB + JWT fail-fast. Incomplete for worker + providers + production CORS. README wrong secret name.

---

## Critical Blockers

These must be true before inviting a paying customer. **Any one blocks “yes.”**

| ID | Blocker | Evidence | Area |
|----|---------|----------|------|
| B1 | No customer content → review product path on `main` | No content/review routes; UI health-only | Backend/Frontend |
| B2 | Orchestration loops inert in production process | No scheduler/relay/`register_all` in `main.py` lifespan | AI orchestration |
| B3 | Generation is a stub | `_default_executor` always succeeds empty | Workers |
| B4 | No way to take payment | No Stripe/billing code | Billing |
| B5 | Spend not customer-controllable | No spend API; caps not seeded; monthly unused | Spend |
| B6 | No real login/onboarding UX | No Supabase client; invite by UUID only | Auth/Onboarding |
| B7 | No deploy + backup story | CI only; no CD; no DR | Ops |
| B8 | Docs actively mislead operators | README “auth/data model not built” | Documentation |

**Also critical if promising “AI content” rather than “review desk for drafts”:** B3 is non-negotiable. A review-only Private Beta with manual drafts could temporarily soften B3 **only** with honest sales messaging (PR #23 direction) — still blocked by B1/B2/B4/B5/B6/B7 on `main`.

---

## High Priority Work

| Item | Why |
|------|-----|
| Merge or re-land Review Desk (PR #23) onto `main` | Unlocks Gate as product |
| Wire scheduler + relay + `consumers.register_all()` (+ scheduler lease reap) | Makes pipelines move |
| Seed default spend caps on workspace create + spend read/update API | Sellable control + safety |
| Supabase Auth in web (real login) | Replace token paste |
| One real BYOK generation path **or** explicit “draft desk” SKU | Avoid selling empty AI |
| Stripe Checkout + webhook entitlement | First dollar |
| Dockerfile/compose for API+worker+web + staging deploy | Actually host it |
| Operator onboarding doc + README rewrite | Stop lying to ourselves |
| Email or Slack on `REVIEW_REQUESTED` | Agency won’t poll forever |
| Lock down `/docs` in production; set CORS | Security hygiene |

---

## Medium Priority Work

| Item | Why |
|------|-----|
| Enforce `monthly_cap_usd` in `reserve_spend` | Schema promise unbroken |
| Email-based invites | Reduce UUID friction |
| Audit events for workspace/membership mutations | Trust |
| DLQ list/replay admin API | Ops |
| `/metrics` + basic alerting | See fires |
| Brand kit fields at Gate | Agency WTP |
| Export approved artifact (file/Drive) | Completes “first video” story without full publish |
| Rate limiting on worker + auth routes | Abuse |

---

## Low Priority Work

| Item | Why |
|------|-----|
| Full social publishing integrations | Buffer/Hootsuite already own this |
| Analytics snapshots productization | After revenue |
| n8n workflow pack | Distraction |
| Recurring job type | Explicitly unimplemented |
| Agent OS / connector marketplace | Anti-PMF |
| White-label / SSO / SOC2 theater | After paid demand |
| Skill sprawl / unused Cursor skill PRs | Not product |

---

## What should be removed or stopped

Brutal recommendations:

1. **Stop milestone theater as a success metric.** M4 engine quality ≠ launch.  
2. **Do not merge the long list of Cursor skill/agent draft PRs (#9–#19 era) into `main` as “progress.”** They do not onboard customers. Archive or close.  
3. **Delete or quarantine repo cruft:** `attached_assets/`, one-off HTML/PDF audit reports at repo root, stale `RELEASE_CHECKSUMS.md` if obsolete, empty `n8n/`/`packages/` promises until used.  
4. **Do not build Zapier-scale integrations or autonomous publish** before Review Desk + billing work. PMF audit (unmerged) already said PIVOT — agree.  
5. **Treat `_default_executor` as a liability:** either replace before any “AI” sales call or rename the offer to Draft Review Desk.

---

## Estimated effort (technical, founder-focused)

Not calendar promises — **focused founder-weeks of execution** assuming one senior full-stack founder, no big-team parallelization tax.

| Milestone | Effort | Scope |
|-----------|--------|-------|
| **Private Beta (invite-only, founder-assisted)** | **3–5 founder-weeks** | Merge Review Desk; wire scheduler+relay; spend seed+API; real login; draft-or-one-provider path; staging deploy; onboarding doc; optional manual invoicing |
| **First paying customer** | **+1–2 founder-weeks** after beta | Stripe Checkout + entitlement; Slack/email review ping; spend ledger UI; support runbook; backups |
| **Public launch posture** | **+4–8 founder-weeks** after first paid | Real BYOK+providers; export/publish v1; observability/alerts; rate limits; monthly caps; harden tenancy incidents; marketing site; self-serve onboarding |

**Assumption:** Founder sells to agencies who accept “Private Beta” constraints. If the offer requires full video factory automation on day one, add **+4–6 weeks** for generation quality alone.

---

## New roadmap (business impact only)

Ignore prior milestone numbering. Prioritize Revenue → Customer value → Reliability → Security.

### P0 — Must exist before Beta

| # | Work | Outcome |
|---|------|---------|
| P0-1 | Land Review Desk (content job + gate decide + UI) on `main` | Customer can operate the Gate |
| P0-2 | Start scheduler + outbox relay + register consumers (+ scheduler lease reap) | Pipelines actually advance |
| P0-3 | Seed + expose spend caps (daily enforced; monthly enforced or removed from schema promises) | Hard $ controls are real |
| P0-4 | Supabase login in web (kill token-paste as primary UX) | Real users |
| P0-5 | Staging deploy (API + worker + web + Postgres) with secrets | Hosted demo |
| P0-6 | Operator onboarding doc + honest README | Founder can board a design partner |
| P0-7 | Choose SKU: **Draft Review Desk** *or* ship **one** BYOK generator | Honest product |

### P1 — Must exist before first paying customer

| # | Work | Outcome |
|---|------|---------|
| P1-1 | Stripe Checkout + webhook → workspace entitlement | Take money |
| P1-2 | Slack or email on Review Gate request | Reviewers get notified |
| P1-3 | Spend ledger read API + simple UI | Trust / FinOps story |
| P1-4 | Automated DB backups + restore drill | Don’t lose paid tenant data |
| P1-5 | Export approved artifact (download or Drive) | Completes first value loop |
| P1-6 | Audit log for membership/workspace admin actions | Agency trust |
| P1-7 | Production CORS + disable public OpenAPI | Security |

### P2 — Important after revenue begins

| # | Work |
|---|------|
| P2-1 | Second provider / better generation quality |
| P2-2 | Brand kit checks at Gate |
| P2-3 | Email invites (not UUID) |
| P2-4 | Metrics endpoint + basic alerts |
| P2-5 | DLQ admin UI/API |
| P2-6 | Buffer/one scheduler integration |
| P2-7 | Rate limits + abuse controls |

### P3 — Nice to have

| # | Work |
|---|------|
| P3-1 | Full publish network integrations |
| P3-2 | Analytics product |
| P3-3 | SSO / SOC2 |
| P3-4 | White-label |
| P3-5 | n8n pack / self-host |
| P3-6 | Autonomous agents |

---

## Architecture change recommendations (evidence-based)

1. **Treat background orchestration as a first-class process requirement.** Evidence: scheduler/relay exist and are tested but absent from `lifespan`. Either wire them in the API process or run a dedicated `apps/orchestrator` worker — today the “engine” is a library.  
2. **Do not expand worker protocol further before a product loop.** Evidence: M4 WS1–4 depth vs zero customer content API on `main`.  
3. **BYOK encryption before any provider key UI.** Evidence: `encrypted_secret` column with no crypto implementation — shipping plaintext would be a trust-ending mistake.  
4. **Separate “engine completeness” from “launch readiness” in all future CEO reports.** Evidence: 136 tests / head `0029` coexist with Launch Score 28.

---

## Unmerged work that changes the score (not shipped)

| PR / branch | If merged | Still missing |
|-------------|-----------|---------------|
| #23 Review Desk | Content/review APIs + UI + relay tick | Scheduler, billing, BYOK, login, spend API, CD |
| #22 PMF audit | Strategy only | Code |
| #21 Business foundation | Strategy only | Code |
| #20 Cursor foundation refactor | Eng process/CI | Product loop |
| Skill/agent PRs #9–#19 | Process noise | Product loop |

**Recommendation:** Merge #23 only as part of a **P0 bundle** that also wires the scheduler; otherwise Gate APIs still won’t advance runs for real worker-driven stages.

---

## Final Verdict

# NOT READY

**Evidence summary:**

- `main` exposes **no** content-job or review-gate routes.  
- Web app is a **health check**.  
- Worker generation is a **stub**.  
- Scheduler and outbox relay are **not running** in production lifespan.  
- **Billing code does not exist.**  
- Spend caps are **not** a customer-facing feature.  
- No **deploy/backup** path for a paying tenant.

**Could we onboard our first paying customer today?**  
**No.**

Closest honest near-term target: **Private Beta in 3–5 founder-weeks** if P0 is executed without milestone distraction — still founder-assisted, still narrow SKU, still not public launch.

---

*Audit stance: assume previous decisions are wrong until the product path is verified. This document supersedes milestone completion as the launch scorecard.*
