# Beta Release Checklist — Private Beta

**Branch:** `cursor/p2-beta-launch-b52d`  
**Date:** 2026-08-03

Use this checklist before inviting Private Beta customers.

## Gate (must be green)

- [x] P0 COMPLETE and frozen
- [x] P-001 Stripe billing (opt-in `BILLING_ENABLED=false` for beta)
- [x] P-002 DR restore drill signed (`docs/DISASTER_RECOVERY_REPORT.md`)
- [x] P-003 / P-004 CVE remediation + fail-closed CI audits
- [x] P-005 OpenAPI lockdown outside development
- [x] P-006 FK covering indexes (0 unindexed FKs)
- [x] P-007 `AGENTS.md` + Cursor rules
- [x] P-008 `/metrics` + on-call runbook
- [x] P-009 Spend cap `numeric(12,4)` precision
- [x] Alembic single head `0032_merge_p1`
- [x] Full regression suite green on integration branch
- [x] No Critical / High launch blockers open

## Pre-invite ops

- [ ] Point staging `DATABASE_URL` / `APP_DATABASE_URL` at the intended host
- [ ] Set `SUPABASE_JWT_SECRET` (≥ 32 bytes) and rotate if previously shared
- [ ] Confirm `ENVIRONMENT=staging` (OpenAPI docs off)
- [ ] Confirm `BILLING_ENABLED=false` until Stripe secrets + Price ID ready
- [ ] Nightly `pg_dump` off-host with ≥ 30 day retention
- [ ] Smoke: signup → workspace → content-job → Gate approve/reject → spend PATCH
- [ ] Worker registered and Draft Desk produces non-empty script artifacts
- [ ] `/health/live`, `/health/ready`, `/health/automation`, `/metrics` monitored

## Customer-facing

- [ ] Review Desk UI reachable behind auth
- [ ] Support channel + on-call owner named (`docs/ops/ON_CALL.md`)
- [ ] Known limitations communicated (BYOK incomplete; billing opt-in)

## Stop-ship if

- Any Critical/High security regression (RLS, Gate bypass, spend bypass)
- Alembic heads diverge again without a merge revision
- Restore drill older than 90 days without a fresh sign-off
