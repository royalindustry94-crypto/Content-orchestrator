# Final Release Audit — Merge Gate (PR #34 + PR #35)

**Date:** 2026-08-05  
**Auditor stance:** Independent principal engineer — prior audits not trusted  
**Combined tip under review:** `cursor/p2-fix-pr34-highs-b52d` @ (post-fix commit; see git log)  
**PR #35:** https://github.com/royalindustry94-crypto/Content-orchestrator/pull/35 → base `cursor/p2-beta-launch-b52d`  
**PR #34:** https://github.com/royalindustry94-crypto/Content-orchestrator/pull/34 → base `main`  

**Merge rule:** PR #34 alone must **not** merge to `main` (it still carries the pre-fix High findings). Merge path is **#35 → #34 → `main`**, or merge the combined tip branch to `main`.

---

## Verdict

| Gate | Result |
|------|--------|
| Critical issues | **0** |
| High issues | **0** |
| Migration replay (fresh DB → head → base → head) | **PASS** — single head `0033` |
| Full API tests | **PASS** — 191 passed, coverage 83% |
| Worker tests | **PASS** — 4 passed |
| Frontend lint / typecheck+build / tests | **PASS** |
| Isolated pip-audit (API + worker) | **PASS** — 0 known vulns |
| npm audit (high+) | **PASS** — 0 vulnerabilities |
| RLS / FORCE RLS (sampled workspace tables) | **PASS** |
| Human Review Gate integrity (C-1 regression) | **PASS** after fix |
| CI on tip | See CI summary (must be green for merge) |

### Final verdict

# APPROVED FOR MERGE TO MAIN

**Scope of approval:** Combined stack only (`cursor/p2-fix-pr34-highs-b52d` including PR #35 fixes).  
**Not approved:** Merging PR #34 without PR #35.

**Not production-complete:** Managed PITR credentials, live Stripe go-live, optional APM remain post-beta ops — none re-open Critical/High code gates for this baseline.

---

## Critical issues

None remaining.

### Fixed during this gate (was Critical)

| ID | Finding | Fix |
|----|---------|-----|
| **C-1** | Content Desk left orphan `job_schedule` for scripting; after approve→publish, stale `handle_stage_success` / claimable work could open a **new awaiting Review Gate** on a `SUCCEEDED` run | Cancel orphan STAGE/RETRY jobs after sync scripting; ignore stage-success on terminal runs; refuse `pause_for_review` on terminal runs / duplicate awaiting gates; `dispatch_stage` returns `SKIPPED` for terminal/review-paused runs |

---

## High issues

None remaining.

### Fixed during this gate (were High)

| ID | Finding | Fix |
|----|---------|-----|
| **H-1** | Orphan Content Desk `job_schedule` → duplicate gates / stale dispatch | Same as C-1 (cancel orphans) |
| **H-2** | NO_WORKER retries minted duplicate PENDING assignments | Scheduler marks job `DONE` when `NO_WORKER` created a claimable PENDING assignment |
| **H-3** | NO_WORKER DLQ left RESERVED spend open | DLQ path releases reservations + cancels open assignments for the stage |
| **H-4** | `commit_spend` double-wrote `SpendLog` | Idempotent when already `COMMITTED` |
| **H-5** | Stripe webhook applied mutations before unique event insert | Insert+apply inside one savepoint; `IntegrityError` → duplicate |

### Previously fixed on PR #35 (confirmed still holding)

| ID | Control |
|----|---------|
| Auth H-1 | `AUTH_MODE` default `supabase`; production forbids `local` without override |
| Billing H-2 | Checkout links only; entitlement from subscription `active`/`trialing` |
| Spend H-3 | `commit_spend` clamps `actual ≤ reserved` |
| Spend H-4 | Release prior open `(run, stage)` + partial unique index `0033` |
| M-1 | `DispatchOutcome.SPEND_HOLD` parks without DLQ/attempt burn |
| M-2 | Webhook duplicate race handled |
| M-3 | `/metrics` Bearer token; required in production |

---

## Medium issues (non-blocking for this merge)

| ID | Finding | Notes |
|----|---------|-------|
| M-A | `BILLING_ENABLED` defaults false with no production fail-closed guard | Intentional Private Beta default; ops must enable for paid launch |
| M-B | `ALLOW_LOCAL_AUTH_IN_PRODUCTION` break-glass reopens signup | Explicit env override; keep false in prod |
| M-C | Scheduler lease reaper always increments `job.attempt` | Can still mis-count under crash; SPEND_HOLD happy path is safe |
| M-D | Concurrent `decide_review_gate` lacks `FOR UPDATE` | Consumer is idempotent; residual race under dual reviewers |
| M-E | `alembic check` reports metadata/index drift | Replay works; autogenerate noise (indexes in DB not mirrored on models) |
| M-F | `local_auth_credentials` has no RLS (runtime grants) | Pre-JWT lookup by design; no HTTP exposure of hashes |
| M-G | Staging `/metrics` open when token unset | Production fail-closed; set `METRICS_SCRAPER_TOKEN` on shared hosts |
| M-H | Owner-session content-jobs/billing rely on HTTP guards (no RLS backstop) | Guards present + IDOR tests for billing; architectural residual |

---

## Low issues

| ID | Finding |
|----|---------|
| L-1 | No rate limit on local `/auth/signup`/`/login` |
| L-2 | `/auth/mode` public |
| L-3 | JWT `iss` not bound |
| L-4 | `trialing` counts as entitled (Stripe-config dependent) |
| L-5 | Subscription webhook does not assert `STRIPE_PRICE_ID_PRO` |
| L-6 | Worker malformed cost falls back to default estimate (still clamped to reserve) |

---

## Regression summary

| Suite | Result |
|-------|--------|
| API (`pytest --cov-fail-under=75`) | **191 passed**, coverage **83.32%** |
| Worker | **4 passed** |
| Web lint | **PASS** |
| Web `tsc -b && vite build` | **PASS** |
| Web vitest | **1 passed** |
| New gate tests | `test_c1_content_desk_cancels_orphan_stage_job_and_blocks_resurrection`, `test_h4_commit_spend_is_idempotent`, plus prior H-1…H-4 / M-1 / metrics token tests |

Attack reproductions that now fail closed:

1. Orphan scripting job after Content Desk create → **cancelled**  
2. Forced `handle_stage_success` on `SUCCEEDED` run → **no new awaiting gate**  
3. Double `commit_spend` → **single SpendLog**  
4. Checkout without subscription → **not entitled**  
5. Worker cost overage → **clamped to reserved**

---

## Migration summary

| Check | Result |
|-------|--------|
| Fresh DB `alembic upgrade head` | **PASS** → `0033` |
| `alembic downgrade base` | **PASS** |
| `alembic upgrade head` (replay) | **PASS** |
| Heads | **Single** `0033` (via `0032_merge_p1` over `0031` / `0031_fk` / `0031_spend_precision`) |
| `0033` partial unique open reservation index | Present; upgrade dedupes then creates `ux_spend_reservations_open_run_stage` |
| `alembic check` | **FAIL** (autogenerate noise / model Index metadata) — **not** a broken revision chain |

---

## Security summary

| Area | Result |
|------|--------|
| Workspace RLS + FORCE RLS (billing, spend, runs, gates, assignments) | **PASS** |
| Billing webhook table: FORCE RLS, no `app_runtime` grants | **PASS** |
| JWT verification (secret, aud, alg) | **PASS** |
| Metrics production without token | **401** |
| Isolated pip-audit API/worker | **0 vulns** |
| npm audit `--audit-level=high` | **0 vulns** |
| Human Review Gate resurrection (C-1) | **Fixed + tested** |

---

## CI summary

| PR | Jobs | Notes |
|----|------|-------|
| #35 (prior tip `9e61caf`) | api / worker / web / security / docker-build **SUCCESS** | Pre-gate-fix tip |
| #34 | Prior tip green | Does **not** include C-1/H-* gate fixes |
| Post-fix tip | Must show green after push of this audit commit | Required before merge |

Docker build: not runnable in this agent host (`docker` absent); rely on GitHub Actions `docker-build` job.

---

## Confidence score

**88%** — Critical HRG resurrection and High spend/idempotency defects were reproduced on real Postgres and fixed with regression tests; full suites and isolated dependency audits pass. Residual uncertainty: concurrent Stripe/review races under production load, `alembic check` metadata drift, and ops misconfiguration paths (billing left off / local auth break-glass) which are Medium by design.

---

## Required merge checklist

1. Merge **PR #35** into `cursor/p2-beta-launch-b52d`  
2. Confirm CI green on updated PR #34  
3. Merge **PR #34** → `main`  
4. Do **not** merge #34 without #35
