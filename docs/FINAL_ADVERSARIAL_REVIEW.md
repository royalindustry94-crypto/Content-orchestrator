# Final Independent Adversarial Review

**Review target before this pass:** audit branch `audit/closure-evidence-0035` at `8c2ecb0bcd4013e1416a4ec138592300bd22100f`.

**Review method:** independently inspect the branch delta, migrate a real local PostgreSQL database down to base and back to head, run focused adversarial regressions, then run an expanded control suite covering tenant isolation, Human Review Gate, spend, lease recovery, publication policy, governance, metrics, authentication, and repository-secret patterns. Documentation was treated as a claim only; a control was promoted only after direct execution.

## Newly reproduced defects

| ID | Severity | Reproduction | Result before fix | Fix | Regression evidence |
|---|---|---|---|---|---|
| AR-01 | High | Create content item A with an approved HRG; create item B in the same workspace; attach A's gate to B's otherwise complete publication-eligibility record; call the single publish gate. | `assert_publishable` returned success instead of raising `PublicationBlocked`. An approved gate was functioning as a workspace-wide capability, not an exact-item decision. | `publication_policy.assert_publishable` now loads the gate's `PipelineRun` and fails closed unless its `content_item_id` matches the requested item. | `test_approved_gate_for_a_different_item_cannot_authorize_publication`; full publication-policy suite: 16 passed. |
| AR-02 | Medium | Lock a known local-auth credential, instrument `verify_password`, then invoke `local_auth.login` with a bad password. | Locked-account path returned generic failure without PBKDF work, while ordinary/unknown failures performed verification. This created a measurable lockout-status/account-existence timing signal. | Locked-account path now verifies against the stored password hash before returning the generic failure. | `test_mf_locked_account_keeps_password_work_timing_equalized`; security and publication control suites: 36 passed. |

No migration was needed for either remediation. Neither fix weakens tenant isolation, spend controls, Human Review Gate requirements, or production-auth defaults.

## Independent control evidence

| Control area | Direct evidence | Result |
|---|---|---|
| Migrations / schema | `alembic downgrade base`, `alembic upgrade head`, and `alembic check` against isolated PostgreSQL. | Passed; no metadata drift. |
| API release gate | `ruff check app tests`; complete coverage-gated suite. | 264 passed; 78.13% total coverage; 75% gate passed. |
| Adversarial control suite | Cross-workspace isolation, review decisions, data governance, publication policy, local auth/metrics, spend, recovery, and claiming tests. | 121 passed in focused independent pass. |
| Worker/web gates | Worker lint/tests; web lint/build/tests/dependency audit. | 4 worker tests passed; web build passed; 23 web tests passed; no high-severity npm audit finding. |
| Dependency scan | API and worker dependency lock generation plus `pip-audit`. | No known vulnerabilities found. |
| Repository credential patterns | Tracked app/script pattern scan after preview-default remediation. | No non-test hard-coded credential literal found. |
| Secret history scan | Local `gitleaks` executable was unavailable. | **BLOCKED — EVIDENCE UNAVAILABLE** locally; the final hosted security job remains the required full-history evidence. |

## Findings not reopened by this review

The review did not find a new migration/RLS privilege widening, a new direct spend-cap bypass, a concurrent-HRG regression, or an owner-session cross-tenant route bypass. This is a limited result tied to the executed suites and code inspected; it is not a substitute for hosted-environment validation.

## Remaining non-repository boundaries

| Item | Evidence state | Required owner action |
|---|---|---|
| Managed database backup/PITR and restore | **BLOCKED — EVIDENCE UNAVAILABLE.** | Platform/database owner executes an authorised managed restore drill and records recovery point, RPO, RTO, integrity checks, and sign-off. |
| Live billing / Stripe delivery | **BLOCKED — EVIDENCE UNAVAILABLE.** | Billing owner performs authorised test/live reconciliation drill. Keep `BILLING_ENABLED=false`. |
| Hosted tokenless metrics request | PARTIALLY CLOSED. Code fails closed; deployment must prove `401` without token. | Operations owner records a deployment-specific check without exposing token. |
| Commercial validation / economics | **BLOCKED — EVIDENCE UNAVAILABLE.** No customer or provider-invoice data exists. | Follow beta recruitment and cost-measurement package; do not claim validation before measured cohort evidence. |

## Release statement

This pass closes **AR-01** and **AR-02** only after reproduction and regression coverage. It does **not** authorise merge, production launch, live billing, automatic external publishing, or deployment without the evidence gates in `BETA_GO_NO_GO_CHECKLIST.md` and `MONDAY_DEPLOYMENT_RUNBOOK.md`.

## References

[1]: [Audit Finding Closure Register](AUDIT_FINDING_CLOSURE.md)
[2]: [Open Finding Closure Report](OPEN_FINDING_CLOSURE_REPORT.md)
[3]: [Beta Go / No-Go Checklist](BETA_GO_NO_GO_CHECKLIST.md)
[4]: [Monday Deployment Runbook](MONDAY_DEPLOYMENT_RUNBOOK.md)
