# Changelog

All notable changes to Content Orchestrator are documented in this file.

## [Unreleased]

### Added — WP-PB-005 Pipeline provider abstraction (2026-08-29)

- **Provider seam**: `app/providers` is now the single boundary between the orchestration services and content vendors. Activating a vendor is an implementation swap rather than an edit to five stage services.
- **`PIPELINE_PROVIDER_MODE`** selects the implementation. Default `null` preserves the previous fail-closed behaviour exactly: no vendor call, no spend, every stage stops at `provider_not_configured`.
- **Simulation provider** (`simulation`): deterministic, offline, zero-cost, for exercising the pipeline before a paid vendor exists. Refused when `ENVIRONMENT` is production, with no override.
- **Independent auditors that previously existed only as test-only helpers are now real**: the four mandatory Content Department auditors (`POST .../packages/{id}/audits`), Media QA (`POST .../artifacts/{id}/media-qa`), and Chief Auditor gate reconciliation (`POST .../artifacts/{id}/chief-audit`). They read persisted state and never consult the provider that produced the work.
- **The chain now terminates at a human**: a Chief Auditor pass assembles the Human Review Package and opens the mandatory Human Review Gate.
- **`GET /pipeline/provider`** plus a persistent web banner so simulated output can never be read as real.
- **`scripts/dev_up.sh`**: one command to bring up a testable stack. Walkthrough in `docs/TESTING_GUIDE.md`.

### Fixed

- `GET /production/runs/{id}` raised on every real job: the production output schemas lacked `from_attributes`, so the route's `model_validate` against ORM rows always failed. Only the 401/403 path had been covered.

### Changed

- `content_desk.open_review_gate` is extracted so every path that puts content in front of a reviewer shares one implementation of the gate.
- Research, Strategy, and Content Department fixture paths now run through the same persistence routines as the live provider path, so tests exercise the code that really runs.

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
