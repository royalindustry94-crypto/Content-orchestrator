# Milestone Audit Standard

Every milestone must be independently audited before merge/release approval.

## Required identity

Record milestone/work package, branch/PR, base SHA, audited head SHA, migration head (when applicable), builder, and independent auditor.

## Required audit domains

1. **Scope** — acceptance criteria, non-goals, scope drift, undocumented behavior changes.
2. **Security and tenancy** — authn/authz, workspace membership, RLS/FORCE RLS, cross-tenant negative tests, secrets, audit logging, relevant injection/SSRF/webhook/privilege risks.
3. **Human Review Gate** — prove unreviewed or materially changed content cannot bypass mandatory review.
4. **Spend/providers** — caps fail closed; cost logging; idempotency; bounded retries/backoff; timeouts; truthful disabled/unconfigured states.
5. **Data/migrations** — upgrade, required downgrade/rollback evidence, intended single/merged head, indexes/FKs/constraints, destructive-change review.
6. **Reliability** — explicit error paths; no silent placeholders; concurrency/locking/idempotency review; observability.
7. **Tests/CI** — applicable API coverage gate, worker tests, web tests/build, security/dependency/secret scans, targeted regressions.
8. **UI/browser** — for visible changes, test representative desktop/mobile flows, loading/error/empty states, console failures, overflow, and truthful unavailable states.
9. **Runtime/external evidence** — verify database/provider/deployment facts through connected systems when code cannot prove them. Mark unavailable evidence NOT VERIFIED.
10. **Documentation** — reconcile milestone/work-package docs, launch blockers, technical debt, architecture, executive/release status, audit and rollback notes.

Consult relevant `.agents/memory/*` notes for known project-specific traps.

## Finding severity

Rank findings Critical, High, Medium, Low, or Informational. Each finding must include evidence, affected control, impact, remediation, and whether it blocks merge.

## Verdicts

### PASS
All blocking controls verified; no unresolved Critical/High findings; required evidence complete.

### CONDITIONAL
Only non-safety-critical evidence/work remains. Every condition must be explicit, owner-assigned, time-bounded, and Founder-approved. Never use CONDITIONAL for uncertainty in tenancy, Human Review Gate integrity, spend controls, secrets, destructive migration safety, or critical data integrity.

### FAIL
One or more blocking controls failed or material evidence is missing for a safety-critical claim. Merge is blocked unless the Founder explicitly overrides after reviewing the documented risk.

## Merge re-check

Immediately before merge, re-check the exact PR head SHA, CI, unresolved review threads/findings, migration head, required external/runtime evidence, and Founder approval where required.
