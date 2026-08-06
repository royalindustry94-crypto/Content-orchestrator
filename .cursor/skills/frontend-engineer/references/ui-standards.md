# UI standards — Content Orchestrator frontend

## Stack

- **App:** `apps/web` — Vite + React 18 + TypeScript
- **Tests:** Vitest (`npm run test`)
- **Gates:** `npm run lint`, `npm run test`, `npm run build` (`tsc -b && vite build`)

## Composition principles

Aligned with product operator UX (not marketing landing pages unless scoped):

1. **One job per screen/section** — avoid dashboard clutter on focused Review Gate / spend / audit flows.
2. **Truthful status** — job, review, spend, and budget states come from the API; never invent.
3. **Reusable primitives** — buttons, form fields, tables, empty/error panels, workspace switchers shared across screens.
4. **Cards only when interactive containers need them** — prefer clear layout over decorative card grids.
5. **Motion sparingly** — use for hierarchy/feedback (e.g. loading), not noise.

When extending an existing design system in-repo, **preserve** established patterns rather than introducing a parallel look.

## TypeScript

- Prefer strict typing; avoid `any` and unjustified `as` casts
- Model API DTOs from OpenAPI / shared types — do not hand-wave response shapes
- Fail the build on type errors (`tsc -b` in `npm run build`)

## State and data

- Keep workspace id / tenant context explicit in client state and requests
- Prefer server state for authoritative resources; avoid duplicating business rules in reducers
- Do not persist secrets in `localStorage` beyond approved auth token patterns (escalate Security if unclear)

## Review Gate / spend / audit UX

- Review actions must be explicit (approve / reject / etc. per product) — no accidental one-click bypass patterns
- Spend and budget displays must label currency/units as returned by API
- Audit/history views prioritize readability and correct timestamps/actors from API

## Out of scope for this skill alone

- New backend endpoints → Backend Engineer
- Schema/RLS → PostgreSQL Expert
- Product go/no-go → CEO
- Security sign-off → Security Auditor
- Adversarial proof → QA Breaker
