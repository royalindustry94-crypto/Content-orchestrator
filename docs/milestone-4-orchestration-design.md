# Milestone 4 — Orchestration Engine Architecture (DESIGN ONLY)

Status: design for CEO review. No implementation code. Built on the
accepted M2 (identity/RLS) and M3 (content-domain schema) foundations.

Fixed decisions honored throughout: PostgreSQL-backed transactional
outbox; every domain change and its events commit in one DB transaction;
no Redis/Kafka/RabbitMQ; producers are broker-agnostic so a future broker
swap doesn't touch them; worker registry with a reference client only, no
real workers; no AI generation, provider integrations, or publishing.

---

# 1. Overall architecture

Five cooperating subsystems, all coordinating through Postgres. No
component calls another component's code across a process boundary —
they coordinate through rows.

```
                    ┌──────────────────────────────────────────┐
                    │              PostgreSQL (Supabase)          │
                    │                                             │
   domain writes ──▶│  content_items / pipeline_runs / assets …   │
   (M3 tables)      │  workflow_definitions / workflow_stages     │
                    │  outbox_events   ← the transactional bus    │
                    │  event_consumers / consumer_checkpoints     │
                    │  worker_registry / worker_leases            │
                    │  stage_assignments / job_schedule           │
                    │  review_gates    spend_reservations (M3)    │
                    └───▲───────▲──────────▲─────────▲────────────┘
                        │       │          │         │
        (1) writes domain change + outbox event in ONE txn
                        │       │          │         │
        ┌───────────────┴──┐ ┌──┴───────┐ ┌┴─────────┴───┐ ┌───────────────┐
        │ Execution        │ │ Outbox   │ │ Scheduler(s) │ │ Worker        │
        │ Controller       │ │ Relay    │ │ (leased)     │ │ Registry API  │
        │ (advances runs)  │ │ (poll →  │ │ poll → lease │ │ register/     │
        │                  │ │ dispatch)│ │ → dispatch   │ │ heartbeat     │
        └──────────────────┘ └────┬─────┘ └──────┬───────┘ └───────▲───────┘
                                   │              │                 │
                                   ▼              ▼                 │
                             event consumers  stage_assignments     │
                                   │              │                 │
                                   └──────────────┴─────────────────┘
                                                  │
                                        ┌─────────▼──────────┐
                                        │  Reference Worker  │
                                        │  Client (SDK only; │
                                        │  no generation)    │
                                        └────────────────────┘
```

**Control-plane vs data-plane.** The orchestration engine is a *control
plane*: it decides what should happen next and records that decision. The
*data plane* (actual stage execution — later milestones) is workers that
lease assignments and report results. M4 builds the entire control plane
plus the worker-side contract (reference client), and stops at the line
where real generation would begin.

**Why everything routes through Postgres.** The fixed transactional-outbox
decision means the source of truth for "what has happened" and "what
should happen next" is the same database that holds domain state. This
buys three things the directive demands: (a) a domain change and its event
are atomic — no dual-write gap; (b) full traceability, because every
decision is a durable row; (c) horizontal scalability without a broker,
via `SELECT … FOR UPDATE SKIP LOCKED` lease patterns that let N identical
workers/schedulers run safely.

**Horizontal scalability model.** Every long-running role (outbox relay,
scheduler, execution controller, worker) is designed to run as N
identical replicas. Coordination is pessimistic row leasing (`FOR UPDATE
SKIP LOCKED`) — each replica grabs a disjoint set of rows, so adding
replicas adds throughput with no leader election and no sharding config.

**Determinism.** Given the same ordered event log and the same workflow
definition, the engine reaches the same state. All routing decisions are
pure functions of (current run state, workflow definition, event
payload). No decision depends on wall-clock races; time enters only
through explicit, recorded timeout rows.

---

# 2. Workflow Engine

## 2.1 Concept

A **workflow definition** is a versioned, immutable description of a
pipeline: its ordered stages, the transitions between them, and the
policies (retry, timeout) per stage. A **pipeline run** (M3
`pipeline_runs`) is one execution instance of a definition against one
content item. The engine never hard-codes the idea→…→published sequence;
it reads it from the definition, so new pipelines are data, not code.

## 2.2 New tables (detail in §12 and the DB section)

- `workflow_definitions` — versioned; a row is one immutable version of a
  named workflow. Editing = new version, never mutate.
- `workflow_stages` — the stages belonging to a definition version, with
  order, stage key (maps to `content_stage`), retry policy, timeout,
  and whether the stage is a review gate.
- `workflow_transitions` — edges: from_stage → to_stage, guarded by an
  optional condition expression and a trigger (on_success, on_failure,
  on_review_approved, on_review_rejected).

## 2.3 Stages

A stage has: `stage_key` (e.g. scripting), `ordinal`, `max_attempts`,
`backoff_policy`, `timeout_seconds`, `is_review_gate` (bool),
`is_terminal` (bool), and `compensation_stage_key` (nullable — see 2.10).
`pipeline_runs.current_stage` (M3) is the live cursor; `pipeline_stage_runs`
(M3, immutable) is the per-attempt history.

## 2.4 Transitions & conditional routing

A transition fires when its `trigger` matches an event and its optional
`condition` evaluates true. Conditions are a **restricted, declarative
expression** over a whitelisted context (run fields, last stage result,
content metadata) — NOT arbitrary code — so routing stays deterministic,
sandboxed, and storable. Example: `on_success AND content.target_length >
60 → stage:long_form_review`. If multiple transitions match, the one with
the lowest `priority` integer wins (ties are a definition-validation
error, caught when the definition is created).

## 2.5 Retry behaviour

Per-stage `max_attempts` + `backoff_policy` (see §6). A failed stage
attempt writes an immutable `pipeline_stage_runs` row (status=failed) and,
if attempts remain, schedules the next attempt via the scheduler with a
computed `run_after` timestamp. Exhausted attempts route to the DLQ and
flip the run to failed.

## 2.6 Cancellation

Cancellation is an event (`pipeline.cancel_requested`), never a direct
mutation. The controller, on consuming it, sets `pipeline_runs.status =
cancelled`, revokes any open `stage_assignments` (marks them
`cancelled` so a worker's later ACK is rejected), and releases open spend
reservations (§9). In-flight worker attempts are allowed to finish but
their results are ignored (the assignment is already void). Cancellation
is idempotent — a second cancel event is a no-op.

## 2.7 Pause / 2.8 Resume

Pause is a first-class run state (`paused`) with a `pause_reason`
(review_gate | manual | spend_hold). Entering pause records the stage the
run is parked at; the scheduler skips paused runs. Resume is an event
(`pipeline.resume_requested`, or the specific `review.approved`) that
transitions the run back to `running` at the parked stage and enqueues the
next assignment. Because the parked position is a durable row, resume
after any crash is deterministic.

## 2.9 Timeout

Two timeout layers. **Stage-execution timeout**: when a stage is
dispatched, a `job_schedule` row (type=stage_timeout) is inserted with
`run_after = now + timeout_seconds`; if the stage hasn't completed by
then, the timeout fires, marks the attempt failed (reason=timeout), and
enters the retry path. **Review-gate timeout**: §8. Timeouts are rows, not
in-memory timers, so a controller crash doesn't lose them.

## 2.10 Compensation strategy

For a stage that produced external side effects that must be undone on a
later failure (this milestone: only internal effects like spend
reservations exist; external publish is later), a stage may declare a
`compensation_stage_key`. On a downstream permanent failure, the engine
walks *backwards* through completed stages that declared compensations and
enqueues each compensation stage in reverse order (a saga). For M4 the
only concrete compensation is **release spend reservations** (§9);
external-effect compensation (un-publishing) is designed-for but not
populated until publishing exists. Compensation actions are themselves
ret/tried and DLQ'd like any stage.

---

# 3. Event System

## 3.1 The transactional outbox

`outbox_events` is the bus. A producer NEVER publishes to an external
broker. Instead, inside the same transaction that writes the domain
change, it inserts an `outbox_events` row. Commit is atomic: either both
the state change and the event persist, or neither does. This eliminates
the dual-write problem by construction.

A separate **outbox relay** process polls unpublished `outbox_events`
(`FOR UPDATE SKIP LOCKED`), delivers each to registered consumers
(in-process consumer handlers for M4; a future broker adapter later), and
marks them dispatched — at-least-once (§7). Because delivery is separate
from the producing transaction, a relay crash never rolls back domain
state; it just redelivers.

## 3.2 Event envelope

Every event, regardless of type, shares one envelope so consumers and a
future broker adapter treat them uniformly:

```
{
  "event_id":       uuid,          // PK, unique — dedup anchor
  "event_type":     text,          // "stage.completed", versioned name
  "event_version":  int,           // schema version of the payload
  "workspace_id":   uuid,          // tenant scope (RLS)
  "aggregate_type": text,          // "pipeline_run" | "content_item" | …
  "aggregate_id":   uuid,          // the entity this is about
  "correlation_id": uuid,          // one workflow execution, end-to-end
  "causation_id":   uuid | null,   // the event_id that caused this one
  "sequence":       bigint,        // per-aggregate monotonic ordering
  "payload":        jsonb,         // event-type-specific, versioned
  "occurred_at":    timestamptz,
  "produced_by":    text           // component/worker that emitted it
}
```

`correlation_id` threads an entire pipeline execution; `causation_id`
forms the cause→effect chain for tracing (§10).

## 3.3 Event versioning

`event_type` names are stable; `event_version` integers track payload
schema evolution. Consumers declare the max version they understand;
payloads are **upcast** by pure functions (v1→v2→…) before a handler sees
them, so old events remain replayable forever. New fields are additive;
breaking changes get a new `event_version` + an upcaster. Event *type*
renames are never done in place — a new type is introduced and the old one
deprecated.

## 3.4 Ordering guarantees

Global total ordering is neither needed nor provided (it doesn't scale).
Ordering is **per-aggregate**: `sequence` is a monotonic counter per
`(aggregate_type, aggregate_id)`, assigned inside the producing
transaction. Consumers that care about order process an aggregate's events
in `sequence` order and track their position via checkpoints (§3.6).
Cross-aggregate order is expressed through `causation_id`, not a global
clock.

## 3.5 Event replay

Because `outbox_events` is an append-only log, any consumer can replay
from a chosen point by resetting its checkpoint. Replay is safe because
consumers are idempotent (§7). Use cases: a new consumer backfilling, a
bug fix reprocessing a range, disaster recovery. Replay reads the same
rows; it never rewrites history.

## 3.6 Consumer checkpoints

`event_consumers` registers each logical consumer; `consumer_checkpoints`
stores, per (consumer, aggregate or partition), the last `sequence`
processed. A consumer advances its checkpoint only after its handler
commits successfully — so a crash mid-handle re-delivers from the last
committed checkpoint (at-least-once). Checkpoints make replay and
resumption a single mechanism.

## 3.7 Duplicate protection

Two layers. **Delivery dedup**: consumers record processed `event_id`s
(or rely on the checkpoint high-water mark) and skip anything already
applied. **Effect dedup**: handlers use idempotency keys (§7) so even a
re-applied event produces no second effect. Together these give effective
exactly-once *processing* on top of at-least-once *delivery*.

## 3.8 Poison-event handling

An event whose handler fails repeatedly (beyond a per-consumer
`max_delivery_attempts`) is moved to a **poison/dead-letter lane**:
`outbox_events.status = poison`, copied into `dead_letter_jobs` (M3) with
the failing consumer, error, and attempt count. The consumer's checkpoint
advances past it so one poison event can't block the whole stream
(head-of-line blocking is avoided per-consumer). Poison events are
inspected and either fixed-and-replayed or discarded through the DLQ
recovery flow (§Failure scenarios).

## 3.9 Transaction boundaries (explicit)

- **Producer transaction:** { domain row change(s) } + { INSERT
  outbox_events } → COMMIT. Atomic. This is the only place events are
  born.
- **Relay transaction:** { SELECT unpublished FOR UPDATE SKIP LOCKED } →
  deliver → { UPDATE status=dispatched } → COMMIT. Separate from the
  producer; failure here redelivers, never corrupts domain state.
- **Consumer transaction:** { apply handler effects, which may themselves
  insert new outbox_events } + { UPDATE consumer_checkpoint } → COMMIT.
  Effects and checkpoint advance atomically, so re-delivery is bounded and
  idempotent.

The chain domain-change → event → consumer-effect → new event is a series
of individually-atomic transactions linked by the durable log — never one
giant transaction, never a cross-service 2PC.

---

# 4. Scheduler

## 4.1 Role

The scheduler turns "work that should happen" into "work assigned to a
worker." It scans for runnable units — a stage attempt whose `run_after`
has passed, a retry that's due, a scheduled/delayed job — and produces
`stage_assignments`. It does not execute work.

## 4.2 Polling strategy

Bounded-interval polling with backoff-on-idle. Each scheduler tick:
`SELECT … FROM job_schedule WHERE status='pending' AND run_after <= now()
ORDER BY run_after FOR UPDATE SKIP LOCKED LIMIT :batch`. Empty result →
exponential poll backoff up to a cap (e.g. 100ms→2s) to keep idle DB load
low; non-empty → process and poll again immediately. `LISTEN/NOTIFY` is an
optional latency optimizer layered on top (a producer NOTIFYs on insert so
schedulers wake instantly), but correctness never depends on it — polling
is the floor.

## 4.3 Lease acquisition

Picking a row with `FOR UPDATE SKIP LOCKED` inside a transaction is the
lease: the row is invisible to other schedulers for the txn. For work that
outlives a single transaction (a dispatched stage), the scheduler writes a
`lease_expires_at` on the assignment and commits; the lease is now a
data-level fact, not a held DB lock.

## 4.4 Lease expiry

A lease is `(owner_id, acquired_at, expires_at)`. Owners renew by
extending `expires_at` (heartbeat). A reaper query finds assignments whose
`expires_at < now()` and `status='dispatched'`, and returns them to
`pending` (incrementing an attempt counter) so another worker can take
them. Expiry is how every crash (worker or scheduler) self-heals.

## 4.5 Concurrent schedulers

N schedulers run identically. `SKIP LOCKED` guarantees they never select
the same row, so they partition work dynamically with zero coordination.
No leader, no static sharding. Throughput scales ~linearly until DB
contention, well beyond target load.

## 4.6 Fairness & 4.7 Starvation prevention

Naive `ORDER BY run_after` can starve a busy workspace behind a flood from
another. Fairness is enforced by **weighted round-robin over workspaces**:
the scheduler selects due work grouped by `workspace_id`, capped per
workspace per tick (a max in-flight per workspace), so no single tenant
monopolizes workers. A secondary `ORDER BY run_after` within each
workspace preserves FIFO per tenant. An aging term (boost priority the
longer a job has waited) guarantees eventual execution — nothing waits
forever.

## 4.8 Delayed execution & 4.9 Scheduled jobs

`job_schedule.run_after` handles both: a retry sets it to now+backoff; a
future-scheduled publish sets it to the target time; a recurring job
(e.g. analytics poll) is re-inserted with the next `run_after` on
completion. One uniform mechanism — a time-ordered queue of intentions —
covers retries, delays, timeouts, and cron-like recurrence.

---

# 5. Dispatcher

## 5.1 Role

Given a runnable stage and the pool of registered workers, the dispatcher
selects a worker, creates the assignment, and manages the ack/lease
lifecycle. It is the bridge between scheduler output and the worker
registry.

## 5.2 Assignment algorithm

For a stage needing `stage_key = scripting`:
1. Query `worker_registry` for workers that are `online`, `status != busy`
   (or below their `max_concurrency`), advertise `scripting` in
   `supported_stages`, and have a health score above threshold.
2. Rank by: health score desc, then current load asc, then
   least-recently-assigned (spreads load, avoids hot workers).
3. Create a `stage_assignments` row (status=dispatched, lease set) bound
   to the chosen worker, emit `stage.assigned`.
If no eligible worker exists, the assignment stays `pending` and is retried
next tick (with aging) — work is never dropped for lack of a worker.

## 5.3 Worker selection

Capability match is exact on `stage_key ∈ supported_stages`; capacity is
`current_load < max_concurrency`; health is `health_score >= min`.
Selection is pull-friendly too: a worker may instead *poll* for the next
assignment matching its capabilities (`FOR UPDATE SKIP LOCKED`), which is
the reference client's default. Push (dispatcher-assigns) and pull
(worker-claims) use the same `stage_assignments` table; the difference is
only who writes the binding.

## 5.4 Acknowledgement

On receiving/claiming an assignment the worker ACKs (status →
`acknowledged`, sets `worker_id`, starts lease renewal). Missing ACK
within an ack-timeout returns the assignment to `pending` (the worker may
have died between dispatch and ack — the lost-ack scenario). ACK is
idempotent by assignment id.

## 5.5 Lease renewal

While working, the worker renews the assignment lease (extends
`expires_at`) on a heartbeat interval < lease TTL. Stop renewing (crash,
hang) → lease expires → reaper reclaims (§4.4). Result submission is a
final transaction: write `pipeline_stage_runs` (immutable result) + advance
`pipeline_runs` + insert the outcome `outbox_events`, all atomic, then the
assignment → `completed`.

## 5.6 Failure recovery

Every dispatcher failure mode reduces to lease expiry + reaper: worker
dies pre-ack (ack-timeout reclaim), dies mid-work (lease-expiry reclaim),
completes but the completion txn fails (assignment still leased → reclaim →
idempotency key prevents double effect on redo). No dispatcher state lives
in memory that isn't reconstructable from the tables.

---

# 6. Retry Framework

## 6.1 Exponential backoff (with jitter)

`delay = min(base * 2^(attempt-1), max_delay)` then add full jitter
(`random(0, delay)`) to avoid thundering herds when many jobs fail
together (e.g. a provider outage — relevant later). Parameters
(`base`, `max_delay`, `multiplier`) live on the stage's `backoff_policy`,
so retry tuning is definition data, not code. The LOVABLE standard's
"backoff **with jitter**" is satisfied here.

## 6.2 Retry limits

`max_attempts` per stage. Attempt count is derived from the immutable
`pipeline_stage_runs` rows for that (run, stage), so it survives crashes
and can't be lost or double-counted.

## 6.3 Permanent failure detection

Errors are classified: **retryable** (timeout, transient provider error,
lease loss) vs **permanent** (validation failure, unsupported input,
policy rejection). Permanent errors skip remaining retries and go straight
to DLQ. Classification is a property of the reported failure, defaulting to
retryable only for a known-transient allowlist — fail safe by not
retrying unknown-permanent errors forever.

## 6.4 Dead-letter routing

On exhausted retries or a permanent error, the engine writes a
`dead_letter_jobs` (M3) row: `related_table`, `related_id`, `job_type`,
`payload` (enough to replay), `failure_reason`, `attempt_count`,
`first/last_failed_at`. The run goes `failed`; a `pipeline.failed` event
fires; compensation (§2.10) is triggered if declared.

## 6.5 Replay strategy

A DLQ entry is replayable: an operator (later, via API/UI) marks it
`pending`→ re-enqueue, which creates a fresh `job_schedule` row with reset
attempts (or continued, configurable). Replays are idempotent via the
original idempotency key, so replaying a job that actually half-succeeded
won't double its effects.

---

# 7. Idempotency

## 7.1 Idempotency keys

Producers attach an `idempotency_key` to actions that could be retried:
M3 already added it to `pipeline_runs`, `publish_jobs`, `webhook_events`;
M4 adds it to `stage_assignments` and to `outbox_events` (the `event_id`
itself is the event's key). Keys are unique per workspace (partial unique
index).

## 7.2 Duplicate request protection

A create request carrying an existing `idempotency_key` returns the
existing entity instead of creating a second — the unique index makes the
second insert fail, caught and translated to "return the original." So a
client retry after a lost response is safe.

## 7.3 Duplicate event protection

`outbox_events.event_id` is unique; consumers track applied ids /
checkpoints. A redelivered event is recognized and skipped before its
handler runs.

## 7.4 Exactly-once where possible

True exactly-once delivery is impossible across a crash boundary; we
achieve exactly-once **effect** by combining at-least-once delivery with
idempotent handlers keyed on stable ids. The effect (a stage result, a
spend commit) happens once even if the event/message arrives twice.

## 7.5 At-least-once delivery guarantee

The outbox relay and consumer checkpoints guarantee every event is
delivered at least once: an event is marked dispatched only after delivery,
and a consumer advances its checkpoint only after its effect commits. A
crash at any point causes redelivery, never loss.

---

# 8. Human Review Gate

## 8.1 Pause execution

A stage with `is_review_gate=true` does not dispatch to a worker. On
reaching it, the controller sets `pipeline_runs.status=paused`,
`pause_reason=review_gate`, creates a `review_gates` row (run, stage,
requested_at, timeout_at, status=awaiting), and emits `review.requested`.
The scheduler ignores paused runs, so nothing proceeds until a decision.

## 8.2 Approval events / 8.3 Rejection events

A reviewer's decision (recorded via the existing M3 `review_decisions`
table) emits `review.approved` or `review.rejected`. These are ordinary
events on the bus — the review UI (later) only writes a `review_decisions`
row + outbox event in one txn; it doesn't call the engine directly.

## 8.4 Resume execution

Consuming `review.approved` transitions the run `paused→running` and fires
the gate's `on_review_approved` transition (usually → next stage).
`review.rejected` fires `on_review_rejected` (route back to an earlier
stage for rework, or to `failed`, per the definition). Resume position is
the durable parked stage, so it's crash-safe.

## 8.5 Timeout behaviour

`review_gates.timeout_at` is enforced by a `job_schedule` timeout row. On
expiry with no decision: configurable policy per stage — `escalate`
(default), `auto_reject`, or `auto_approve` (rare, for low-risk stages).
Timeout firing emits `review.timed_out`.

## 8.6 Escalation

On escalation, the engine emits `review.escalated` (a notification
consumer — later — would alert a senior reviewer) and optionally re-arms a
second, longer timeout. Escalation is itself event-driven and recorded, so
the audit trail shows the gate waited, escalated, and to whom.

---

# 9. Spend Protection (orchestration hooks)

Integrates with M3 `spend_reservations`, `spend_logs`, `spend_caps`.

## 9.1 Spend reservation

Before dispatching a stage that will cost money, the controller **reserves**
estimated spend: insert `spend_reservations` (status=reserved,
estimated_cost_usd) in the same txn as the assignment. The cap check sums
`spend_logs` (committed) + open `spend_reservations` and compares to
`spend_caps` — closing the check-then-spend race by construction.

## 9.2 Spend release

If the stage is cancelled, fails permanently, or over-estimated, the
reservation is **released** (status=released) so it stops counting against
the cap. Release is part of cancellation and compensation (§2.6, §2.10).

## 9.3 Spend commit

On stage success with a known actual cost, the reservation is **committed**:
status=committed and an immutable `spend_logs` row is written for the
actual amount, in the same txn as the stage result. Reserve→commit turns an
estimate into a fact atomically.

## 9.4 Budget exceeded

If a reservation would push committed+reserved over the cap, the reservation
is refused; the controller sets the run `paused`, `pause_reason=spend_hold`,
emits `spend.budget_exceeded`, and does not dispatch. The run resumes only
when budget frees up (a new cap, a reset window, or released reservations)
or is cancelled.

## 9.5 Pipeline cancellation on budget

Policy per workspace: a budget breach can either hold (pause) or hard-cancel
the run. Cancellation runs the normal cancel path (§2.6) including releasing
all that run's reservations. Either way the spend cap is never exceeded,
because dispatch is gated on the reserve succeeding.

---

# 10. Observability

## 10.1 Execution timeline

Every run has a reconstructable timeline from immutable rows:
`pipeline_stage_runs` (attempts), `outbox_events` (what happened, ordered
by sequence), `stage_assignments` (who did what, when), `review_gates`,
`spend_*`. A timeline view is `SELECT … ORDER BY occurred_at` across these
by `correlation_id` — no separate tracing store needed for the durable
record.

## 10.2 Structured logging

All components emit JSON logs (M1 `app/core/logging.py` already does),
every line carrying `correlation_id`, `causation_id`, `workspace_id`,
`run_id`, `stage`, and `component`. Logs are the ephemeral, high-detail
companion to the durable event log.

## 10.3 Correlation IDs / 10.4 Tracing IDs

`correlation_id` = one workflow execution end-to-end (set when the run
starts, copied onto every event, assignment, log line). `causation_id` =
the parent event id, forming a span tree. Together they let you trace a
single content item from `content.created` through `publish.completed`
across every component and worker. A `trace_id`/`span_id` pair
(OpenTelemetry-compatible) is carried in the envelope for export to a
tracing backend later, without redesign.

## 10.5 Metrics

Counters/gauges/histograms designed (not yet emitted): events
produced/dispatched/poisoned, assignment latency, stage duration by
stage_key, retry counts, DLQ depth, review-gate wait time, worker
utilization, scheduler poll latency, reservation/commit amounts. All are
derivable from the tables, so metrics can be computed even retroactively.

## 10.6 Audit events

Security/governance-relevant actions (review decisions, cancellations,
budget holds, credential use later) emit dedicated audit events, retained
immutably. Because events are already the system's backbone, audit is a
consumer/filter over the existing log, not a parallel mechanism.

---

# 11. Failure scenarios (explicit handling)

| Scenario | Detection | Handling | Guarantee |
|---|---|---|---|
| **Worker crash** (mid-stage) | Lease `expires_at` passes with no renewal | Reaper returns assignment to `pending`, attempt++; another worker takes it; idempotency key prevents double effect if the dead worker had partially committed | No lost work, no double effect |
| **Scheduler crash** | Its `FOR UPDATE SKIP LOCKED` txn aborts; leases it hadn't committed vanish | Other schedulers pick up untouched rows immediately; committed leases reaped on expiry | Zero coordination needed; self-heals |
| **Duplicate events** | `event_id` unique + consumer checkpoint | Redelivery recognized and skipped before handler runs | Exactly-once effect |
| **Lost acknowledgements** | ACK-timeout on a `dispatched` assignment | Assignment returned to `pending`; reassigned; original worker's late ACK rejected (assignment already moved) | No stuck assignments |
| **Database restart** | Connections drop; components reconnect with backoff | All state is in committed rows; in-flight uncommitted txns roll back cleanly (outbox atomicity); nothing half-applied | No corruption; resume where left off |
| **Partial transaction failure** | Any error before COMMIT | Whole txn rolls back — domain change AND its outbox event together; producer retries | No dual-write gap ever |
| **Lease expiry** (slow but alive worker) | `expires_at < now()` while worker still running | Assignment reclaimed; the slow worker's eventual result is rejected (lease lost); it re-runs under a new lease with the same idempotency key | Safe; at most re-execution, never double effect |
| **Replay** | Operator resets a checkpoint / re-enqueues a DLQ job | Events reprocessed through idempotent handlers; effects not duplicated | Deterministic reprocessing |
| **Dead-letter recovery** | Poison event / exhausted job in `dead_letter_jobs` | Operator inspects, fixes root cause, marks `pending`; re-enqueued with reset/continued attempts under original idempotency key | Nothing silently dropped |

Cross-cutting principle: **every failure reduces to "a lease expires and a
reaper requeues," or "a transaction rolls back atomically."** There are no
bespoke recovery paths to get wrong, and no in-memory state whose loss
matters.

---

# Deliverable 2 — Sequence diagrams

## 2.1 Happy-path stage execution (transactional outbox throughout)

```
Controller        Postgres           OutboxRelay      Scheduler      Worker
    |                 |                   |               |             |
    |-- BEGIN --------|                   |               |             |
    | UPDATE pipeline_runs (advance)      |               |             |
    | INSERT job_schedule(stage,run_after)|               |             |
    | INSERT outbox_events(stage.ready)   |               |             |
    |-- COMMIT (atomic) ------------------|               |             |
    |                 |                   |               |             |
    |                 |<-- poll due job (FOR UPDATE SKIP LOCKED) -------|
    |                 |                   |               |-- lease ----|
    |                 |                   |               | dispatch:   |
    |                 |                   |               | INSERT stage_assignments(dispatched,lease)
    |                 |                   |               | INSERT outbox_events(stage.assigned)
    |                 |                   |               |-- COMMIT ----|
    |                 |                   |               |             |
    |                 |                   |               |<- claim/ACK-|
    |                 |                   |               |  (status=acknowledged, renew lease)
    |                 |                   |               |             |-- work --
    |                 |                   |               |             |  (renew lease heartbeat)
    |                 |                   |               |             |
    |                 |<--- result txn: INSERT pipeline_stage_runs(succeeded) ------|
    |                 |     UPDATE pipeline_runs(current_stage->next)    |          |
    |                 |     UPDATE spend_reservations(committed)+INSERT spend_logs  |
    |                 |     INSERT outbox_events(stage.completed)        |          |
    |                 |     UPDATE stage_assignments(completed)          |          |
    |                 |<--- COMMIT (atomic) -----------------------------|----------|
    |                 |                   |               |             |
    |<- consume stage.completed (relay delivers) ---------|             |
    | evaluate transitions -> next stage; loop            |             |
```

## 2.2 Worker crash & recovery

```
Scheduler        Postgres          Reaper           Worker-A     Worker-B
    |-- dispatch -->| assignment(dispatched, lease=T+30s, worker=A)     |
    |               |<------------- ACK, renew --------- A              |
    |               |                  |          A working…            |
    |               |                  |          [A CRASHES]           |
    |               |   (no renewals; lease ages)                       |
    |               |<- reaper: SELECT WHERE expires_at<now AND status IN(dispatched,acknowledged)
    |               |   UPDATE assignment -> pending, attempt++         |
    |               |   INSERT outbox_events(stage.reassigned)          |
    |-- next tick: re-dispatch ------------------------->|              |
    |               | assignment(dispatched, worker=B, new lease)       |
    |               |<--------------- ACK ------------------------------ B
    |               |   B completes; idempotency_key == A's, so if A had
    |               |   partially written, the unique key blocks a 2nd effect
```

## 2.3 Human review gate

```
Controller        Postgres                 ReviewUI(later)     Consumer
    | reach stage is_review_gate=true       |                    |
    |-- BEGIN                               |                    |
    | UPDATE pipeline_runs(paused, reason=review_gate)           |
    | INSERT review_gates(awaiting, timeout_at)                  |
    | INSERT job_schedule(review_timeout, run_after=timeout_at)  |
    | INSERT outbox_events(review.requested)                     |
    |-- COMMIT                              |                    |
    |                                       |                    |
    |     (scheduler skips paused run)      |                    |
    |                                       |-- reviewer decides |
    |                                       |  BEGIN             |
    |                                       |  INSERT review_decisions(approved)
    |                                       |  INSERT outbox_events(review.approved)
    |                                       |  COMMIT            |
    |<---------------- consume review.approved -----------------|
    | UPDATE pipeline_runs(running); fire on_review_approved -> next stage
    |                                       |                    |
    | (if timeout fires first: job_schedule -> review.timed_out -> escalate)
```

## 2.4 Spend reservation → commit

```
Controller                     Postgres
    | before dispatch:  BEGIN
    | SELECT sum(spend_logs)+sum(open spend_reservations) vs spend_caps
    |   if would exceed -> UPDATE run(paused, spend_hold); INSERT outbox(spend.budget_exceeded); COMMIT; stop
    | else -> INSERT spend_reservations(reserved, est); INSERT stage_assignments; INSERT outbox(stage.assigned); COMMIT
    |
    | on stage success:  BEGIN
    | UPDATE spend_reservations(committed); INSERT spend_logs(actual); INSERT outbox(stage.completed); COMMIT
    |
    | on cancel/fail:     BEGIN
    | UPDATE spend_reservations(released); INSERT outbox(spend.released); COMMIT
```

---

# Deliverable 3 — Event lifecycle

```
 produced ──▶ pending ──▶ dispatched ──▶ (per consumer) processing ──▶ applied
    │            │             │                              │
    │            │             │                              ├─ handler ok ─▶ checkpoint advances (done)
    │            │             │                              └─ handler fails ─▶ retry (redeliver)
    │            │             │                                          │ (attempts exhausted)
    │            │             │                                          ▼
    │            │             │                                       poison ──▶ dead_letter_jobs
    │            │             └─ relay crash before mark ─▶ redelivered (at-least-once)
    │            └─ produced in same txn as domain change (atomic)
    └─ event_id assigned (dedup anchor), sequence assigned per aggregate
```

Terminal states: **applied** (all consumers checkpointed past it) or
**poison** (moved to DLQ for at least one consumer, checkpoint advanced so
the stream is unblocked).

---

# Deliverable 4 — Workflow lifecycle

```
              ┌───────────────────────────────────────────────┐
              ▼                                                │
  created ─▶ running ─▶ (stage loop) ─▶ succeeded              │ (resume)
              │  │  ▲          │                               │
              │  │  └──────────┘ next stage on transition      │
              │  │                                             │
              │  ├─▶ paused (review_gate | manual | spend_hold)─┘
              │  │
              │  ├─▶ failed        (stage permanent failure / retries exhausted)
              │  └─▶ cancelled     (cancel_requested)
              │
   compensating ◀─ (on failure with declared compensations) ─▶ failed
```

---

# Deliverable 5 — Worker lifecycle

```
  (register) ─▶ online/idle ─▶ acknowledged/busy ─▶ online/idle ─▶ …
        │            │  ▲                │                 ▲
        │            │  └── result submitted, lease closed ┘
        │            │
        │            ├─▶ draining (graceful shutdown: finish current, take no new)
        │            │        └─▶ offline (clean)
        │            │
        │            └─▶ (missed heartbeats) ─▶ unhealthy ─▶ offline (reaped);
        │                     its leased assignments expire and are requeued
        └─ heartbeat every < TTL; health_score from heartbeat recency + recent success/failure
```

---

# Deliverable 6 — Database additions (0014+)

All new tables carry `workspace_id` + RLS (ENABLE + FORCE) like M3, with
the same owner/`app_runtime` split. Migrations are additive.

**0014_workflow_definitions**
- `workflow_definitions` (id, workspace_id, name, version int, is_active,
  created_at/by; immutable per version; unique (workspace_id,name,version))
- `workflow_stages` (id, workspace_id, definition_id, stage_key
  content_stage, ordinal, max_attempts, backoff_policy jsonb,
  timeout_seconds, is_review_gate, is_terminal, compensation_stage_key)
- `workflow_transitions` (id, workspace_id, definition_id, from_stage,
  to_stage, trigger enum, condition jsonb, priority int)
  — immutable definitions; version bump to change.

**0015_outbox_events**
- `outbox_events` (event_id PK, workspace_id, event_type, event_version,
  aggregate_type, aggregate_id, correlation_id, causation_id, sequence
  bigint, payload jsonb, status enum[pending,dispatched,poison],
  delivery_attempts, occurred_at, produced_by; indexes on
  (status, occurred_at), (aggregate_type, aggregate_id, sequence),
  (workspace_id)) — append-only; immutable except status/attempts via a
  controlled path.
- `event_consumers` (id, name, max_version, max_delivery_attempts)
- `consumer_checkpoints` (consumer_id, aggregate_type, partition_key,
  last_sequence, updated_at; unique per (consumer, partition))

**0016_scheduler_jobs**
- `job_schedule` (id, workspace_id, job_type enum[stage, retry,
  stage_timeout, review_timeout, recurring], ref_table, ref_id, run_after,
  status enum[pending,leased,done,cancelled], lease_owner, lease_expires_at,
  attempt, priority; index (status, run_after), (workspace_id, run_after))

**0017_worker_registry**
- `worker_registry` (id, workspace_id nullable[global workers allowed],
  name, supported_stages content_stage[], capabilities jsonb, status
  enum[online,offline,busy,draining], max_concurrency, current_load,
  health_score, last_heartbeat_at, registered_at)
- `worker_heartbeats` (optional append-only heartbeat log, or fold
  last_heartbeat_at into registry; design keeps a lightweight
  `worker_heartbeats` for health history)

**0018_stage_assignments**
- `stage_assignments` (id, workspace_id, pipeline_run_id, stage,
  attempt_number, worker_id, status enum[pending,dispatched,acknowledged,
  completed,failed,cancelled], idempotency_key, lease_expires_at,
  dispatched_at, acknowledged_at, completed_at, result jsonb;
  partial unique (workspace_id, idempotency_key); index (status,
  lease_expires_at) for the reaper)

**0019_review_gates**
- `review_gates` (id, workspace_id, pipeline_run_id, stage, status
  enum[awaiting,approved,rejected,timed_out,escalated], requested_at,
  timeout_at, decided_at, decided_by, escalation_level)

Immutability: `outbox_events`, `workflow_*` (per version), and the
per-attempt records stay append-only via the existing `prevent_update()`
pattern where a row is a fact; mutable coordination tables
(`job_schedule`, `worker_registry`, `stage_assignments`, `review_gates`)
carry `version` + `set_version_and_updated_at()` for optimistic locking.

---

# Deliverable 7 — State machine diagrams

**pipeline_runs.status**
```
created → running ⇄ paused → running → succeeded
                 ↘ failed
                 ↘ cancelled
running → compensating → failed
```

**stage_assignments.status**
```
pending → dispatched → acknowledged → completed
   ▲          │              │            
   └──────────┴──────────────┘  (lease expiry / ack timeout → pending, attempt++)
pending/dispatched/acknowledged → cancelled  (run cancelled)
acknowledged → failed → (retry:new attempt) | (permanent:DLQ)
```

**outbox_events.status**
```
pending → dispatched → (per-consumer applied)   [terminal: applied]
pending → dispatched → poison → dead_letter_jobs [terminal: poison]
```

**job_schedule.status**
```
pending → leased → done
   ▲         │
   └─────────┘ (lease expiry → pending)
pending/leased → cancelled
```

**worker_registry.status**
```
online ⇄ busy
online → draining → offline
online/busy → (missed heartbeats) → offline (reaped)
```

**review_gates.status**
```
awaiting → approved
awaiting → rejected
awaiting → timed_out → escalated → (approved|rejected|auto_*)
```

---

# Deliverable 8 — Architectural decisions

1. **Transactional outbox on Postgres** (fixed by directive). Domain
   change + event atomic; no dual-write. Relay delivers separately.
2. **Broker-agnostic producers.** Producers only ever INSERT
   `outbox_events`. Delivery is behind a relay + consumer interface, so a
   future Redis/Kafka adapter is a new relay target, not a producer change.
3. **Pessimistic row leasing (`FOR UPDATE SKIP LOCKED`)** for all
   queue-like access → N-replica horizontal scale with no leader election.
4. **Leases as data (`expires_at`), not held locks**, so work survives
   process lifetime and crashes self-heal via a reaper.
5. **Per-aggregate ordering, not global.** Scales; sufficient because
   causal order is captured by `causation_id`.
6. **Workflow-as-data.** Stages/transitions/policies are rows; new
   pipelines need no code — satisfies the "register, don't rewrite" goal.
7. **Events as the only inter-component channel.** No direct calls between
   controller/scheduler/workers; everything is produce/consume.
8. **Exactly-once effect via at-least-once delivery + idempotent handlers.**
   The only honest guarantee across crashes.
9. **Reference worker client, not real workers.** M4 ships the contract
   and an SDK/simulator; generation stays out.
10. **Spend gating at dispatch via reserve/commit/release**, summed with
    committed logs, closing the check-then-spend race.

---

# Deliverable 9 — Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Outbox relay becomes a throughput bottleneck | Delivery lag | Batch delivery, multiple relay replicas via SKIP LOCKED, optional LISTEN/NOTIFY wake |
| Postgres as a queue at high scale | DB load, lock contention | Fine at target (50/day); partial indexes on hot predicates; documented broker-swap path when needed |
| Poison event blocks a consumer | Stalled stream | Per-consumer checkpoint advances past poison into DLQ (no head-of-line block) |
| Clock skew across replicas affects lease expiry | Premature/late reclaim | Use DB `now()` as the single clock for all lease math, never process clocks |
| Condition-expression engine over-powerful | Non-determinism / injection | Restricted whitelisted DSL over a fixed context, no arbitrary code, validated at definition-create |
| Long review waits pin runs in `paused` | Resource/attention leak | Review timeouts + escalation; metrics on gate wait time |
| Reservation leak (reserved never committed/released) | Phantom budget consumption | Reservations tied to assignment lease; reaper releases reservations of reclaimed/failed assignments |
| Definition version drift mid-run | Ambiguous routing | A run pins the `definition_id`+version at start; edits create a new version, never affect running instances |

---

# Deliverable 10 — Trade-offs

- **Postgres-queue simplicity vs broker throughput.** Chosen: simplicity +
  atomicity + zero new infra, accepting a throughput ceiling far above
  current need, with a documented swap path.
- **At-least-once + idempotency vs true exactly-once.** Chosen: the only
  achievable honest guarantee; costs handler idempotency discipline.
- **Per-aggregate ordering vs global ordering.** Chosen: scalability over a
  global total order nobody needs.
- **Workflow-as-data vs code-defined pipelines.** Chosen: flexibility and
  "register don't rewrite," costing a small DSL/validator to build.
- **Pull (worker-claims) + push (dispatcher-assigns) both supported.** Costs
  a little complexity for deployment flexibility; same table underneath.
- **Leasing/polling vs event-driven wakeups.** Polling is the correctness
  floor; NOTIFY is a latency optimization layered on, never required.

---

# Deliverable 11 — Alternatives considered

1. **Redis Streams / RabbitMQ / Kafka broker.** Rejected (directive, and
   independently sound at this scale): reintroduces the dual-write problem,
   new infra/ops burden, and no throughput need yet. The outbox keeps the
   door open to adopt one later behind the relay interface.
2. **Direct worker-to-worker calls / orchestration in code.** Rejected:
   couples components, no durability, no replay, no dynamic worker
   addition — the opposite of the milestone's goal.
3. **Temporal / other workflow engine as a dependency.** Rejected for now:
   heavy external dependency and operational surface; the durable-log +
   state-machine core we need is small and better owned. Revisit only if
   workflow complexity explodes.
4. **Global event ordering via a single sequence.** Rejected: serialization
   bottleneck; per-aggregate order + causation covers real needs.
5. **In-memory scheduler state with periodic snapshots.** Rejected: crash
   recovery complexity and correctness risk vs. all-state-in-rows.
6. **Choreography-only (no controller).** Rejected: pure choreography makes
   global concerns (spend caps, review gates, end-to-end timeouts) hard to
   enforce and observe; a thin controller for cross-cutting decisions plus
   event choreography for propagation is the balance chosen.

---

# Deliverable 12 — Repository impact

Planned (on approval), additive to the current tree:

```
apps/api/app/models/
   workflow.py         # workflow_definitions, workflow_stages, workflow_transitions
   events.py           # outbox_events, event_consumers, consumer_checkpoints
   scheduling.py       # job_schedule
   workers.py          # worker_registry, worker_heartbeats
   assignments.py      # stage_assignments
   review_gate.py      # review_gates
apps/api/alembic/versions/
   0014_workflow_definitions.py … 0019_review_gates.py
apps/api/app/orchestration/          # NEW package (control-plane logic — later phase)
   outbox.py           # producer helper: write domain change + event in one txn
   relay.py            # outbox relay (poll → deliver → mark)
   scheduler.py        # lease/poll/fairness
   dispatcher.py       # worker selection + assignment lifecycle
   controller.py       # execution controller: transitions, review, spend, compensation
   retry.py            # backoff + classification + DLQ routing
   events/
      envelope.py      # event envelope + versioning/upcasters
      types.py         # event type constants (content.created, stage.completed, …)
apps/worker/worker/
   client.py           # REFERENCE worker client/SDK (claim, ack, renew, submit) — no generation
docs/
   milestone-4-orchestration-design.md   # this document
tests/                                   # simulated workers/schedulers, lease-expiry, replay, dedup, review, spend
.github/workflows/ci.yml                 # already runs alembic upgrade head + pytest; picks up 0014-0019
```

No changes to M2/M3 tables. Event *emission* from existing writes is
additive (same-txn outbox inserts). The reference worker client lives under
`apps/worker` but performs no generation — it exercises the assignment
contract only.

---

# Scope boundary (restated)

This document is design only. No AI generation, provider integrations,
publishing, or real workers. The Phase-1 code (workflow engine, event
outbox, scheduler, worker registry, dispatcher, retry/DLQ, review-gate
orchestration, spend hooks, observability plumbing, reference client, and
tests) is written only after CEO approval of this design.

---

# CEO Amendments Incorporated

Four amendments were required before implementation began. All four are
implemented in migrations 0014–0020 and the `app/orchestration` package.

## 1. Distributed tracing (trace_id / correlation_id propagation)

`trace_id`/`span_id` were added alongside `correlation_id`/`causation_id`
to every event-adjacent table: `outbox_events`, `job_schedule`,
`stage_assignments`, and `pipeline_runs` (new columns on the existing M3
table). `app.orchestration.events.envelope.child_span()` is the single
function that continues a trace with a new span (or starts one if none
exists yet), called at every hop: run start, stage dispatch, lease
reclaim, review request/decision, spend reserve/commit/release. Every
structured log line already carries `correlation_id`/`trace_id` via the
same fields passed to `emit()`. No separate tracing store is wired up —
the identifiers are OpenTelemetry-compatible so a real backend can be
attached by exporting from the same fields, without a schema change.

## 2. Back-pressure & workspace fairness

`workspace_concurrency_limits` (migration 0016) is the configurable
back-pressure knob: `max_concurrent_assignments` (enforced in
`dispatcher.dispatch_stage` — checked before worker selection, so an
over-cap workspace never consumes a worker slot; the stage stays
unscheduled and is retried on a later tick rather than dropped) and
`max_per_scheduler_tick`, enforced in `scheduler.poll_and_lease()`, which
groups due jobs by workspace and round-robins across workspaces up to
each one's configured (or default) per-tick cap before leasing more from
any single workspace. Together these stop a flooding tenant both at
"how much can be claimed in one tick" and "how many workers can it hold
at once." Regression-covered by
`test_scheduler_fairness_caps_per_workspace_per_tick`. Overload behavior:
work beyond either cap simply remains `pending`/undispatched and is
retried on a later tick — no jobs are dropped, only delayed, and delay
scales with how far over its fair share a workspace's backlog is.

## 3. Operational metrics

`app.orchestration.metrics` implements all eight requested signals:
queue depth, event latency, workflow execution duration, retry counts,
dead-letter counts, dispatch success/failure rate, worker lease
contention, and scheduler throughput — as query functions over the
durable tables (no metrics backend exists in the declared stack, so this
follows the design doc's own §10.5 commitment: metrics are derivable
on demand, not a parallel write path). `emit_counter`/`emit_histogram`
give instrumentation points that aren't naturally a table query a
structured-log-based emission path, ready to forward to a real backend
later without changing call sites.

## 4. Workflow-definition versioning

`workflow_definitions.version` + `is_active` (migration 0014) implement
this: a `pipeline_run.definition_id` is pinned at `start_run()` and never
re-resolved, so an in-flight run always replays deterministically against
the exact stage/transition rows it started with, regardless of later
edits. A new active version is a new row (immutable, `prevent_update`
trigger), never a mutation of an existing one. New-execution resolution
("use the latest active version") is the one piece left for the
service-layer milestone that will expose `start_run` behind an API — this
milestone provides the schema and the pin-at-start mechanism; it doesn't
yet include a `resolve_latest_active(name)` lookup helper, since nothing
calls `start_run` from outside a test in this milestone. Flagged in Known
Limitations.
