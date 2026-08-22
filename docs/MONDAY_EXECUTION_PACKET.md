# Monday Execution Packet — Lumora Private Beta

**Prepared:** 2026-08-21 GMT+8
**GitHub source of truth:** [`royalindustry94-crypto/Content-orchestrator`](https://github.com/royalindustry94-crypto/Content-orchestrator)
**Pull request:** [#44](https://github.com/royalindustry94-crypto/Content-orchestrator/pull/44) — **OPEN**, base `main`, head `audit/closure-evidence-0035`, merge state **CLEAN**.
**CI-validated audit-branch SHA:** [`b6757c9ae4138d706a274341e2552116b3d4dd73`](https://github.com/royalindustry94-crypto/Content-orchestrator/commit/b6757c9ae4138d706a274341e2552116b3d4dd73).
**Hosted validation:** [CI run 32489120577](https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/32489120577): API, worker, web, security, and Docker build all succeeded.

> **Release authority is not granted by this packet.** The SHA above is the exact reviewed and CI-validated branch head. The Founder must explicitly approve it for deployment or merge. Do not merge the PR, push to `main`, enable billing, or enable automatic external publishing as part of this handoff.

## 1. Monday objective

Deploy **only if authorised** the exact SHA above to a controlled private-beta environment, then admit no more than the approved first-wave tester cohort. The beta workflow remains:

> **Idea/input → generation → processing → Human Review Gate → approval or rejection → publish-ready output → analytics review.**

The release is not production-ready. It is not a commercial launch. It does not authorise live billing or automatic posting to external platforms.

## 2. One instruction for Cursor/Replit

```text
Act as Lumora release operator. GitHub is the only source of truth. Read docs/MONDAY_EXECUTION_PACKET.md, docs/MONDAY_DEPLOYMENT_RUNBOOK.md, docs/BETA_GO_NO_GO_CHECKLIST.md, docs/AUDIT_FINDING_CLOSURE.md, and PR #44 before acting. The CI-validated audit-branch SHA is b6757c9ae4138d706a274341e2552116b3d4dd73, but deploy it only after I explicitly approve it. Do not merge, force-push, write to main, enable live billing, enable automatic external publishing, or reveal secrets. Inspect the deployment provider and secret store without printing values. If required access, backup/PITR evidence, or approved SHA is missing, stop with BLOCKED — EVIDENCE UNAVAILABLE. Follow the deployment runbook preflight, backup, migration, API, worker, web, health, HRG, spend, and Mission Control checks. Preserve the current deployment reference for rollback. Report executed commands, deployed SHA, migration head, health, worker state, and any blocker. Do not invent or substitute a provider, secret, customer, cost, or test result.
```

## 3. What is verified on the audit branch

| Area | Evidence |
|---|---|
| Independent security fixes | HRG approval reuse across content items was reproduced and closed; locked-account timing leak was reproduced and closed. [1] |
| Local API gate | 264 tests passed with 78.13% coverage; lint and Alembic drift check passed. |
| Focused adversarial controls | 121 tests passed across cross-tenant isolation, HRG, governance, metrics/auth, spend, recovery, and claiming. [1] |
| Worker/web | Worker lint + 4 tests passed; web lint, production build, 23 tests, and high-severity dependency audit passed. |
| Hosted CI | Exact SHA CI run succeeded across API, worker, web, security, and Docker build. [2] |
| Private-beta materials | Operator runbook, onboarding, feedback, incident, go/no-go, recruitment, economics, Mission Control, and deployment package are committed on the SHA. |

## 4. Founder decisions required before deployment

| Decision | Required Founder action | Default if no decision |
|---|---|---|
| Release authority | Explicitly approve the SHA for the intended beta environment. | Do not deploy or merge. |
| Environment | Name the deployment provider/environment and authorised operator. | **BLOCKED — EVIDENCE UNAVAILABLE.** |
| Backup/PITR risk | Provide managed backup/PITR drill evidence or explicitly accept the stated beta data-loss risk. | Do not claim rollback readiness. |
| Beta cohort | Approve initial cohort cap and named operator/reviewer coverage. | Do not invite testers. |
| Billing | Keep `BILLING_ENABLED=false`. | No live billing. |
| External publishing | Keep automatic publication disabled; outputs remain publish-ready only. | No automatic posting. |

## 5. Mandatory no-go checks at deployment time

| Gate | Pass condition | Evidence owner |
|---|---|---|
| Source/CI | Exact approved SHA is clean and the corresponding required checks remain successful. | Release operator. |
| Database | Intended `DATABASE_URL` owner path and `APP_DATABASE_URL` runtime path are verified; runtime remains `app_runtime`. | Database owner. |
| Recovery | Managed recovery point/backup and rollback reference recorded. | Platform/database owner. |
| Secrets | Required secret names exist in approved store; values are never printed. | Deployment owner. |
| Billing/publish boundaries | Billing disabled; automatic external publish path absent. | Founder/operator. |
| Health | `/health/live`, `/health/ready`, `/health/automation`, worker state, and Mission Control agree. | Beta operator. |
| Metrics | Tokenless deployed `/metrics` request is `401`, without exposing the token. | Operations owner. |
| HRG/spend | Disposable authorised smoke confirms exact-item HRG, no automatic publish, and truthful spend/worker state. | Engineering/operator. |

## 6. Unresolved blockers and their owners

| Blocker | State | Owner and required action |
|---|---|---|
| Managed database backup/PITR restore | **BLOCKED — EVIDENCE UNAVAILABLE.** | Platform/database owner: run authorised managed restore drill; record recovery point, RPO, RTO, integrity checks, and sign-off. |
| Live billing reconciliation | **BLOCKED — EVIDENCE UNAVAILABLE.** | Billing owner: keep disabled; perform authorised Stripe drill before any activation. |
| Deployment-specific metrics verification | PARTIALLY CLOSED. | Operations owner: record tokenless `401` from deployed environment. |
| Customer validation and WTP | **BLOCKED — EVIDENCE UNAVAILABLE.** | Founder/product: recruit qualified testers, capture actual workflow/feedback, and do not claim validation before cohort evidence. |
| Provider invoices and realised unit economics | **BLOCKED — EVIDENCE UNAVAILABLE.** | Founder/FinOps: reconcile actual invoices/usage through `BETA_COST_MEASUREMENT_SPEC.md`; no price or margin claim yet. |

## 7. First-week operating sequence

| Time | Action | Artefact |
|---|---|---|
| Before first deploy | Complete `BETA_GO_NO_GO_CHECKLIST.md` and deployment preflight. | Access-controlled release record. |
| Day 0 | Deploy authorised SHA; perform disposable workspace smoke; verify Mission Control. | `MONDAY_DEPLOYMENT_RUNBOOK.md` log. |
| Day 1 | Invite only the approved first wave; complete tester onboarding and baseline workflow. | `BETA_TESTER_ONBOARDING.md`, lead record. |
| Per workflow | Record intentional start, HRG result, spend/failure state, and feedback link. | `BETA_OPERATOR_RUNBOOK.md` operator log. |
| Daily | Review health, alerts, worker/DLQ, HRG queue, spend, and incidents. | Operator log / incident record. |
| Weekly | Review activation, completion, accepted output, repeat use, technical failure, cost, and WTP evidence. | `PRIVATE_BETA_VALIDATION_PLAN.md`. |

## 8. Essential document map

| Need | Document |
|---|---|
| Exact deployment procedure | [Monday Deployment Runbook](MONDAY_DEPLOYMENT_RUNBOOK.md) |
| Launch gate | [Beta Go / No-Go Checklist](BETA_GO_NO_GO_CHECKLIST.md) |
| Daily operation | [Beta Operator Runbook](BETA_OPERATOR_RUNBOOK.md) |
| Incident response | [Beta Incident Playbook](BETA_INCIDENT_PLAYBOOK.md) |
| Tester onboarding/feedback | [Tester Onboarding](BETA_TESTER_ONBOARDING.md) and [Feedback Form](BETA_FEEDBACK_FORM.md) |
| Recruitment | [Founding-Tester Recruitment Plan](BETA_TESTER_RECRUITMENT.md) and CSV template |
| Economics | [Beta Cost-Measurement Specification](BETA_COST_MEASUREMENT_SPEC.md) and `scripts/beta_cost_model.py` |
| Audit evidence | [Final Adversarial Review](FINAL_ADVERSARIAL_REVIEW.md) and [Closure Register](AUDIT_FINDING_CLOSURE.md) |

## References

[1]: [Final Adversarial Review](FINAL_ADVERSARIAL_REVIEW.md)
[2]: [GitHub Actions CI run 32489120577](https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/32489120577)
[3]: [PR #44](https://github.com/royalindustry94-crypto/Content-orchestrator/pull/44)
