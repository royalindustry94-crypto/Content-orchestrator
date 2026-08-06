# P-006 / TD-021 — Covering indexes for foreign-key columns

## Objective

Add btree indexes on FK columns that lacked a leading-column index so
deletes/joins do not degrade to sequential scans at scale.

## Plan

1. Probe Postgres for FKs without a leading-column index (35 on P0 schema).
2. Alembic `0031_fk`: `CREATE INDEX IF NOT EXISTS` for each.
3. Regression test asserting zero unindexed FK columns.
4. Docs: LAUNCH_BLOCKERS, TD-021.

## Dependencies

- P0 schema at migration `0030`
- Note: Stripe PR #27 also introduces a `0031_*` revision — rebase one
  branch onto the other before merge (linearize Alembic heads).

## Rollback

`alembic downgrade 0030` drops the indexes.

## Status — COMPLETE (2026-07-28)

| Deliverable | Location |
|-------------|----------|
| Migration | `apps/api/alembic/versions/0031_fk_covering_indexes.py` (35 indexes) |
| Test | `apps/api/tests/test_fk_indexes_p1.py` |
| Probe result | 35 → 0 unindexed FK columns |
