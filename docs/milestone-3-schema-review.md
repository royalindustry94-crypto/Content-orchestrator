# Milestone 3 — Content Domain Schema Review

Produced before any migration, per standing instruction. Scope: database
architecture only — no generation pipelines, AI providers, publishing
logic, analytics processing, or background workers. This review is the
design; the migrations that follow implement exactly what's here.

Built on the accepted Milestone 2 foundation (profiles, workspaces,
workspace_memberships, RLS with FORCE + owner/runtime role separation,
`app_current_user_id()`).

## 0. Cross-cutting conventions

### 0.1 Audit columns

Standard set: `created_at`, `updated_at`, `created_by`, `updated_by`.
Applied by table character, not blanket:

- `created_at` — every table.
- `updated_at` — every table that is UPDATEd after insert (i.e. mutable
  tables only; an immutable row's updated_at would always equal
  created_at and mislead).
- `created_by` / `updated_by` — nullable FKs to `profiles(id)`. NULL is a
  real value meaning "system/worker acted," not a blank. `created_by`
  appears where a specific actor causes the row; `updated_by` where more
  than one actor mutates it over time.

### 0.2 Concurrency (optimistic locking)

Mutable tables carry `version integer NOT NULL DEFAULT 1` and a shared
`BEFORE UPDATE` trigger (`set_version_and_updated_at()`) that increments
`version` and stamps `updated_at`. Writers use
`UPDATE ... WHERE id = :id AND version = :expected`; zero rows affected ⇒
stale read ⇒ conflict (surfaced by the service layer in a later
milestone). Immutable tables carry no `version`.

### 0.3 Soft deletion

`deleted_at timestamptz NULL` on user-facing business entities
(content_items, assets, publish_jobs, content_pillars,
provider_credentials). RLS SELECT policies exclude soft-deleted rows.
Immutable event tables are never soft-deleted (a deleted history row
would falsify the record). Purely operational tables (spend_reservations,
dead_letter_jobs) are hard-delete eligible on a retention schedule.
Unique constraints on soft-deletable tables are partial
(`WHERE deleted_at IS NULL`) so a deleted row's name can be reused.

### 0.4 Immutability enforcement

Immutable tables get a `BEFORE UPDATE` trigger (`prevent_update()`) that
raises — immutability is enforced by the database, not convention.
DELETE is not blocked, so `ON DELETE CASCADE` still works for a genuine
workspace/content purge. Immutable set: content_versions,
pipeline_stage_runs, review_decisions, analytics_snapshots, spend_logs,
provider_usage.

### 0.5 Tenancy

Every table carries `workspace_id NOT NULL` (FK → workspaces, ON DELETE
CASCADE) and full RLS (ENABLE + FORCE), even child tables that could
reach workspace via a join — so every policy is a direct workspace_id
check, never a recursive join. Runtime traffic connects as the non-owner
`app_runtime` role from M2.

## 1. Tables (16) and relationships

```
workspaces (M2)
 ├─ content_pillars           mutable, soft-delete
 ├─ spend_caps                mutable
 ├─ provider_credentials      mutable, soft-delete, ADMIN-ONLY
 ├─ provider_usage            immutable
 ├─ spend_logs                immutable
 ├─ spend_reservations        mutable, hard-delete eligible
 ├─ webhook_events            mutable (status), system-written
 ├─ dead_letter_jobs          mutable (status), hard-delete eligible
 └─ content_items             mutable, soft-delete   (pillar_id → content_pillars)
      ├─ content_versions     immutable   (content_items.current_version_id ⇒ back-ref)
      ├─ pipeline_runs        mutable     (content_items.current_pipeline_run_id ⇒ back-ref)
      │    └─ pipeline_stage_runs   immutable, append-per-attempt
      ├─ assets               mutable, soft-delete   (→ content_versions optional)
      ├─ publish_jobs         mutable, soft-delete
      ├─ review_decisions     immutable   (→ content_versions, → profiles reviewer)
      └─ analytics_snapshots  immutable
```

Two deferred self-referential cursors on content_items, added after their
targets exist: `current_version_id → content_versions(id)` and
`current_pipeline_run_id → pipeline_runs(id)`. Nullable (a fresh item has
neither); denormalized for fast "active script / current run" reads.

Required-table mapping: all 14 authorized tables are present.
`content_pillars` and `spend_caps` are added (v2-spec config the domain
needs — content_items.pillar_id and spend enforcement). `publish_jobs`
carries both scheduling intent and publish outcome (no separate schedule
table).

## 2. Pipeline: runs vs stage runs

`pipeline_runs` — one full pipeline execution for a content item; mutable,
holds the live cursor (`current_stage`), overall `status`, timing,
`version`. `pipeline_stage_runs` — immutable record of individual stage
attempts; one row per attempt, written once at completion, retries are new
rows (`attempt_number + 1`). Live "currently running stage" is the parent
run's cursor; a stage_run row exists only once its attempt has finished.
This satisfies both "optimistic versioning where mutable" (the run) and
"immutable history for pipeline execution" (the stage runs) without
contradiction.

## 3. State machines

**content_items.current_stage:** idea → scripting → voiceover → visuals →
rendering → seo → review → scheduled → published; review can route back to
an earlier stage on changes_requested (app decides which, later milestone).

**content_items.status** (orthogonal health): active → failed (terminal
stage failure) | archived (user action). Separate from stage so no
`visuals_failed`/`rendering_failed` enum explosion.

**pipeline_runs.status:** running → succeeded | failed | cancelled.

**pipeline_stage_runs.status** (terminal-only): succeeded | failed.

**publish_jobs.status:** pending → publishing → published | failed |
cancelled.

**review_decisions.decision** (each row immutable): approved |
changes_requested | rejected.

**webhook_events.status:** received → processed | failed | duplicate.

**dead_letter_jobs.status:** pending → resolved | discarded.

**spend_reservations.status:** reserved → committed | released.

**provider_credentials.status:** active → revoked (revoke also sets
deleted_at).

## 4. Indexing strategy

Principles: (a) index every FK used in lookups/cascades (Postgres doesn't
auto-index FKs); (b) lead RLS-predicate indexes with workspace_id;
(c) partial indexes `WHERE deleted_at IS NULL` on soft-deletable tables.

- content_pillars: `uq (workspace_id, name) WHERE deleted_at IS NULL`; `ix (workspace_id)`
- spend_caps: `uq (workspace_id, COALESCE(provider,''))`
- provider_credentials: `uq (workspace_id, provider, label) WHERE deleted_at IS NULL`; `ix (workspace_id)`
- content_items: `ix (workspace_id, current_stage) WHERE deleted_at IS NULL`; `ix (workspace_id, pillar_id) WHERE deleted_at IS NULL`; `ix (workspace_id, status) WHERE deleted_at IS NULL`
- content_versions: `ix (content_item_id, created_at DESC)`; `ix (workspace_id)`
- pipeline_runs: `ix (content_item_id, created_at DESC)`; `ix (workspace_id, status) WHERE status = 'running'`
- pipeline_stage_runs: `uq (pipeline_run_id, stage, attempt_number)`; `ix (pipeline_run_id, stage)`; `ix (workspace_id, status)`
- assets: `ix (content_item_id, type) WHERE deleted_at IS NULL`; `ix (workspace_id)`
- publish_jobs: `ix (workspace_id, scheduled_time) WHERE deleted_at IS NULL`; `ix (workspace_id, status)`; `ix (content_item_id)`
- review_decisions: `ix (content_item_id, created_at DESC)`; `ix (workspace_id)`
- analytics_snapshots: `ix (content_item_id, metric, captured_at DESC)`; `ix (workspace_id, captured_at DESC)`
- spend_logs: `ix (workspace_id, occurred_at DESC)`; `ix (workspace_id, provider, occurred_at DESC)`
- spend_reservations: `ix (workspace_id, status) WHERE status = 'reserved'`
- provider_usage: `ix (workspace_id, provider, occurred_at DESC)`; `ix (content_item_id) WHERE content_item_id IS NOT NULL`
- webhook_events: `uq (source, external_event_id)`; `ix (status) WHERE status IN ('received','failed')`; `ix (workspace_id)`
- dead_letter_jobs: `ix (workspace_id, status) WHERE status = 'pending'`; `ix (related_table, related_id)`

## 5. Concurrency model summary

Mutable + versioned: content_items, content_pillars, spend_caps, assets,
publish_jobs, pipeline_runs, spend_reservations, provider_credentials,
webhook_events, dead_letter_jobs. Immutable (no version, prevent_update
trigger): content_versions, pipeline_stage_runs, review_decisions,
analytics_snapshots, spend_logs, provider_usage.

## 6. provider_credentials — sensitive handling

Stores ciphertext only: `encrypted_secret` (text) + `encryption_key_id`
(text, key reference for envelope encryption/rotation). No plaintext
column ever. Encryption itself is a later-milestone concern; the schema is
shaped so a raw secret cannot be stored. RLS is admin-only for all
operations — editors/reviewers never see credential rows, even ciphertext.

## 7. Deletion strategy summary

Soft delete: content_items, assets, publish_jobs, content_pillars,
provider_credentials. Immutable (no delete except cascade purge):
content_versions, pipeline_stage_runs, review_decisions,
analytics_snapshots, spend_logs, provider_usage. Hard-delete eligible:
spend_reservations, dead_letter_jobs (and webhook_events on retention).
ON DELETE CASCADE from workspaces and content_items down to children.

## 8. RLS strategy

New helper `app_user_has_workspace_role(workspace_id, roles[])` (STABLE)
so policies aren't copy-pasted membership subqueries. Pattern per table:
SELECT for members with an allowed role (+ `deleted_at IS NULL` on
soft-deletables); INSERT/UPDATE for write-authorized roles.
provider_credentials is admin-only. System-written tables (pipeline_runs,
pipeline_stage_runs, spend_logs, spend_reservations, provider_usage,
analytics_snapshots, webhook_events, dead_letter_jobs) get member SELECT
but no end-user write policy — those are written by the future worker/
service role, deferred with the worker, not stubbed now.

## 9. Authorization matrix (extends M2)

| Action | admin | editor | reviewer |
|--------|:-----:|:------:|:--------:|
| Read content/versions/assets/runs/publish/analytics | ✓ | ✓ | ✓ |
| Create/update content_items, assets, publish_jobs | ✓ | ✓ | ✗ |
| Manage content_pillars | ✓ | ✓ | ✗ |
| Submit review_decisions | ✓ | ✗ | ✓ |
| Read spend_logs/reservations/caps, provider_usage | ✓ | ✓ | ✓ |
| Manage spend_caps | ✓ | ✗ | ✗ |
| Read/manage provider_credentials | ✓ | ✗ | ✗ |
| Read webhook_events, dead_letter_jobs | ✓ | ✓ | ✗ |

## 10. Migration order

Each migration creates its tables with RLS, indexes, constraints, and
triggers inline — no table without its access control in the same
migration.

1. `0002_shared_helpers` — set_version_and_updated_at(), prevent_update(),
   app_user_has_workspace_role(). No tables.
2. `0003_workspace_config` — content_pillars, spend_caps,
   provider_credentials.
3. `0004_content_core` — content_items, content_versions (+ deferred
   current_version_id FK).
4. `0005_pipeline` — pipeline_runs, pipeline_stage_runs (+ deferred
   current_pipeline_run_id FK).
5. `0006_assets` — assets.
6. `0007_publishing` — publish_jobs.
7. `0008_review` — review_decisions.
8. `0009_analytics` — analytics_snapshots.
9. `0010_spend` — spend_logs, spend_reservations.
10. `0011_provider_usage` — provider_usage.
11. `0012_webhooks_dlq` — webhook_events, dead_letter_jobs.

## 11. Out of scope (by directive)

No generation pipelines, AI providers, publishing logic, analytics
processing, or background workers. ORM models are included because in a
SQLAlchemy project the models are the schema definition Alembic autogenerate
compares against; they carry column/relationship mappings only, no logic.

## 12. Post-approval amendments (migration 0013)

Four CEO-approved additions, applied as an additive migration (0013) on
top of 0002–0012 rather than editing them:

1. **Idempotency keys** — `idempotency_key text` on `pipeline_runs`,
   `publish_jobs`, and `webhook_events`, each with a partial unique index
   `(workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL`.
   Nullable, so non-idempotent inserts still work; when supplied, a retried
   request can't create a duplicate. For webhook_events this complements the
   existing `(source, external_event_id)` uniqueness — that dedupes on the
   provider's event id, `idempotency_key` dedupes on our own submitter's key.

2. **Content lineage** — a dedicated immutable `content_lineage` table
   (parent_content_item_id, child_content_item_id, relationship_type ∈
   {translated, remixed, clipped, derived}), not a self-FK on
   content_items. A table lets one source fan out to many derivatives, each
   edge typed. Guards: `CHECK (parent <> child)` and
   `UNIQUE (parent, child, relationship_type)`. Immutable (an edge is a
   fact), member-read / editor-write RLS.

3. **Asset storage metadata** — `assets` gains `storage_provider`,
   `storage_bucket`, `storage_object_key`, `checksum`,
   `checksum_algorithm`, `mime_type`, `size_bytes` (all nullable; a pending
   asset has no stored object). Provider-agnostic source of truth for the
   stored object and integrity checks; `url` remains a resolved/public URL.

4. **Extensible provider metadata** — `provider_metadata jsonb` on
   `pipeline_stage_runs`, `provider_usage`, `spend_logs`, and `assets`, for
   provider-specific response fields without a column per provider. Core
   columns stay normalized.

Immutability note: the three immutable tables gaining `provider_metadata`
(pipeline_stage_runs, provider_usage, spend_logs) carry the
`prevent_update()` trigger. `ADD COLUMN ... jsonb` with **no default** is a
metadata-only change in Postgres (no row rewrite, no per-row UPDATE), so it
does not trip the trigger. A future column with a non-null default on those
tables would force a table rewrite and must instead be added nullable then
backfilled, or the trigger temporarily detached under review.
