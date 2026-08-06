# Invariants check (release)

Before RELEASE READY, confirm via specialist evidence (not vibes) that the
release does **not** weaken:

| Invariant | What “intact” means | Typical evidence |
|-----------|---------------------|------------------|
| Human Review Gate | No path advances past review without approval APIs/state | QA attack matrix; Backend tests |
| Spend controls | Caps/reservations still enforced; no bypass flags | QA spend concurrency; Backend tests |
| Audit logging | Sensitive actions still audited; no secret leakage in audit | Security + Backend |
| RLS | FORCE RLS on tenant tables; fail-closed | PG Expert + adversarial RLS tests |
| Workspace isolation | No cross-tenant read/write | QA + Security |

## Placeholders / incomplete work

Reject the release if in-scope production paths contain:

- TODO / FIXME / NotImplemented on shipped surfaces (unless explicitly out of scope and loud-fail guarded)
- Mock success / fake provider responses presented as production
- Swallowed exceptions / silent drops
- Skipped Critical tests without CEO-written waiver

## Sign-off line (paste into report)

```text
Invariants: Review Gate [OK|FAIL] · Spend [OK|FAIL] · Audit [OK|FAIL] · RLS [OK|FAIL] · Isolation [OK|FAIL]
Placeholders in scope: [NONE|FOUND]
Evidence: [links / test names]
```
