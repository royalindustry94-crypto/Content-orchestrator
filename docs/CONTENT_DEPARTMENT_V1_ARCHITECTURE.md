# Content Department V1 Architecture

## Decision and scope

Content Department V1 converts an approved **Strategy Brief** into an independently audited **Creative Package** that may be handed to a future Producer. It does not publish, does not approve publication, and does not replace the existing pipeline, spend, Human Review Gate, retry, outbox, or tenant-isolation systems. The initial implementation is a **bounded, workspace-scoped vertical slice** on the disposable Founder Preview; no merge is authorized.

The execution chain is deliberately separated by responsibility. A Creative Director derives how the approved strategy should be executed. A Writer creates an immutable Content Version only from an approved Creative Direction. Language, Fact, Brand, and Originality Auditors inspect the resulting artifact independently. A single blocking audit prevents package readiness. Only a passing set of mandatory audits can form an audited Creative Package, and only the existing Human Review Gate can approve the exact reviewed version for subsequent publication policy checks.

## Capability matrix

| Capability | Status | Reused or delivered V1 behavior | Explicit limitation |
|---|---|---|---|
| Workspace isolation and RLS | **EXISTS** | Existing workspace-scoped tables, role checks, RLS policies, and direct-RLS tests are reused. | None within the current schema model. |
| Immutable content versions | **PARTIAL** | Existing `ContentVersion` rows are immutable creation artifacts. V1 links Content Department data to these rows and never overwrites them. | Existing version columns are narrow; V1 stores package metadata in its own append-only records. |
| Human Review exact-version binding | **EXISTS** | Existing `ReviewGate.content_version_id` and publication policy fail closed unless it matches the current version. | Content Department cannot make a publication decision. |
| Pipeline, retry, outbox, and DLQ | **EXISTS** | Existing run, stage-attempt, retry/backoff, outbox, and provider-effect primitives are reused. | V1 content-provider execution is not configured in the preview. |
| Spend controls | **EXISTS** | Existing reservation, commit, release, hard-cap, and provider-usage controls are reused. | Provider-not-configured V1 makes no chargeable call. |
| Creative Direction | **MISSING → V1** | Workspace-scoped immutable direction record based on an audited-passed Strategy Brief. | No live creative model/provider is configured. |
| Writer package | **PARTIAL → V1** | Existing Draft Desk and immutable Content Version are reused. V1 introduces structured package metadata and a test-only fixture path for lifecycle validation. | Browser path remains `WRITER PROVIDER NOT CONFIGURED`; it never creates fictional copy. |
| Claim extraction and fact verification | **MISSING → V1** | Structured Claim records and independent Fact Auditor findings are added. | Current evidence retrieval/provider is not configured; factual claims are blocked or marked unavailable rather than guessed. |
| Language and Brand audit | **MISSING → V1** | Independent audit records/finding model and conservative status aggregation are added. | Complete Business Brain vocabulary, voice, prohibited language, and persona configuration are missing. |
| Originality audit | **PARTIAL → V1** | Existing normalized publication fingerprinting is reused; V1 adds version text, hook, and structure fingerprints plus workspace history comparison. | No external plagiarism or semantic-similarity provider is configured. |
| Creative Package / Producer gate | **MISSING → V1** | Package readiness is derived only after all mandatory audits pass; Producer eligibility is a future gate. | Producer/media execution remains deferred and cannot publish. |
| Bulk content jobs | **DEFER** | Data model supports one bounded package per content item/version. | No CSV/catalog ingestion or bulk dispatcher is exposed in V1. |
| Autonomous schedule | **DEFER** | Schedules remain disabled by default. | No recurring execution is enabled in the Founder Preview. |

## Data model and lineage

The V1 domain adds `CreativeDirection`, `ContentDepartmentRun`, `ContentPackage`, `ContentClaim`, `ContentAudit`, `ContentAuditFinding`, `OriginalityFingerprint`, and immutable links between an approved Strategy Brief, Creative Direction, Content Version, and audit records. Every domain table includes `workspace_id`; migration policy enables RLS, grants only the required runtime roles, adds foreign-key indexes, version/timestamp fields where the established project convention applies, and classifies the records for export and retained-audit governance.

A Content Version is never rewritten. A revision creates a new `ContentVersion`, points its lineage metadata to the prior version, creates a new writer package record, and invalidates all affected audits. Conservative invalidation is the default: a material change invalidates Language, Fact, Brand, Originality, and package readiness. A spelling-only revision may be classified as language/brand/originality affected, but V1 never carries a prior audit result forward without an explicit invalidation decision.

Every claim is tied to an immutable Content Version. Claim records include the text, type, source-required flag, supporting evidence reference, verification state, confidence, risk, evidence freshness, and auditor reasoning. Writer-generated text, citations, prompts, or model output are never accepted as independent verification evidence.

## Independent department responsibilities

| Department role | Input boundary | Output | Prohibited authority |
|---|---|---|---|
| Creative Director | Strategy Auditor PASS brief and approved source opportunity context | Immutable Creative Direction | Cannot write final copy, audit itself, or publish. |
| Writer | Approved Creative Direction only | New immutable Content Version / structured package fields | Cannot self-audit, self-approve, or modify a prior version. |
| Language Auditor | Artifact plus platform/readability requirements | PASS, PASS_WITH_WARNING, BLOCKED, or ERROR with findings | Cannot rewrite the Writer artifact. |
| Fact Auditor | Artifact claims plus independent evidence context | Per-claim verification and audit state | Cannot use Writer text/citation as verification or create content. |
| Brand Auditor | Artifact plus configured Business Brain context | Brand findings and audit state | Cannot create content or assume missing brand rules. |
| Originality Auditor | Version fingerprints plus workspace history | Repetition findings and audit state | Cannot waive duplicate/repetition thresholds without policy. |
| Producer | Only an audited Creative Package | Future production eligibility | Cannot publish or override Human Review. |

The aggregate package status is fail-closed. Any mandatory `BLOCKED` or `ERROR` audit blocks the package. Warnings remain visible and do not silently convert to pass. Auditors are records and roles distinct from Writer/Creative Director provenance; each receives the artifact and relevant requirements rather than a self-assessment from the creator.

## Bounded execution, provider routing, and security

A department run carries explicit `max_provider_calls`, `max_tokens`, `max_cost_usd`, `max_attempts`, and timeout. Before a chargeable operation it must use the existing spend reservation boundary; at cap it stops and records an explicit hold/error state. Provider/model routing is controlled by a persisted capability configuration, never by browser input or uncontrolled fallback. Every generated artifact must record worker role, provider/model, prompt/template version, input references, Business Brain/Strategy/Creative Direction versions, timestamp, token usage, and cost without persisting secrets.

Untrusted research, source, comments, uploaded text, and competitor material are data only. V1 rejects secret-like content and instruction patterns that attempt to override system rules, workspace scope, budgets, audit requirements, or Human Review. Prompt-injection checks are tested on all externally sourced or fixture-driven text paths.

## Founder Preview behavior

No content-generation, fact-verification, originality, or creative provider is configured in the disposable Founder Preview. Browser-visible routes therefore state `PROVIDER NOT CONFIGURED`, `MISSING REQUIRED INFORMATION`, `NO AUDITED CREATIVE PACKAGE`, or an empty data state as appropriate. The sole exception is explicitly labelled **TEST DATA** in isolated tests; it is not exposed through browser actions and cannot be mistaken for real telemetry.

The preview does not make external content calls, current-information claims, price claims, provider charges, automatic retries, autonomous schedules, external publishing, or billing changes. The existing Human Review Gate, RLS, spend controls, manual-publishing boundary, and preview-only restrictions remain non-negotiable.

## Validation plan

V1 validation must demonstrate API and direct-RLS workspace isolation; immutable version lineage; Writer self-approval denial; each auditor's blocking effect; conservative audit invalidation; unsupported factual claim/fake citation rejection; duplicate script/hook detection; Business Brain conflict; injection rejection; bounded token/provider/cost limits; retry exhaustion/idempotency; secret redaction; Human Review bypass denial; and truthful `NOT CONFIGURED` states. It must also pass TypeScript, frontend lint/tests/build, API/worker/security suites, migration drift check, desktop smoke, exact 390px mobile smoke, console-error check, and horizontal-overflow check.

## Deferred follow-up

Before any live Creator/Writer/Auditor execution, add a single approved provider adapter per role with source policy, explicit model routing, provider capability records, spend reserve/commit integration, a secret-excluding Business Brain projection, current-evidence retrieval, external originality evaluation where justified, and a Founder-approved schedule policy. These are separate gates and do not authorize a merge.
