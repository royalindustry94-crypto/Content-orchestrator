# AGENTS.md — Content Orchestrator

Instructions for coding agents and humans working in this repository.

## Product north star

Private Beta → first paying customers → PMF. Prioritize **revenue path**,
**customer-reachable Review Desk**, and **non-negotiable safety** over
speculative platform work.

## Non-negotiables (do not weaken)

1. **Human Review Gate** — content never auto-publishes past review.
2. **Workspace isolation** — FORCE RLS on tenant tables; no cross-tenant leaks.
3. **Spend controls** — daily/monthly caps fail closed (HTTP 402 / hold).
4. **Provider abstraction** — no hard-coding a single LLM/vendor into the core path.
5. **Audit logging** — security-relevant mutations emit structured audit events.
6. **No placeholders** — no TODOs, stubs, or silent fallbacks in production paths.

## Milestone governance

- Every milestone ends with an evidence-backed **PASS**, **CONDITIONAL**, or **FAIL** audit using `docs/MILESTONE_AUDIT_STANDARD.md`.
- The coding worker/agent must not be the sole certifier of its own milestone. Use an independent auditor where available; otherwise perform a separate adversarial audit pass from fresh evidence.
- **FAIL blocks merge.** Only the Founder may explicitly override a failed gate after reviewing the documented risks.
- **CONDITIONAL** is allowed only for non-safety-critical, owner-assigned, time-bounded conditions approved by the Founder.
- Unknown or missing evidence for workspace isolation, Human Review Gate integrity, spend controls, secrets, destructive migration safety, or critical data integrity is a **FAIL**, not a conditional pass.
- Preview branches or PRs marked `do not merge` require explicit Founder approval before merge.
- Re-check the exact PR head SHA, CI state, migration head, unresolved findings, and required external/runtime evidence immediately before merge.

## Stack

| Area | Tech |
|------|------|
| API | FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL |
| Web | React + TypeScript + Vite |
| Worker | Python claim/execute/submit (Draft Desk) |

## Layout

```
apps/api/     Backend + migrations + tests
apps/web/     Review Desk UI
apps/worker/  Background worker
docs/         Architecture, ops, audits, work packages
```

## Engineering rules

- **P0 is frozen** unless a Critical defect is proven. Prefer additive P1 work.
- **No new frameworks** without an explicit work package. Upgrade pins to fix
  CVEs is allowed; swapping stacks is not.
- **Highest business-value backlog item first** (`docs/LAUNCH_BLOCKERS.md`).
- Schema changes need Alembic upgrade **and** downgrade, plus a rollback note.
- Parallel Alembic heads off the same parent must be linearized before merge.
- Tests: API `pytest --cov-fail-under=75`, worker `pytest`, web `npm test` + build.
- Auth: `AUTH_MODE=local` for Private Beta; JWTs are Supabase-shaped (`PyJWT`).
- OpenAPI `/docs` is **development-only** (`ENVIRONMENT=development|dev`).

## Security checklist for every change

- [ ] Workspace membership / role guards on new routes
- [ ] RLS / FORCE RLS preserved for new tables (or owner-only by design)
- [ ] Spend path still fail-closed where money is spent
- [ ] Gate still mandatory for publishable content
- [ ] Secrets only via env (see `.env.example`); never commit `.env`
- [ ] CI security jobs remain fail-closed (`pip-audit`, `npm audit`, gitleaks)

## Docs to update when closing a launch item

- `docs/LAUNCH_BLOCKERS.md`
- `docs/TECHNICAL_DEBT_REGISTER.md` (matching TD-*)
- `docs/EXECUTIVE_STATUS_REPORT.md` / completeness when materially changed
- Work package under `docs/work-packages/`

## Explicit non-goals (until PMF)

- Connector races (Zapier/Make parity)
- Autonomous publish modes
- Enterprise SSO/SOC theater without paid demand
- Self-host as a product SKU
