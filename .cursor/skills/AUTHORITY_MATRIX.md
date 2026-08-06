# Skill authority matrix (Content Orchestrator)

This file is **not** a skill. It defines who decides what so agents cannot
silently exceed authority or approve their own work.

| Concern | Primary | Must consult | Must not |
|---|---|---|---|
| Product scope, quality bar, go/no-go, VERIFIED label | `/ceo` | Specialists + `/security-auditor` evidence when security-sensitive | Implement specialist deep work as substitute for delegation |
| Stack freeze, SoT, service boundaries, ADR acceptance | `/chief-architect` | `/postgresql-expert` for schema/RLS/SQL; `/ceo` for product/security escalate | Replace backend/PG implementation; merge PRs |
| FastAPI/worker code, DI, auth wiring, tests for app behavior | `/backend-engineer` | `/chief-architect` before arch change; `/postgresql-expert` before schema/RLS/migration design | Invent architecture; declare migration-safe without PG review; self-security-approve |
| Schema, RLS, Alembic chain, constraints, SQL concurrency, DB correctness | `/postgresql-expert` | `/chief-architect` if SoT/boundaries change; `/ceo` on isolation/financial escalate | Own FastAPI route design; merge PRs; accept SQLite/mocks |
| Independent security audit before PR/release approval | `/security-auditor` | `/postgresql-expert` for RLS depth; `/backend-engineer` for remediations; `/ceo` for residual Medium acceptance | Implement the change under review; approve own fixes without fresh re-audit; merge |

## Independent review (mandatory)

No skill may:

1. **Merge** a pull request (human only; cloud agents never merge unless the human explicitly orders merge **and** QA + **security** have approved).
2. Mark work **VERIFIED** or **COMPLETE** without **factual evidence** (CI URL + SHA, migration head, test counts, adversarial RLS results, security audit report when applicable).
3. **Approve its own implementation** as final: the implementer skill proposes; a different skill or human reviewer must sign off on architecture/schema/security as applicable.
4. Skip **QA** (full `pytest -W error`, ruff, migration replay) or **security** review (`/security-auditor` on security-sensitive surfaces) before release claims.
5. **Security Auditor** may not approve remediations it authored without restarting the full audit on the new SHA.

## GitHub is source of truth

- Canonical code lives on GitHub (`royalindustry94-crypto/Content-orchestrator`).
- Commits/PRs on GitHub beat local-only claims.
- Never force-push shared milestone branches.
- Never rewrite history to hide failed gates.

## Approved stack (all skills)

FastAPI · SQLAlchemy 2.x · Alembic · PostgreSQL · React + TypeScript · Python workers.
