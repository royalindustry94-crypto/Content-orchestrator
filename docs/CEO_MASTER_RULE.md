# CEO Master Rule (Cursor rule)

Always-on, **highest-priority** project rule:
[`.cursor/rules/ceo-master-rule.mdc`](../.cursor/rules/ceo-master-rule.mdc).

Applies to every task, agent, skill, pull request, and release. Overrides
conflicting project guidance unless the **Founder** explicitly approves an
exception. Enforces approved architecture/roadmap, no drift/TODOs/placeholders/
silent failures, PostgreSQL-only production DB, SQLAlchemy 2.x + reversible
Alembic, `workspace_id` + ENABLE/FORCE RLS, mandatory Review Gate and spend
controls, tests, independent QA + Security before merge, evidence before
VERIFIED, and immediate escalation for security/isolation/financial/compliance/
integrity/maintainability risks.

Related baseline (subordinate on conflict):
[`ENGINEERING_STANDARD_RULE.md`](./ENGINEERING_STANDARD_RULE.md).

See also: [CURSOR_SKILLS.md](./CURSOR_SKILLS.md), [`/ceo`](../.cursor/skills/ceo/).
