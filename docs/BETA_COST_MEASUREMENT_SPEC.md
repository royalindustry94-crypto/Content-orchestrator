# Lumora Beta Cost-Measurement Specification

**Purpose:** make beta economics measurable from actual event records without inventing provider prices, customer revenue, support cost, or usage. The companion executable is `scripts/beta_cost_model.py`; it emits `N/M` whenever a required commercial input has not been supplied.

> **Current commercial evidence:** **BLOCKED — EVIDENCE UNAVAILABLE.** Lumora has no beta provider invoices, usage cohort, accepted-output cohort, paid revenue, support-time data, or approved price schedule. This specification is an input contract and measurement procedure, not a claim about cost, margin, or willingness to pay.

## 1. Metric definitions

| Metric | Formula | Required actual inputs | Output when inputs are missing |
|---|---|---|---|
| Cost per accepted output | `all workspace-attributable actual costs in period ÷ distinct content items with HRG status=approved in period` | Immutable cost events, exact HRG approval records, workspace/content IDs. Failed/retry costs are included. | `N/M` if approved-output count is zero. |
| Cost per workspace | `sum of all actual cost events for workspace/month` | Actual cost events grouped by workspace and UTC month. | `0` only when there are zero measured events; never infer a zero invoice. |
| Monthly gross margin | `(monthly revenue − actual workspace cost) ÷ monthly revenue` | Cost per workspace plus an authorised monthly revenue record. | `N/M` if revenue is absent or zero. |
| Cost by capability | Sum costs mapped to `llm`, `tts`, `image_video`, `render`, `storage`, `retry_failure`, `support`, or `other`. | Cost event bucket and immutable source record. | Bucket remains zero only if no measured event exists; it is not an estimate. |
| Retry/failure cost | Sum event costs where outcome is `failed`, `retry`, `timed_out`, or `dead_letter`. | Run/assignment outcome plus actual provider or operation cost. | `N/M` only if the event source cannot determine outcome. |
| Overage outputs | `max(accepted outputs − included accepted outputs, 0)` | Approved outputs plus an explicit approved pricing/threshold record. | `N/M` without a pricing record. |
| Throttle decision | `actual cumulative workspace cost ≥ approved throttle threshold` | Workspace actual cost and an explicit approved threshold. | `N/M` without an approved threshold. |

**Accepted output** means one distinct `content_item_id` with an **approved Human Review Gate** in the measurement period. A generation alone, a pending gate, a rejection, an external post, and a tester claim are not accepted-output evidence. An approval is exact-item/run bound and may not be reused.

## 2. Cost buckets and input map

| Bucket | What belongs in it | Existing Lumora source | Required mapping / gap |
|---|---|---|---|
| `llm` | Text-model prompts, completions, moderation, embeddings if paid. | `spend_logs` (`provider`, `stage`, `units`, `cost_usd`, `provider_metadata`); `provider_usage` (`operation`, `quantity`, `unit_type`). | Map provider operation/model metadata to `llm`; reconcile actual invoice/usage if internal cost differs. |
| `tts` | Speech synthesis, voice cloning, transcription when product-attributable. | Same spend/usage tables. | Map operation/unit type; do not place tester-provided external tools here. |
| `image_video` | Image/video generation and provider processing. | Same spend/usage tables plus asset provider metadata. | Map provider operation and asset source/type. |
| `render` | Rendering/transcoding/composition compute. | `provider_usage`; stage/run/assignment records; spend log if costed. | Record real compute/third-party render cost; if no price is known, measure usage and mark cost `N/M` until reconciled. |
| `storage` | Object storage and egress attributable to the workspace. | `assets.size_bytes`, `storage_provider`, `storage_bucket`, `storage_object_key`; provider invoice/export. | Daily asset snapshot plus approved invoice/rate allocation. Do not infer price from byte count alone. |
| `retry_failure` | Provider or compute costs consumed by retry, timeout, failure, or DLQ. | `stage_assignments`, `stage_recovery_audit`, `dead_letter_jobs`, spend/usage records. | Tag actual cost events with attempt/outcome; include them in COGS. |
| `support` | Measured operator/engineering support time assigned to a workspace. | **Not currently a product event.** | Operator appends an actual time/cost event; use an authorised fully-loaded rate only when one exists. |
| `other` | Explicit, attributable operational cost not covered above. | Spend log/provider invoice or operator record. | Requires source-record ID and reconciliation state; no catch-all estimate. |

## 3. What Lumora already captures

| Required dimension | Current repository record | Field(s) |
|---|---|---|
| Workspace attribution | `spend_logs`, `provider_usage`, assets, pipeline records, HRG. | `workspace_id` or workspace through related run/item. |
| Content attribution | Spend and usage can point to content; HRG and runs are content-bound. | `content_item_id`, `pipeline_stage_run_id`, `pipeline_run_id`. |
| Actual cost ledger | Immutable spend ledger. | `spend_logs.cost_usd`, `provider`, `stage`, `units`, `occurred_at`, `provider_metadata`. |
| Usage/metering | Immutable usage log. | `provider_usage.operation`, `quantity`, `unit_type`, `occurred_at`, `provider_metadata`. |
| Storage quantity | Asset storage metadata. | `assets.size_bytes`, storage provider/bucket/object key. |
| Retry/failure lineage | Assignment/recovery/DLQ and reservation history. | Attempt, status, recovery/audit records, dead-letter state. |
| Accepted output | Human Review Gate and pipeline/content linkage. | `review_gates.status`, `pipeline_run_id`, `content_item_id`, decision timestamp. |
| Analytics outcome | Workspace-scoped content analytics record. | `analytics_snapshots` content/platform/metric/value/timestamp. |

## 4. Measurement gaps and the required beta procedure

The repository does not automatically turn every provider invoice, storage rate, staff time, or price decision into a cost event. The operator must close the following gaps before reporting economics.

| Gap | Required operating action | Evidence standard |
|---|---|---|
| Provider invoice reconciliation | Export actual provider billing/usage for the period and reconcile to Lumora `spend_logs` / `provider_usage` by provider, workspace, time, request/effect key where available. | Retain source reference, reconciliation status, and variance explanation. |
| Storage price | Snapshot live non-deleted asset bytes by workspace/provider and apply an authorised invoice/rate source. | Record the billing period, rate source, byte snapshot, allocation basis, and cost event. |
| Rendering price | Reconcile actual render provider invoice or measured compute charge; tag by run/workspace. | No rate → usage only; cost must remain `N/M`. |
| Support allowance | Operator records actual support minutes per workspace/incident. Apply an authorised cost rate only after leadership approves it. | Time record, owner, activity, rate approval reference. |
| Revenue / included usage / overage | Founder records an explicit approved beta pricing or threshold row. Live billing remains disabled. | Approved pricing reference; no row means margin/overage/throttle model output is `N/M`. |
| External analytics | Tester supplies voluntary, consented metrics or an approved integration records them. | Source, timestamp, content ID, consent/authorisation basis. |

## 5. Normalized input contracts

The model uses three CSVs. Blank templates are committed in `docs/templates/`; they contain no dummy prices, customer values, or fabricated usage.

### A. Actual cost events — `beta_cost_events_template.csv`

Every row represents one immutable, attributable cost event. Event IDs must be unique. Costs must be actual reconciled amounts or remain out of the cost input until reconciled; do not place a reservation estimate in this file as actual cost.

| Required column | Rule |
|---|---|
| `event_id` | Immutable unique identifier; duplicates cause the CLI to fail. |
| `occurred_at_utc`, `workspace_id`, `content_item_id` | Required for workspace-month and accepted-output attribution. Use a documented surrogate only if a cost genuinely cannot map to an item. |
| `cost_bucket`, `cost_usd`, `outcome` | One allowed bucket; non-negative actual cost; outcome identifies success/retry/failure/timeout/DLQ. |
| `source_record_type`, `source_record_id`, `reconciliation_status` | Links the cost to a ledger row, provider invoice, support record, or other source. |
| Optional lineage | `pipeline_run_id`, `pipeline_stage_run_id`, provider, operation, unit, provider request ID, notes. |

### B. Approved outputs — `beta_accepted_outputs_template.csv`

One row per HRG decision record. The model includes only `hrg_status=approved` and rejects duplicate approved `(workspace, month, content item)` records.

### C. Pricing and thresholds — `beta_workspace_pricing_template.csv`

This optional file contains only Founder-approved numbers for a workspace/month: revenue, included accepted outputs, overage per accepted output, throttle threshold, and hard spend cap. It is intentionally blank until approved. It is not a billing activation mechanism.

## 6. Executable model procedure

Run the model after a measurement period closes. The command is deterministic and contains no provider-rate defaults:

```bash
python3 scripts/beta_cost_model.py \
  --cost-events docs/templates/beta_cost_events_template.csv \
  --accepted-outputs docs/templates/beta_accepted_outputs_template.csv \
  --pricing docs/templates/beta_workspace_pricing_template.csv \
  --output /secure/operator-workspace/beta_economics_YYYY-MM.csv
```

For a real run, copy the blank templates to an access-controlled operator workspace, replace only with measured records, and keep the result outside the repository if it includes customer-identifying information. The model fails on duplicate event IDs, duplicate approved-output records, unsupported buckets, negative costs, or missing required columns. It does not silently substitute estimates.

## 7. Usage thresholds, overage, and throttle strategy

Lumora must not invent commercial thresholds before beta data exists. The operating strategy is therefore parameterised rather than priced:

| Control | Input owner | Action when measured threshold is reached |
|---|---|---|
| Soft throttle threshold | Founder/FinOps-approved pricing row. | Pause new expensive stage claims for the workspace; investigate cost composition; obtain owner approval before resuming. |
| Hard spend cap | Existing workspace spend-cap control plus approved pricing row. | Preserve current fail-closed cap behaviour; do not override it to complete a beta task. |
| Included accepted outputs | Founder-approved pricing row. | Report overage output count only; do not bill or block without an approved beta policy. |
| Overage strategy | Founder/product decision after measured cost and WTP evidence. | Use reports to compare marginal cost with a proposed price; no charge is collected in this beta. |
| Retry/failure budget | Workspace cap plus incident threshold. | Treat a rising failure-cost share as an engineering pause signal, not a reason to raise the cap. |

## 8. Daily and weekly cadence

| Cadence | Owner | Action |
|---|---|---|
| Per workflow | Operator | Preserve run, HRG, spend, provider-effect, and failure identifiers. |
| Daily | Operator/engineering | Reconcile new spend/usage records, inspect open reservations, DLQ/retries, and storage growth; flag unreconciled cost as unknown. |
| Weekly | Founder/product + engineering | Run the CLI by workspace/month; compare cost per accepted output, failure cost, activation, completion, acceptance, repeat use, and feedback. |
| Monthly | Founder/FinOps | Review invoices and approved price/threshold inputs; decide continue, narrow, pause, or prepare a separate pricing decision. |

## 9. Integrity checks before publishing a beta economics report

1. Every cost event has a unique event ID, source record, workspace, UTC timestamp, and reconciliation state.
2. Reservation estimates are not counted as actual cost; only committed/reconciled actual events are included.
3. Failed/retry/DLQ costs are included rather than hidden.
4. Accepted-output numerator uses distinct approved content items, not generated drafts or external posts.
5. Cross-workspace cost records are not mixed; do not create a global blended number before workspace-level reconciliation.
6. Storage and support cost include their documented allocation basis.
7. Revenue, margin, overage, and throttle output is `N/M` if no approved input exists.
8. Provider invoice variance is disclosed rather than netted away.

## References

[1]: [Unit Economics Model](UNIT_ECONOMICS_MODEL.md)
[2]: [Private Beta Validation Plan](PRIVATE_BETA_VALIDATION_PLAN.md)
[3]: [Beta Operator Runbook](BETA_OPERATOR_RUNBOOK.md)
[4]: [Data Governance Baseline](DATA_GOVERNANCE.md)
