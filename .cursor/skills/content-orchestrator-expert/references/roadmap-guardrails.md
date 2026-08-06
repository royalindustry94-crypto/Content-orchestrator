# Roadmap guardrails

## Alignment questions

1. Does this belong in the current milestone, or is it premature?
2. Does an existing workflow/stage/outbox concept already cover it?
3. Does it create a second source of truth?
4. Does it hard-wire a vendor into the domain model?
5. Does it weaken Review Gate, spend, isolation, or audit?
6. Is Executive Hub integration implied without an ADR?

## Creep signals

- Renaming existing concepts to justify a greenfield module
- “Temporary” bypass flags for review or spend
- Per-feature databases, queues, or auth systems
- Duplicate job/lease/claim implementations

## Drift signals

- Non-Postgres orchestration SoT
- Cross-workspace APIs without membership checks
- Worker protocol incompatible with claim/lease/submit
- UI-only enforcement of tenancy or approvals

## Responses

| Signal | Domain verdict | Next |
|--------|----------------|------|
| Mild sequencing issue | CONDITIONAL | Recommend milestone split |
| Duplicate capability | CREEP | Reuse existing module |
| SoT/boundary violation | DRIFT | `/chief-architect` |
| Principle FAIL | REJECT_DOMAIN | `/ceo` (+ Security/PG as needed) |
