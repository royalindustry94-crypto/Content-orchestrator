# Hub architecture — Executive Operations Hub

## Purpose

Coordinate **people, agents, and systems** that build and operate Content
Orchestrator:

- Engineering tasks and PR lifecycle
- Cursor Background Agent assignment and status
- Approval tracking (ops approvals ≠ product Review Gate)
- Release coordination signals
- Dashboards, notifications, audit trails for ops activity

## Suggested bounded contexts (modular)

| Module | Responsibility |
|--------|----------------|
| Work intake | Normalize goals/issues into hub tasks |
| Agent broker | Assign/monitor Cursor (and future) agents |
| Approval desk | Ops-level approvals (merge readiness signals, change windows) — does not replace product Review Gate |
| Release board | Track readiness inputs from `/release-manager` evidence |
| Integration bus | Adapters for GitHub, Actions, chat/email, future business apps |
| Audit & notify | Append-only ops audit + notification routing |
| Hub console | Operator UI (separate from tenant content UI where practical) |

## Architectural style

- **Event-driven** between modules where possible
- **Clear ownership** per module (API + data + on-call)
- **Idempotent** handlers for agent/CI webhooks
- **Scalable** — avoid single-threaded manual bots as the only path

## Data guidance

- Hub may store **ops metadata** (task ids, agent run ids, links to PRs/SHAs)
- Tenant **content orchestration state** stays in product Postgres schema via product APIs
- If Hub needs Postgres, isolate schemas/roles; consult `/postgresql-expert` + `/chief-architect` before sharing product tables

## Relation to product

```text
Executive Ops Hub          Content Orchestrator (product)
─────────────────          ─────────────────────────────
tasks / agents /           workflows / leases / outbox /
ops approvals /            Review Gate / spend /
release tracking    ──►    tenant content pipelines
        ▲                         │
        └──── status via APIs/events ──┘
```
