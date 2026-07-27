# Cursor Skills (Content Orchestrator)

Project skills live under `.cursor/skills/<skill-id>/` with a required
`SKILL.md` (see [Cursor Skills docs](https://cursor.com/docs/skills.md)).

**Authority matrix:** [skills/AUTHORITY_MATRIX.md](./skills/AUTHORITY_MATRIX.md)  
**Audit:** [docs/CURSOR_SKILLS_AUDIT.md](../docs/CURSOR_SKILLS_AUDIT.md)

## Installed skills

| Skill | Invoke | Primary authority |
|---|---|---|
| [`ceo`](./skills/ceo/) | `/ceo` | Product direction, quality bar, go/no-go, evidence-backed VERIFIED |
| [`content-orchestrator-expert`](./skills/content-orchestrator-expert/) | `/content-orchestrator-expert` | Domain principles, roadmap fit, creep/drift, product impact |
| [`chief-architect`](./skills/chief-architect/) | `/chief-architect` | Stack freeze, SoT, boundaries, ADRs |
| [`executive-operations-hub-architect`](./skills/executive-operations-hub-architect/) | `/executive-operations-hub-architect` | Ops Hub architecture; agents/approvals/integrations; Hub ≠ content SoT |
| [`backend-engineer`](./skills/backend-engineer/) | `/backend-engineer` | FastAPI / Python worker implementation + app tests |
| [`postgresql-expert`](./skills/postgresql-expert/) | `/postgresql-expert` | Schema, RLS, Alembic, SQL concurrency, DB correctness |
| [`security-auditor`](./skills/security-auditor/) | `/security-auditor` | Independent security audit; blocks Critical/High |
| [`qa-breaker`](./skills/qa-breaker/) | `/qa-breaker` | Adversarial QA; concurrency/recovery/migration/frontend gates |
| [`frontend-engineer`](./skills/frontend-engineer/) | `/frontend-engineer` | React+TypeScript UI, reusable components, API UX, a11y, frontend gates |
| [`devops-engineer`](./skills/devops-engineer/) | `/devops-engineer` | CI/CD, Actions least privilege, deploy/rollback, secrets/env, migration-safe rollout |
| [`release-manager`](./skills/release-manager/) | `/release-manager` | Release readiness, versioning/changelog, gate evidence, RELEASE READY report |
| [`documentation-writer`](./skills/documentation-writer/) | `/documentation-writer` | Docs/ADRs/reports accuracy; no invention; doc↔code sync |

## Hard rules for all skills

- GitHub is the source of truth for code and CI evidence.
- No skill merges PRs without explicit human order **and** QA + security approval.
- No skill marks VERIFIED/COMPLETE without factual evidence.
- No skill silently exceeds the authority matrix.
- Approved stack: FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, React+TypeScript, Python workers.

## Adding a skill

1. Create `.cursor/skills/<kebab-name>/SKILL.md`
2. Frontmatter `name` must match folder name
3. Strong `description`; progressive `references/` / `assets/` / `scripts/`
4. Update `AUTHORITY_MATRIX.md` and this README
5. Do not create overlapping authority without an audit
