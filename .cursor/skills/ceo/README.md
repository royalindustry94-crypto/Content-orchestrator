# CEO Skill — Documentation

**Skill id:** `ceo`  
**Location:** `.cursor/skills/ceo/`  
**Invoke:** `/ceo` or ask for a CEO decision on architecture, quality, security, or release.

## Purpose

Project-scoped Cursor Skill that acts as the **CEO of Content Orchestrator**.
It makes high-level technical and product decisions, protects long-term
architecture, and enforces Lovable Quality Standards plus the project’s
hard invariants (Postgres SoT, RLS/workspace isolation, Human Review Gate,
spend caps, zero placeholders, no silent failures, testing & release
discipline).

## Layout (Cursor best practices)

```text
.cursor/skills/ceo/
├── SKILL.md                          # required — frontmatter + instructions
├── references/                       # progressive disclosure (load on demand)
│   ├── lovable-quality-standards.md
│   ├── architecture-invariants.md
│   ├── decision-framework.md
│   └── release-discipline.md
├── assets/
│   └── decision-record-template.md
├── scripts/
│   └── ceo-release-gate.sh           # advisory local gate
└── README.md                         # this file
```

Per [Cursor Skills](https://cursor.com/docs/skills.md):

- Folder name matches frontmatter `name` (`ceo`)
- Strong `description` for auto-discovery
- Keep `SKILL.md` focused; put deep material in `references/`
- Optional `scripts/` and `assets/` for actionable helpers

## How agents should use it

1. Read `SKILL.md` when the task matches the description or user says `/ceo`.
2. Load only the reference files needed for the decision.
3. Emit a verdict: APPROVE / CONDITIONAL / REJECT / DEFER.
4. For lasting decisions, update `docs/architecture-decisions.md`.
5. For ship/go-no-go, follow `references/release-discipline.md` and optionally run:

```bash
bash .cursor/skills/ceo/scripts/ceo-release-gate.sh
```

## Related project docs

| Doc | Role |
|---|---|
| `docs/architecture-decisions.md` | Standing ADRs |
| `docs/M4_*_DESIGN.md` | Active workstream designs |
| `docs/milestone-2-identity-and-access.md` | Auth / RLS foundation |
| `replit.md` | Repo overview / operator notes |

## Non-goals

- Replacing short always-on Cursor **rules** (skills are for multi-step CEO workflows)
- Implementing the rejected TeslaFlow 369 numerology product constraints
- Auto-merging PRs
