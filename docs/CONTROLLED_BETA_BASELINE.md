# Controlled Beta Baseline

**Baseline status:** Merged, verified, and not deployed

| Field | Value |
|---|---|
| Approved executable SHA | `c4c501b61dea23f036560d6473c85cd848f4aadc` |
| PR #44 final head | `aa906e5c42f313057e0b851c000553a7f8dc5c7a` |
| Main merge SHA | `64974855ddabfda2ff05de4069d93c0178f58acc` |
| Final main executable baseline SHA | `64974855ddabfda2ff05de4069d93c0178f58acc` |
| Migration head | `0040` |
| Main CI | [Run 32578620932](https://github.com/royalindustry94-crypto/actions/runs/32578620932) — API, worker, web, security, and Docker successful |

## Scope of this baseline

The controlled-beta baseline contains the audited executable tree approved at `c4c501b…`. PR #44’s final head and the merge commit contain only additional audit and verification documentation after that executable SHA; they introduce no executable, migration, infrastructure, security-control, Human Review Gate, spend, worker, billing, tenant-isolation, or frontend behavior change.

The merged repository passed migration replay and drift verification at head `0040`; targeted post-merge control validation passed 63 API tests, worker lint and 4 tests, and frontend lint, production build, 25 tests, and dependency audit. Critical findings are 0 and High findings are 0 in repository scope.

## Non-negotiable beta boundaries

| Boundary | State |
|---|---|
| Live billing | **Disabled.** Keep `BILLING_ENABLED=false`. |
| Automatic external publishing | **Disabled.** A reviewed item is publish-ready only; no automation may substitute for the required human release decision. |
| Human Review Gate | **Mandatory.** Approval is bound to the exact reviewed immutable content version. |
| Public deployment | **Not performed.** |
| Tester invitations | **Not performed.** |
| Production-readiness claim | **Not permitted.** |

## Remaining external blockers

A deployment operator must first provide managed recovery/PITR evidence, hosted metrics authentication proof, an approved deployment environment and rollback owner, and a decision on beta data-loss-risk acceptance. Billing requires a separate authorised Stripe reconciliation drill. Commercial validation and realised unit economics require actual controlled-beta evidence, not repository assumptions.

## Next gate

The next gate is an authorised, non-public deployment verification against the exact merged executable baseline. No deployment action is authorized by this document.
