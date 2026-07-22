# Milestone 4 — Final Verification Report

Produced under the directive to separate what was personally confirmed
in this sandbox from what requires infrastructure this sandbox doesn't
have. No execution results are fabricated or implied anywhere below.

## Environment (re-confirmed this turn)

No `psql`/Postgres, no installable Python packages, no network egress
(`pypi.org` unreachable). No ruff/mypy/black installed or installable.
This has not changed and cannot change within this sandbox.

---

## VERIFIED (personally confirmed within the sandbox)

- **Compilation**: every `.py` file in `apps/api` and `apps/worker`
  compiles cleanly (`python3 -m py_compile`), re-checked after every
  edit made this session.
- **No TODO/FIXME/XXX markers** anywhere in `apps/api/app`,
  `apps/api/alembic/versions`, `apps/api/tests`, `apps/worker/worker`.
- **No placeholder code**: the two grep hits for "placeholder" are both
  comments explicitly documenting the *absence* of placeholders, not
  placeholder code itself.
- **No mocked orchestration logic**: zero occurrences of mock/fake/stub
  in `app/orchestration`, `worker/client.py`, or `app/models`, outside
  one comment describing what is *not* stubbed.
- **No silent exception swallowing**: every `except` block in the
  orchestration package and its dependencies does real work (log +
  reraise, rollback, route to DLQ). The one `except Exception` in
  `relay.py` is documented (`# noqa: BLE001` with rationale) and never
  discards the error — it logs, increments a bounded attempt counter,
  and DLQs on exhaustion.
- **No unbounded retries**: `retry.compute_backoff_seconds` always caps
  at `max_seconds`; `controller.handle_stage_failure` checks
  `attempt_number < stage_def.max_attempts` before retrying, else
  dead-letters; `scheduler`'s "no eligible worker" reschedule loop is
  capped at `NO_WORKER_MAX_RETRIES` (fixed this session — was previously
  unbounded); review-gate escalation has exactly one escalation level
  before a terminal outcome.
- **Workspace scoping**: every M4 tenant table has `workspace_id NOT
  NULL` except two deliberately-documented exceptions —
  `worker_registry` (a worker may serve multiple/all workspaces) and
  `event_consumers`/`consumer_checkpoints` (process-level registries,
  not tenant data). Global-scan queries in the scheduler/reaper are
  correct-by-design (a shared scheduler must see all workspaces' due
  work; per-workspace fairness is applied after the scan, in Python).
  Controller queries that don't carry an explicit `workspace_id`
  predicate transitively scope through a workspace-unique FK
  (`pipeline_run_id`, `definition_id`) — verified no query returns
  rows outside the caller's intended workspace by construction.
- **Secrets audit**: no `.env` committed, no hardcoded secret-shaped
  values in source, `.gitignore` covers `.env`/`__pycache__`/`*.pyc`,
  and `git ls-files` confirms none are actually tracked.
- **Unused imports**: found and removed 3 genuinely-unused imports
  (`relay.py`: `datetime`, `timezone`; `client.py`: `asyncio`,
  `timedelta`) — each verified to have zero other occurrence in its file
  before removal.
- **Line length**: found 61 lines exceeding the project's own configured
  `ruff line-length = 100` (`apps/api/pyproject.toml`). 41 wrapped and
  verified to still compile after every change. **20 remain** — not
  safely auto-wrappable without a real formatter or manual literal
  restructuring; listed below rather than hidden.
- **Migration/model parity** (0014–0020): re-verified column-by-column
  against models; 6 real defects found and fixed (full detail in
  `docs/milestone-4-migration-parity-report.md`), re-confirmed clean
  after fixes.
- **Migration upgrade/downgrade symmetry**: verified programmatically
  for all 7 migrations — every `CREATE`/`ADD COLUMN` has a matching
  `DROP` in `downgrade()`, with one documented, unavoidable exception
  (Postgres cannot drop enum values added via `ALTER TYPE ADD VALUE`).
- **Design document**: "CEO Amendments Incorporated" section exists
  (confirmed present at commit `b31363c`, re-read this turn), covering
  all four required points: trace_id/correlation_id propagation,
  back-pressure/workspace fairness, operational metrics,
  workflow-definition versioning.

### Remaining lines over 100 chars (honest, not hidden)

```
apps/api/app/orchestration/controller.py:107, 119, 162, 191, 420, 429, 441, 443, 454, 485, 514, 555, 581, 593
apps/api/app/orchestration/dispatcher.py:78, 81, 185, 202
apps/api/app/orchestration/metrics.py:79
apps/worker/worker/client.py:164
```
20 lines, all in the 101–118 char range. None affect compilation or
correctness. Closing this fully needs `ruff format` run for real, or
careful manual restructuring of dict-literal/call-argument lines that
don't have a single safe comma-break point.

---

## NOT VERIFIED (requires PostgreSQL, external packages, or network access)

- Migrations 0001→0020 have **not** been executed against any database —
  clean upgrade, clean downgrade, absence of forks/drift are all
  **unconfirmed by execution**. Static chain-linkage and DDL/model parity
  were checked (see VERIFIED above); actual `alembic upgrade head` /
  `alembic downgrade base` have not run.
- **No test has executed.** Not one, anywhere, this session. Unit,
  integration, end-to-end, migration, concurrency, and the two
  regression tests are all written and confirmed to compile — none has
  produced a pass/fail result.
- **Concurrency-sensitive behavior is unverified by execution**:
  transactional outbox atomicity, per-aggregate event ordering,
  duplicate-event protection, scheduler leasing races, workspace
  fairness under real load, back-pressure enforcement under real load,
  worker lease expiry/reaping under real load, lost-acknowledgement
  recovery, retry/dead-letter behavior under real load, idempotent
  result submission under concurrent duplicate calls. All are supported
  by code review (documented mechanism-by-mechanism in
  `docs/milestone-4-verification-status.md`) but code review is not a
  substitute for running them, especially `pg_advisory_xact_lock`
  behavior and `FOR UPDATE SKIP LOCKED` races, which are exactly the
  kind of thing that looks right on paper and needs real concurrent
  transactions to trust.
- **ruff/mypy/black have not run.** The line-length and unused-import
  fixes above were done by direct inspection against the project's own
  configured rule, not by invoking the actual linter/type-checker. Real
  ruff/mypy output could surface issues this manual pass cannot see
  (import ordering, type errors, other style rules beyond line length).

---

## Remaining production-readiness checklist

Everything below is the actual gate — nothing further is achievable
inside this sandbox:

1. `docker compose up -d postgres && cd apps/api && pip install -e ".[dev]" && alembic upgrade head` — confirm clean, no errors.
2. `alembic downgrade base` then `alembic upgrade head` again — confirm round-trip works.
3. `pytest -v` — capture the real pass/fail total. Fix any failure before proceeding.
4. `pip install ruff mypy && ruff check . && mypy app` — capture real lint/type output; fix findings.
5. `pytest -n 4 tests/test_orchestration_scheduler_dispatcher.py` (or an equivalent concurrent harness) — specifically exercise the leasing/advisory-lock races that single-process pytest doesn't stress.
6. Only after 1–5 pass: revisit the M3-era `spend_logs`/`spend_reservations.content_item_id` missing-cascade item flagged in the migration parity report (fix via new migration, or explicitly accept as intentional).
7. Decide the open item from the verification-status doc: what DB role/connection the scheduler/dispatcher/controller run as in production (system-level vs RLS-scoped) — currently unspecified.

## Git commit hash

`6a35625` (quality pass — unused imports + line-length), on top of
`b31363c` (verification docs) → `ca44733` (M4 implementation) → `c438bfc`
(M4 design). All in this turn's packaged repository.

## Repository package

Attached: `content-orchestrator-m4-quality-pass.zip`, `.git` history
included.
