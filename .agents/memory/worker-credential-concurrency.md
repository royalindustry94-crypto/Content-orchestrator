---
name: Worker credential rotate/revoke serialization
description: Credential mutation endpoints must lock the worker row to keep the revoke kill-switch correct under concurrency
---

# Worker credential rotate/revoke must serialize on the worker row

**Rule:** Any endpoint that mutates a worker's credential set (rotate, revoke)
must `SELECT … FOR UPDATE` the parent `worker_registry` row before reading and
writing `worker_credentials`.

**Why:** Without the shared lock, a kill-switch `revoke` can SELECT the active
credential set before a concurrent `rotate` inserts its brand-new ACTIVE
credential, then revoke only the rows it saw — stranding the new credential
ACTIVE after the admin believes everything was killed. Found in the WS1
external audit.

**How to apply:** In the service-role session, do
`await session.get(WorkerRegistration, worker_id, with_for_update=True)` first,
then mutate credentials. Deterministic regression:
`test_rotate_revoke_serialized_kill_switch` (hold the worker lock with an
uncommitted new credential; revoke must block, then kill it too).
