# Managed Supabase Test Runtime Runbook

Status: PRE-APPLY / NOT YET EXECUTED

This runbook is for the isolated `content-orchestrator-test` managed Supabase project. It is not production authorization.

## Hard boundaries

- Keep live providers, billing go-live, external publishing, and production deployment disabled.
- Never apply `scripts/bootstrap_local_postgres.sql` to managed Supabase. The script now self-refuses when the managed Supabase role `supabase_auth_admin` is present, but operators must still treat it as local/CI-only.
- Never place database passwords, service-role keys, or private provider credentials in source control, issue comments, workflow YAML, or chat.
- Preserve FORCE RLS and use a non-owner, `NOBYPASSRLS` runtime role for authenticated application traffic.

## Managed database prerequisites

1. Supabase-managed `auth.users` must already exist.
2. The exact migration identity must be able to create/alter application objects in `public`, attach the application-owned signup trigger to `auth.users`, and have `BYPASSRLS`. This is load-bearing because the signup trigger and SECURITY DEFINER RLS helper functions run as their defining owner while FORCE RLS is enabled.
3. `app_runtime` must exist as `NOBYPASSRLS`, `NOCREATEROLE`, `NOCREATEDB`. Canonical migrations create it as `NOLOGIN` when absent.
4. A strong runtime login credential may be enabled only out-of-band when an approved application host exists. Store that credential in the host secret store and set `APP_DATABASE_URL` there. Do not reuse the local/CI password `app_runtime`.

Verify the exact migration identity before apply:

```sql
select current_user as rolname, rolbypassrls, rolsuper
from pg_roles
where rolname = current_user;
```

Required: `rolbypassrls = true`. `rolsuper` is not required. If `rolbypassrls` is false, do not apply the schema with that role.

## Apply path

1. Generate Alembic offline SQL from the exact candidate head.
2. Verify the SQL contains no `CREATE SCHEMA auth`, no `CREATE TABLE auth.users`, and no password literal for `app_runtime`.
3. Review the only intended managed-auth interaction: application trigger `content_orchestrator_on_auth_user_created` on `auth.users`, executing `public.content_orchestrator_handle_new_auth_user()`.
4. Re-run the migration-identity query above in the same managed channel that will apply DDL and confirm `rolbypassrls = true`.
5. Apply schema DDL through the managed migration channel in order.
6. Verify Alembic head is `0050` (or the exact newer audited head if this runbook is superseded).
7. Re-run Supabase security advisors after DDL.

## Verification queries

Verify role posture:

```sql
select rolname, rolcanlogin, rolbypassrls, rolcreaterole, rolcreatedb
from pg_roles
where rolname = 'app_runtime';
```

Expected before host credential provisioning: `rolcanlogin = false`, `rolbypassrls = false`, `rolcreaterole = false`, `rolcreatedb = false`.

Verify RLS is enabled and forced on application tables:

```sql
select c.relname, c.relrowsecurity, c.relforcerowsecurity
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relname in ('profiles','workspaces','workspace_memberships');
```

Verify the application-owned auth trigger only:

```sql
select t.tgname
from pg_trigger t
join pg_class c on c.oid = t.tgrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'auth'
  and c.relname = 'users'
  and not t.tgisinternal
  and t.tgname = 'content_orchestrator_on_auth_user_created';
```

Verify the signup trigger behavior with one real isolated-test signup. The new Supabase auth user id must have a matching profile row:

```sql
select p.id, p.email
from public.profiles p
where p.id = '<new-test-auth-user-uuid>'::uuid;
```

A missing profile row or failed signup is a managed-runtime failure. Stop and investigate before any Founder testing.

## Runtime isolation proof before Founder testing

- Create two test users and two workspaces.
- Exercise application traffic through the non-owner runtime identity.
- Prove each user cannot select/update the other workspace through direct application queries.
- Prove missing `request.jwt.claim.sub` fails closed.
- Prove Human Review and spend controls still fail closed.

## Rollback rule

Do not improvise destructive rollback on managed Supabase. If migration application fails, stop, capture the failing statement and database state, and use the audited Alembic downgrade path only after confirming it does not touch Supabase-managed objects. For a fresh isolated test project, project reset/recreate is preferred over destructive manual surgery when evidence is incomplete.

## Release gate

Managed schema application remains blocked until the remediation candidate has exact-head CI evidence and an independent PASS/CONDITIONAL audit is available. A CONDITIONAL audit may authorize isolated-test application only when every stated pre-apply condition is explicitly satisfied and recorded. It does not authorize production, live providers, billing, deployment, external publishing, or Founder hands-on testing before the post-apply runtime isolation proof passes.
