# Test quality bars

## Reject as final proof

- SQLite or in-memory stand-ins for RLS/acceptance
- Mocks that skip Postgres policies or locks
- Assertions of HTTP 200/201 **only** with no DB/state verification
- `pytest.mark.skip` / `xfail` on critical security/isolation/money paths without CEO-accepted residual
- Order-dependent tests that pass only in full-suite order
- Flaky timing tests without injectable `now=`
- Tests named for coverage but asserting `assert True` / trivial constants

## Require

- Real PostgreSQL after `alembic upgrade head`
- `pytest -W error` for final backend validation
- Unique workspace/user fixtures (no cross-test pollution); scoped cleanup
- Parallel sessions for concurrency proofs
- Regression test per defect (fails before fix narrative documented)

## Inspect existing suite

Before trusting green:

```bash
cd apps/api && python3 -m pytest -W error -q --collect-only
# hunt skips/xfails
rg -n "pytest.mark.(skip|xfail)" apps/api/tests apps/worker apps/web
```

Record skipped/xfailed totals in the report. Critical-path skips ⇒ **FAILED** or **NOT VERIFIED**.
