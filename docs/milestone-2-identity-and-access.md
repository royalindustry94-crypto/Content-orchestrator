# Milestone 2: Identity and Access Foundation

Status: design → implementation (this doc precedes the code in this same change)

## 1. Auth model decision

Supabase Auth is the authentication authority. It owns `auth.users`
(signup, password/OAuth, email verification, password reset) — none of
that is reimplemented here.

FastAPI's job is narrower: **verify** the JWT Supabase issues and derive
the caller's identity from its claims. No custom password hashing, token
issuance, refresh, or session storage.

**JWT verification:** Supabase Auth signs access tokens with the
project's JWT secret (HS256) unless asymmetric signing (RS256/ES256 via
JWKS) has been explicitly enabled on the project. This build assumes the
default HS256 shared-secret model — `SUPABASE_JWT_SECRET` is a required
env var, verified with `PyJWT`. If the project later switches to
JWKS-based asymmetric signing, only `app/core/security.py` needs to
change (fetch + cache the JWKS, verify by `kid`) — nothing above that
layer does.

**Why FastAPI doesn't rely on Supabase's `auth.uid()` / PostgREST role
model:** `auth.uid()` and the `anon`/`authenticated` Postgres roles are
part of Supabase's PostgREST layer. This architecture doesn't put
PostgREST in the request path — FastAPI is the sole DB client, per the
project instructions' "backend enforcement is required" rule. So RLS
here is defense-in-depth behind FastAPI's own authorization guards, not
the primary enforcement mechanism, and it's implemented with our own
session-scoped GUC instead of depending on Supabase-specific functions.
That keeps the same RLS policies working identically against a real
Supabase Postgres instance and a vanilla Postgres in local dev/CI.

## 2. Schema (Milestone 2 scope only)

```sql
CREATE TYPE workspace_role AS ENUM ('admin', 'editor', 'reviewer');

-- Mirrors auth.users 1:1. id is NOT a separate generated PK — it IS the
-- Supabase auth user id, so there is exactly one join key across the
-- whole system for "which user."
CREATE TABLE profiles (
    id          uuid PRIMARY KEY,          -- = auth.users.id
    email       text NOT NULL,
    full_name   text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE workspaces (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    created_by  uuid NOT NULL REFERENCES profiles(id),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE workspace_memberships (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role            workspace_role NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, user_id)
);
```

**Profile creation:** a trigger on `auth.users` (`AFTER INSERT`) inserts
the matching `profiles` row. This runs inside Supabase's own Postgres
regardless of which client created the user (Supabase Auth API, social
login, admin invite), so profile existence is guaranteed at the
database level rather than "whichever code path happens to call the API
first." The migration includes this trigger; it's a no-op in plain local
Postgres (no `auth.users` table there) — see §6 for the local/CI shim.

## 3. Row Level Security

Every table above gets `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL
SECURITY` (the latter matters: without it, the table owner — which
migrations run as — bypasses RLS entirely, silently). The runtime API
role is a **separate, non-owner Postgres role** (`app_runtime`) with only
DML grants, no `BYPASSRLS`, so policies actually apply to it. Table
ownership and migrations stay on the admin/owner role. This split is
what makes RLS a real control instead of decoration — see §6 for how
it's set up in Docker/CI to mirror how it must be set up against the
real Supabase instance.

```sql
CREATE OR REPLACE FUNCTION app_current_user_id() RETURNS uuid AS $$
  SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid
$$ LANGUAGE sql STABLE;

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles FORCE ROW LEVEL SECURITY;
CREATE POLICY profiles_select_authenticated ON profiles
    FOR SELECT USING (app_current_user_id() IS NOT NULL);
CREATE POLICY profiles_insert_own ON profiles
    FOR INSERT WITH CHECK (id = app_current_user_id());
CREATE POLICY profiles_update_own ON profiles
    FOR UPDATE USING (id = app_current_user_id());

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces FORCE ROW LEVEL SECURITY;
CREATE POLICY workspaces_select_member ON workspaces
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM workspace_memberships m
                WHERE m.workspace_id = workspaces.id
                  AND m.user_id = app_current_user_id())
    );
CREATE POLICY workspaces_insert_any_authenticated ON workspaces
    FOR INSERT WITH CHECK (created_by = app_current_user_id());
CREATE POLICY workspaces_update_admin ON workspaces
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM workspace_memberships m
                WHERE m.workspace_id = workspaces.id
                  AND m.user_id = app_current_user_id()
                  AND m.role = 'admin')
    );

ALTER TABLE workspace_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY memberships_select_same_workspace ON workspace_memberships
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM workspace_memberships m
                WHERE m.workspace_id = workspace_memberships.workspace_id
                  AND m.user_id = app_current_user_id())
    );
CREATE POLICY memberships_write_admin_only ON workspace_memberships
    FOR ALL USING (
        EXISTS (SELECT 1 FROM workspace_memberships m
                WHERE m.workspace_id = workspace_memberships.workspace_id
                  AND m.user_id = app_current_user_id()
                  AND m.role = 'admin')
    );
```

`app_current_user_id()` reads a GUC that FastAPI sets per-request (§5) —
it is never trusted from client input.

**Why `profiles` SELECT is any-authenticated, not self-only:** inviting a
member by `user_id` (§5) requires looking up a profile that doesn't yet
share a workspace with the caller — self-only would make that lookup
return nothing for every profile except the admin's own, silently
breaking invites. Profile rows only ever contain id/email/full_name, so
this is a deliberate, documented tradeoff, not an oversight. INSERT and
UPDATE stay self-only. If profile data grows to include anything
sensitive later, split it into a separate table that keeps the
self-only policy.

## 4. Authorization matrix

App-layer guards (`app/core/authorization.py`) are the primary
enforcement; RLS above is the defense-in-depth backstop if a guard is
ever missing or buggy.

| Action                              | admin | editor | reviewer | non-member |
|--------------------------------------|:-----:|:------:|:--------:|:----------:|
| Create a workspace                   | n/a — any authenticated user | | | |
| View workspace                       | ✓ | ✓ | ✓ | ✗ |
| Rename / update workspace            | ✓ | ✗ | ✗ | ✗ |
| List memberships                     | ✓ | ✓ | ✓ | ✗ |
| Invite member                        | ✓ | ✗ | ✗ | ✗ |
| Change a member's role               | ✓ | ✗ | ✗ | ✗ |
| Remove a member                      | ✓ | ✗ | ✗ | ✗ |
| Leave workspace (remove self)        | ✓ | ✓ | ✓ | ✗ |
| View own profile                     | ✓ | ✓ | ✓ | ✓ (own only) |

Editor/reviewer permissions on the *content* pipeline (script edits,
review decisions, publish approval) are Milestone 3 scope — this table
only covers identity/workspace actions.

## 5. API endpoints

All routes require a valid Supabase JWT (`Authorization: Bearer <token>`)
except none — there is no anonymous access anywhere in this milestone.

| Method | Path                                              | Guard                    |
|--------|----------------------------------------------------|---------------------------|
| GET    | `/me`                                              | authenticated             |
| GET    | `/workspaces`                                      | authenticated (own list)  |
| POST   | `/workspaces`                                      | authenticated             |
| GET    | `/workspaces/{workspace_id}`                       | member                    |
| PATCH  | `/workspaces/{workspace_id}`                       | admin                     |
| GET    | `/workspaces/{workspace_id}/memberships`           | member                    |
| POST   | `/workspaces/{workspace_id}/memberships`            | admin                     |
| PATCH  | `/workspaces/{workspace_id}/memberships/{user_id}` | admin                     |
| DELETE | `/workspaces/{workspace_id}/memberships/{user_id}` | admin, or self            |

`POST /workspaces` creates the workspace and, in the same transaction,
inserts an `admin` membership row for the creator — a workspace with
zero admins is never a reachable state.

## 6. Local/CI parity with Supabase

Plain Docker/CI Postgres has no `auth.users` table and no Supabase
extensions. To exercise the real code path in tests without depending on
a hosted Supabase project:

- The migration creates a **minimal `auth.users` shim** (schema `auth`,
  table `users(id uuid primary key, email text)`) only when it doesn't
  already exist — on real Supabase this check short-circuits and the
  migration touches nothing, since Supabase already owns that schema.
- The same migration creates the **`app_runtime` role** (`LOGIN`, no
  `BYPASSRLS`, no `CREATEROLE`/`CREATEDB`) and grants it `SELECT,
  INSERT, UPDATE, DELETE` on the three tables — idempotently (`DO $$ ...
  IF NOT EXISTS $$`), so re-running the migration is safe. Deploying
  against a real Supabase project: if the migration's connecting role
  lacks `CREATE ROLE` privilege there, run that one block manually via
  the SQL editor once instead — the rest of the migration is unaffected.
- `APP_DATABASE_URL` (new env var) is the runtime connection string,
  using `app_runtime`. `DATABASE_URL` (existing) stays the
  migration/owner connection. The API uses `APP_DATABASE_URL` for every
  request-scoped session (`app/db/session.py:rls_scoped_session`);
  Alembic keeps using `DATABASE_URL`.

## 7. Test plan

All tests run against the real Postgres service container in CI (not
mocked), through the actual `app_runtime` role, so RLS is genuinely
exercised, not assumed.

1. **Workspace creation** — creating user becomes the sole `admin` member.
2. **Membership listing** — member of workspace A sees A's members; a
   non-member of A gets 403 (app layer) even before RLS is reached.
3. **Cross-workspace isolation (RLS)** — user B, member only of
   workspace B, is given a *valid, unexpired* JWT and attempts to read
   workspace A's rows via a raw RLS-scoped session bypassing the app
   guard entirely (simulating an app-layer bug) — asserts RLS alone
   still returns zero rows for A. This is the test that actually proves
   RLS works, not just that the FastAPI guard works.
4. **Role enforcement** — editor and reviewer both get 403 on invite/
   role-change/remove-member; admin succeeds.
5. **Self-leave** — non-admin member can remove themselves; cannot
   remove others.
6. **Last-admin protection** — removing the only remaining admin from a
   workspace is rejected (a workspace must always have ≥1 admin).
7. **Invalid/expired JWT** — 401, not 403 or 500.
8. **Missing profile edge case** — a verified JWT for a user with no
   `profiles` row yet (shim/trigger race) is handled explicitly (409 or
   auto-heal by inserting the row), not a 500.
