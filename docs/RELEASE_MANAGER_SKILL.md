# Release Manager skill

Cursor skill: **`release-manager`** (`/release-manager`).

Package: [`.cursor/skills/release-manager/`](../.cursor/skills/release-manager/).

Owns release readiness for Content Orchestrator — PR/SHA/CI identity,
architecture + QA + security evidence, migration verification, versioning/
tags/changelogs, rollback confirmation, invariants (Review Gate, spend, audit,
RLS, isolation), and the release readiness report. Never merges or approves on
assumptions. Product go/no-go **VERIFIED** remains `/ceo`; CI/CD ownership
remains `/devops-engineer`.

See also: [CURSOR_SKILLS.md](./CURSOR_SKILLS.md), [AUTHORITY_MATRIX](../.cursor/skills/AUTHORITY_MATRIX.md),
example [M3_RELEASE_REPORT.md](./M3_RELEASE_REPORT.md).
