# Architecture Review Record

**Date:** YYYY-MM-DD  
**Review ID:** ARCH-YYYYMMDD-##  
**Verdict:** APPROVE | CONDITIONAL | REJECT | ESCALATE  
**Reviewer:** Chief Architect (Content Orchestrator)

## Change under review

Summary:

Apps / paths touched:

## Stack & drift

- Approved stack preserved? Y/N
- New dependencies:
- Drift risks:

## Isolation (workspace_id / FORCE RLS)

- Tables/policies:
- Adversarial tests:

## Data & migrations

- Models/constraints/indexes:
- Upgrade / downgrade / expand-contract:
- Rollback plan:

## Transactions & concurrency

- Lock order:
- Races identified:
- Idempotency keys:
- Retry / DLQ behavior:

## Boundaries

- API / service / worker / web dependency direction:
- Auth principals:

## Control planes

- Human Review Gate impact:
- Spend-control impact:

## Production readiness

- Placeholders / silent failures:
- Error handling:

## Conditions (if CONDITIONAL)

- [ ] …
- [ ] …

## Escalation (if ESCALATE)

Risk domain: security | data integrity | tenant isolation | financial | maintainability  

Ask `/ceo` to decide:

## Required tests

1. …
2. …

## ADR required?

- [ ] No
- [ ] Yes → draft with `assets/adr-template.md` before implementation
