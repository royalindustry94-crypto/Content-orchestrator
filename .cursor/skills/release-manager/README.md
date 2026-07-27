# Release Manager skill

Invoke with **`/release-manager`** (Cursor skill name: `release-manager`).

Owns release readiness from feature completion to production: PR/SHA/CI
identity, architecture + QA + security evidence, migrations, versioning,
changelog, rollback, and the release readiness report.

- **Entry:** [SKILL.md](./SKILL.md)
- **Authority:** [AUTHORITY_MATRIX.md](../AUTHORITY_MATRIX.md)
- **Docs pointer:** [docs/RELEASE_MANAGER_SKILL.md](../../../docs/RELEASE_MANAGER_SKILL.md)

## Quick rules

- Exact SHA for CI / QA / Security evidence
- No Critical/High; no red CI; no incomplete migrations
- Reject TODOs / placeholders / silent failures
- Rollback plan required
- Evidence only — never merge on assumptions
- Product **VERIFIED** remains `/ceo`; this skill certifies **release readiness**
