# ADR guide

## When to write an ADR

- Stack or SoT change proposals
- New service boundaries or data planes
- Cross-cutting decisions (auth, tenancy, outbox, review/spend architecture)
- Explicit rejection of an alternate approach (see `docs/architecture-decisions.md`)

**Acceptance** of ADRs that change stack/SoT/boundaries is owned by
`/chief-architect` (escalate `/ceo` for product/security as required).
Documentation Writer **drafts and maintains**; does not unilaterally accept.

## ADR shape

Use `assets/adr-template.md`:

1. Title + status (Proposed / Accepted / Superseded / Rejected)
2. Context
3. Decision
4. Alternatives considered
5. Consequences (positive / negative)
6. Rollback / exit criteria
7. References (PRs, code, related ADRs)

## Sync

After Architect **Accepted**:

- Update `docs/architecture-decisions.md` index/summary if present
- Ensure implementation reports do not contradict the ADR
- Mark superseded ADRs clearly — do not delete history
