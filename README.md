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
scripts/dev_up.sh --simulation
```

One command: creates `.env`, generates the JWT secret, starts Postgres,
installs dependencies, migrates, and runs the API, worker, and web app.
Then visit `http://localhost:5173` and create an account.

`--simulation` selects the deterministic offline content provider so the
full pipeline produces visible output. Without it the pipeline stages
stop truthfully at `provider_not_configured`. See
[`docs/TESTING_GUIDE.md`](docs/TESTING_GUIDE.md) for a walkthrough.

<details>
<summary>Manual setup</summary>

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

</details>

Full stack (API + worker + web + Postgres):

```bash
docker compose -f docker-compose.staging.yml up --build
```

## Auth

- `AUTH_MODE=local` (default): `POST /auth/signup`, `POST /auth/login`
  mint Supabase-shaped JWTs verified by the API.
- `AUTH_MODE=supabase`: local signup/login disabled; use Supabase-issued tokens.

## Content providers

`PIPELINE_PROVIDER_MODE` selects the implementation behind every pipeline
stage. It defaults to `null` — no vendor, every stage stops at
`provider_not_configured` and spends nothing.

`simulation` is a deterministic offline provider for testing. It makes no
network calls and costs nothing, labels every record it writes, and is
refused when `ENVIRONMENT` is production. Human Review stays mandatory and
external publishing stays disabled in both modes.

Activating a paid vendor is a separate audited milestone — see PROVIDER-001
in `docs/LAUNCH_BLOCKERS.md` and
[`docs/work-packages/WP-PB-005-pipeline-provider-abstraction.md`](docs/work-packages/WP-PB-005-pipeline-provider-abstraction.md).

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

- Testing walkthrough: `docs/TESTING_GUIDE.md`
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
