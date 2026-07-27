# Milestone 4 — Workstream 4 Implementation Report

**Branch:** `feature/milestone-4`  
**Migration head:** `0029`  
**Depends on:** WS1–WS3 (`0025`–`0028`)

## Delivered

| Area | Implementation |
|---|---|
| Design | `docs/M4_WS4_DESIGN.md` (landed before production code) |
| Schema | Migration `0029_priority_backpressure_ws4` |
| Priority | `stage_assignments.priority` + age boost at claim (`priority.py`) |
| Workspace tier | `workspaces.priority_tier` → base priority / job priority |
| Provider budgets | `provider_concurrency_budgets` + claim/dispatch gates |
| Back-pressure | `workspace_backpressure_state` + ENTERED/CLEARED outbox events |
| Scheduler throttle | `effective_scheduler_tick_limit` halves tick when THROTTLED |
| Spend lock | `reserve_spend` uses `SELECT … FOR UPDATE` on `spend_caps` |
| Admin APIs | `GET/PUT …/concurrency`, provider-budget CRUD, PATCH `priority_tier` |
| Maintenance | Back-pressure eval in `_orchestration_maintenance_loop` |
| Config | Age-boost, tier weight, queue defaults, claim candidate batch |
| Tests | `tests/test_priority_backpressure_ws4.py` |
| Decisions | `docs/architecture-decisions.md` WS4 section |

## Files (primary)

- `apps/api/alembic/versions/0029_priority_backpressure_ws4.py`
- `apps/api/app/orchestration/{priority,backpressure,provider_budgets}.py`
- `apps/api/app/orchestration/{claiming,dispatcher,scheduler,controller}.py`
- `apps/api/app/api/routes/concurrency.py`
- `apps/api/app/models/{backpressure,assignments,workspace,scheduling,enums}.py`
- `apps/api/app/schemas/{concurrency,workspace}.py`
- `apps/api/app/main.py`, `apps/api/app/core/config.py`
- `apps/api/tests/test_priority_backpressure_ws4.py`

## Behaviour notes

1. **Effective priority** = `priority + age_boost(created_at)`; boost computed in SQL at claim time (no stale column).
2. **Provider budget skip** uses per-candidate `SAVEPOINT` so over-budget rows release locks and do not starve concurrent claimers.
3. **Missing provider budget** ⇒ unlimited (fail-open); admin must insert a budget to constrain.
4. **THROTTLED** halves `max_per_scheduler_tick` (min 1); PENDING rows are never deleted by back-pressure.
5. **Spend race** serialized on the `spend_caps` row; concurrent last-dollar reservations → exactly one succeeds.

## Out of scope (WS5+)

RECURRING jobs, DLQ replay endpoint, Prometheus `/metrics` HTTP, real AI executors, Web UI.

## Validation performed

- `pytest -W error` (API full suite)
- Worker pytest + ruff
- `alembic` 0029 ↔ 0028 roundtrip; fresh DB `upgrade head` → `0029`
- `ruff check` clean
- Coverage measured on WS4 modules + full suite
