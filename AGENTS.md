# AGENTS.md — Content Orchestrator

Entry point for AI agents working in this repository.
([Cursor AGENTS.md](https://cursor.com/docs/rules.md#agentsmd) · [Subagents](https://cursor.com/docs/subagents.md))

## Product

Multi-tenant **Content Orchestrator**: FastAPI + SQLAlchemy 2.x + Alembic +
**PostgreSQL** (source of truth) + React/TypeScript web + Python workers.

Canonical code and CI evidence live on **GitHub**.

## Non-negotiables

1. No architecture drift — approved stack only.
2. No TODOs, placeholders, fake implementations, or silent failures in production paths.
3. **Human Review Gate** and **spend controls** are mandatory and non-bypassable.
4. Tenant data: `workspace_id` + **ENABLE RLS** + **FORCE RLS**.
5. Alembic for all schema changes; migrations must be reversible and verified on fresh Postgres.
6. Comprehensive tests for every feature; never weaken quality to green CI.
7. Never merge without independent **Security** + **QA** evidence.
8. Never claim **VERIFIED** without objective evidence (CI URL, SHA, tests, migration head).
9. Prefer existing patterns; protect backward compatibility unless an approved migration plan exists.
10. Escalate risks to security, tenant isolation, financial controls, compliance, data integrity, or maintainability.

Detailed always-on and scoped rules: [`.cursor/rules/`](.cursor/rules/).

## Reviewer agents (only)

Custom subagents live in [`.cursor/agents/`](.cursor/agents/). Use these — not a sprawl of overlapping role skills:

| Agent | File | Use when |
|-------|------|----------|
| **Planner** | [`planner.md`](.cursor/agents/planner.md) | Decompose work, sequencing, acceptance criteria, risk flags |
| **Migration Reviewer** | [`migration-reviewer.md`](.cursor/agents/migration-reviewer.md) | Alembic/RLS/schema review before/after DDL |
| **Security Reviewer** | [`security-reviewer.md`](.cursor/agents/security-reviewer.md) | AuthZ, secrets, RLS adversarial review, supply chain |
| **Test Writer** | [`test-writer.md`](.cursor/agents/test-writer.md) | Add/strengthen Postgres-backed and invariant tests |

## Layout

```text
apps/api      FastAPI, SQLAlchemy 2.x, Alembic, pytest
apps/worker   Python workers
apps/web      React + TypeScript (Vite)
docs/         Design, audits, engineering foundation reports
.cursor/rules Modular project rules (*.mdc)
.cursor/agents Focused reviewer subagents
```

## CI gates (see `.github/workflows/ci.yml`)

API: Postgres · Alembic upgrade/downgrade/replay · ruff check/format · mypy ·
pytest + coverage · engineering invariants · placeholder scan ·  
Worker: ruff · pytest ·  
Web: ESLint · TypeScript + production build ·  
Repo: secret scan · CodeQL (analyze)

## Documentation

- Architecture decisions: `docs/architecture-decisions.md`
- Foundation audit (this refactor): `docs/CURSOR_SETUP_FINAL_AUDIT.md`
- Milestone reports under `docs/M*_*.md`

## Out of scope for agents by default

- Merging PRs without human order + Security + QA evidence
- Inventing product features not in scope
- Replacing PostgreSQL as orchestration SoT
- Bypassing Review Gate or spend controls
