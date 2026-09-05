---
name: safe-migration
description: Design or verify Business Manager Alembic and PostgreSQL changes involving schemas, indexes, grants, RLS, tenant data, or rollback safety.
---

# Safe Migration

Read `apps/api/alembic/AGENTS.md` before changing or approving a migration.

- Never rewrite an applied migration. Add a new revision.
- Require one Alembic head. Linearize competing heads before approval.
- Every tenant table must include `workspace_id`, appropriate composite integrity where needed, ENABLE RLS, FORCE RLS, and least-privilege policies.
- Index foreign-key columns unless a documented query and locking analysis proves an exception.
- Pin `search_path` on security-definer functions and explicitly manage grants.
- Keep managed-Supabase bootstrap separate from local/CI role and auth emulation.
- Provide a downgrade and state whether it is data-preserving. A syntactically present but destructive downgrade is not automatically safe.

Verification must use a disposable local database whose host is localhost and whose name ends in `_test`. Run upgrade to head, downgrade to base, re-upgrade, inspect the live catalog for RLS/FORCE and indexes, and run targeted API tests. Never run migration replay against staging, production, or managed Supabase.

Report exact revision identifiers, current/head output, commands, catalog evidence, downgrade consequences, and any unverified runtime assumptions.
