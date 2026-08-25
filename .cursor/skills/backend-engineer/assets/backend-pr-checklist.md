# Backend PR self-checklist

**Author:** Backend Engineer  
**PR / workstream:**

## Authority gates

- [ ] No unapproved architecture change (else `/chief-architect` APPROVE on record)
- [ ] No new/changed schema/RLS/migration without `/postgresql-expert` APPROVE on record
- [ ] Not claiming VERIFIED (CEO + evidence only)
- [ ] Not merging

## Architecture

- [ ] No stack drift (FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Python workers; React+TS contracts intact)
- [ ] Escalated to `/chief-architect` if boundaries/SoT changed

## Tenancy & security

- [ ] `workspace_id` on new tenant tables/rows
- [ ] FORCE RLS + grants + policies (PG expert designed)
- [ ] Correct auth principal & guards
- [ ] No secrets in logs/audit/outbox
- [ ] Security review requested/completed

## Correctness

- [ ] Idempotency keys / unique constraints / replay behavior documented in code or tests
- [ ] Retries bounded with backoff where appropriate
- [ ] Transactions co-commit state + outbox
- [ ] Lock order safe; races tested if relevant

## Control planes

- [ ] Human Review Gate intact
- [ ] Spend controls intact
- [ ] Audit logging for sensitive mutations

## Quality

- [ ] No TODO/FIXME/placeholder/silent failure on in-scope paths
- [ ] Complete error handling + structured logging
- [ ] Migrations upgrade + downgrade (or expand/contract plan) per PG notes
- [ ] Performance/indexes considered for new queries

## Tests / QA

- [ ] Unit / integration as needed
- [ ] Adversarial RLS if schema/policy changed (real Postgres — not SQLite/mocks)
- [ ] `pytest -W error` green locally
- [ ] `ruff check` clean
- [ ] QA sign-off recorded

## Docs / evidence

- [ ] Design exists for workstream production changes
- [ ] Impl/audit updated when required
- [ ] Evidence pack: PR URL, SHA, CI URL, migration head, test counts
