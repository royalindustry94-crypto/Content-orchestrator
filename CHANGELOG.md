# Changelog

All notable changes to Content Orchestrator are documented in this file.

## [Unreleased]

### Added — WP-PB-001 Private Beta Review Desk (2026-07-27)

- **Content Jobs API**: `POST /workspaces/{id}/content-jobs` submits a draft that lands in the mandatory Human Review Gate (Private Beta stub generation uses the supplied script; Gate is never skipped).
- **Review Desk API**: `GET /workspaces/{id}/review-gates`, `GET .../{gate_id}`, `POST .../{gate_id}/decision` (approve/reject with notes; admin/reviewer only).
- **Default workflow** `agency_content_desk` v1 provisioned per workspace on first job.
- **Outbox relay loop** in API lifespan so review decisions advance runs in production.
- **Review Desk web UI** for Private Beta operators (token + workspace, submit draft, approve/reject).
- Vite `/api` proxy rewrite so the web app reaches FastAPI routes correctly.
- Work package: `docs/work-packages/WP-PB-001-review-desk-api.md`.

### Changed

- `resume_from_review`: reject with no `on_review_rejected` transition **fails the run** (`review_rejected`) instead of erroring or silently succeeding.
- `submit_review_decision` records `decided_by` on the gate.
- Authorization helpers: `require_workspace_content_author`, `require_workspace_reviewer`.
