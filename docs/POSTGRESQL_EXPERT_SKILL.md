# PostgreSQL Expert Skill

The **PostgreSQL Expert** Cursor Skill owns database architecture for
Content Orchestrator.

| | |
|---|---|
| **Invoke** | `/postgresql-expert` |
| **Package** | [`.cursor/skills/postgresql-expert/`](../.cursor/skills/postgresql-expert/) |
| **Guide** | [`.cursor/skills/postgresql-expert/README.md`](../.cursor/skills/postgresql-expert/README.md) |

## Responsibilities

- Production-ready PostgreSQL schemas with SQLAlchemy 2.x + Alembic
- Safe reversible migrations; single valid migration chain
- `workspace_id` scoping; ENABLE + FORCE RLS; fail-closed policies
- Composite FKs/constraints against cross-workspace contamination
- `numeric` for money; `timestamptz` for timestamps
- PKs/FKs/uniques/checks/indexes/triggers/functions done correctly
- Query plans; prevent N+1, unbounded scans, missing indexes
- Locking, isolation, `SKIP LOCKED`, advisory locks, race detection
- Idempotency and atomic transaction boundaries
- Immutable audit/spend/review protection
- SECURITY DEFINER + locked `search_path`; reject permissive grants
- Fresh DB up/down/up; adversarial `app_runtime` RLS tests
- Reject SQLite/mocked DB as final validation
- Clear migration/rollback docs; escalate isolation/data-loss/financial/migration/concurrency risks

## Advisory gate

```bash
bash .cursor/skills/postgresql-expert/scripts/pg-schema-gate.sh
```

**Authority:** see [`.cursor/skills/AUTHORITY_MATRIX.md`](../.cursor/skills/AUTHORITY_MATRIX.md) · **Audit:** [`CURSOR_SKILLS_AUDIT.md`](./CURSOR_SKILLS_AUDIT.md)
