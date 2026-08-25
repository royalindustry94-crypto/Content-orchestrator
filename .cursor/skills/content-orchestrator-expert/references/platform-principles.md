# Platform principles — Content Orchestrator

## Multi-tenancy & workspace isolation

- Every tenant-owned row is workspace-scoped
- RLS ENABLE + FORCE is the backstop; app filters are not enough alone
- No “god mode” query paths that skip workspace context in product features

## Human Review Gate

- Restricted workflow advances require human approval
- Timeouts and rejects must fail loudly / route correctly — not silent skip
- UI must not invent approve/reject without API authority

## Spend controls

- Reserve/check caps before costly provider work
- Over-cap behavior is explicit (hold/pause), not best-effort continue
- Concurrent reservation hazards are a known risk class — do not regress M4 hardening

## Provider abstraction

- Core orchestration speaks stage/job/result contracts
- Vendor SDKs live in worker/adapters
- Swapping a provider must not require rewriting workflow SoT

## Auditability

- Sensitive actions and money/review transitions leave an audit trail
- No secrets in audit payloads or logs

## Production reliability

- Idempotent mutations; bounded retries; outbox co-commit with state
- Leases reclaim on failure; no stranded work without recovery
- No TODO / mock success / swallowed errors on shipped paths

## Escalation trigger

Any design that weakens the above → `/ceo` immediately; add `/security-auditor`
and `/postgresql-expert` when isolation or authz/RLS is involved.
