# Chief Architect Skill

The **Chief Architect** Cursor Skill protects Content Orchestrator architecture.

| | |
|---|---|
| **Invoke** | `/chief-architect` |
| **Package** | [`.cursor/skills/chief-architect/`](../.cursor/skills/chief-architect/) |
| **Guide** | [`.cursor/skills/chief-architect/README.md`](../.cursor/skills/chief-architect/README.md) |

## Responsibilities

- Preserve approved stack (FastAPI, SQLAlchemy, Alembic, PostgreSQL, React, TypeScript, Python workers)
- Prevent architecture drift and unnecessary dependencies
- Enforce `workspace_id` scoping and FORCE RLS
- Review models, migrations, indexes, constraints, transactions
- Review API/service boundaries and dependency direction
- Identify concurrency, race, idempotency, and retry hazards
- Protect Human Review Gate and spend-control architecture
- Require production-ready errors; reject placeholders and silent failures
- Prefer simple maintainable designs; require ADRs, tests, and rollback plans
- Escalate security / integrity / tenant / financial / maintainability risks to `/ceo`

## Advisory scan

```bash
bash .cursor/skills/chief-architect/scripts/architect-drift-scan.sh
```
