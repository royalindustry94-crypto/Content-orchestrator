# Lumora Operations Dashboard — Mission Control (V3)

Extends V1/V2 into the Founder Mission Control. Existing screens remain;
V3 adds live activity, system health, cost control, worker timelines,
content command center, quick actions, and executive insights.

## Screens and APIs

| Screen | API |
|---|---|
| Live Activity Feed | `GET .../operations/activity` |
| System Health | `GET .../operations/health` |
| Cost Control | `GET .../operations/cost-control` |
| Worker Timeline | `GET .../operations/worker-timeline` |
| Content Command Center | `GET .../operations/content-command` |
| Executive Insights | `GET .../operations/insights` |
| Quick Actions | `POST .../operations/actions/*` |

Quick actions:

- `pause-workers` / `resume-workers` — set `worker_registry.drain`
- `emergency-stop` — revoke credentials + reap assignments
- `retry-failed-jobs` — enqueue RETRY schedules from DLQ / failed assignments
- `clear-dead-letter` — mark pending DLQ rows discarded
- `sync-github` — refresh live GitHub status
- Create Workspace / Create Pipeline — existing `POST /workspaces` and content-jobs

All Mission Control endpoints require workspace admin JWT. No fabricated metrics.
