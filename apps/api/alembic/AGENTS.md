# Alembic agent guidance

This file adds migration-specific guidance to the repository-root and API `AGENTS.md` files.

- Never edit a migration that may have been applied. Add a new revision with one current parent.
- Implement and explain both upgrade and downgrade. State explicitly when downgrade loses data.
- Tenant tables require `workspace_id`, appropriate referential integrity, indexes for foreign keys, ENABLE RLS, FORCE RLS, and least-privilege policies.
- Do not place reusable credentials in migration SQL. Local/CI bootstrap belongs outside canonical migrations.
- Security-definer functions require a pinned `search_path` and explicit EXECUTE grants.
- Avoid long table rewrites and unbounded locks; use staged/backfilled changes where required.

Verify on a disposable localhost database ending `_test`: upgrade head, downgrade base, re-upgrade, then inspect the live PostgreSQL catalog. Never replay against staging, production, or managed Supabase.
