# Milestone 3 — Release Report

**Release tag:** `v0.3.0-milestone-3`
**Release date:** 2026-07-25
**Status:** FROZEN — audited, verified, ready for merge

---

## Release Identity

| Field | Value |
|---|---|
| Repository | https://github.com/royalindustry94-crypto/Content-orchestrator |
| Pull Request | https://github.com/royalindustry94-crypto/Content-orchestrator/pull/1 (targets `main`) |
| Branch | `feature/milestone-3` |
| Final commit SHA | `eefc84ddf54e53e6946aea1490bd64e442c1f12e` |
| GitHub Actions run | 30174197545 — https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/30174197545 (api ✅ web ✅ worker ✅) |

## Release Metrics

| Metric | Value |
|---|---|
| Migration head | `0024` |
| Migrations | 24 (single linear chain 0001 → 0024) |
| Tests | 39 / 39 passing (real PostgreSQL, warnings promoted to errors) |
| Coverage | 85.45% (gate: 70%) |
| FORCE RLS tables | 28 / 28 user-data tables |
| RLS policies | 54 |
| API endpoints | 11 |
| SQLAlchemy models | 32 |
| Changed files vs `main` | 96 (+12,866 / −76 lines) |
| Ruff violations | 0 (API + worker) |
| Hardcoded secrets | 0 |
| PUBLIC grants | 0 |

## Architecture Summary

Milestone 3 delivers the content-orchestration engine on top of the M2 identity foundation:

- **Transactional outbox** (`outbox.py`): `emit()` writes events inside the caller's transaction; per-aggregate monotonic sequences enforced via `pg_advisory_xact_lock` + unique index. Producers never commit; atomicity belongs to the caller.
- **Relay** (`relay.py`): polls PENDING outbox events with `FOR UPDATE SKIP LOCKED`, delivers to registered consumers with per-consumer checkpoints (`last_sequence`) for exactly-once effect; poison events route to the dead-letter queue after max delivery attempts.
- **Workflow state machine** (`controller.py`): declarative `workflow_definitions` / `workflow_stages` / `workflow_transitions` with triggers `on_success`, `on_review_approved`, `on_review_rejected`; terminal-stage detection; single-advance guarantees under regression test.
- **Scheduler & dispatcher** (`scheduler.py`, `dispatcher.py`): fair per-workspace scheduling caps, lease-based assignment with expiry reaping, worker selection by health and load, back-pressure via max-concurrent-assignment limits.
- **Human review gate**: `pause_for_review` → `REVIEW_REQUESTED` event; approval/rejection resumes the state machine; gate timeout fails the run loudly.
- **Spend controls**: `reserve_spend` checks committed + reserved spend against daily/monthly caps before dispatch; over-cap pauses the run (`SPEND_HOLD`); failure and cancel release reservations.
- **Retry policy** (`retry.py`): exponential backoff with full jitter (base 5s, ×2, cap 300s, 3 attempts); unknown errors default to non-retryable; exhaustion routes to the dead-letter queue.
- **Reference worker** (`apps/worker`): register → heartbeat → claim (SKIP LOCKED) → execute → submit protocol; executor is a documented M3 stub (AI backends are M4 scope).
- **Web** (`apps/web`): React 18 + Vite + TypeScript strict scaffold with ESLint; full UI is a later milestone.

## Database Summary

- 33 tables (28 user-data + 5 infrastructure), 103 indexes, 74 foreign keys, 271 check constraints, 28 triggers, 44 functions.
- All 28 user-data tables carry `FORCE ROW LEVEL SECURITY` with 54 policies; infrastructure tables (`consumer_checkpoints`, `event_consumers`, `worker_heartbeats`, `worker_registry`) are service-role-only by design.
- Versioning triggers on mutable tables; immutability triggers reject UPDATE on append-only tables (lineage, events, logs).
- Migration chain replays cleanly onto a blank database and round-trips downgrade/upgrade (verified this release).

## Security Summary

- JWT validation: audience, subject, and expiry enforced; 401 on missing/garbage/expired tokens (verified by live probe).
- RLS verified adversarially as the runtime role: cross-workspace reads/updates return 0 rows, non-member inserts raise RLS violations, members can delete only their own membership row (self-leave, migration 0024), and no rows are visible without a JWT claim.
- 4 minimal-privilege `SECURITY DEFINER` helpers prevent RLS recursion.
- No hardcoded secrets; `SUPABASE_JWT_SECRET` has no default and the app refuses to start without it; zero PUBLIC grants; ORM-only data access (no SQL string interpolation).

## Performance Summary

- All hot paths ride partial indexes confirmed via EXPLAIN: pending-assignment claims (`ix_stage_assignments_pending_stage`), lease reaping (`ix_stage_assignments_lease`), outbox polling (`ix_outbox_events_status_time`).
- GIN index on `worker_registry.supported_stages` for array-containment worker matching.
- Advisory locks serialize per-aggregate sequence emission without table-level locking; `SKIP LOCKED` lets relay/dispatcher replicas partition work with zero coordination.

## Known Limitations (accepted for M3)

1. **Spend cap race**: `reserve_spend` does not `SELECT FOR UPDATE` the cap row; two concurrent reservations can both pass the check. Documented design-doc limitation; M4 hardening item.
2. **RECURRING job type** raises `NotImplementedError` — intentional loud-fail guard until a recurring producer exists (M4).
3. **Worker executor is a stub** — returns canned success; real AI provider execution is M4 scope.
4. **Web app is a scaffold** — lint/typecheck/build pipeline only; no product UI yet.
5. **Local Node runtime unavailable** in the development workspace; frontend builds are verified via CI.

## Milestone 4 — Planned Work

- Real AI provider executors (script, voice, video generation) behind the worker protocol.
- Spend-cap row locking (`SELECT FOR UPDATE`) and provider-usage reconciliation.
- Recurring job producer + policy for `JobType.RECURRING`.
- Web product UI: run dashboard, review-gate approval screens, spend monitoring.
- Observability: metrics export (`metrics.py` wiring), tracing spans end-to-end.
- Multi-replica relay/dispatcher deployment validation under load.

---

*Generated as part of the M3 release package. See `RELEASE_CHECKSUMS.md` for document integrity hashes.*
