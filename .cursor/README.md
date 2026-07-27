# Cursor configuration

## AGENTS.md

Repository entry point: [`AGENTS.md`](../AGENTS.md)

## Rules (modular `.mdc`)

| Rule | Apply |
|------|-------|
| `architecture.mdc` | always |
| `quality-bar.mdc` | always |
| `review-gate-spend.mdc` | always |
| `verification-release.mdc` | always |
| `tenancy-rls.mdc` | `apps/api/**` |
| `migrations.mdc` | `apps/api/alembic/**` |
| `python-api.mdc` | `apps/api/**` |
| `python-worker.mdc` | `apps/worker/**` |
| `frontend-web.mdc` | `apps/web/**` |

## Reviewer agents

| Agent | Path |
|-------|------|
| Planner | `agents/planner.md` |
| Migration Reviewer | `agents/migration-reviewer.md` |
| Security Reviewer | `agents/security-reviewer.md` |
| Test Writer | `agents/test-writer.md` |

## Skills

Large overlapping role skills were **retired** in the Cursor foundation refactor
in favor of `AGENTS.md` + modular rules + the four reviewer agents above.
Do not reintroduce parallel skill sprawl without an audit.
