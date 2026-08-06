# Migration QA

## Required sequences

### Fresh replay

1. Empty database
2. `alembic upgrade head`
3. `alembic downgrade <parent-or-base>` (as designed)
4. `alembic upgrade head` again
5. Confirm single `alembic heads`

### From previous released head

1. Upgrade only to previous release revision
2. Upgrade to current head
3. Smoke critical tables/policies still FORCE RLS

## Assert

- Downgrade actually reverses (or expand/contract plan documented and tested)
- App tests pass on final head
- No reliance on “already migrated” developer DBs as sole proof

SQLite is invalid. Pair with `/postgresql-expert` on schema defects.
