# Threat surfaces — Content Orchestrator

## Trust boundaries

```text
Browser/operator ──JWT──► apps/api ──RLS──► PostgreSQL
Python worker ──credential──► apps/api / service-role TX ──► PostgreSQL
GitHub Actions ──secrets──► CI Postgres / registries
```

## High-value assets

- Workspace tenant data (content, pipelines, analytics)
- Worker credentials and provider secrets
- Spend caps / reservations / logs (financial integrity)
- Review gates / decisions (human control plane)
- Outbox events and audit ledgers (integrity / non-repudiation)

## Common attack themes

| Theme | Example |
|---|---|
| Broken tenant isolation | Guess UUID → read other workspace via missing RLS/policy |
| PrivEsc | Editor calls admin-only service-role path without guard |
| Worker impersonation | Stolen/expired credential still accepted |
| Replay | Retry claim/submit doubles provider effect |
| Race | Dual `reserve_spend` exceeds cap |
| Review bypass | Recovery auto-advances past review stage |
| Secret leakage | Token in audit log or Actions log |
| CI poison | `pull_request_target` + checkout untrusted code with secrets |

## Assume hostile

- Clients choose any UUID in paths/bodies
- Workers retry aggressively
- Attackers read GitHub histories and CI logs
- Multi-replica races are the default, not the edge case
