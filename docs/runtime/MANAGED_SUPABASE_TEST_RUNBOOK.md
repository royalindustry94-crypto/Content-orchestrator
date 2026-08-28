# Managed Supabase Test Runtime Runbook

Status: PRE-APPLY / NOT YET EXECUTED

This runbook is for the isolated `content-orchestrator-test` managed Supabase project. It is not production authorization.

## Hard boundaries

- Keep live providers, billing go-live, external publishing, and production deployment disabled.
- Never apply `scripts/bootstrap_local_postgres.sql` to managed Supabase.
- Never place database passwords, service-role keys, or private provider credentials in source control, issue comments, workflow YAML, or chat.
- Preserve FORCE RLS and use a non-owner, `NOBYPASSRLS` runtime role for authenticated application traffic.

## Managed database prerequisites

1. Supabase-managed `auth.users` must already exist.
2. The migration owner must be able to create/alter application objects in `public` and attach the application-owned signup trigger to `auth.users`.
3. `app_runtime` must exist as `NOBYPASSRLS`, `NOCREATEROLE`, `NOCREATEDB`. Canonical migrations create it as `NOLOGIN` when absent.
4. A strong runtime login credential may be enabled only out-of-band when an approved application host exists. Store that credential in the host secret store and set `APP_DATABASE_URL` there. Do not reuse the local/CI password `app_runtime`.

## Apply path

1. Generate Alembic offline SQL from the exact candidate head.
2. Verify the SQL contains no `CREATE SCHEMA auth`, no `CREATE TABLE auth.users`, and no password literal for `app_runtime`.
3. Review the only intended managed-auth interaction: application trigger `content_orchestrator_on_auth_user_created` on `auth.users`, executing `public.content_orchestrator_handle_new_auth_user()`.
4. Apply schema DDL through the managed migration channel in order.
5. Verify Alembic head is `0050` (or the exact newer audited head if this runbook is superseded).
6. Re-run Supabase security advisors after DDL.

## Verification queries

Verify role posture:

```sql
select rolname, rolcanlogin, rolbypassrls, rolcreaterole, rolcreatedb
from pg_roles
where rolname = 'app_runtime';
```

Expected before host credential provisioning: `rolcanlogin = false`, all elevated flags false.

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

## Runtime isolation proof before Founder testing

- Create two test users and two workspaces.
- Exercise application traffic through the non-owner runtime identity.
- Prove each user cannot select/update the other workspace through direct application queries.
- Prove missing `request.jwt.claim.sub` fails closed.
- Prove Human Review and spend controls still fail closed.

## Rollback rule

Do not improvise destructive rollback on managed Supabase. If migration application fails, stop, capture the failing statement and database state, and use the audited Alembic downgrade path only after confirming it does not touch Supabase-managed objects. For a fresh isolated test project, project reset/recreate is preferred over destructive manual surgery when evidence is incomplete.

## Release gate

Managed schema application remains blocked until the remediation candidate has exact-head CI evidence and an independent PASS/CONDITIONAL audit is available. If no independent auditor is available, technical work may continue but the milestone cannot self-certify PASS.
