# SQLAlchemy 2.x, Alembic & PostgreSQL

## SQLAlchemy 2.x

- Use `Mapped[]` / `mapped_column` style models.
- Async sessions: `AsyncSession`, `async with` sessionmakers from `app/db/session.py`.
- Prefer `select()` / `session.execute()`; avoid legacy query API.
- Inherit mixins: `TimestampMixin`, `VersionMixin`, `WorkspaceScopedMixin`, etc. from `app/db/base.py`.
- Enums: Postgres native enums with `values_callable` consistent with existing models.

## Transactions & locking

- One business invariant → one transaction.
- Co-commit: state change + `outbox.emit` (+ audit ledger rows).
- Use `with_for_update()` / `with_for_update(skip_locked=True)` for claim, spend caps, budgets, recovery.
- Document lock order in the function docstring when multiple rows lock.
- Never hold DB locks across external provider HTTP calls.

## Queries

- Filter by `workspace_id` explicitly on tenant queries.
- Match `ORDER BY` / `WHERE` to partial indexes (claims, in-flight provider, etc.).
- Avoid N+1: eager load only what you need; prefer targeted selects.
- For counts used in control flow, consider races — lock parent/budget/cap rows first.

## Alembic

| Rule | Detail |
|---|---|
| Revisions | Sequential string ids matching repo convention (`0029_...`) |
| Helpers | Use `alembic/migration_helpers.py` for RLS/triggers/grants |
| Downgrade | Real reverse of upgrade unless expand/contract ADR exists |
| Data migrations | Explicit, batched if large; never unbounded table rewrites unmarked |
| Replay | Must succeed on empty DB through `upgrade head` |

FORCE RLS pattern for new tenant tables:

1. `CREATE TABLE` with `workspace_id`
2. `attach_version_trigger` if versioned
3. `enable_rls` (ENABLE + FORCE)
4. `grant_runtime(...)` least privilege
5. `policy_select_members` / insert / update policies as required

## PostgreSQL as SoT

- No dual-write to Redis/queues as authoritative job state.
- Use DB constraints (unique, check, FK) as the last line of defense for idempotency and integrity.
