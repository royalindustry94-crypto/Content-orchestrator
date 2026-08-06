# Chief Architect Skill — Documentation

**Skill id:** `chief-architect`  
**Location:** `.cursor/skills/chief-architect/`  
**Invoke:** `/chief-architect` or ask for an architecture review.

## Purpose

Protects Content Orchestrator architecture: approved stack, multi-tenant
isolation (workspace_id + FORCE RLS), clean boundaries, concurrency/idempotency
correctness, Human Review Gate and spend-control planes, production-ready
errors, and ADR-before-major-change discipline.

Complements `/ceo` (product/quality/release authority). Escalate security,
integrity, tenant, financial, or maintainability risks to CEO.

## Layout (Cursor best practices)

```text
.cursor/skills/chief-architect/
├── SKILL.md
├── README.md
├── references/
│   ├── approved-stack.md
│   ├── data-architecture.md
│   ├── boundaries-and-dependencies.md
│   ├── concurrency-and-correctness.md
│   └── review-protocol.md
├── assets/
│   ├── architecture-review-template.md
│   └── adr-template.md
└── scripts/
    └── architect-drift-scan.sh
```

## How agents should use it

1. Load `SKILL.md` when architecture/stack/schema/boundary/concurrency work starts.
2. Open only needed `references/` files.
3. Emit **ARCHITECT VERDICT**: APPROVE / CONDITIONAL / REJECT / ESCALATE.
4. For lasting decisions, write ADR → `docs/architecture-decisions.md` before major impl.
5. Optional: `bash .cursor/skills/chief-architect/scripts/architect-drift-scan.sh`

## Related docs

- `docs/architecture-decisions.md`
- `docs/milestone-2-identity-and-access.md`
- `docs/M4_*_DESIGN.md` / implementation / audit docs
- `docs/CHIEF_ARCHITECT_SKILL.md` (pointer)
