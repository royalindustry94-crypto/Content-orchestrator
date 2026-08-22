# Mission Control V4

V4 integrates search, timeline, commands, executive mode, worker logs, and a
live-data assistant into the existing Mission Control shell. It does not create
standalone applications or synthetic data.

## APIs

- `GET /workspaces/{id}/operations/search?q=...`
- `GET /workspaces/{id}/operations/timeline`
- `GET /workspaces/{id}/operations/executive-mode`
- `GET /workspaces/{id}/operations/logs`
- `POST /workspaces/{id}/operations/assistant`
- `POST /workers/logs` (worker credential)

All workspace operations routes require workspace-admin authorization. Worker
log ingestion derives worker/workspace identity from the machine credential.

## Data sources

- Search: workspaces/billing, leads, pipelines, workers, assignments, content,
  review gates, visual/render assets, GitHub API, and durable worker logs.
- Timeline: transactional outbox, leads, memberships, billing webhooks,
  operational alerts, GitHub merges, assets, and worker logs.
- Executive mode: V3 health, billing revenue, spend ledger/caps, workers,
  pipeline/job state, alerts, reviews, customer memberships, and insights.
- Assistant: deterministic intent routing over live projections for failures,
  idle workers, spend, blocked reviews, failed pipelines, and executive risk.

## Worker logs

Migration `0035` adds append-only `worker_logs` with workspace, worker,
pipeline, assignment, severity, message, context, event time, and receipt time.
The reference worker client exposes `log(...)`. Mission Control supports
workspace-fixed filtering by worker, pipeline, job, and severity.
