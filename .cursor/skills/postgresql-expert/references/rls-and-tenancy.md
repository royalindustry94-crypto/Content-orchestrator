# RLS & tenant isolation

## Requirements

For tenant-owned tables:

1. `ALTER TABLE … ENABLE ROW LEVEL SECURITY`
2. `ALTER TABLE … FORCE ROW LEVEL SECURITY` (so table owner cannot accidentally bypass in app misuse; production traffic uses `app_runtime`)
3. Least-privilege `GRANT` to `app_runtime` via `grant_runtime(...)`
4. Explicit policies — **no policy ⇒ no access** (fail closed)

Use `alembic/migration_helpers.py`: `enable_rls`, `grant_runtime`, `policy_select_members`, `policy_insert_roles`, `policy_update_roles`.

## Policy design (fail closed)

- SELECT: membership role arrays (`admin`/`editor`/`reviewer` as appropriate)
- INSERT/UPDATE: tighter roles (often admin or admin+editor)
- DELETE: rare; prefer soft delete + update policy
- Service-only tables (secrets, some ledgers): **SELECT-only or zero grants** for runtime; writes via service-role after authz

Never use `USING (true)` for tenant data.

## Cross-workspace contamination

Application filters are not enough. Prefer:

- Composite FK: `(workspace_id, parent_id) → parent(workspace_id, id)` when children must stay in-tenant
- Unique `(workspace_id, natural_key)` rather than global natural keys
- RLS on both parent and child

Reject designs where a client can supply another tenant’s UUID and satisfy a single-column FK.

## Runtime role testing

Adversarial tests **must** use `APP_DATABASE_URL` / `RuntimeSessionLocal` (`app_runtime`), not the owner role:

```sql
SELECT set_config('request.jwt.claim.sub', :user_id, true);
```

Assert:

- Member sees own workspace rows
- Outsider sees **zero**
- Forbidden INSERT/UPDATE/DELETE fails (permission or RLS)

## Session wiring

- Request path: `rls_scoped_session` sets JWT claim transaction-locally
- Owner/`AsyncSessionLocal`: migrations, health, maintenance, service-role writes after guards

Document which paths intentionally use owner connections.
