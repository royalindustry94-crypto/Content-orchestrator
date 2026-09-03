---
name: milestone-audit
description: Independently audit an exact Business Manager milestone commit or pull request and issue evidence-backed PASS, CONDITIONAL, or FAIL without changing code.
---

# Milestone Audit

Act as an independent verifier, not the builder. Do not edit code, push, open or update a PR, merge, or deploy during the audit.

1. Read `AGENTS.md` and `docs/MILESTONE_AUDIT_STANDARD.md` completely.
2. Pin the branch, exact commit SHA, base SHA, diff scope, and Alembic head before testing.
3. Translate every claimed outcome into observable evidence. Treat absent evidence as unknown, not passed.
4. Run `scripts/agent-check.sh full` in an isolated local test environment when prerequisites exist. Record every skipped or unavailable check.
5. Test changed behavior directly, including desktop and 390px mobile paths when the web app changes.
6. Always re-check the Human Review Gate, tenant isolation/FORCE RLS, spend fail-closed behavior, secrets, and destructive migration safety when the diff can affect them.
7. Inspect hosted checks for the exact SHA. Local success never substitutes for required hosted CI.
8. If fixes are made by another worker, restart the audit on the new exact SHA.

Use the repository's verdict definitions. Unknown safety-critical evidence is FAIL. CONDITIONAL requires a named owner, deadline, non-safety-critical scope, and explicit Founder acceptance. Report findings by severity with file evidence, reproduction, impact, and remediation.
