# Web agent guidance

This file adds web-specific guidance to the repository-root `AGENTS.md`.

- User-facing branding is **The Business Manager**. Do not introduce Lumora or Content Orchestrator labels into new customer-facing UI.
- Keep provider and runtime states truthful. Unavailable functionality must say it is unavailable; no fake success, fake balances, or silent placeholders.
- Preserve keyboard access, visible focus, semantic headings, labels, dialog focus handling, reduced motion, and at least 44px primary touch targets.
- Verify changed journeys at desktop and 390px mobile widths with no horizontal overflow.
- Treat the Human Review queue as a safety surface: distinguish awaiting, approved, rejected, and externally published states precisely.
- Keep API access behind the existing client boundary and handle loading, empty, error, and unauthorized states.

From `apps/web`, run `npm run lint`, `npm test`, `npm run build`, and `npm audit --audit-level=high`.
