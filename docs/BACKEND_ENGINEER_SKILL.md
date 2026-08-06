# Backend Engineer Skill

The **Backend Engineer** Cursor Skill is the Senior Backend Engineer for
Content Orchestrator.

| | |
|---|---|
| **Invoke** | `/backend-engineer` |
| **Package** | [`.cursor/skills/backend-engineer/`](../.cursor/skills/backend-engineer/) |
| **Guide** | [`.cursor/skills/backend-engineer/README.md`](../.cursor/skills/backend-engineer/README.md) |

## Responsibilities

- Production-ready FastAPI and Python worker services
- SQLAlchemy 2.x, Alembic, PostgreSQL — no architecture drift
- `workspace_id` isolation and FORCE RLS
- Idempotent APIs/worker ops; retries with exponential backoff
- Secure authn/authz; REST/OpenAPI; dependency injection
- Comprehensive unit, integration, and adversarial tests
- No TODOs, placeholders, or silent failures
- Complete error handling and structured logging
- Safe, reversible migrations
- Compatibility with Human Review Gate, spend controls, audit logging
- Performance review before new queries/dependencies
- Refuse reliability/security/maintainability shortcuts

## Advisory gate

```bash
bash .cursor/skills/backend-engineer/scripts/backend-quality-gate.sh
```

**Authority:** see [`.cursor/skills/AUTHORITY_MATRIX.md`](../.cursor/skills/AUTHORITY_MATRIX.md) · **Audit:** [`CURSOR_SKILLS_AUDIT.md`](./CURSOR_SKILLS_AUDIT.md)
