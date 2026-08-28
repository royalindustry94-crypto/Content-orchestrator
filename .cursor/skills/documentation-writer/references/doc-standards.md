# Documentation standards — Content Orchestrator

## Quality bar

- **Accurate** — matches implemented behavior or clearly marks planned work
- **Complete for scope** — milestone docs cover implementation + audit (or list gaps)
- **Actionable** — operators/engineers can find rollback, migrations, and invariants
- **Consistent** — shared terms from `terminology.md`
- **Traceable** — cite PR, SHA, migration head, ADR id when relevant

## Preferred structure

1. Purpose / scope  
2. Current behavior (implemented)  
3. Non-goals / out of scope  
4. Assumptions & trade-offs  
5. Risks & rollback  
6. References (code paths, PRs, related docs)

## Diagrams

Use mermaid or concise tables for:

- Service boundaries (api / worker / web / Postgres)
- Review Gate and spend control flows
- Migration expand/contract sequences
- Tenant isolation (workspace_id + RLS)

## Sync rules

| Change type | Docs to touch |
|-------------|----------------|
| New/changed API | OpenAPI notes / route docs; changelog |
| Schema/RLS | Migration doc + architecture/IAM docs as needed |
| ADR | `docs/architecture-decisions.md` or dedicated ADR file |
| Milestone ship | Implementation report + audit + release notes |
| Skill/process | `docs/CURSOR_SKILLS.md` + skill pointer |

## Forbidden

- Documenting aspirational UI/API as live
- Leaving broken links in “done” docs
- Contradicting FORCE RLS / Review Gate / spend without an explicit CEO-accepted exception note
