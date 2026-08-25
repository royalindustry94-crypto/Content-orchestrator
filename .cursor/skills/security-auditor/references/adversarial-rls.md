# Adversarial RLS & authz testing

Final isolation proof requires **PostgreSQL** with migrations applied and the
**non-owner** `app_runtime` role (`APP_DATABASE_URL` / `RuntimeSessionLocal`).

## Method

1. Create users A (member of workspace W) and B (outsider or other workspace).
2. As owner/service session, seed a sensitive row in W.
3. As B with:

```sql
SELECT set_config('request.jwt.claim.sub', :b_user_id, true);
```

4. Assert SELECT returns **zero** rows for W’s tenant tables under test.
5. Attempt INSERT/UPDATE/DELETE; expect failure (`DBAPIError` / insufficient privilege / RLS).
6. As A, assert legitimate SELECT works for allowed policies.
7. HTTP-level: B’s JWT → `403`/`404` on W admin/member routes as designed; never data leakage in error bodies.

## Must cover when touched

- New tenant tables / policies
- Changed grants
- Service-role write paths (confirm guard runs **before** owner session)
- Worker routes (credential principal cannot act on another worker)

## Reject as final evidence

- SQLite
- Mocked Session that skips RLS
- Tests that only use table-owner connections

Coordinate deep policy design with `/postgresql-expert`; you still **execute**
adversarial verification yourself.
