# Backend implementation standards

## Completeness

- Deliver working code for the claimed scope end-to-end in `apps/api` / `apps/worker`.
- Prefer omitting out-of-scope features over stubbing them.
- If a job type is not implemented, **raise explicitly** (documented) — never pretend success.

## Error handling

- Map domain errors to stable HTTP codes (`400/401/403/404/409/422/503` as appropriate).
- Use typed domain errors (e.g. `LeaseError`) at the edge; do not leak stack traces to clients.
- Log failures with structured fields (`request_id`, `workspace_id`, `worker_id`, correlation ids) — never secrets.
- Transaction failures → rollback; do not partial-commit domain + outbox.

## Logging

- Use the project logging/audit helpers (`app.core.logging`, `app.core.audit`).
- Prefer `audit(request, event, **fields)` for security-sensitive mutations.
- No `print` debugging in committed code.

## Documentation in code

- Docstrings on public orchestration entrypoints explaining invariants (locks, idempotency).
- Avoid narrating what the next line does.
- Design/impl/audit docs belong under `docs/` for workstreams — not as substitute for tests.

## Maintainability

- One module, one job; keep routers thin.
- Reuse existing orchestration (`claiming`, `dispatcher`, `controller`, `recovery`, `outbox`) before inventing parallel paths.
- Match existing naming, typing, and formatter/linter (`ruff`) settings.

## Compatibility

- Expanding columns: additive migrations first; dual-read if needed; then tighten.
- Worker/API contract changes: keep old clients working through a grace window when credentials/lease semantics change.
- Do not break Human Review Gate or spend reservation semantics for convenience.

## Collaboration with other skills

| Situation | Skill |
|---|---|
| New framework / SoT / boundary redesign | `/chief-architect` (stop; do not invent) |
| Schema / RLS / Alembic design | `/postgresql-expert` (stop; do not land unapproved DDL) |
| Scope cut, quality bar, merge/VERIFIED | `/ceo` (evidence pack only; no self-VERIFIED) |
| Implementation inside approved design | `/backend-engineer` (this skill) |

Never merge PRs. Never approve your own work as final architecture or schema review.
