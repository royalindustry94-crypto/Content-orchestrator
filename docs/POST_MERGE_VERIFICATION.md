# Post-Merge Verification — Controlled Beta Baseline

**Date:** 2026-08-22 UTC

| Field | Recorded value |
|---|---|
| Approved executable SHA | `c4c501b61dea23f036560d6473c85cd848f4aadc` |
| PR | [#44](https://github.com/royalindustry94-crypto/Content-orchestrator/pull/44) |
| PR final head | `aa906e5c42f313057e0b851c000553a7f8dc5c7a` |
| Merge SHA | `64974855ddabfda2ff05de4069d93c0178f58acc` |
| Final main executable baseline SHA | `64974855ddabfda2ff05de4069d93c0178f58acc` |
| Migration head | `0040` |
| Main CI | [Run 32578620932](https://github.com/royalindustry94-crypto/actions/runs/32578620932) |

> The merge is a two-parent GitHub merge commit. The approved executable SHA and the PR final head are both ancestors of main. A tree comparison confirmed that main has no executable, infrastructure, or migration-path delta from the approved SHA; the post-approved commits are documentation-only.

## Verification results

| Check | Result |
|---|---|
| Main CI | **PASS** — API, worker, web, security, and Docker all succeeded. |
| Migration replay | **PASS** — downgrade to base, upgrade to head `0040`, then `alembic check` reported no new upgrade operations. |
| HRG regression suite | **PASS** — review decision and publication-version controls included in the 63-test targeted control set. |
| Tenant-isolation suite | **PASS** — cross-workspace/RLS coverage included in the 63-test targeted control set. |
| Spend/idempotency suite | **PASS** — cap, reservation, retry, and recovery controls included in the 63-test targeted control set. |
| Security controls | **PASS** — local-auth, runtime credential, metrics, and preview credential coverage included in the 63-test targeted control set. |
| Worker | **PASS** — lint and 4 tests. |
| Frontend | **PASS** — lint, production build, 25 tests, and high-severity dependency audit. |

## Finding and boundary status

**Critical findings:** 0 open in repository scope.

**High findings:** 0 open in repository scope.

The baseline retains all controlled-beta boundaries. `BILLING_ENABLED=false` remains the default. Automatic external publishing remains disabled. The Human Review Gate remains mandatory. No public deployment, tester invitation, billing activation, or production-readiness claim was made by this merge.

## Remaining external blockers

| Blocker | Required owner action |
|---|---|
| Managed recovery | Perform and sign off an authorised managed backup/PITR restore drill. |
| Hosted metrics | Record tokenless deployed `/metrics` returning `401` without exposing the token. |
| Billing | Keep disabled until an authorised Stripe reconciliation and entitlement drill completes. |
| Beta evidence | Obtain a qualified tester cohort, consented workflow outcomes, provider invoices, and realised cost/acceptance data. |

## Verdict

**CONTROLLED BETA BASELINE MERGED.** Deployment is the next gate and remains out of scope for this record.
