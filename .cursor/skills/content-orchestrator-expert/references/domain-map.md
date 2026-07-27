# Domain map — modules & integrations

Use this map when listing **affected modules** in impact assessments.

| Domain area | Typical code / docs | Notes |
|-------------|---------------------|-------|
| Identity / IAM | `docs/milestone-2-identity-and-access.md`, api auth | JWT, membership, roles |
| Orchestration engine | `apps/api/app/orchestration/` | workflows, stages, transitions |
| Outbox / relay | orchestration outbox/relay | transactional events |
| Scheduling / dispatch | scheduler, dispatcher | fair caps, leases |
| Review Gate | review pause/approve/reject paths | human-in-the-loop |
| Spend | spend reservation / caps | financial control |
| Workers | `apps/worker` | claim / heartbeat / submit |
| Web operator UI | `apps/web` | review/spend/audit surfaces |
| Schema / RLS | Alembic + models | `/postgresql-expert` |
| CI / deploy | `.github/workflows`, compose | `/devops-engineer` |

## Pipeline lens

```text
Plan/create → Generate (providers) → Review Gate → Publish → Analyze
                 ↑                      ↑
            spend/lease            audit/approve
```

Changes should state which stages they touch and whether they introduce a
parallel pipeline (usually **CREEP** / **DRIFT**).

## Executive Operations Hub (future)

- Treat as a **consumer/coordinator** of orchestration signals, not a second SoT
- Prefer events/APIs with stable contracts
- Do not embed hub-specific product UI into core milestones without `/ceo` + `/chief-architect`
