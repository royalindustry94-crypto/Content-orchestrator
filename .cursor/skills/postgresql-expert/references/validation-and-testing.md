# Validation & testing (PostgreSQL)

## Final validation = real Postgres

| Acceptable evidence | Not final evidence |
|---|---|
| CI Postgres 16 service + Alembic + pytest | SQLite |
| Local Postgres with `app_runtime` role | Mocked session pretending RLS |
| Fresh DB upgrade/downgrade/re-upgrade | “It worked on my already-migrated DB only” |

## Required gates for schema changes

1. `alembic upgrade head` on fresh DB
2. Downgrade to parent (or documented contract phase)
3. Upgrade to head again
4. `ruff` / model import sanity if models changed
5. Pytest including:
   - Schema presence (columns/tables)
   - FORCE RLS flags (`relrowsecurity` / `relforcerowsecurity`)
   - Adversarial runtime role probes
   - Immutability trigger rejects UPDATE/DELETE where applicable
   - Constraint rejection cases (check/unique) when critical

## Adversarial RLS pattern

```python
async with RuntimeSessionLocal() as s:
    await s.execute(text("SELECT set_config('request.jwt.claim.sub', :u, true)"), {"u": outsider_id})
    rows = (await s.execute(select(Model))).scalars().all()
    assert rows == []
```

Attempt forbidden writes; expect `DBAPIError` / `ProgrammingError`.

## Money & time regressions

- Grep migrations/models for money stored as float → fail review
- Grep for `DateTime` without `timezone=True` on new timestamp columns → fail review

## Documentation output

Provide:

- Migration notes (template)
- Rollback steps
- Any expand/contract timeline
- Known lock risks during apply
