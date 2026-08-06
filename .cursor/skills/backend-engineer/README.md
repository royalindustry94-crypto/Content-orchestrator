# Backend Engineer Skill — Documentation

**Skill id:** `backend-engineer`  
**Location:** `.cursor/skills/backend-engineer/`  
**Invoke:** `/backend-engineer`

## Purpose

Senior Backend Engineer for Content Orchestrator: implements production-ready
FastAPI/Python services with SQLAlchemy 2.x, Alembic, and PostgreSQL; preserves
workspace isolation and FORCE RLS; builds idempotent APIs and worker ops with
robust retries; writes secure authz, complete error handling, structured
logging, safe migrations, and comprehensive tests — without placeholders,
silent failures, or architecture drift.

## Layout (Cursor best practices)

```text
.cursor/skills/backend-engineer/
├── SKILL.md
├── README.md
├── references/
│   ├── implementation-standards.md
│   ├── fastapi-and-services.md
│   ├── sqlalchemy-alembic-postgres.md
│   ├── security-auth-rls.md
│   ├── idempotency-and-retries.md
│   ├── testing-standards.md
│   └── performance.md
├── assets/
│   ├── backend-pr-checklist.md
│   └── error-handling-notes.md
└── scripts/
    └── backend-quality-gate.sh
```

## How agents should use it

1. Load `SKILL.md` when implementing backend/worker changes.
2. Open only needed `references/` files.
3. Escalate stack/boundary changes to `/chief-architect`; release/quality to `/ceo`.
4. Before claiming done, run:

```bash
bash .cursor/skills/backend-engineer/scripts/backend-quality-gate.sh
```

5. Use `assets/backend-pr-checklist.md` as a self-review gate.

## Related skills

| Skill | Role |
|---|---|
| `/chief-architect` | Architecture protection / ADR |
| `/ceo` | Product quality / release VERIFIED |

## Related docs

- `docs/architecture-decisions.md`
- `docs/milestone-2-identity-and-access.md`
- `docs/M*_WS*_DESIGN.md`
- `docs/BACKEND_ENGINEER_SKILL.md`
