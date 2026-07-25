---
name: RLS set_config + flush vs commit in route handlers
description: Calling db.commit() mid-route when RLS is active via set_config('request.jwt.claim.sub') drops the config, making the subsequent db.refresh() invisible under RLS.
---

# RLS + flush vs commit

**Rule:** In route handlers that use `rls_scoped_session` (which sets `request.jwt.claim.sub` via `SET LOCAL`), never call `await db.commit()` followed by `await db.refresh(obj)`. Use `await db.flush()` instead; the outer session context manager commits after the route returns.

**Why:** `SET LOCAL` config survives only within the current transaction. Calling `db.commit()` ends the transaction and clears the config. Any subsequent query (including `db.refresh()`) runs without the JWT claim, so RLS policies see no authenticated user and hide all rows — the refresh either returns nothing or raises.

**How to apply:** Replace every `await db.commit(); await db.refresh(x)` pair inside route handlers with `await db.flush()`. The `rls_scoped_session` dependency handles the final commit. Affected routes: workspaces (create_workspace, update_workspace), memberships (invite_member, update_member_role), profiles (get_my_profile self-heal path).
