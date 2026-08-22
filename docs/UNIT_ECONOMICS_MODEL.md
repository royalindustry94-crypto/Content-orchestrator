# Unit Economics Model — v0.1 (Evidence-Bounded)

**Model version:** `0.1`
**Reference date:** 2026-08-18 GMT+8
**Candidate basis:** `c91d9d3a3530b944801c50ad8f2be77879101e49`
**Currency:** USD
**Scope:** One HRG-approved content output from the private-beta core workflow.

> **Evidence boundary:** The repository defines spend-control fields and default workspace caps but does not provide production provider invoices, token/media usage, storage bills, support costs, pricing, customer volume, or actual acceptance data. Therefore, this is a **parameterized operating model**, not a measured P&L, forecast, valuation, or pricing recommendation. Any blank input must remain blank until measured or sourced from an approved provider price sheet.

## Known repository-side inputs

| Input | Value / status | Basis |
|---|---|---|
| Currency convention | USD | Spend and billing fields are USD-labelled in repository configuration. |
| Default daily spend cap | `$50.00` | `.env.example`; default only, not observed spend. |
| Default monthly spend cap | `$1,000.00` | `.env.example`; default only, not observed spend. |
| Spend authorization | Reservation and commit/release lifecycle | Local candidate test suite passed cost cap, duplicate reservation, idempotent commit, and retry-related regression coverage. |
| Billing default | Disabled | Candidate configuration/code documentation. No live activation proof. |
| Actual provider price / usage | BLOCKED — EVIDENCE UNAVAILABLE | No selected-provider price sheet, invoice, or production usage cohort supplied. |

## Per accepted-output cost model

Let `A` equal the number of HRG-approved outputs in the period. Let each stage use actual provider cost attributable to that output. Do not estimate from list prices when actual provider usage records are available.

| Component | Variable | Formula per accepted output | Required source | Current state |
|---|---:|---|---|---|
| Script / LLM | `C_llm` | `(input_tokens × input_rate + output_tokens × output_rate) / A` | Provider usage record and approved pricing basis | BLOCKED |
| Speech / TTS | `C_tts` | `characters_or_minutes × rate / A` | Provider usage record | BLOCKED |
| Visual generation / licensing | `C_visual` | `generation_calls × rate + licensed_asset_cost` divided by `A` | Provider/asset invoice or usage data | BLOCKED |
| Rendering / transcoding | `C_render` | `render_minutes × rate / A` | Render-provider usage record | BLOCKED |
| Storage / egress | `C_storage` | `(GB-month × rate + egress × rate) / A` | Storage bill | BLOCKED |
| Publishing / platform operations | `C_publish` | destination/API/provider cost divided by `A` | Provider contract and usage | BLOCKED |
| Retry and failed-work cost | `C_failure` | `(cost of failed attempts + charged retries − recoveries/credits) / A` | Reservation/commit/release and provider-effect ledger | PARTIALLY CLOSED in code; BLOCKED for real values |
| Support allowance | `C_support` | `(support labor cost + tooling) / A` | Time tracking and tooling bills | BLOCKED |
| Shared infrastructure | `C_infra` | period hosting, monitoring, database, and security cost / `A` | Infrastructure invoices | BLOCKED |
| Total cost per accepted output | `C_total` | `C_llm + C_tts + C_visual + C_render + C_storage + C_publish + C_failure + C_support + C_infra` | All above | BLOCKED |

## Workflow-stage and retry model

| Stage | Provider / unit | Success cost variable | Failure / retry rule | Financial safety requirement |
|---|---|---:|---|---|
| Input validation / planning | Internal compute | `C_plan` | No paid action before authorization. | Workspace and action context required. |
| Generation | Model/provider units | `C_llm` | Retry only when bounded and idempotent; record provider effect. | Reserve before paid effect; no duplicate charge for same idempotency key. |
| TTS / visual / render | Provider units | `C_tts`, `C_visual`, `C_render` | Retry cost must be separately attributable. | Reservation must cover highest permitted charged effect or the stage fails closed. |
| HRG | Reviewer labor | `C_review` | Rejection is not a successful output; rework is a new tracked cost. | No publish without an authorized decision. |
| Publish / analytics | Destination/provider units | `C_publish`, `C_monitor` | Failure must not trigger unbounded duplicate publication. | Provider-effect/idempotency and HRG version binding. |

## Pricing hypotheses and margin formulas

No production price is selected in this repository. Keep each hypothesis separate from actual results.

| Hypothesis | Monthly price `P` | Included accepted outputs `I` | Overage / throttle | Gross-margin formula | Evidence state |
|---|---:|---:|---|---|---|
| Private-beta learning plan | TBD | TBD | Default to throttle/approval, not automatic overage billing | `(recognized_revenue − total attributable cost) / recognized_revenue` | BLOCKED |
| Standard recurring plan | TBD | TBD | `overage_price` only after verified billing and metering | `(P + overage_revenue − cost) / (P + overage_revenue)` | BLOCKED |
| High-usage plan | TBD | TBD | Require cap, concurrency limit, and manual commercial review | Same formula with customer-specific costs | BLOCKED |

**Target gross margin:** TBD. A target cannot be responsibly chosen until at least one measured accepted-output cost distribution exists. For a planned margin `GM_target`, the maximum included-cost envelope is `P × (1 − GM_target)`. A high-usage breakpoint occurs when forecast attributable cost exceeds that envelope; the system must throttle, require approval, or apply a verified contractual overage policy before service continues.

## Measurement and reconciliation contract

| Event | Minimum fields | Reconciliation check |
|---|---|---|
| Spend reservation | workspace, run, stage, provider, estimate, idempotency key, timestamp | One open reservation per `(run, stage)` where enforced; caps include reserved and committed cost. |
| Provider effect | workspace, provider, provider-effect/idempotency reference, outcome, charged amount if known | Duplicate retries must not silently create a second chargeable effect. |
| Spend commit / release | reservation ID, actual cost, status, timestamp, reason | Actual cannot exceed authorized reservation without explicit safe policy; terminal failures release open reservations. |
| HRG decision | version, decision, reviewer, timestamp | Only approved versions count in `A`; rejected/reworked cost remains visible. |
| Publish outcome | destination, version, provider response ID, timestamp | Reconcile successful publish count to approved/version-authorized actions. |
| Invoice / provider bill | provider period, SKU/unit, amount, credits, tax where applicable | Reconcile aggregate ledger to invoice; unexplained variance blocks pricing expansion. |

## Required next evidence

1. Select actual providers and record the contractual/list-price basis, rate units, region, and billing period.
2. Instrument provider usage and provider-effect outcomes by workspace/run/stage/version.
3. Reconcile a closed monthly provider bill to the internal spend ledger before setting included usage or overage pricing.
4. Measure HRG-approved output rate and failure/retry distribution for a real beta cohort.
5. Obtain authorized support and infrastructure cost allocation before presenting a gross-margin claim.
6. Keep live billing disabled until webhook, entitlement, reconciliation, and production-key evidence are complete.
