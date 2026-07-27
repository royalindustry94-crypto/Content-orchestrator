---
name: Scheduler tests pollute shared DB and flake
description: poll_and_lease/reap tests must retire leftover job_schedule rows or accumulated state pushes their own jobs out of the window
---

# Scheduler tests must retire leftover job_schedule rows at start

**Rule:** Tests exercising `scheduler.poll_and_lease` or
`reap_expired_leases` must first neutralize pre-existing rows:
`UPDATE job_schedule SET status='cancelled' WHERE status IN ('pending','leased')`.

**Why:** The suite runs against a shared Postgres that is never truncated
between tests. `poll_and_lease` over-fetches only `batch_size*3` candidates
ordered by `run_after ASC`; `reap_expired_leases` caps at `batch_size`. Each
run leaves due-PENDING/expired-LEASED leftovers (the fairness test abandons 9
jobs every run). As they accumulate (hundreds observed), a test's freshly
created jobs — newest `run_after`, sorted last — fall outside the window, so
`counts[ws]` becomes 0 and the suite flakes (2/1/0 failures across runs).

**How to apply:** This is the same "park leftover state at test start" pattern
already used by the dispatcher tests for workers. It is a test-isolation gap,
not a product defect. If scheduler tests flake intermittently only in the full
suite (pass alone), suspect this first.
