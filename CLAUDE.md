# CLAUDE.md

## Start here

- Read `./AGENTS.md` before making changes.
- Keep changes tightly scoped to the issue or pull request you were asked to handle.
- Prefer additive fixes over speculative refactors.

## Product and safety guardrails

- Never bypass the Human Review Gate or auto-publish content past review.
- Preserve workspace isolation and FORCE RLS on tenant-scoped data.
- Keep spend controls fail-closed when money can be spent.
- Maintain provider abstraction; do not hard-code the product around one model vendor.
- Emit structured audit events for security-relevant mutations.
- Never commit secrets, credentials, or `.env` files.

## Repository map

- `apps/api/`: FastAPI API, auth, workspaces, spend controls, review gates, Alembic migrations
- `apps/web/`: React + TypeScript Review Desk UI
- `apps/worker/`: background draft execution worker
- `docs/`: audits, launch blockers, architecture, and operating procedures

## Validation commands

- API: `cd apps/api && ruff check . && pytest --cov=app --cov-fail-under=75`
- Worker: `cd apps/worker && ruff check . && pytest`
- Web: `cd apps/web && npm test && npm run build`

## Change guidance

- Update docs when operator setup, workflow behavior, or user-facing behavior changes.
- For GitHub Actions changes, keep permissions minimal and prefer fail-closed behavior.
- For API changes, verify membership/role guards, RLS expectations, spend controls, and audit logging.
- Treat `/docs` OpenAPI exposure as development-only (`ENVIRONMENT=development|dev`).
