# Milestone 4 — Migration Parity & Verification Report

## Scope

Static re-verification of migrations 0014–0020 against their SQLAlchemy
models: table names, columns/types, nullability, defaults, foreign keys,
unique constraints, indexes, enum values, cascade behavior, and
upgrade/downgrade correctness. Plus targeted fixes for defects this pass
surfaced.

**Method:** direct inspection of migration DDL against model column
definitions (`sed`/`grep`-extracted blocks compared side by side) and a
programmatic diff of table names and enum values. This is static
verification, not execution — see the companion note on why a live
Postgres run wasn't possible in this environment.

## Defects found and fixed during this pass

| # | Defect | Where | Fix |
|---|---|---|---|
| 1 | `WorkflowDefinition` used `ActorMixin` (created_by + updated_by), but the migration and the table's immutability trigger mean it never has `updated_by` — the column didn't exist in the DB at all | `app/models/workflow.py` | Changed to `CreatedByMixin` (created_by only), matching the migration and the table's immutable-per-version nature |
| 2 | `WorkflowStage.backoff_multiplier` type-hinted `Mapped[float]` over an `Integer` column — misleading, would silently truncate a fractional value if ever set | `app/models/workflow.py` | Corrected the hint to `Mapped[int]`, matching the actual column type in both migration and model |
| 3 | `OutboxEvent` uses `VersionMixin` (whose trigger requires `updated_at`), but no `updated_at` column was mapped at all, though the migration creates one | `app/models/events.py` | Added the missing `updated_at` mapped column |
| 4 | `spend_reservations.pipeline_run_id` (added in 0020) had no `ON DELETE` clause — default `RESTRICT` — which would make a workspace/pipeline_run deletion fail with a FK violation whenever an open reservation exists, breaking the "workspace purge is a single delete" guarantee | `alembic/versions/0020_spend_reservation_run_link.py`, `app/models/spend.py` | Added `ON DELETE CASCADE` to both the migration and the model's FK |
| 5 | `dispatcher.dispatch_stage` never checked `workspace_concurrency_limits.max_concurrent_assignments` — the back-pressure cap existed in schema but wasn't enforced anywhere | `app/orchestration/dispatcher.py` | Added an in-flight-assignment count check before worker selection; over-cap dispatch returns `None` (stage stays unscheduled, retried later — nothing dropped) |
| 6 | `scheduler.process_leased_job`'s "no eligible worker" path rescheduled the job every 15s with no bound — genuinely unbounded if a stage's worker never registers | `app/orchestration/scheduler.py` | Added exponential backoff (capped) and a `NO_WORKER_MAX_RETRIES` ceiling; exceeding it dead-letters the job instead of looping forever |

All six were caught by re-reading migration DDL against model definitions
line by line, not by running anything — worth stating plainly since it
means they're a real-but-partial safety net: logic errors that don't
show up as a name/type/constraint mismatch (e.g. a wrong `WHERE` clause,
a race condition) are NOT caught by this method. Only execution against
real Postgres and concurrent load would catch those.

## Table-by-table parity (0014–0020, post-fix)

All 12 new M4 tables plus the one M3 table amendment (`spend_reservations.
pipeline_run_id`) verified column-for-column: name, SQL type, nullability,
default, and (where applicable) enum values, unique constraints, and FK
target/cascade — **all consistent between migration DDL and ORM model**
after the six fixes above.

| Table | Columns match | Enum values match | Indexes/constraints present | Cascade behavior correct |
|---|:---:|:---:|:---:|:---:|
| workflow_definitions | ✓ (after fix #1) | n/a | ✓ | ✓ |
| workflow_stages | ✓ (after fix #2) | ✓ (content_stage, reused) | ✓ | ✓ |
| workflow_transitions | ✓ | ✓ workflow_transition_trigger | ✓ | ✓ |
| outbox_events | ✓ (after fix #3) | ✓ outbox_event_status | ✓ | n/a (no FK cascade concern beyond workspace_id) |
| event_consumers | ✓ | n/a | ✓ | n/a (not tenant-scoped) |
| consumer_checkpoints | ✓ | n/a | ✓ | ✓ |
| job_schedule | ✓ | ✓ job_type, job_schedule_status | ✓ | ✓ |
| workspace_concurrency_limits | ✓ | n/a | ✓ | ✓ |
| worker_registry | ✓ | ✓ worker_status | ✓ | ✓ (not tenant-scoped by design) |
| worker_heartbeats | ✓ | ✓ worker_status (reused) | ✓ | ✓ |
| stage_assignments | ✓ | ✓ stage_assignment_status | ✓ | ✓ |
| review_gates | ✓ | ✓ review_gate_status | ✓ | ✓ |
| spend_reservations.pipeline_run_id (0020) | ✓ | n/a | ✓ | ✓ (after fix #4) |

## Upgrade/downgrade symmetry

Verified programmatically (regex diff of `CREATE`/`DROP` pairs across
`upgrade()`/`downgrade()`): all 7 migrations (0014–0020) are symmetric —
every table, type, and column created in `upgrade()` has a matching drop
in `downgrade()`. One intentional, documented asymmetry: migration 0014's
`ALTER TYPE pipeline_run_status ADD VALUE` calls cannot be reversed
(Postgres does not support dropping enum values), so `'created'`,
`'paused'`, `'compensating'` remain in the type after a downgrade — noted
in the migration's `downgrade()` as a harmless no-op, not silently
dropped from documentation.

## Known-issue found but NOT fixed (out of this pass's authority)

`spend_logs.content_item_id` and `spend_reservations.content_item_id`
(both from **M3**, already CEO-accepted) have the same missing-cascade
pattern as defect #4 above — no `ON DELETE` clause. Per the practice
established this session (accepted migrations are not edited after
acceptance), this was **not** silently patched. Flagged here for your
decision: fix via a new additive migration, or accept as-is (a
content_item deletion while spend history references it would currently
fail rather than cascade — arguably the *safer* default for financial
records, so this may be intentional rather than a defect; worth a
deliberate call either way).
