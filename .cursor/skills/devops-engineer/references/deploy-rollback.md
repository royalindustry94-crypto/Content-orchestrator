# Deploy & rollback — Content Orchestrator

## Goals

- Repeatable, environment-driven deploys
- Migration-safe order
- Documented rollback
- Zero-downtime **where practical** (rolling compatible)

## Recommended order (expand/contract friendly)

```text
1. Pre-check: CI green on SHA; secrets present; migration head known
2. Backup / snapshot policy per environment (document owner)
3. Migrate (expand): alembic upgrade head — additive / dual-write safe steps first
4. Deploy api (health + readiness must pass)
5. Deploy / restart workers (drain or allow lease reclaim)
6. Deploy web (static/assets)
7. Smoke: auth, workspace isolation sample, review/spend paths if touched
8. Contract migrations only after old code is gone (when applicable)
```

If the environment cannot support zero-downtime, say so explicitly and get `/ceo` risk acceptance for downtime windows.

## Health / readiness / shutdown

| Probe | Expectation |
|-------|-------------|
| Liveness | Process up; cheap |
| Readiness | DB reachable (api); not accepting work if migrating critically |
| Shutdown | SIGTERM → stop new work; finish or release in-flight; workers release/reap leases |

If probes are missing in code → escalate `/backend-engineer`; do not invent fake success in load balancers.

## Worker restart & leases

- Prefer drain: stop claiming → wait in-flight → exit
- On crash: reclaim/expired leases must recover (Backend + QA own proof; DevOps verifies restart config enables it)
- Never approve “restart all workers hard” as the only recovery story without lease reclaim evidence

## Rollback

Document before approve:

1. **App rollback** — previous image/SHA; how to redeploy
2. **DB rollback** — `alembic downgrade` only if revision is reversible and PG Expert approved; otherwise forward-fix plan
3. **Trigger** — red smoke, error budget, failed migration
4. **Validation** — was rollback rehearsed in staging? If not, residual risk → `/ceo`

## Blockers (auto FAILED)

- CI red on deploy SHA
- Migration failed / partial head
- Unresolved Critical/High from `/security-auditor`
- Missing rollback story for production-like target
- Intentional bypass of Review Gate or spend controls
