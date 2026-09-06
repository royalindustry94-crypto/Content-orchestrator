# Build-to-live process map

This is the authoritative walkthrough an auditor or continuation agent must
internalize before judging or extending work. "Live" here means a Founder-
approved private-beta environment with health checks green — not production,
not paid billing, and not autonomous publishing.

Planning docs alone never count as progress. Exact-head evidence does.

## 1. Product north star

Private Beta → first paying customers → PMF.

Sellable path today:

1. Operator signs in (`AUTH_MODE=local` for Private Beta)
2. Workspace is created and membership/roles are assigned
3. A content job enters the pipeline
4. Preview departments may run: Scout → Strategist → Content → Producer → Compliance
5. Mandatory **Human Review Gate** decides the exact reviewed artifact
6. Output is publish-ready only. External publishing stays disabled
7. Spend caps fail closed (HTTP 402 / hold) on chargeable work

Non-negotiables that must survive every change:

- Human Review Gate
- FORCE RLS / workspace isolation
- Spend fail-closed
- Provider abstraction (no single-vendor hard-code on the core path)
- Structured audit logging for security-relevant mutations
- No TODOs, stubs, or silent fallbacks on production paths

## 2. Repository layout

| Path | Role |
|---|---|
| `apps/api` | FastAPI, SQLAlchemy 2.x async, Alembic, product APIs, orchestration |
| `apps/web` | React + TypeScript + Vite Review Desk / Business Manager UI |
| `apps/worker` | Draft Desk claim / execute / submit |
| `docs/` | Architecture, ops, audits, work packages |
| `.github/workflows/ci.yml` | Required six-job CI |
| `docker-compose.yml` | Local Postgres only |
| `docker-compose.staging.yml` | Full API + worker + web + Postgres staging stack |

## 3. Local build (developer start)

```bash
cp .env.example .env
# Required: SUPABASE_JWT_SECRET
docker compose up -d postgres

cd apps/api && pip install -e ".[dev]" && alembic upgrade head
uvicorn app.main:app --reload --port 8000

cd apps/worker && pip install -e ".[dev]" && python -m worker.main

cd apps/web && npm install && npm run dev
```

Web: `http://localhost:5173`  
API: `http://localhost:8000` — OpenAPI only when `ENVIRONMENT=development|dev`

Auth: `POST /auth/signup` and `/auth/login` mint Supabase-shaped JWTs.

## 4. Staging / container build (app actually running)

```bash
cp .env.example .env
docker compose -f docker-compose.staging.yml up --build
```

| Service | Port | Ready when |
|---|---|---|
| postgres | 5432 | `pg_isready` |
| api | 8000 | `GET /health/live` then `/health/ready` |
| worker | — | API healthy; worker registered with `WORKER_CREDENTIAL` / `WORKER_ID` |
| web | 8080 | nginx `dist`; `/api/` proxied to API |

API entrypoint runs `alembic upgrade head` when `RUN_MIGRATIONS=1`.  
Migrations use `DATABASE_URL` (owner). Runtime queries must use
`APP_DATABASE_URL` as `app_runtime` so RLS stays enforced.

Health after the stack is up:

```bash
curl -sf http://localhost:8000/health/live
curl -sf http://localhost:8000/health/ready
curl -sf http://localhost:8000/health/automation
curl -sf http://localhost:8080/api/health/live
```

Tokenless `/metrics` on a deployed non-local environment must return `401`
when `METRICS_SCRAPER_TOKEN` is required.

## 5. End-to-end product path that must stay true

```text
signup/login
  → workspace + membership
  → content job (or preview department run)
  → worker claim (if a real stage is claimed)
  → immutable content version
  → Human Review Gate (mandatory)
  → approve / reject of the exact reviewed version
  → publish-ready artifact
  → no automatic external publish
```

Preview department chain on the audited `main` baseline (PR #48):

1. Business Manager UI
2. Scout + independent Research Auditor
3. Strategist + independent Strategy Auditor
4. Content Department (writer + language/fact/brand/originality audits)
5. Producer + independent Media QA
6. Compliance + Chief Auditor
7. Human Review package boundary

Unconfigured providers must show a truthful `NOT CONFIGURED` state and spend
zero provider cost. Test-only fixtures must not appear as live telemetry.

## 6. Engineering change process (start of a build)

1. Read `docs/LAUNCH_BLOCKERS.md` and take the highest business-value open item
2. Branch from current `origin/main` (`git fetch origin main` first)
3. Keep the change additive. P0 is frozen unless a Critical defect is proven
4. Schema: Alembic upgrade **and** downgrade, single linear head, rollback note
5. Preserve workspace membership/role guards on every new route
6. Preserve FORCE RLS on new tenant tables (or owner-only by explicit design)
7. Spend path remains fail-closed
8. Gate remains mandatory for publishable content
9. Secrets only via env; never commit `.env`
10. Tests:
    - API: `pytest --cov-fail-under=75`
    - Worker: `pytest`
    - Web: `npm test` and production build
11. Update launch/debt/work-package docs when closing a P0/P1 item
12. Open a PR. Do not merge. Do not self-certify

## 7. CI that must pass on the exact candidate SHA

From `.github/workflows/ci.yml`:

| Job | Proof |
|---|---|
| `api` | migrate, downgrade base, re-upgrade, ruff, pytest coverage ≥ 75% |
| `worker` | ruff + pytest |
| `web` | lint, typecheck/build, tests, `npm audit --audit-level=high` |
| `browser-smoke` | exact PR head SHA, desktop + 390px, artifact retained 30 days |
| `security` | gitleaks + pip-audit for API and worker |
| `docker-build` | API, worker, and web images |

Vercel preview statuses exist on some PRs. They are **not** required product
gates. This app is FastAPI + Vite + nginx, not a Vercel-native deployment.

## 8. Independent audit gate (before merge)

Every milestone uses `docs/MILESTONE_AUDIT_STANDARD.md`.

- The builder cannot be the sole certifier
- Verdicts: **PASS**, **CONDITIONAL**, or **FAIL**
- FAIL blocks merge unless the Founder explicitly overrides after reviewing risk
- CONDITIONAL is only for non-safety-critical, owner-assigned, time-bounded items
- Missing evidence for tenancy, Human Review, spend, secrets, destructive
  migrations, or critical data integrity is **FAIL**, not conditional

Audit domains: scope, security/tenancy, Human Review Gate, spend/providers,
data/migrations, reliability, tests/CI, UI/browser, runtime/external evidence,
documentation.

## 9. Merge re-check

Immediately before any merge, re-check:

- Exact PR head SHA
- CI on that SHA
- Unresolved review threads and findings
- Alembic head (linear)
- Required runtime/external evidence
- Founder approval where required
- Preview / `do not merge` drafts need explicit Founder approval

`main` protection must be independently verified as technically enforced.
Issue #50 is closed in GitHub; auditors must still re-read the live
protection/ruleset rather than trust the ticket state.

## 10. Deploy-to-live (private beta only)

Follow `docs/MONDAY_DEPLOYMENT_RUNBOOK.md` and
`docs/BETA_GO_NO_GO_CHECKLIST.md`.

Hard stops:

- No deploy without an exact Founder-approved SHA
- No merge, force-push, or direct `main` write from an agent
- `BILLING_ENABLED` stays `false` unless a separate audited billing milestone
- Automatic external publishing stays disabled
- Secrets are inspected by name only; values are never printed
- Managed backup/PITR evidence is required before claiming rollback readiness
- Runtime connection remains `app_runtime`; never "fix" RLS by using owner

Deploy sequence:

1. Clean checkout of the approved SHA
2. Confirm CI on that SHA
3. Record rollback reference and backup/PITR point
4. Migrate once through the owner connection
5. Start API, worker, web
6. Prove `/health/live`, `/health/ready`, `/health/automation`
7. Prove tokenless `/metrics` is `401`
8. Disposable workspace smoke: create job, land in Gate, approve/reject exact
   item, confirm no automatic publish, confirm truthful spend/worker state
9. Record SHA, migration head, health, worker state, and blockers

The app is "live" only when those checks pass on the intended environment.

## 11. What is not live yet

As of the audited `main` baseline (`abb20981f68cb0de8e3ed75af9759e0b5b6fb656`
after PR #51):

| Target | State |
|---|---|
| Product code on `main` | Private-beta capable preview pipeline |
| Operational private beta | Not runtime-verified in-repo |
| Managed Supabase | Issue #66 HIGH default-grant exposure still open |
| Live LLM/media providers | Deferred |
| Billing go-live | Deferred |
| External publishing | Blocked by design |
| Production | Blocked |

## 12. Known builder traps

Consult `.agents/memory/*` before changing claim, RLS, enum, or lockfile code:

- npm lockfile must use `registry.npmjs.org`, not Replit firewall URLs
- SQLAlchemy native enums need `values_callable` or asyncpg sends `.name`
- Never `commit` mid-route while RLS `set_config` is active; `flush` only
- Returning an assignment to PENDING must clear `claimed_by` / `claimed_at` /
  `claim_token`
- Worker credential rotate/revoke must lock the registry row first
- Claim/scheduler tests must park leftover workers and retire stale rows

## 13. Current highest-value sequence after familiarization

1. Independently audit ChatGPT/Codex draft work (PRs #79, #82) before any merge
2. Do not take over implementation unless the Founder says so
3. After takeover, continue the authorized lane without weakening gates
4. Runtime/Supabase evidence and issue #66 remain blocking for managed-live claims
5. One provider path at a time, behind spend + Human Review, separately audited
