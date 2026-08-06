# Backend testing standards

## Environment

- Real PostgreSQL (CI service / local), not mocked RLS.
- `ENVIRONMENT=test`, test DSNs, `NullPool` as configured in `app/db/session.py`.
- Apply migrations: `alembic upgrade head` before suites.

## Layers

| Layer | What to prove |
|---|---|
| Unit | Pure functions deterministic with injectable clocks |
| Integration | Routes + DB + auth; worker machine flows |
| Adversarial | Cross-tenant SELECT empty; forbidden writes fail; authz 403 |
| Concurrency | Two sessions racing claim/spend/lease → single winner |

## Practices

- `pytest -W error` (warnings are failures).
- Unique UUIDs per test; scope cleanup to the test workspace when shared DB pollution is possible.
- Park/cancel unrelated pending jobs when testing scheduler fairness.
- Prefer API-level tests for auth matrices; call orchestration directly for lock/clock control.
- Assert durable signals: outbox event types, audit ledger rows, status enums — not just HTTP 200.

## Required with certain changes

| Change | Required tests |
|---|---|
| New tenant table / RLS policy | Adversarial runtime role probes |
| Claim / lease / recovery | Race + expiry + idempotent replay |
| Spend | Cap hold + concurrent reservation |
| Migration | Columns/tables exist; optional roundtrip test |

## Anti-patterns

- Mocking away Postgres for RLS tests
- Sleep-based flake timing (use injectable `now=`)
- Asserting only happy path for security code
- Leaving `pytest.mark.skip` on production-critical coverage without CEO/Architect acknowledgment
