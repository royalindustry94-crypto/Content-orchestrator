# Content Orchestrator

Private Beta focus: **Agency Content Desk** — submit drafts, mandatory
Human Review Gate, workspace isolation (FORCE RLS), and spend controls.

See `docs/architecture-decisions.md` for the orchestration engine design
and `docs/ops/DEPLOYMENT.md` for staging/production startup.

## Repository layout

```
apps/api      FastAPI backend (auth, workspaces, content-jobs, review-gates, spend, workers)
apps/web      React + TypeScript Review Desk UI
apps/worker   Draft Desk worker (claim / execute / submit)
docs/         Architecture, ops, audits
```

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker (Postgres + optional full staging stack)

## Local setup

```bash
cp .env.example .env
# Required: SUPABASE_JWT_SECRET (also used to mint local auth JWTs)
python -c "import secrets; print(secrets.token_urlsafe(32))"

docker compose up -d postgres

cd apps/api
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# separate terminal
cd apps/worker
pip install -e ".[dev]"
python -m worker.main

# separate terminal
cd apps/web
npm install
npm run dev
```

With `AUTH_MODE=local` explicitly set for development, visit
`http://localhost:5173` — sign up / log in, submit a topic (optional script),
then approve or reject it at the Review Gate.

Full stack (API + worker + web + Postgres):

```bash
docker compose -f docker-compose.staging.yml up --build
```

## Auth

- `AUTH_MODE=supabase` (default, fail-closed): local signup/login is disabled;
  use Supabase-issued tokens.
- `AUTH_MODE=local` (explicit Private Beta/development opt-in):
  `POST /auth/signup` and `POST /auth/login` mint Supabase-shaped JWTs verified
  by the API. Production refuses this mode unless the audited break-glass flag
  is also explicitly enabled.

## Key APIs

- `POST /workspaces/{id}/content-jobs`
- `GET /workspaces/{id}/review-gates`
- `POST /workspaces/{id}/review-gates/{gate_id}/decision`
- `GET|PATCH /workspaces/{id}/spend`
- `GET /health/live`, `/health/ready`, `/health/automation`

## Tests

```bash
cd apps/api && alembic upgrade head && pytest --cov=app --cov-fail-under=75
cd apps/worker && pytest
cd apps/web && npm test && npm run build
```

## Ops

- Deployment: `docs/ops/DEPLOYMENT.md`
- Backup / restore: `docs/ops/BACKUP_AND_RESTORE.md`
- Launch status: `docs/EXECUTIVE_STATUS_REPORT.md`

## Agent / contributor guide

See [`AGENTS.md`](./AGENTS.md) (non-negotiables, working rules) and
`.cursor/rules/content-orchestrator.mdc`.

## Status

Orchestration engine (M3–M4) + Private Beta Review Desk surfaces are
implemented on this branch. See audit docs under `docs/` for readiness
verdicts — do not assume production readiness without reading them.
