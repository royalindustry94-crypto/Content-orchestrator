# Component / screen checklist

Use before claiming a surface complete.

## Reuse

- [ ] Shared primitive exists or was extracted (Button, Field, Table, EmptyState, ErrorState, …)
- [ ] No copy-pasted divergent styling for the same pattern

## Behavior

- [ ] Loading state
- [ ] Empty state
- [ ] Error state with message
- [ ] Retry (or explicit non-retryable)
- [ ] Success feedback only when API confirms

## Tenancy / RBAC

- [ ] Workspace context required for data views
- [ ] Unauthorized actions hidden or disabled with clear reason when known
- [ ] No cross-workspace client cache bleed

## Quality

- [ ] TypeScript clean
- [ ] No TODO / placeholder / mock production data
- [ ] Lint clean for touched files
- [ ] Tests for critical interaction
- [ ] Review Gate / spend / audit copy remains accurate
