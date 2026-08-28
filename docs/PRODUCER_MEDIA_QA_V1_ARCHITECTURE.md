# Producer + Media QA V1 Architecture

## Purpose and scope

Producer + Media QA V1 introduces a bounded, workspace-scoped production domain for turning an **audited Content Package** into a final media artifact, then independently evaluating that exact artifact before any downstream Compliance, Chief Auditor, or Human Review handoff can be considered. It is a Founder Preview implementation only. It does not enable billing, automatic external publishing, a live provider, or a second media/publishing pipeline.

The V1 design reuses the existing immutable `ContentVersion`, Human Review Gate, workspace RLS, spend reservation, outbox, retry/DLQ, provider-effect key, and asset-storage metadata. It adds only the missing domain records needed to express a truthful production request, immutable asset lineage, hash-bound Media QA, bounded repair history, and fail-closed downstream readiness.

## Capability matrix

| Capability | State | V1 decision |
|---|---|---|
| Workspace RLS and membership | **EXISTS** | Apply to every production, asset, artifact, QA, repair, compliance, and Chief Audit record. |
| Immutable Content Version and exact HRG binding | **EXISTS** | Reuse as upstream and final approval invariant. Producer cannot alter or approve it. |
| Asset storage metadata and checksum | **EXISTS** | Reuse `assets` for generated component assets and provider/storage metadata. |
| Spend cap / reserve / commit / release | **EXISTS** | Reserve before every chargeable provider operation; stop on reserve failure. |
| Provider-effect idempotency | **EXISTS** | Reuse durable per-workspace effect keys to prevent duplicate external effects. |
| Retry, exponential backoff, jitter, DLQ | **EXISTS** | Reuse for bounded recovery; cap retries and repairs. |
| Outbox / durable event trail | **EXISTS** | Emit production request, artifact, QA, repair, and readiness events. |
| Provider routing capability model | **PARTIAL** | Persist an explicit provider plan and fallback ordering, but do not invoke unconfigured providers. |
| Provider-specific media clients | **MISSING** | No image, video, TTS, music, subtitle, or render provider is configured in the preview. |
| Webhook authenticity and reconciliation adapters | **MISSING** | Design contracts only; do not accept unauthenticated provider callbacks. |
| Media QA visual/audio/ASR analyzers | **MISSING** | Persist hash-bound independent QA contract; preview shows `NOT CONFIGURED`, never a fake pass. |
| Secure signed media delivery | **PARTIAL** | Existing asset metadata supports controlled storage; final signed URL implementation is deferred to a configured storage provider. |
| Compliance / Chief Auditor final-artifact evidence | **PARTIAL** | Persist fail-closed readiness state and required evidence contracts; no automated approval is introduced. |
| Real provider mode | **DEFER** | Requires Founder authorization, configured credentials, provider adapter, workspace budgets, policy, and a supervised test. |

## Production contract

Every `ProductionJob` is workspace-scoped and immutable in its request identity. It records `workspace_id`, `content_item_id`, `content_version_id`, `creative_package_id`, `pipeline_run_id`, `producer_worker_id`, target platform/format/duration, required assets, provider plan, max provider/render calls, max cost, max attempts, timeout, repair cap, deadline, status, and timestamps. A job starts only after all upstream Content Package and Content Audit requirements are satisfied.

The requested provider plan is declarative and controlled. It lists the operation class, permitted providers, fallback order, expected cost, idempotency key, and reconciliation rule. It does not expose provider credentials. A missing provider produces `NOT_CONFIGURED`; it cannot produce a successful artifact, provider charge, fake progress percentage, or synthetic QA result.

## Immutable media lineage

`ProductionAsset` records each generated or received component without silently replacing a prior asset. It links workspace, content item/version, production job, base `Asset` record, asset type, provider, provider job identifier, sanitized input provenance, generation settings, model/version, file hash, media metadata, cost, status, and test/real mode. A new generation always creates a new asset record.

`FinalArtifact` records the finished render with an immutable artifact hash, content version, production job, render provider/job identifier, storage-safe reference, duration, resolution, aspect ratio, container/codec, creation time, cost, and status. Any new render hash is a new final artifact. Changing the exact artifact invalidates prior Media QA and any pending or prior Human Review eligibility for that artifact.

## Independent Media QA

Media QA is a separate worker responsibility and does not generate media. Each `MediaQaResult` binds to the exact `FinalArtifact` identifier and immutable artifact hash. It captures start/completion times, status (`PASS`, `PASS_WITH_WARNING`, `BLOCKED`, `ERROR`, or `NOT_CONFIGURED`), checks run, visual findings, audio findings, subtitle findings, script/voice alignment findings, platform result, package-alignment result, severity, evidence, repair recommendation, and QA cost.

A V1 QA pass is impossible when no real artifact analyzer is configured. The preview can persist only an explicit not-configured state or test-only fixture evidence. Producer may not mark Media QA as passed, and the Media QA result may not be reused against a different artifact hash.

## Repair and idempotency

`ProductionRepair` records only the affected component, the Media QA finding, repair operation, incremented repair cycle, bounded cost/call allowance, outcome, and resulting asset/artifact references. Repair does not recreate upstream assets unless the repair contract explicitly requires it. Repair exhaustion, budget exhaustion, ambiguous provider outcome, or timeout transitions the production job to `BLOCKED` and requires manual intervention.

Before a chargeable call, the job checks workspace spend capacity and creates a reservation through the existing controller. A durable provider-effect key is inserted before external work. A duplicate effect key is a no-op. Ambiguous outcomes require provider-state reconciliation before retry. A callback must resolve its internal job through a stored provider job ID and server-side mapping; it may never trust workspace identity supplied by an external payload.

## Downstream gates

A final artifact may be marked **Compliance Ready** only when all of the following are bound to the same content version and artifact hash: upstream Content Package audits, Media QA result, complete production lineage, attributable cost records, and no blocking error. Chief Audit and Human Review remain separate fail-closed gates. Human Review must display the actual final artifact, exact hash/version, Media QA, Compliance, Chief Audit, total production cost, and relevant warnings. Neither Producer nor Media QA can approve, publish, or bypass any of these controls.

## Founder Preview behavior

The preview default is `NOT_CONFIGURED`. It can display bounded job contracts, empty state, provider plan, available cost budget, and downstream blocked reasons. It cannot create actual media, fake final renders, fabricated QA results, fake platform validation, fake provider cost, or publish externally. Test fixture mode is explicitly tagged and is never mixed silently with real-provider mode.

## Real-provider test prerequisites

A real supervised test requires Founder-authorized spend, an approved provider adapter, workspace-scoped credentials stored server-side, provider pricing/usage mapping, storage policy and signed delivery, provider callback verification, spend caps, Business Brain/capability policy, source and rights policy, platform requirements source, a test artifact, QA analyzer configuration, and a manual-only review plan.
