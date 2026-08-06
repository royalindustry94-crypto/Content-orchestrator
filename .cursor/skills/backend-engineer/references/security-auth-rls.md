# Security, authentication & RLS

## Principals

| Principal | Mechanism | Session |
|---|---|---|
| Human user | Supabase JWT (`Authorization: Bearer`) | `rls_scoped_session` / `get_current_session` |
| Worker | Credential `<id>.<secret>` | Often `AsyncSessionLocal` (service-role) after worker auth |
| System maintenance | Background tick | `AsyncSessionLocal` |

## Authorization

- Workspace access via membership roles: `admin` / `editor` / `reviewer`.
- Admin-only for credential minting, drain, concurrency budgets, etc.
- Never trust client-supplied `workspace_id` alone — join with membership + RLS.

## RLS engineering rules

- Table owner connections bypass RLS unless **FORCE** — production app traffic must use `app_runtime`.
- Policies use `app_user_has_workspace_role` / helpers from migrations.
- Service-role writes: authenticate/authorize first, then owner session (pattern in workers admin routes).
- Test as runtime role with:

```sql
SELECT set_config('request.jwt.claim.sub', :user_id, true);
```

## Secrets

- Worker secrets: generate with CSPRNG; store **SHA-256 hash** only; compare constant-time.
- Provider credentials: encrypted at rest per existing columns; never log plaintext.
- Audit denylist: do not pass raw tokens/secrets into `audit(...)`.

## Auth failure behavior

- Missing/invalid user JWT → `401`
- Not a workspace member → `403` (or `404` where concealment is intentional and consistent)
- Worker credential unknown/revoked/expired/bad secret → uniform `401` where designed (no enumeration)

## Control-plane security

- Recovery/reaper must not grant review approval.
- Spend paths must not proceed past cap without reservation.
- Revoke/deregister paths should not leave stranded privileged leases (reap as designed).
