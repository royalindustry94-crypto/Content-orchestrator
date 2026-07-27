# Backend PR self-checklist

**Author:** Backend Engineer  
**PR / workstream:**

## Architecture

- [ ] No stack drift (FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Python workers)
- [ ] Escalated to `/chief-architect` if boundaries/SoT changed

## Tenancy & security

- [ ] `workspace_id` on new tenant tables/rows
- [ ] FORCE RLS + grants + policies
- [ ] Correct auth principal & guards
- [ ] No secrets in logs/audit/outbox

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
- [ ] Migrations upgrade + downgrade (or expand/contract plan)
- [ ] Performance/indexes considered for new queries

## Tests

- [ ] Unit / integration as needed
- [ ] Adversarial RLS if schema/policy changed
- [ ] `pytest -W error` green locally
- [ ] `ruff check` clean

## Docs

- [ ] Design exists for workstream production changes
- [ ] Impl/audit updated when required by milestone process
