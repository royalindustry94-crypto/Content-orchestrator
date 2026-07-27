# Data architecture — models, migrations, RLS, transactions

## Workspace scoping

- Tenant-owned tables **must** include `workspace_id` (UUID FK to `workspaces`).
- Prefer `WorkspaceScopedMixin` from `apps/api/app/db/base.py` so the column cannot be forgotten.
- Queries that load tenant data must be workspace-constrained in application predicates **and** rely on RLS as the backstop — never “app checks only.”

## FORCE RLS

For every new tenant-owned table:

1. `ENABLE ROW LEVEL SECURITY`
2. `FORCE ROW LEVEL SECURITY` (owner cannot accidentally bypass in app paths)
3. `grant_runtime(...)` with least privilege
4. Explicit policies (`policy_select_members`, insert/update role policies as needed)
5. Adversarial tests as `app_runtime` with `request.jwt.claim.sub` set:
   - member of A sees A’s rows
   - outsider sees zero
   - forbidden writes fail

Tables that are service-role-only (e.g. secrets/credentials) may have **zero** runtime grants — document that choice; still FORCE RLS if the table is workspace-scoped.

## Models & constraints

Review for:

- Correct nullability and defaults (no silent null that means “failed”)
- Check constraints for status machines / numeric bounds
- Unique constraints for idempotency natural keys
- FKs with deliberate `ON DELETE` behavior
- Append-only tables: `prevent_update` / `prevent_delete` triggers where required
- Version columns + triggers for optimistic concurrency on mutable aggregates

## Indexes

- Partial indexes for hot queues (e.g. PENDING claims, in-flight by provider)
- Avoid redundant indexes; justify each in design/migration comments
- Claim/order indexes must match actual `ORDER BY` / filter predicates

## Migrations (Alembic)

| Required | Detail |
|---|---|
| Forward | `upgrade()` complete, deterministic |
| Backward | `downgrade()` real (or explicit one-way ADR with expand/contract plan) |
| Replay | Fresh DB `upgrade head` succeeds |
| Roundtrip | `head → parent → head` for new revisions |
| Data | Expand/contract for breaking changes; never strand production rows |

Reject “fix it in prod SQL” as the primary change mechanism.

## Transaction boundaries

Architect must verify:

- State change + outbox emit (+ audit row) commit **together** or not at all
- Lock order is consistent (avoid deadlocks: e.g. worker row then assignment, or budget then assignment — document the order)
- `SKIP LOCKED` used where multiple workers/schedulers partition work
- `SELECT … FOR UPDATE` used where dual check-then-act would race (spend caps, budgets)
- Long transactions do not hold locks across external provider I/O

## Spend & review data paths

- `spend_caps` / reservations / logs remain the financial control plane
- `review_gates` / review decisions remain the human control plane
- Recovery and reaper paths must not skip review or invent spend

## Rollback plans

Architectural data changes require one of:

1. Alembic downgrade that restores prior shape, or
2. Documented expand/contract with feature flag fail-closed, or
3. Explicit `/ceo` acceptance of irreversible migration + backup/restore procedure
