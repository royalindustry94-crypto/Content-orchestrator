# Architecture review protocol

Run this checklist for schema, boundary, stack, or control-plane changes.

## 1. Frame

- Change summary (1–3 sentences)
- Apps touched: `api` / `web` / `worker` / migrations / docs
- New dependencies? New tables? New network calls?

## 2. Stack & drift

- [ ] Stays on FastAPI, SQLAlchemy, Alembic, PostgreSQL, React, TS, Python workers
- [ ] No new SoT or unnecessary framework
- [ ] New dependency justified or rejected

## 3. Tenant isolation

- [ ] `workspace_id` on all new tenant tables
- [ ] FORCE RLS + least-privilege grants
- [ ] Policies match intended roles (admin/editor/reviewer)
- [ ] Adversarial RLS tests planned/present

## 4. Data design

- [ ] Constraints/indexes/FKs match access patterns
- [ ] Migration upgrade **and** downgrade (or expand/contract ADR)
- [ ] Immutability triggers where ledger/audit semantics apply
- [ ] Fresh replay considered

## 5. Transactions & locks

- [ ] Invariants hold inside one transaction where required
- [ ] Lock order documented
- [ ] No lock held across external I/O
- [ ] Outbox/audit co-committed with state

## 6. Boundaries

- [ ] HTTP at the edge; domain logic inward
- [ ] Dependency direction respected
- [ ] Auth principal correct for each route

## 7. Concurrency / idempotency / retries

- [ ] Hazards listed (`references/concurrency-and-correctness.md`)
- [ ] Mitigations implemented or required as CONDITIONAL
- [ ] Tests for races/retries named

## 8. Control planes

- [ ] Human Review Gate preserved
- [ ] Spend reservation/cap/hold architecture preserved
- [ ] No bypass “for workers” or “for recovery”

## 9. Production readiness

- [ ] No placeholders / fake success / unfinished prod paths
- [ ] No silent failures; explicit outcomes or durable signals
- [ ] Error handling fail-closed where safety demands

## 10. Compat, tests, rollback

- [ ] Backward compatible **or** explicit migration plan
- [ ] Test plan sufficient for architectural risk
- [ ] Rollback plan stated

## 11. Verdict

| Verdict | When |
|---|---|
| **APPROVE** | Architecture acceptable; list required `/postgresql-expert` and `/backend-engineer` follow-ups |
| **CONDITIONAL** | Proceed only if listed mitigations + specialist sign-offs land in the same PR |
| **REJECT** | Drift, isolation hole, control bypass, or unjustified complexity |
| **ESCALATE** | Security, integrity, tenant, financial, or maintainability risk needs `/ceo` |
| **DEFER_TO_PG** | Schema/RLS/SQL/locking depth must be decided by `/postgresql-expert` |
| **DEFER_TO_BACKEND** | Implementation detail belongs to `/backend-engineer` |

Record using `assets/architecture-review-template.md`.
If the decision is lasting, add an ADR via `assets/adr-template.md` into
`docs/architecture-decisions.md` **before** major implementation.

Architect APPROVE is **not** VERIFIED and **not** merge authority.
