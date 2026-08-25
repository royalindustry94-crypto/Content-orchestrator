# Schema design standards

## Table design

- Every tenant-owned table: `workspace_id uuid NOT NULL REFERENCES workspaces(id)` (ON DELETE per product rules — usually `CASCADE` for tenant data, never accidental cross-tenant orphans).
- Prefer SQLAlchemy mixins: `WorkspaceScopedMixin`, `TimestampMixin`, `VersionMixin`, `SoftDeleteMixin` as appropriate (`apps/api/app/db/base.py`).
- PKs: `uuid` with `gen_random_uuid()` (or app-assigned UUID) unless a natural key is the PK by design.
- Soft deletes: partial unique indexes `WHERE deleted_at IS NULL` when names must be unique among live rows.

## Types

| Domain | Required type | Reject |
|---|---|---|
| Money / cost | `numeric(p,s)` fixed (project uses `numeric(10,2)` for caps/costs) | `float`, `double precision`, `real` |
| Timestamps | `timestamptz` | `timestamp without time zone` |
| IDs | `uuid` | serial ints for new tenant aggregates (unless ADR) |
| Status | Postgres `ENUM` or text + CHECK — match existing enums | ad-hoc unchecked strings on critical machines |
| JSON docs | `jsonb` | `json` unless proven need |

## Constraints

- **FOREIGN KEY** for every real relationship; include `workspace_id` in composite FKs when the parent is tenant-scoped and children must not reference another workspace’s row.
- **UNIQUE** for idempotency natural keys (e.g. assignment idempotency, effect keys, budget `(workspace_id, provider)`).
- **CHECK** for bounds (`priority_tier` 0–10, `max_concurrent > 0`, queue hard ≥ soft).
- Partial **UNIQUE** / **INDEX** with `WHERE` for soft-delete and status-specific queues.

## Indexes

Design indexes from access paths:

- Claim queues: `(workspace_id, …) WHERE status = 'pending'`
- In-flight provider: `(workspace_id, provider) WHERE status IN (...)`
- Time-range reporting: `(workspace_id, provider, occurred_at)`

Every new hot `WHERE`/`ORDER BY` in orchestration should cite its supporting index in the migration comments.

## Immutability

Audit, spend logs, review decisions, recovery/claim ledgers:

- Prefer append-only tables
- `prevent_update` / `prevent_delete` triggers via migration helpers where required
- No “update in place” for financial facts — correct via compensating rows if needed

## SQLAlchemy 2.x alignment

- Models must match DB: nullability, enums (`values_callable`), server defaults.
- Never ship a model column without a migration (or vice versa) in the same change set.
