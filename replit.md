# Content Orchestrator

## Overview
AI-driven faceless video content pipeline (idea → script → voiceover → visuals → render → SEO → review → publish → analytics). This repl mirrors the GitHub repo `royalindustry94-crypto/Content-orchestrator` (branch `main`).

Current state: **Milestone 3 complete** — orchestration engine, worker reference client, RLS, 39/39 tests, 85% coverage. Branch `feature/milestone-3` is on GitHub with PR #1 open (CI green). Do not merge without explicit instruction.

## Structure
- `apps/api` — FastAPI backend (async SQLAlchemy + Alembic; identity/workspaces/memberships)
- `apps/web` — React + TypeScript (Vite)
- `apps/worker` — background worker skeleton
- `database/`, `docs/`, `n8n/`, `packages/` — see README.md

## Git
- Push with the `GITHUB_PERSONAL_ACCESS_TOKEN` secret (see `.agents/memory/github-push-auth.md`); never force-push.
- The token has `repo` + `workflow` scopes; the full repo including CI workflow is pushed and in sync.

## User preferences
- User works from a mobile phone; keep instructions short, step-by-step, with exact URLs to tap.
- Plain language; avoid jargon unless the user uses it first.
