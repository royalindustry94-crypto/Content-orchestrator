# Architecture Decisions

## Source-of-truth spec

`content_engine_app_spec_v2.md` + the Claude Project Instructions doc are
authoritative. `lovable_app_spec_369.md` ("TeslaFlow 369") was reviewed and
**rejected** — see below.

## Why the 369 spec was rejected

The 369 doc hard-codes Tesla 3-6-9 numerology into product constraints with
no engineering rationale: content pillars capped at 3, exactly 9 visuals per
video, keyword counts fixed at 3/6/9, publish times restricted to 3:00 /
6:00 / 9:00, batch sizes fixed at 3/6/9.

This directly conflicts with the real requirements:

- **Scale target** (v2 spec, carried into project instructions): up to
  **5** content pillars, 50 videos/day peak. Incompatible with a hard cap
  of 3 pillars.
- **Roles**: the mandatory Human Review Gate needs its own `reviewer` role
  (admin/editor/reviewer). The 369 spec only has admin/editor.
- **Configurability**: v2 explicitly states its numbers are defaults, not
  hard constraints. Every count in this system (pillars, visuals, keywords,
  batch sizes, schedule presets) is a configurable value, not a fixed one.

None of the 369 spec's constraints are implemented. If a future request
references "the 369 spec," confirm before building against it.

## Data store

Postgres only for v1 (structured data + logs/events). The 369 spec's
"potentially NoSQL for logs" suggestion was not adopted — no second
datastore without a concrete scale reason.

## Worker identity & authentication (Milestone 4 · Workstream 1)

Workers authenticate with **per-worker credentials** (`worker_credentials`
table), not a shared global token. Bearer format `<credential_id>.<secret>`;
the secret is a server-generated 256-bit random token stored only as a
SHA-256 hash and compared in constant time. Rationale: individual worker
identity (audit, kill switch per worker), zero-downtime rotation (old
credential gets a grace `expires_at` while a new one is issued), and no
single shared secret whose leak compromises the whole fleet. Failure modes
(unknown, malformed, revoked, expired, wrong secret) all return the same
401 so credential state cannot be enumerated.

**Soft deregistration**: worker rows are never hard-deleted. Deregistering
sets `deregistered_at` (+ offline, load 0, enforced by a DB check
constraint); re-registration revives the same row. History and heartbeat
FKs remain intact for audit.

**Server-driven liveness**: heartbeat timestamps are assigned server-side;
worker clocks are never consulted, so clock skew is irrelevant by
construction. Liveness (healthy/suspect/dead) is computed from
`last_heartbeat_at` on read; a background sweep flips stale workers to
OFFLINE with a single idempotent UPDATE. `status` (observation) is separate
from `drain` (admin intent) — registration never clears drain.

**RLS refinement**: `worker_registry` FORCE RLS — global workers visible to
any authenticated user, workspace-pinned workers to members only; no write
policies for `app_runtime` (all writes go through the service role).
`worker_heartbeats` readable only by workspace admins (telemetry is
operator-facing, not member-facing). `worker_credentials` has zero policies
and zero grants — service-role only; app roles cannot even SELECT.

**Capability negotiation**: registration payloads carry a versioned
capability spec (`protocol_version`, `extra="forbid"`); the server rejects
unsupported versions (accepted set: `[1]`) and echoes the accepted version
back — no silent downgrades.

## Lease management & recovery (Milestone 4 · Workstream 3)

**Bounded leases**: each acquisition sets `lease_started_at`; renew/ack
extends `lease_expires_at` by `assignment_lease_seconds` but is rejected
when the extension would exceed `assignment_max_lease_seconds` from
`lease_started_at`. This prevents heartbeat-extend from creating immortal
assignments while still allowing long provider calls within a hard ceiling.

**Same-row requeue with attempt bump**: lease expiry and dead-worker
recovery return the *same* `stage_assignments` row to `PENDING`, bump
`attempt_number`, rewrite `idempotency_key` to `{run}:{stage}:{attempt}`,
and clear lease/claim fields (`claim_count` is a lifetime counter and is
preserved). Exhaustion (`attempt+1 > max_attempts`) routes to
`dead_letter_jobs` and fails the run — never silent drop.

**Provider effect keys**: durable `provider_effect_keys` rows keyed by
`(workspace_id, effect_key)` with default key `{assignment_id}:{attempt}`
prevent duplicate provider side-effects across crash → requeue → re-claim.
A recovered attempt has a new attempt number and therefore a new key.

**Recovery audit ledger**: append-only `stage_recovery_audit` (FORCE RLS,
member-readable, service-role-written, `prevent_update` trigger) records
every recovery with reason/outcome — parallel to `stage_claim_audit`.

**Combined maintenance tick**: offline sweep and lease reaper share one
loop. Ordering is offline flip → reap that worker's holdings → reap
global expired leases, closing the window where `current_load=0` but
assignments remain `DISPATCHED`. Reap also runs on register (restart),
deregister, and credential revoke so identity-state changes do not wait
for lease timeout.

**HTTP lease lifecycle**: machine-auth `ack` / `renew` / `submit` endpoints
enforce ownership, status, live lease, and max-total bounds; revoked
credentials cannot renew (401 at auth). Drain is enforced at claim time.

## Priority, back-pressure & resource protection (Milestone 4 · Workstream 4)

**Effective priority at claim**: `stage_assignments.priority` is a base
value (seeded from `workspaces.priority_tier * weight`). Claim selection
orders by `priority + age_boost(created_at)` descending, then
`created_at` ascending. Age boost is computed in SQL from the server
clock so it cannot go stale and needs no refresher.

**Provider concurrency budgets**: optional per-`(workspace, provider)`
ceilings. Claim/dispatch take `FOR UPDATE` on the budget row, count
DISPATCHED/ACKNOWLEDGED rows with that provider, and skip (claim) or
leave PENDING (dispatch) when exhausted. Missing budget ⇒ no limit.
Over-budget claim skips use PostgreSQL `SAVEPOINT` so locks release and
concurrent claimers are not starved.

**Queue-depth back-pressure**: PENDING depth vs soft/hard limits on
`workspace_concurrency_limits` drives `workspace_backpressure_state`
(`normal|pressured|throttled`). Transitions emit at-most-one
`backpressure.entered` / `backpressure.cleared` outbox event. THROTTLED
halves scheduler `max_per_scheduler_tick` (min 1). Work is never dropped.

**Spend-cap serialization**: `reserve_spend` locks the matching
`spend_caps` row `FOR UPDATE` so concurrent reservations cannot both
pass the remaining-budget check.

## Workspace scoping

Single workspace per account at launch (v2 spec). Every tenant-owned table
carries `workspace_id` via `WorkspaceScopedMixin` (see `apps/api/app/db/base.py`)
so this can't be omitted on a new model.
