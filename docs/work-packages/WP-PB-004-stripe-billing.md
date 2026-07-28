# WP-PB-004 / P-001 — Stripe Checkout + entitlements

## Objective

Sell founding Pro ($149–$199 list; Price ID via env) via Stripe Checkout,
persist workspace entitlement, and enforce it when billing is enabled.

## Plan

1. Schema: `workspace_billing` (FORCE RLS) + `billing_webhook_events` (idempotent webhook log, owner-only).
2. Config: `BILLING_ENABLED` (default false preserves P0 beta). When true, require Stripe secret, webhook secret, Pro price ID, success/cancel URLs.
3. API: `GET/POST /workspaces/{id}/billing/*` (admin), `POST /webhooks/stripe` (signature verified).
4. Entitlement: when `BILLING_ENABLED=true`, block `content-jobs` without active/trialing Pro.
5. Tests: mocked Stripe SDK; webhook idempotency; entitlement gate; RLS/IDOR.
6. Docs: ROADMAP, LAUNCH_BLOCKERS, DEPLOYMENT, work-package note.

## Dependencies

- `stripe` Python SDK
- Existing workspace admin auth + audit logging
- Alembic migration 0031

## Non-goals

- Customer portal UI redesign
- Multiple SKUs / seat metering
- Changing Review Gate or spend control semantics

## Rollback

- `alembic downgrade 0030` drops new tables
- Disable with `BILLING_ENABLED=false` (no entitlement checks)

## Status — COMPLETE (2026-07-28)

| Deliverable | Location |
|-------------|----------|
| Schema | `apps/api/alembic/versions/0031_workspace_billing.py` |
| Models / service | `app/models/billing.py`, `app/services/billing.py` |
| Routes | `GET/POST .../billing`, `POST /webhooks/stripe` |
| Entitlement gate | `content_jobs` → 402 when billing on and not entitled |
| Tests | `apps/api/tests/test_billing_p1.py` (10) |
| Config | `BILLING_ENABLED` default **false** (P0 beta preserved) |
