---
name: Claim bookkeeping reset invariant
description: Any path that returns a stage assignment to PENDING must clear ALL claim bookkeeping columns.
---

The rule: whenever an assignment transitions back to PENDING (lease reap,
cancellation, manual requeue), clear `claimed_by`, `claimed_at`, and
`claim_token` along with `worker_id`/`lease_expires_at`. Keep `claim_count`
(lifetime counter).

**Why:** `ck_stage_assignments_claimed_by_matches` requires
`claimed_by IS NULL OR claimed_by = worker_id`. The WS2 architect review
caught the reaper nulling `worker_id` but not `claimed_by` — the reap
transaction would fail on flush and strand expired pull-claimed work forever.

**How to apply:** when adding any new requeue/reset path for
`stage_assignments`, grep for every column set by the claim/dispatch grant
paths and reset them symmetrically; add an end-to-end claim → expire → reap →
re-claim test.
