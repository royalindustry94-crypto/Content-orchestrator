# Tester #1 Private Beta Handoff

**Deployment baseline:** `6a5bc999129309a55b6ea1f088d9de708e94be6c` on `main`

**Executable baseline:** `c4c501b61dea23f036560d6473c85cd848f4aadc`

**Migration head:** `0040`

**Tester:** Founder / Tester #1
**State:** Workspace is **not created** until a non-public deployed environment, a real Founder identity, and backup/PITR evidence exist.

> This handoff prepares a real founder workflow. It does not create fake production data, activate billing, create platform credentials, publish externally, or claim TikTok performance that has not actually occurred.

## 1. Local preflight evidence

An isolated host-process verification was executed against the verified `main` revision and a fresh local PostgreSQL database. Docker Compose was unavailable in the sandbox, so this is deployment-equivalent evidence only, not a hosted deployment.

| Control | Result |
|---|---|
| Migration | Fresh database upgraded through `0040`; `alembic check` passed. |
| Health | `/health/live` and `/health/ready` returned `200`; `/health/automation` showed maintenance, outbox relay, and scheduler running with advancing ticks and no errors. |
| Metrics | Tokenless `/metrics` returned `401`; a bearer-authenticated scrape returned Prometheus text. |
| HRG | Disposable content job created an awaiting gate; approval persisted; second decision was rejected with `409`. |
| Isolation | Foreign tenant reads of dashboard, review gates, and health returned denial; unauthenticated read was denied. |
| Spend | Disposable workspace admin set a low reversible cap; a foreign tenant was denied the spend-cap update. |
| Worker and queue | One disposable credentialed worker registered, heartbeated, claimed safely, deregistered on shutdown, and appeared online in the operations worker monitor while automation remained healthy. |
| Restrictions | Local preflight used `BILLING_ENABLED=false`; no external publishing path or platform credential was configured. |

## 2. Founder workflow

The first real workflow is a **founder-owned AI-influencer TikTok content workflow**. Lumora is not permitted to publish it. The Founder performs publication manually outside Lumora only after approving the exact reviewed version.

```text
IDEA
  → DRAFT
  → CONTENT GENERATION
  → HUMAN REVIEW GATE
  → APPROVED
  → MANUAL PUBLISH BY FOUNDER
  → PERFORMANCE DATA PROVIDED WITH CONSENT
  → LEARNING / ITERATION
```

The minimum workflow is one real content job created in the Founder’s assigned workspace. Use a real topic and source material only after the deployed environment and identity are ready. Do not import credentials, TikTok cookies, or platform access tokens into Lumora for this beta.

## 3. Founder workspace setup after deployment

The named beta operator performs these steps only on the deployed, non-public URL:

1. Confirm deployment SHA, image identifier, migration `0040`, managed restore-point ID, and all deployment-smoke results are recorded.
2. Pre-provision the Founder identity using the selected deployed authentication path. Do not enable anonymous public signup.
3. Create exactly one workspace named by the Founder; assign the Founder as workspace administrator.
4. Set a conservative Founder-approved daily and monthly workspace spend cap through the Workspace Spend control. Record the initial values outside source control; do not use a global cap change.
5. Provision exactly one reference worker with a unique credential held only by the operator’s secret manager. Confirm worker registration/heartbeat in Mission Control.
6. Create the first real content job from the Founder’s own idea. The Founder reviews the resulting exact version in the Human Review Gate.
7. The Founder either approves or rejects the exact reviewed version. An approval means **publish-ready only**. The Founder performs any TikTok publication manually and records only voluntary, consented performance data later.
8. After the attempt, complete `docs/BETA_FEEDBACK_FORM.md` using real workspace, content item, pipeline run, and review-gate identifiers.

## 4. Measurement matrix

| Measurement need | Existing repository source | Beta operating procedure | Boundary |
|---|---|---|---|
| Ideas and drafts generated | Content jobs, pipeline runs, content items, and content versions | Count real workflow records by workspace and period. | Do not infer ideas from external posts. |
| Approval and rejection rates | `review_gates.status`, decision timestamp, content/run linkage | Use every final HRG decision for the workspace; divide by decided gates only. | Pending gates are not approvals or rejections. |
| Regeneration rate | Content-version and pipeline/run lineage | Count additional generated versions/runs for the same real content item and record reason in feedback. | Revisions must not be conflated with independent ideas. |
| Human edits required | Founder feedback form: outside-Lumora steps, active/review minutes, friction and comments | Founder records whether material edits were needed, what changed, and review time. | There is no automatic semantic edit detector; do not fabricate one. |
| Idea-to-approved time | Content/job/run creation time plus approved HRG decision time | Calculate elapsed time for each approved item. | Exclude incomplete/rejected items from the approval-time numerator. |
| LLM, generation, render, and retry cost | `spend_logs`, `provider_usage`, assets, assignments, recovery/DLQ lineage | Reconcile actual provider invoices/usage to immutable source records; classify in the cost-event template. | Reservation estimates are not actual cost. |
| Cost per approved asset | `scripts/beta_cost_model.py` plus approved HRG rows | Run against real measured CSV extracts after the measurement period. | Output remains `N/M` without reconciled actual costs. |
| Failures and retries | Stage assignments, recovery audit, dead letters, spend/usage records | Preserve identifiers and include retry/failure cost events rather than hiding them. | Do not turn failures into successful outputs. |
| HRG decisions | Review-gate records and audit/outbox events | Review each decision in the workspace timeline. | Approval is item/version-bound; it does not permit autonomous publication. |
| TikTok performance | Consent-based Founder-provided performance data or an explicitly approved future integration | Record source, timestamp, content ID, and consent basis after manual publication. | No TikTok result may be invented or implied before the Founder supplies it. |

## 5. Economics procedure

Use the committed blank templates outside source control with only measured records:

```bash
python3 scripts/beta_cost_model.py \
  --cost-events /secure/operator/beta_cost_events.csv \
  --accepted-outputs /secure/operator/beta_accepted_outputs.csv \
  --pricing /secure/operator/beta_workspace_pricing.csv \
  --output /secure/operator/tester1_economics_YYYY-MM.csv
```

The output is valid only after actual provider cost reconciliation and HRG-approved-output extraction. Revenue, margin, pricing, overage, and throttle fields remain `N/M` until the Founder supplies an approved pricing/threshold record. Billing stays disabled.

## 6. Hard beta boundaries

| Boundary | Required state |
|---|---|
| Billing | `BILLING_ENABLED=false`. |
| Publishing | No automatic external publication, platform credential, or posting action. |
| Human Review Gate | Mandatory before any item becomes publish-ready. |
| Authentication | No public signup. Founder identity is provisioned deliberately. |
| Data | No seed/fake production records. Local smoke data is disposable and is not the Founder workspace. |
| Deployment | Non-public URL and allowlisted access only. |

## 7. Tester #1 admission gate

Tester #1 is eligible only when the deployed URL, not the local preflight environment, has documented evidence of managed backup/PITR restore, health and automation checks, tokenless metrics `401`, authenticated metrics, HRG/isolation smoke, spend smoke, worker/queue smoke, billing false, automatic publishing disabled, and the operator-created Founder identity/workspace.

## References

[1]: [Controlled Beta Deployment Preparation](CONTROLLED_BETA_DEPLOYMENT.md)
[2]: [Beta Cost Measurement Specification](BETA_COST_MEASUREMENT_SPEC.md)
[3]: [Beta Feedback Form](BETA_FEEDBACK_FORM.md)
[4]: [Beta Operator Runbook](BETA_OPERATOR_RUNBOOK.md)
