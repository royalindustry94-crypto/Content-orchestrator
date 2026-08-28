# The Business Manager V2 — Product Architecture

**Status:** Founder Preview architecture and limited interface implementation plan.  
**Scope:** Disposable preview only. **Do not merge without explicit Founder visual approval.**  
**Operating promise:** *We get it sorted.*

## Product position

The Business Manager is a **business operating system powered by an AI workforce**. Content orchestration remains an important department, but it is no longer the complete product identity. The operating interface must translate technical detail into five practical founder questions: what happened, what it cost, what it made, what needs the founder now, and what the system recommends.

The V2 preview implements only the opening experience, Home information architecture, a truthful financial hero shell, What Needs You, an AI Workforce summary, and navigation restructuring. It does not introduce a new financial ledger, Business Brain schema, autonomous worker department, recurring research job, content-audit engine, engagement automation, billing, or automatic publishing.

> **Truthfulness rule.** A value is displayed as measured only when it comes from a workspace-scoped durable source. When the required source does not exist or is disconnected, the interface must say **Connect your financial data to see profitability**, **Not configured**, **Not connected**, or **No data**. It must never substitute `$0`, estimated profit, simulated worker activity, or a synthetic completion percentage.

## V2 information architecture

| Surface | Founder question answered | Existing truthful sources | V2 preview behavior |
|---|---|---|---|
| **Launch** | What product did I open? | Session entry and local accessibility preference | A premium TB launch moment that immediately transitions to Home without delaying app readiness or replaying during ordinary navigation. |
| **Home — Financial hero** | Is my business making money? | No complete workspace financial ledger; provider spend exists; Stripe invoice-webhook revenue is conditional and not business profit. | A visual gradient-donut shell with range controls and a connected-data call to action instead of invented revenue, expenses, profit, or margin. |
| **What Needs You** | What must I decide now? | Human Review Gates, operation alerts, pipeline/assignment failure, worker availability, spend warning, failed webhooks. | Severity-ordered, actionable founder decisions only. |
| **AI Workforce summary** | What departments are working and what is blocked? | Worker registry, liveness, assignments, queue, retries, worker logs, activity, health. | Truthful real-worker summary plus clearly labelled department roles that are not yet configured. |
| **Content department** | Where is content and what evidence exists? | Pipeline runs, stage assignments, content versions, review gates, assets, outbox, worker logs. | Existing Content Pipeline and Human Review screens remain available through navigation; no audit-tab backend is claimed in V2. |
| **Business context** | What do workers know about my business? | Workspace identity only; no workspace Business Brain. | A future architecture boundary, visibly not configured until a schema and controlled context projection exist. |
| **Advanced operational detail** | Why did this happen and how can it be investigated? | Mission timeline, live logs, system health, cost control, worker timeline, existing controlled actions. | Preserved in drill-down routes rather than forcing technical infrastructure into the Home hierarchy. |

## Capability matrix

### Financial intelligence

| Capability | State | Existing evidence | V2 decision |
|---|---|---|---|
| Provider and AI spend by day, week, month, and provider | **EXISTS** | Workspace-scoped `spend_logs`, `spend_caps`, operations spend and cost-control read models | Reuse only in operating/drill-down views. |
| Daily/monthly budget remaining | **EXISTS** | Existing cap reads and locked reservation enforcement | Reuse for spend warnings and later financial intelligence. |
| Revenue month-to-date from stored billing receipts | **PARTIAL** | Existing billing-webhook aggregation; billing is disabled in the preview | Do not present as business profitability. |
| Workspace operating revenue sources | **MISSING** | No revenue-source records or financial connector model | Require a source-of-truth financial ingestion model. |
| Operating expenses, advertising spend, and production cost allocation | **MISSING** | Only provider spend is durable today | Require workspace-scoped expense and allocation records. |
| Net profit, margin, ROI, cost per lead/acquisition | **MISSING** | Inputs and attribution rules do not exist | Render connected-data shell; defer calculation. |
| Financial connector and reconciliation boundary | **DEFER** | No provider integration selected | Add provider adapters, imports, reconciliation, and audit source metadata after Founder approval. |

### Workforce and content assurance

| Capability | State | Existing evidence | V2 decision |
|---|---|---|---|
| Worker identity, liveness, heartbeats, drain, credentials, and soft deregistration | **EXISTS** | `worker_registry`, `worker_heartbeats`, credential lifecycle, server-side liveness | Reuse for truthful workforce summary. |
| Assignment claiming, leases, idempotency, bounded retry, recovery, and dead-letter handling | **EXISTS** | Stage assignments, scheduler, recovery, provider-effect keys, claim audit | Preserve unchanged. |
| Worker logs, durable activity, timeline, live logs, and asset evidence | **EXISTS** | Worker log, outbox, mission/activity/timeline services | Reuse for drill-down evidence only. |
| Draft writing capability | **PARTIAL** | Draft Desk supports narrow idea/scripting output and refuses the human-gated review stage | Do not describe as a general Writer department. |
| Scout, Strategist, Producer, Compliance, Chief Auditor, and Analyst runtime departments | **MISSING** | No verified executor, role registry, or output model for these departments | Render **Not configured**; do not simulate work. |
| Six/seven-role workforce-to-worker mapping | **MISSING** | Worker registry stores generic process identity and supported stages, not business department role | Require a workspace-scoped role binding with clear capability declaration. |
| Per-worker cost, inputs, outputs, permissions, and restrictions | **PARTIAL** | Assignment/timeline/effects and provider spend exist, but no per-worker spend or role policy model | Defer dedicated detail API until role binding is added. |
| Content audit-chain records and audit evidence UI | **PARTIAL** | Version-bound Human Review, worker logs, stage runs, assets, outbox events exist; no audit record model or audit tab | Document the target model; do not claim it exists. |
| Chief Auditor gate | **MISSING** | No independent required-evidence evaluator or terminal audit chain | Defer until audit records and version/hash verification are modeled. |

### Business context and engagement

| Capability | State | Existing evidence | V2 decision |
|---|---|---|---|
| Workspace identity and membership | **EXISTS** | Workspace and membership models with RLS/guarded APIs | Reuse as the tenancy root. |
| Business Brain | **MISSING** | User profile contains identity fields only; it is not workspace business context | Define schema/API design; do not hardcode founder information. |
| Controlled prompt projection | **MISSING** | No allow-listed context projection service | Require secret-excluding projection and audit before workers consume Business Brain. |
| Engagement provider boundary | **DEFER** | No existing engagement provider | Document adapters for DM/comment/lead/inbox providers; do not build a Manychat clone. |
| Performance-data connector | **DEFER** | No platform performance connector | Keep analyst outcomes as **Not connected/No data**. |

## Home data contract

The V2 Home is intentionally a composition of existing read models, not a backend redesign. The first release uses the current executive, pipeline, alerts/notifications, activity, health, worker-monitor, spend, and cost-control responses. These endpoints already use a workspace identifier guarded by membership checks and database RLS paths.

The financial hero has a strict contract: it does not calculate profitability unless a future `FinancialSnapshot` is complete and reconciled for the selected range. Until then, its state is `unavailable`, its presentation is the requested gradient-donut shell, and its copy asks the founder to connect financial data. Existing provider spend may be displayed separately as an operating cost only when the existing spend API returns it; it is not silently promoted into total expenses or profit.

The What Needs You view is derived from durable operating conditions. Human Review required, failed workflows, offline workers, failed webhooks/connections, queue pressure, and spend warnings map from existing alerts and review counts. Compliance blocks and important business decisions are shown only when a future durable source exists; their absence is not inferred from a zero count.

## AI Workforce operating model

The target workforce is organized as business departments: Scout, Strategist, Writer, Producer, Compliance, Chief Auditor, and Analyst. A department name is a product concept; it becomes an active worker only after a workspace-scoped role binding, an executable bounded capability, and a durable evidence/output model exist.

The current architecture safely supports a **truthful workforce summary**. Generic registered workers can report server-derived liveness, current assignment, queue, retry count, completed and failed assignments, last heartbeat, and lease status. Department cards without an actual configured role binding must show **Not configured** and must not display synthetic task text, progress, costs, outputs, or activity.

All future worker execution remains a bounded job. A job must have a workspace, role, trigger, allow-listed input, bounded objective, maximum attempts, timeout, spend reservation/budget, output reference, state transitions, timestamps, and immutable/auditable event trail. Recurring research is not implemented: the existing scheduler fails honestly for `RECURRING` jobs because there is no policy producer. The disposable preview leaves autonomous research off.

## Content assurance and Human Review

The target content assurance sequence is:

```text
Creator worker → independent auditor(s) → Chief Auditor → Human Review Gate → Founder decision → Manual publish
```

Creator workers cannot approve their own outputs. Future mandatory audit records must be version-scoped and expose one of `PASS`, `PASS_WITH_WARNING`, `BLOCKED`, `ERROR`, or `NOT_RUN`. `PASS_WITH_WARNING` does not make content publish-ready in the initial beta. The Chief Auditor must create no content; it validates required audit completion, evidence presence, artifact/version consistency, lineage, attributable spend, unresolved blocks, and preservation of the Human Review requirement.

The current non-negotiable control remains in place: a Human Review Gate captures the exact current content-version identifier when opened. Approval is valid only for that reviewed version; a missing or non-current version fails closed. No V2 view or worker control may approve a gate, publish externally, or weaken this invariant.

## Business Brain target design

A future `business_brain` record should be workspace-scoped, revisioned, access-controlled, and audit recorded. It may carry business name/type, products/services, target customer, brand voice, objectives, monthly revenue/profit targets, marketing budget, content objectives, platforms, prohibited topics/actions, risk tolerance, and operating constraints.

Workers must never receive the raw record directly. A server-side projection service must select only role-appropriate, non-secret, workspace-scoped fields for a bounded job. Credential material, OAuth tokens, API keys, database credentials, worker secrets, and signing secrets are excluded by construction. A revision identifier must be attached to every job and output so the system can explain which context influenced work.

## Engagement architecture boundary

The engagement department is a future provider-integration boundary, not a full messaging product in V2. A future adapter contract can normalize inbound conversation events, comments, direct messages, lead-capture forms, contact identity, consent, assignment, follow-up scheduling, and conversion attribution. Providers retain mature inbox and automation capabilities; The Business Manager stores only the minimum workspace-scoped records needed for routing, audit, and business intelligence. No external engagement automation is enabled in the preview.

## Navigation structure for the V2 preview

| Navigation group | V2 label | Existing destination or behavior |
|---|---|---|
| Home | **Home** | New profitability-first, decision-first shell using existing data only. |
| Workforce | **AI Workforce** | Existing worker monitor; V2 summary clarifies real versus not-configured departments. |
| Content | **Content Operations** | Existing Content Pipeline and Human Review views. |
| Intelligence | **Business Intelligence** | Existing Analytics, Spend & Usage, and Audience routes; financial connector remains unavailable. |
| System | **Connections & Settings** | Existing Integrations and Settings routes, including drill-down logs/health where available. |

## Security and operating invariants

| Invariant | V2 requirement |
|---|---|
| Workspace isolation | Every read/action stays workspace-scoped; membership guards and RLS continue as the enforcement backstop. |
| Human Review Gate | No worker or Home control can approve/reject/publish on behalf of a human; exact-version review binding is preserved. |
| Spend | Existing reservations, cap locks, spend hold, idempotency, and provider-effect controls are reused without change. |
| Retry and recovery | Existing bounded backoff, lease recovery, and dead-letter handling remain authoritative. |
| Secrets | No prompt, browser payload, dashboard card, worker log, or Business Brain projection may expose a secret. |
| Billing and publishing | `BILLING_ENABLED=false`; automatic external publishing remains disabled. |
| Preview data | Any safe disposable preview record must be labelled; V2 must not turn missing financial/workforce facts into apparent telemetry. |

## Founder Preview implementation sequence

The V2 preview first adds the non-replaying, reduced-motion-safe launch experience. It then replaces the current operationally dense Command Center entry view with the Home hierarchy: financial availability shell, What Needs You, AI Workforce summary, and operational drill-downs. Existing operational views are retained so Founder decisions, HRG, spend controls, logs, and worker controls remain available without being misrepresented as a new backend department.

## Deferred implementation requirements

The following require a future product decision, schema/API design, migrations, tenancy/RLS review, tests, and Founder approval before implementation: workspace financial records/connectors and reconciliation; a Business Brain record and projection policy; a role-binding/department registry; Scout/Strategist/Producer/Compliance/Chief Auditor/Analyst executors; versioned audit evidence records; content audit tab; performance-data ingestion; engagement-provider adapters; and recurring autonomous research policies.

## Approval gate

This document authorizes neither a merge nor a public deployment. The completed V2 interface is for the disposable Founder Preview only. **Founder visual approval is required before any redesign work is merged.**
