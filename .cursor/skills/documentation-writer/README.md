# Documentation Writer skill

Invoke with **`/documentation-writer`** (Cursor skill name: `documentation-writer`).

Produces and maintains accurate technical/product documentation for Content
Orchestrator — architecture, ADRs, implementation/audit/release docs,
migrations, OpenAPI-aligned API docs, ops/security notes — without inventing
functionality or allowing doc↔code drift.

- **Entry:** [SKILL.md](./SKILL.md)
- **Authority:** [AUTHORITY_MATRIX.md](../AUTHORITY_MATRIX.md)
- **Docs pointer:** [docs/DOCUMENTATION_WRITER_SKILL.md](../../../docs/DOCUMENTATION_WRITER_SKILL.md)

## Quick rules

- Code is truth; never invent shipped features
- Update docs when implementation in scope changes
- Consistent terminology; cite SHA / migration / version
- ADR acceptance remains `/chief-architect`
- Release readiness remains `/release-manager`
- Evidence before VERIFIED; **never merge**
