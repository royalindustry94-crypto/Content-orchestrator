# Project terminology (keep consistent)

| Term | Meaning |
|------|---------|
| Workspace | Tenant boundary; tenant-owned rows carry `workspace_id` |
| RLS | Row Level Security; ENABLE + FORCE on tenant tables |
| Human Review Gate | Mandatory human approval path before advancing restricted stages |
| Spend controls | Caps/reservations preventing over-budget dispatch |
| Outbox | Transactional outbox co-committed with state changes |
| Lease | Time-bounded claim on work; reclaim on expiry/crash |
| Claim | Worker obtaining leased work (`SKIP LOCKED` patterns) |
| Alembic head | Current migration revision id — always cite exactly |
| SoT | Source of truth — PostgreSQL for orchestration state |
| VERIFIED | Evidence-backed completion label (product: `/ceo`; readiness: `/release-manager`) |
| apps/api | FastAPI service |
| apps/worker | Python worker |
| apps/web | React + TypeScript (Vite) UI |

## Writing rules

- Prefer “workspace” over “tenant” in user-facing docs unless discussing multi-tenant architecture abstractly
- Do not say “queue in Redis” — Postgres is orchestration SoT
- Do not imply UI authZ replaces server enforcement
- Label Milestone N “scaffold” vs “production UI” accurately
