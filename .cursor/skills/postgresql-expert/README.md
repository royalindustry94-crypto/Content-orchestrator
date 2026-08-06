# PostgreSQL Expert Skill — Documentation

**Skill id:** `postgresql-expert`  
**Location:** `.cursor/skills/postgresql-expert/`  
**Invoke:** `/postgresql-expert`

## Purpose

Owns PostgreSQL architecture for Content Orchestrator: production schemas,
Alembic migration safety and chain integrity, FORCE RLS / tenant isolation,
constraints and indexes, query performance, locking/concurrency, immutable
financial and audit ledgers, SECURITY DEFINER hygiene, and adversarial
runtime-role validation on real Postgres (never SQLite/mocks as final proof).

## Layout (Cursor best practices)

```text
.cursor/skills/postgresql-expert/
├── SKILL.md
├── README.md
├── references/
│   ├── schema-design.md
│   ├── rls-and-tenancy.md
│   ├── migrations-alembic.md
│   ├── performance-and-plans.md
│   ├── locking-and-concurrency.md
│   ├── functions-triggers-grants.md
│   └── validation-and-testing.md
├── assets/
│   ├── schema-review-template.md
│   └── migration-notes-template.md
└── scripts/
    └── pg-schema-gate.sh
```

## How agents should use it

1. Load `SKILL.md` for any schema/migration/RLS/SQL performance/locking work.
2. Open only needed `references/` files.
3. Emit **PG VERDICT**: APPROVE / CONDITIONAL / REJECT / ESCALATE.
4. Require fresh up → down → up and `app_runtime` RLS adversarial tests.
5. Optional advisory scan:

```bash
bash .cursor/skills/postgresql-expert/scripts/pg-schema-gate.sh
```

## Related skills

| Skill | Role |
|---|---|
| `/chief-architect` | Stack/SoT/boundaries |
| `/backend-engineer` | FastAPI/SQLAlchemy implementation |
| `/ceo` | Product/quality/release escalation |

## Related docs

- `docs/architecture-decisions.md`
- `docs/milestone-2-identity-and-access.md`
- `apps/api/alembic/migration_helpers.py`
- `docs/POSTGRESQL_EXPERT_SKILL.md`
