# Content Orchestrator Engineering Standard (Cursor rule)

Always-on project rule: [`.cursor/rules/content-orchestrator-engineering-standard.mdc`](../.cursor/rules/content-orchestrator-engineering-standard.mdc).

Enforces approved architecture, no drift/TODOs/placeholders/silent failures,
mandatory Review Gate / spend / workspace isolation / FORCE RLS, PostgreSQL SoT,
SQLAlchemy 2.x + reversible Alembic migrations, comprehensive tests, Security
Auditor + QA Breaker + Release Manager gates, evidence before VERIFIED, and
no merge without independent verification.

See also: [CURSOR_SKILLS.md](./CURSOR_SKILLS.md), [AUTHORITY_MATRIX](../.cursor/skills/AUTHORITY_MATRIX.md).
