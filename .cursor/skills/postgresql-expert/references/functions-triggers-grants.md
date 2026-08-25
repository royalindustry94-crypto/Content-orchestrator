# Functions, triggers & grants

## Triggers

Use shared helpers where possible:

- `attach_version_trigger` → `set_version_and_updated_at()`
- `attach_immutable_trigger` → `prevent_update()`
- `attach_immutable_delete_trigger` → `prevent_delete()`

Immutable financial/audit/review tables must not be updatable/deletable by runtime roles.

## SECURITY DEFINER

Any `SECURITY DEFINER` function:

1. **Lock `search_path`** — e.g. `SET search_path = pg_catalog, public` (or the minimal schemas required) on the function
2. Least privilege owner
3. No dynamic SQL with unsanitized identifiers from users
4. Document why DEFINER is required (RLS helpers often need it)

Reject DEFINER functions without fixed `search_path` — classic privilege-escalation footgun.

## Grants

- Prefer `grant_runtime(table, insert=, update=, delete=)` least privilege
- Reject `GRANT ALL … TO PUBLIC` or broad grants to `app_runtime` on sensitive tables
- Credentials / effect of secrets: often **zero** runtime grants
- Sequence/function executes only as needed

## Public schema

- Application tables live in `public` (project convention) but access is via role grants + RLS — not open world
- Do not create unsafe objects writable by `PUBLIC`
- Auth scaffolding (`auth.users`) remains isolated; do not weaken its boundaries

## Failure mode

If grants are too open, **REJECT** and tighten before merge — do not rely on “the API won’t call it.”
