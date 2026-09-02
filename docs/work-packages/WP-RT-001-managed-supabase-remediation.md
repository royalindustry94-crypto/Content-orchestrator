# WP-RT-001 — Managed Supabase remediation

Status: IN PROGRESS

## Objective
Close the blocking findings from independent audit issue #60 before any schema is applied to the managed Supabase test project.

## Safety boundaries

- No schema application to managed Supabase in this work package.
- No live providers, billing, production auth/deployment, external publishing, or destructive production migration.
- Preserve FORCE RLS/workspace isolation, Human Review Gate, spend fail-closed, migration replay, security scans, exact-head browser evidence, and branch protection.
- No broad PAT/admin credential in GitHub Actions.
- Builder cannot self-certify; the exact PR head requires independent re-audit when an independent auditor is available.

## Required changes

1. Remove local-only `auth` shim creation from canonical Alembic migration `0001`; provision the shim only in explicitly local/CI bootstrap.
2. Remove the local static `app_runtime` login password from canonical Alembic migration `0001`; canonical migration may create only a `NOLOGIN`, `NOBYPASSRLS` role when no role exists.
3. Provision local/CI parity explicitly before Alembic: local-only `auth.users` shim plus local-only `app_runtime` login.
4. Keep the application-owned profile-sync trigger on `auth.users`, but make it fail closed on missing prerequisites, use an application-specific trigger name, and harden the SECURITY DEFINER function search path. It must not create, replace, or redefine Supabase-managed auth tables.
5. Add a managed-test pre-apply runbook and immutable ruleset evidence.
6. Reconcile stale governance documentation.

## Acceptance

- Fresh CI database can migrate, downgrade to base, and re-upgrade through `0050`.
- Canonical migration source contains no static `app_runtime` password and no `CREATE SCHEMA auth` / `CREATE TABLE auth.users` shim.
- Managed-safe runbook distinguishes owner/migration access from RLS-enforced runtime access and requires a strong runtime credential stored outside source control before application hosting is enabled.
- Exact-head six-gate CI succeeds.
- Independent re-audit records PASS or narrowly scoped CONDITIONAL before managed Supabase application.
