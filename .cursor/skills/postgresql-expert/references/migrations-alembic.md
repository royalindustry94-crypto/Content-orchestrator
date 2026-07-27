# Alembic migrations & chain integrity

## Single valid chain

- Exactly **one** head on `main` / milestone branches used for deploy.
- Every revision: `revision`, `down_revision` correct; no unreachable nodes.
- Reject merging two heads without an explicit merge revision (prefer linear history for this project).

Check:

```bash
cd apps/api && alembic heads   # expect one head
alembic history | head
```

## Safe & reversible

| Required | Notes |
|---|---|
| `upgrade()` | Deterministic, idempotent enough for CI replay |
| `downgrade()` | Drops/reverses what upgrade added **or** expand/contract ADR |
| Expand/contract | Add nullable → backfill → constrain; reverse in order |
| No prod-only DDL | Schema changes live in Alembic, not manual SSH SQL as source of truth |

## Production readiness

- Short locks preferred; batch data backfills
- Avoid rewriting large tables in one TX without a plan
- Enum changes: follow Postgres-safe patterns (add value carefully; prefer new enum / check evolution strategies already used in repo)
- Use helpers for triggers/RLS so policies do not drift

## Fresh DB proof (required for new revisions)

1. Empty database: `alembic upgrade head`
2. `alembic downgrade <parent>`
3. `alembic upgrade head` again
4. Optionally full `downgrade base` + `upgrade head` on a scratch DB

SQLite or in-memory DBs are **not** acceptable substitutes.

## Documentation

Each non-trivial revision docstring should state:

- Why
- Tables/policies touched
- Rollback method
- Risk (locking, backfill, financial)

Also fill `assets/migration-notes-template.md` for workstream docs when schema is central.
