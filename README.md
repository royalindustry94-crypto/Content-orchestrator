# Content Orchestrator

AI-driven faceless video content pipeline: idea generation → scripting →
voiceover → visuals → rendering → SEO → human review → scheduling/publishing
→ analytics. See `docs/architecture-decisions.md` for the spec this is
built against and why one candidate spec was rejected.

## Repository layout

```
apps/api      FastAPI backend
apps/web      React + TypeScript frontend
apps/worker   Background worker (agents, pipeline job processing)
database/     Seed data, backfills, ER diagrams (not schema migrations)
docs/         Architecture decisions, API docs (added as integrations land)
n8n/          Exported n8n workflow definitions
packages/     Code shared across apps (empty for now)
```

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker (for local Postgres via `docker-compose`)

## Local setup

```bash
cp .env.example .env
# Fill in SUPABASE_JWT_SECRET (Supabase project → Settings → API → JWT
# Settings → JWT Secret). FastAPI uses it only to VERIFY the access tokens
# Supabase Auth issues — the app never signs or issues tokens itself.
# Also set DATABASE_URL (owner/migration role) and APP_DATABASE_URL
# (the non-owner app_runtime role used for request traffic under RLS).

docker compose up -d postgres

cd apps/api
pip install -e ".[dev]"
alembic upgrade head   # applies migration 0001 (identity & access + RLS)
uvicorn app.main:app --reload --port 8000

# separate terminal
cd apps/worker
pip install -e ".[dev]"
python -m worker.main

# separate terminal
cd apps/web
npm install            # generates package-lock.json — commit it
npm run dev
```

Visit `http://localhost:5173` — it calls the API's `/health/ready`
endpoint on load, so you'll see "connected" once both the API and
Postgres are up.

## Health endpoints

- `GET /health/live` — process is up, no dependency check
- `GET /health/ready` — process up AND Postgres reachable (503 if not)

## Tests

```bash
cd apps/api && pytest
cd apps/worker && pytest
cd apps/web && npm test
```

## Status

**Milestone 1: Repository Foundation — complete.** Monorepo scaffold,
FastAPI app with health checks, React+TS frontend wired to the API, worker
process skeleton, Postgres config (async SQLAlchemy + Alembic), CI (lint +
test for all three apps), structured JSON logging.

**Milestone 2: Identity & Access Foundation — complete.** Supabase Auth as
the authentication authority with FastAPI verifying (never issuing) its
JWTs; `profiles` / `workspaces` / `workspace_memberships`; Row Level
Security with `FORCE ROW LEVEL SECURITY` and a non-owner runtime role
(`app_runtime`) separated from the owner/migration role; admin / editor /
reviewer roles; `/me`, workspace CRUD, and membership management. See
`docs/milestone-2-identity-and-access.md`.

Not yet built (by design — see `docs/architecture-decisions.md`): the
content-domain **service layer and APIs** over the M3 schema, provider
integrations, pipeline job processing, and the dashboard UI. These are
Milestone 4 onward.

**Milestone 3: Content Domain Schema — complete.** 16 domain tables
(content_items, content_versions, assets, pipeline_runs,
pipeline_stage_runs, review_decisions, publish_jobs, webhook_events,
analytics_snapshots, spend_logs, spend_reservations, dead_letter_jobs,
provider_credentials, provider_usage, plus content_pillars and spend_caps)
across migrations 0002–0012, with RLS on every table, optimistic
versioning on mutable tables, DB-enforced immutability on event/history
tables, soft deletion on business entities, and full FK/index/constraint
definitions. Schema only — no pipeline, provider, or worker logic. See
`docs/milestone-3-schema-review.md`.
