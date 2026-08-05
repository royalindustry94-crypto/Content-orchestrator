# On-call runbook — Content Orchestrator

**Audience:** engineer on call for Private Beta / staging / production  
**Last updated:** 2026-07-28 (P-008)

## Severity guide

| Sev | Meaning | Example |
|-----|---------|---------|
| SEV-1 | Customer-facing outage or data leak risk | API 5xx storm; RLS regression; Gate bypass |
| SEV-2 | Degraded product path | Scheduler stuck; spend false positives; worker offline fleet-wide |
| SEV-3 | Elevated error / slow | Single provider flake; DLQ growth |

## First 5 minutes

1. Confirm blast radius: `GET /health/live`, `/health/ready`, `/health/automation`
2. Scrape `GET /metrics` (Bearer `METRICS_SCRAPER_TOKEN` when set; required in
   production) — look at `co_dead_letter_pending`, `co_lease_contention`,
   `co_assignment_failure_rate`, `co_job_schedule_depth{status="pending"}`
3. Check recent JSON logs for `exception`, `spend_hold`, `stripe_webhook_rejected`
4. If readiness fails → Postgres / `APP_DATABASE_URL` first
5. If Gate stuck → automation tasks list + outbox `last_error`

## Endpoints

| Path | Use |
|------|-----|
| `/health/live` | Process up |
| `/health/ready` | DB reachable |
| `/health/automation` | Scheduler / outbox / maintenance ticks + last errors |
| `/metrics` | Prometheus text (aggregates only; Bearer token when `METRICS_SCRAPER_TOKEN` is set; required in production) |

## Non-negotiables during incidents

- Do **not** disable the Human Review Gate to “unblock”
- Do **not** raise spend caps globally without owner approval
- Do **not** disable FORCE RLS or switch request traffic to the owner role
- Prefer pause / hold over silent skip

## Rollback levers

| Symptom | Lever |
|---------|-------|
| Bad deploy | Redeploy previous image tag; `alembic downgrade` only with explicit plan |
| Billing gate wrong | `BILLING_ENABLED=false` (beta path) |
| Spend storm | Lower workspace caps via PATCH `/spend`; pause workspaces |
| Bad worker build | Deregister workers; stop claiming |

## Escalation

- Hosted Postgres restore / PITR → follow `BACKUP_AND_RESTORE.md` (P-002 drill sign-off still required)
- Stripe webhook / entitlement disputes → billing owner + audit `stripe_webhook_*` logs
- Suspected cross-tenant leak → SEV-1; freeze writes; preserve DB snapshot

## Follow-ups after stabilize

- File incident note under `docs/` if SEV-1/2
- Add regression test when a code defect caused the page
- Update this runbook if a new lever was used
