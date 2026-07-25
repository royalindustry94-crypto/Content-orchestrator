---
name: Test isolation with shared persistent DB
description: Tests share a real PostgreSQL DB; stale rows from prior runs cause claim_next and dispatch_stage to behave unexpectedly.
---

# Test isolation: stale DB state

**Rule:** Tests that use `dispatcher.dispatch_stage` + `client.claim_next` must:
1. Park all ONLINE/BUSY workers to OFFLINE before calling `dispatch_stage`, OR the assignment may be created as DISPATCHED (not PENDING) if a leftover worker is online.
2. After dispatching, retire all OTHER PENDING assignments (`UPDATE stage_assignments SET status = 'failed' WHERE status = 'pending' AND id != :id`) so `claim_next` (which picks the OLDEST PENDING) doesn't grab a stale assignment from a prior test run whose `pipeline_run.definition_id` may be NULL.

**Why:** The test DB is NOT wiped between tests. `claim_next` uses `ORDER BY created_at LIMIT 1`, so it always picks the oldest matching PENDING row — which might belong to a completely different test's workspace/run. Similarly, if a worker is online at dispatch time, the assignment is DISPATCHED, and `claim_next` (which only queries PENDING) will find nothing.

**How to apply:**
```python
# Park leftover workers at start of Session 1
await session.execute(text(
    "UPDATE worker_registry SET status = 'offline'::worker_status "
    "WHERE status IN ('online'::worker_status, 'busy'::worker_status)"
))
# After dispatch, before claim:
await session.execute(text(
    "UPDATE stage_assignments SET status = 'failed' "
    "WHERE status = 'pending' AND id != :id"
), {"id": str(assignment_id)})
```
