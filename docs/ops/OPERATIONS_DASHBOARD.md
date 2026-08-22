# Lumora Operations Dashboard — Founder Control Center (V2)

Extends V1. Existing Executive / Worker / Pipeline / Alerts projections remain;
V2 adds CRM, customers, spend breakdown, GitHub, AI Pipeline metrics, and a
notification center. All widgets use durable backend data or live upstream APIs
when configured — never placeholders or fabricated values.

## Screens and APIs

| Screen | API |
|---|---|
| Executive Dashboard | `GET /workspaces/{id}/operations/executive` |
| AI Workers | `GET /workspaces/{id}/operations/workers` |
| Leads CRM | `GET/POST /workspaces/{id}/operations/leads`, `PATCH .../leads/{lead_id}` |
| Customers | `GET /workspaces/{id}/operations/customers` |
| Spend | `GET /workspaces/{id}/operations/spend` |
| GitHub | `GET /workspaces/{id}/operations/github` |
| AI Pipeline | `GET /workspaces/{id}/operations/pipelines` |
| Notifications | `GET /workspaces/{id}/operations/notifications` |
| Alerts (V1) | `GET /workspaces/{id}/operations/alerts` |

All endpoints require a verified bearer JWT and `admin` membership.

## Module notes

- **AI Workers:** live status, current task, queue, optional CPU/Memory from
  worker `capabilities` (Unavailable when absent), heartbeat, completed/failed
  today, retry count.
- **Leads CRM:** workspace-scoped `leads` table (migration `0034`) with search
  and status/source filters.
- **Customers:** workspaces the caller administers + `workspace_billing` +
  membership counts. Revenue MTD sums Stripe `invoice.paid` /
  `invoice.payment_succeeded` webhook payloads (cents → USD).
- **Spend:** today / week / month, by provider from `spend_logs`, budget
  remaining vs workspace-wide spend caps.
- **GitHub:** live REST API when `GITHUB_TOKEN` (or `GITHUB_API_TOKEN`) and
  `GITHUB_REPOSITORY` are set; otherwise `available=false` with reason.
  Branch CI still uses deploy-injected `DEPLOYMENT_*` metadata.
- **AI Pipeline:** jobs completed / waiting / failed, human reviews waiting,
  publishing queue (extends V1 pipeline monitor).
- **Notifications:** real-time center (15s poll) for worker offline, pipeline
  failed, spend warning, CI failed, customer signup, new lead, review required.

## Configuration

```env
DEPLOYMENT_GIT_BRANCH=main
DEPLOYMENT_COMMIT_SHA=<deployed commit>
DEPLOYMENT_AT=2026-08-06T05:00:00Z
DEPLOYMENT_CI_STATUS=success
DEPLOYMENT_CI_URL=https://github.com/org/repo/actions/runs/123
GITHUB_TOKEN=<optional>
GITHUB_REPOSITORY=owner/repo
```
