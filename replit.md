# Content Orchestrator

## Overview
AI-driven faceless video content pipeline (idea → script → voiceover → visuals → render → SEO → review → publish → analytics). This repl mirrors the GitHub repo `royalindustry94-crypto/Content-orchestrator` (branch `main`).

Current state: **Milestone 3 complete** — orchestration engine, worker reference client, RLS, 39/39 tests, 85% coverage. PR #1 squash-merged into `main` (`c03af2b`) on 2026-07-25; release tag `v0.3.0-milestone-3` → `3bc4f3e`; feature branch deleted. Milestone 4 not started.

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
