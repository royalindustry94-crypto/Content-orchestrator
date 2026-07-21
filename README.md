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
# fill in JWT_SECRET_KEY at minimum — generate with:
python -c "import secrets; print(secrets.token_urlsafe(32))"

docker compose up -d postgres

cd apps/api
pip install -e ".[dev]"
alembic upgrade head   # no-op until the first migration exists
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

**Phase 1: Repository Foundation — complete.** Monorepo scaffold, FastAPI
app with health checks, React+TS frontend wired to the API, worker process
skeleton, Postgres config (async SQLAlchemy + Alembic, ready for the first
migration), CI (lint + test for all three apps), structured JSON logging.

Not yet built (by design — see `docs/architecture-decisions.md` and the
worker entrypoint's docstring for why): data model / migrations, auth,
any provider integrations, pipeline job processing, the dashboard UI
itself.
