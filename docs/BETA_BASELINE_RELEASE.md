# Beta Baseline Release

**Status:** MERGED TO `main`  
**Date:** 2026-08-06  
**Approved audit tip:** `a31cfef`  
**Source PRs:** #34 (integration) ← #35 (release-gate fixes)

---

## What shipped

Private Beta engineering baseline for Content Orchestrator:

- Human Review Gate (Review Desk) with resurrection defense (C-1)
- Spend controls: reserve/commit clamp, open-reservation uniqueness (`0033`), idempotent commit
- Stripe billing (default off): checkout linkage only; entitlement via subscription events
- Auth fail-closed default (`AUTH_MODE=supabase`) + production local-auth guard
- Metrics scrape auth (`METRICS_SCRAPER_TOKEN`; required in production)
- Scheduler typed dispatch outcomes (`SPEND_HOLD` / `NO_WORKER` / `SKIPPED`)
- P0 + P1 workstreams integrated; Alembic single head **`0033`**
- Docker staging compose, ops runbooks, fail-closed CI dependency audits

---

## Non-negotiables preserved

- `workspace_id` isolation + ENABLE/FORCE RLS on tenant tables
- Human Review Gate (no worker/outbox bypass to publish)
- Spend controls + audit logging
- Idempotency on webhooks, assignments, spend commit

---

## Operator notes

| Setting | Private Beta default | Production paid launch |
|---------|----------------------|------------------------|
| `AUTH_MODE` | `local` (example) / prefer `supabase` | `supabase` |
| `ALLOW_LOCAL_AUTH_IN_PRODUCTION` | unset/false | **false** |
| `BILLING_ENABLED` | `false` | `true` + live Stripe secrets |
| `METRICS_SCRAPER_TOKEN` | optional non-prod | **required** |
| Alembic | `alembic upgrade head` → `0033` | same |

---

## Evidence

- Final gate: `docs/FINAL_RELEASE_AUDIT.md`
- Post-merge: `docs/POST_MERGE_VERIFICATION.md`
- DR drill: `docs/DISASTER_RECOVERY_REPORT.md`

---

## Out of scope for this baseline

New product features, architecture redesign, managed cloud PITR provisioning, live payment go-live ceremony.
