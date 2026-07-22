# Milestone 4 — Verification Status

## Why this document exists

The CEO directive required: run the complete test suite against real
PostgreSQL, capture exact commands and pass/fail totals, and explicitly
forbade claiming production readiness without that execution. This
document reports what was and wasn't possible to do honestly, in this
build environment.

## Environment constraint (confirmed this session)

```
$ which psql pg_ctl postgres
(no output — none installed)
$ python3 -c "import sqlalchemy"
ModuleNotFoundError: No module named 'sqlalchemy'
$ curl https://pypi.org
Host not in allowlist: pypi.org. Add this host to your network egress settings to allow access.
```

This sandbox has no network egress and no Postgres instance. It has been
this way for every milestone in this project — flagged at M2, M3, and
now M4. There is no way to install SQLAlchemy/asyncpg/pytest or start
Postgres here, and therefore no way to execute the test suite in this
environment.

## What WAS done (real, static verification)

- Every `.py` file added or modified compiles cleanly
  (`python3 -m py_compile`), re-checked after every change.
- Migrations 0014–0020 re-verified against their SQLAlchemy models
  column-by-column (names, types, nullability, defaults, FKs, unique
  constraints, indexes, enum values, cascade behavior) — 6 real defects
  found and fixed; see `docs/milestone-4-migration-parity-report.md`.
- Upgrade/downgrade symmetry verified programmatically for all 7
  migrations.
- Repository quality checks run via static analysis (grep-based, since
  no linter/type-checker is installed here either): no TODO/FIXME/
  placeholder markers, no committed `.env` or hardcoded secrets, no bare
  `except: pass`, `.gitignore` covers generated artifacts.
- Two regression tests written for the two self-caught defects (spend
  reservation scoping, controller self-triggering loop) — one of them
  (`test_regression_stage_completed_is_not_registered_as_a_controller_
  consumer`) is a structural check that doesn't need a database at all
  and could, in principle, run right now if pytest were installed.

## What was NOT done (and why)

**The test suite has not been executed.** Not against SQLite, not
against Postgres, not at all, anywhere, in this session. No fabricated
pass/fail numbers are given below — there are none to give.

**Concurrency-sensitive behavior (directive step 4) is unverified by
execution.** Each mechanism was checked by code review, not by running
concurrent load:

| Behavior | Verified by | NOT verified by |
|---|---|---|
| Transactional outbox atomicity | Code review: `emit()` never calls commit itself, uses the caller's session | An actual rollback-then-check test running against Postgres |
| Per-aggregate event ordering | Code review: `pg_advisory_xact_lock` + `MAX(sequence)+1` pattern is a known-correct Postgres idiom | Concurrent emitters actually racing against a live DB |
| Duplicate-event protection | Code review: `event_id` PK + checkpoint comparison | A real redelivery scenario |
| Concurrent scheduler leasing | Code review: `FOR UPDATE SKIP LOCKED` is the standard correct pattern | Two scheduler processes actually racing on the same rows |
| Workspace fairness | Unit-test logic written (`test_scheduler_fairness_caps_per_workspace_per_tick`) | The test executing |
| Back-pressure enforcement | Unit-test logic written (`test_dispatcher_enforces_max_concurrent_assignments_back_pressure`) | The test executing |
| Worker lease expiry/reaping | Unit-test logic written (dispatcher + scheduler reaper tests) | The tests executing |
| Lost acknowledgement recovery | Same mechanism as lease expiry (ack-timeout is a lease with a short TTL) — code review only | Execution |
| Retry and dead-letter behavior | Unit-test logic written (`test_stage_failure_retries_then_dead_letters_after_max_attempts`) | The test executing |
| Idempotent result submission | `idempotency_key` unique index + `dispatch_stage`'s existing-row check, code review only | Execution under concurrent duplicate submission |

`pg_advisory_xact_lock` in particular is a mechanism that is easy to get
subtly wrong (lock scope, release timing) and genuinely needs a real
concurrent-transaction test to trust — code review is necessary but not
sufficient here, and I want that stated plainly rather than implied to be
equivalent to a passing test run.

## Exact commands to run when Postgres/network access exists

```bash
# 1. Start Postgres (local dev)
docker compose up -d postgres

# 2. Install dependencies
cd apps/api
pip install -e ".[dev]"

# 3. Apply all migrations (0001-0020)
alembic upgrade head

# 4. Run the full test suite
pytest -v

# 5. Run only the Milestone 4 orchestration suite
pytest -v tests/test_orchestration_outbox.py \
          tests/test_orchestration_workflow.py \
          tests/test_orchestration_scheduler_dispatcher.py \
          tests/test_reference_worker_client.py \
          tests/test_regression_defects.py

# 6. Concurrency-specific: run the scheduler/dispatcher leasing tests
#    under pytest-xdist or a manual concurrent harness to actually
#    exercise FOR UPDATE SKIP LOCKED racing, which single-process pytest
#    does not exercise even when it passes:
pip install pytest-xdist --break-system-packages
pytest -n 4 tests/test_orchestration_scheduler_dispatcher.py
```

CI (`.github/workflows/ci.yml`) already runs steps 1–4 (via a Postgres
service container) on every push — that is the actual first execution
this code will get. Step 6 (genuine concurrent-load testing) is not yet
in CI and would need to be added as a follow-up if scheduler/dispatcher
correctness under real contention needs continuous verification rather
than a one-time manual check.

## Bottom line

Milestone 4 is implemented and statically verified to the extent this
environment allows. **It is not claimed production-ready, and Milestone
4 is not marked complete**, per the directive. The gate to close is:
run the commands above against real Postgres, fix whatever they surface,
and report actual pass/fail totals — none of which has happened yet.
