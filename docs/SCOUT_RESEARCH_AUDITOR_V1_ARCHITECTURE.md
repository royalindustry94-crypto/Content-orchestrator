# Scout + Research Auditor V1 Architecture

## Scope and non-negotiable boundaries

Scout is an evidence-backed opportunity-intelligence worker. Research Auditor is a separate evaluator that determines whether Scout evidence can be treated as approved intelligence for a later Strategist handoff. Neither component creates final content, approves content, publishes content, accesses raw secrets, overrides Compliance or Chief Auditor, or bypasses the Human Review Gate.

This V1 applies only to the disposable Founder Preview until explicit Founder approval. Billing remains disabled, automatic external publishing remains disabled, scheduled research remains disabled by default, and no public research provider is configured. The live preview must therefore display **RESEARCH PROVIDER NOT CONFIGURED** rather than simulate trends or fabricate research.

## Capability matrix

| Capability | State | Reuse or V1 decision |
|---|---|---|
| Workspace isolation and authorization | **EXISTS** | New research models use `WorkspaceScopedMixin`; every route uses the existing authenticated workspace guard. |
| Worker registry, health, leases, and supported stages | **EXISTS** | A future Scout worker can register `scout_research`; V1 does not claim it exists without a real registered worker. |
| Assignment, idempotency, and stage-result semantics | **PARTIAL** | Existing dispatcher is pipeline-run-specific. V1 borrows its reservation-before-work, lease, worker capability, and idempotency invariants without creating a duplicate worker policy. |
| Scheduler, fairness, and queue back-pressure | **PARTIAL** | Existing queue is reusable for bounded work. Recurring job policy is not implemented, so V1 models schedules as disabled and does not enqueue autonomous cycles. |
| Spend caps, reservation, commit, and release | **EXISTS** | Every chargeable provider operation must reserve workspace capacity first and commit/release attributable usage once. |
| Retry, jitter, and dead-letter handling | **EXISTS** | V1 applies existing exponential backoff and dead-letter records to provider failures; retries are capped by the run’s `max_attempts`. |
| Durable, workspace-scoped events | **EXISTS** | Research lifecycle events use the existing outbox, correlation, trace, and producer-attribution primitives. |
| Opportunity model and evidence provenance | **MISSING** | Add dedicated research records; the existing CRM Lead model is insufficient. |
| Independent Research Auditor gate | **MISSING** | Add dedicated immutable auditor decision records; Scout can never approve its own evidence. |
| Business Brain context | **MISSING** | Existing Profile is user identity only. V1 accepts an optional approved context snapshot; missing context lowers confidence and is visible. |
| Research provider connector | **MISSING** | Live Founder Preview shows provider not configured. Test-only fixtures exercise the real data path under explicit test configuration. |
| Prompt-injection handling | **PARTIAL** | Add an untrusted-source envelope, URL allowlist validation, content-size limits, instruction-pattern detection, and no-secret projection. |
| Performance feedback loop | **DEFER** | Persist `NO_PERFORMANCE_DATA` state only; no performance values are invented. |

## V1 data model

The following workspace-scoped records are required. Their table names are intentionally research-specific rather than overloading CRM leads or content pipeline entities.

| Record | Purpose | Important fields |
|---|---|---|
| `research_runs` | Bounded, attributable Scout execution intent and outcome. | `workspace_id`, trigger, objective, permitted_sources, started_at, deadline, max_searches, max_provider_calls, max_tokens, max_cost_usd, max_attempts, status, provider_state, correlation_id, trace_id, counts, last_error. |
| `research_sources` | Immutable provenance record for a retrieved or rejected external source. | `workspace_id`, research_run_id, canonical_url, source_type, retrieved_at, published_at, publisher, author, supported_claim, freshness, confidence, content_digest, handling_state, rejection_reason. |
| `opportunities` | Evidence-backed opportunity with inspectable component reasoning. | Required directive fields plus `dedupe_key`, component_scores, score_reasoning, audit_gate_status`, and `performance_data_state`. |
| `opportunity_evidence` | Many-to-many source-to-opportunity claim support. | `workspace_id`, opportunity_id, source_id, claim_supported, relevance, contradiction_flag. |
| `research_audits` | Independent evaluation that preserves the original Scout result. | `workspace_id`, opportunity_id, research_run_id, state, evaluator_context_version, findings, warnings, blocked_reasons, checked_at, no_secret_projection. |
| `research_schedules` | Explicit future schedule configuration. | `workspace_id`, frequency, enabled, next_run_at, enabled_by, paused_at. Founder Preview defaults to `enabled=false`. |

`ResearchRun` is the boundary of one bounded research attempt. It receives all limits at creation; no executor may increase those limits. `Opportunity` stores component scores and reasoning rather than presenting a synthetic scientific certainty. `ResearchAudit` is append-only for a given audit attempt and never rewrites Scout’s original evidence or conclusion.

## State and gate model

A research run begins only through an authenticated workspace-scoped manual action. Its terminal states include `SUCCEEDED`, `PROVIDER_NOT_CONFIGURED`, `BUDGET_EXHAUSTED`, `TIMEOUT`, `SOURCE_LIMIT_REACHED`, `FAILED`, and `CANCELLED`. A failed or exhausted run records its failure and emits a durable event; it does not silently produce partial “approved” opportunities.

Opportunity lifecycle states are `ACTIVE`, `WATCHING`, `DECLINING`, `EXPIRED`, and `BLOCKED`. Research audit states are `NOT_RUN`, `PASS`, `PASS_WITH_WARNING`, `BLOCKED`, and `ERROR`. Only `PASS` may satisfy V1’s eventual Strategist eligibility condition. `PASS_WITH_WARNING`, `BLOCKED`, `ERROR`, and `NOT_RUN` are not approved intelligence; `BLOCKED` must never reach Strategist as approved.

> **Scout → Research Auditor → Strategist** is a one-way evidence gate. Research Auditor reads the original Scout output and evidence independently. It must not obtain its verdict by asking Scout whether Scout was correct.

## Bounded execution and spend controls

Every run receives a trigger, objective, permitted sources, deadline, `max_searches`, `max_provider_calls`, `max_tokens`, `max_cost_usd`, and `max_attempts`. Every provider call increments bounded usage. A call that would exceed an execution or provider limit terminates with a truthful terminal state. The existing workspace daily and monthly spend caps remain authoritative; a chargeable provider call must reserve capacity before it starts and must commit actual or release reserved cost exactly once.

A real provider is intentionally absent from the zero-cost preview. The only executable V1 research provider in tests is a deterministic, explicitly labelled fixture provider. It runs through the same model/service/audit path but is unavailable outside test configuration. Scheduled runs are not produced or polled in the Founder Preview unless an explicit future enablement path is implemented and enabled by the Founder.

## Provenance and untrusted source handling

Each external claim stores a source URL/reference, source type, retrieval time, available publication time, available publisher/author, supported claim, freshness, and confidence. Missing provenance stays missing; it must not be inferred. A source lacking sufficient evidence becomes `UNVERIFIED` or is rejected with a recorded reason.

Source material is untrusted input. V1 accepts only safe HTTP(S) URLs, rejects private-network targets and unsupported schemes, normalizes canonical URLs for deduplication, limits fetch/content bytes, strips active content, marks instruction-like strings as untrusted, and projects only bounded text plus provenance to evaluators. No API key, OAuth token, authorization header, system instruction, Human Review decision, tenant identifier from another workspace, or raw secret can be placed in a source payload or audit evidence.

## Deduplication, staleness, and feedback

A deterministic dedupe key is derived from normalized workspace topic, proposed angle, platform, format, and canonical source cluster. A duplicate updates evidence history/momentum only when allowed by the authenticated service; it does not produce unlimited new opportunity rows. Freshness is computed from source timestamps and retrieval time. A stale or unverified “breaking” claim is not promoted as current.

The schema reserves a `performance_data_state` field. Until genuine workspace performance data exists, it is `NO_PERFORMANCE_DATA`; no historical-performance boost is calculated.

## API surface

| Endpoint | Behavior |
|---|---|
| `POST /research/runs` | Creates a bounded manual run after workspace authorization and limit validation. With no configured provider, returns a persisted `PROVIDER_NOT_CONFIGURED` run without external work. |
| `GET /research/runs` and `GET /research/runs/{id}` | Lists only current-workspace runs, usage, status, limits, and errors. |
| `GET /opportunities` and `GET /opportunities/{id}` | Lists only current-workspace opportunities and inspection data, including provenance/audit state. |
| `GET /opportunities/{id}/sources` | Returns safe provenance and evidence claims only. |
| `GET /opportunities/{id}/audit` | Returns independent auditor findings and gate state. |
| `POST /opportunities/{id}/send-to-strategist` | V1 gate endpoint. It denies all states except eventual `PASS`, and it does not publish or approve content. |
| `GET /research/summary` | Returns truthful Scout status, current research, last run, next run, counts, cost, and error state for the UI. |

## Durable events

V1 emits workspace-scoped outbox events for `research.started`, `research.provider_not_configured`, `research.source_rejected`, `research.source_recorded`, `opportunity.created`, `opportunity.updated`, `opportunity.duplicate_detected`, `research.audit.started`, `research.audit.passed`, `research.audit.warning`, `research.audit.blocked`, `research.budget_exhausted`, `research.retry_scheduled`, `research.failed`, and `opportunity.strategist_denied` or `opportunity.sent_to_strategist`.

## Test plan

The implementation must test tenant isolation, worker/admin permissions, provenance, duplicates, stale opportunities, all bounded limits, spend caps, provider failure, retry exhaustion, idempotency, prompt-injection resistance, independent auditor blocking, blocked Strategist handoff, secret non-exposure, and truthful not-configured/empty UI states. Existing API, worker, frontend, production build, desktop smoke, exact-390px mobile smoke, console, and horizontal-overflow gates remain mandatory.
