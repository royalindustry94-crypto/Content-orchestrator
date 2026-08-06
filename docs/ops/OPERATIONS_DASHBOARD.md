# Lumora Operations Dashboard V1

The Operations Dashboard is a read-only, workspace-admin control plane. It
uses durable orchestration tables and deploy-injected metadata; it does not
generate sample data or infer values from browser state.

## Screens and APIs

| Screen | API |
|---|---|
| Executive Dashboard | `GET /workspaces/{workspace_id}/operations/executive` |
| Worker Monitor | `GET /workspaces/{workspace_id}/operations/workers` |
| Pipeline Monitor | `GET /workspaces/{workspace_id}/operations/pipelines` |
| Alerts | `GET /workspaces/{workspace_id}/operations/alerts` |

All endpoints require a verified bearer JWT and `admin` membership in the
requested workspace. Queries are explicitly scoped to `workspace_id`.
Global workers are included because they serve all workspaces; their job
counts and current work remain scoped to the requested workspace.

## Metric definitions

- **Jobs Running:** dispatched or acknowledged stage assignments.
- **Jobs Queued / Queue Depth:** pending `job_schedule` rows.
- **Jobs Failed:** failed stage assignments.
- **Human Reviews Waiting:** review gates in `awaiting`.
- **Spend Today / Month:** committed `spend_logs`, UTC boundaries.
- **Active Workspaces:** the authorized workspace represented by the current
  dashboard (1 when it exists).
- **Retrying Pipelines:** distinct active RETRY schedule references.
- **Dead Letter Queue:** pending dead-letter jobs.
- **Publish Queue:** pending or publishing, non-deleted publish jobs.

Alerts are emitted only for active conditions: dead workers, failed jobs in
the last 24 hours, failed CI metadata, ≥80% spend-cap use, waiting reviews,
queue depth at/above the workspace soft limit, and failed webhooks in the
last 24 hours.

## Deployment metadata

The database does not contain GitHub or deployment state. Inject real values
from the deploy system:

```env
DEPLOYMENT_GIT_BRANCH=main
DEPLOYMENT_COMMIT_SHA=<deployed commit>
DEPLOYMENT_AT=2026-08-06T05:00:00Z
DEPLOYMENT_CI_STATUS=success
DEPLOYMENT_CI_URL=https://github.com/org/repo/actions/runs/123
```

Missing values are returned as `null` / `unavailable` and rendered as
**Unavailable**. The API never substitutes a branch, CI result, deployment
time, or commit.

## Operations

The frontend loads one screen at a time, shows skeleton loading states,
provides explicit retry on errors, and never preserves stale data after a
failed refresh. Use the Refresh action to request a new server projection.
