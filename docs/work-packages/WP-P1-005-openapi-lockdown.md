# P-005 — OpenAPI lockdown outside development

## Objective

Disable unauthenticated `/docs`, `/redoc`, and `/openapi.json` outside
`development` so staging/production do not disclose the API surface.

## Plan

1. Centralize docs URL selection from `Settings.environment`.
2. Pass `docs_url` / `redoc_url` / `openapi_url` into `FastAPI(...)`.
3. Tests: helper unit tests + integration 404 under `ENVIRONMENT=test`.
4. Docs: LAUNCH_BLOCKERS, TD-020, DEPLOYMENT note.

## Dependencies

None (uses existing `environment` setting).

## Non-goals

- Auth-gated docs portal
- Changing CORS or health endpoints

## Rollback

Revert the `FastAPI(...)` kwargs (docs become public again).

## Status — COMPLETE (2026-07-28)

| Deliverable | Location |
|-------------|----------|
| Config helper | `openapi_route_kwargs` / `Settings.openapi_docs_enabled` |
| App wiring | `apps/api/app/main.py` FastAPI docs URLs |
| Tests | `apps/api/tests/test_openapi_lockdown_p1.py` |
