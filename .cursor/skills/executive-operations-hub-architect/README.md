# Executive Operations Hub Architect skill

Invoke with **`/executive-operations-hub-architect`** (Cursor skill name:
`executive-operations-hub-architect`).

Designs the internal Operations Hub that coordinates engineering, AI agents,
approvals, releases, and business ops — without becoming a second content
orchestration SoT or bypassing Review Gate / spend controls.

- **Entry:** [SKILL.md](./SKILL.md)
- **Authority:** [AUTHORITY_MATRIX.md](../AUTHORITY_MATRIX.md)
- **Docs pointer:** [docs/EXECUTIVE_OPERATIONS_HUB_ARCHITECT_SKILL.md](../../../docs/EXECUTIVE_OPERATIONS_HUB_ARCHITECT_SKILL.md)

## Quick rules

- Architecture before major implementation
- Hub coordinates; Content Orchestrator remains product SoT
- Clean interfaces to GitHub, Cursor agents, CI/CD, Postgres, business systems
- Observable, auditable, fault-tolerant, secure
- Escalate reliability/security/compliance/maintainability risks
- Evidence before VERIFIED; **never merge**
