# Compliance + Chief Auditor V1 Architecture

## Purpose and boundary

Compliance + Chief Auditor V1 is the final machine-review layer between Media QA and the existing Human Review Gate:

```text
Media QA (exact final artifact hash)
  → Compliance (platform/policy/rights/brand-safety review)
  → Chief Auditor (whole-chain integrity review)
  → Existing Human Review Gate (exact content version)
  → Manual publication eligibility only
```

Neither Compliance nor Chief Auditor creates, rewrites, repairs, approves publication, or calls a platform publish API. Both are bounded, workspace-scoped, evidence-driven, and fail closed. The Founder Preview has no compliance provider, current platform-policy source, external rights verifier, or schedule enabled; therefore it must render explicit blocked or not-configured states rather than a fabricated pass.

## Capability matrix

| Capability | Status | V1 decision |
|---|---|---|
| Workspace RLS and membership authorization | EXISTS | Reuse for every new record and route. |
| Immutable exact content version identity | EXISTS | Reuse `ContentVersion`, `ContentPackage`, `ReviewGate`, and immutable `ReviewDecision`. |
| Immutable final artifact hash | EXISTS | Reuse `FinalArtifact.artifact_hash` and `MediaQaResult.artifact_hash`. |
| Media QA evidence and invalidation | EXISTS | Reuse as a mandatory upstream gate. |
| Language, Fact, Brand, Originality audits and claims | EXISTS | Reuse `ContentAudit`, `ContentClaim`, originality fingerprints, and audit invalidations. |
| Publication policy and fail-closed prepublication control | PARTIAL | Extend server-side eligibility; do not replace `assert_publishable`. |
| Policy-source versioning | MISSING | Add workspace-scoped platform policy-source metadata with version/date/freshness fields. |
| Rights/provenance status per artifact | PARTIAL | Add explicit rights evidence records; never infer a license. |
| Compliance audit | MISSING | Add independently attributed exact-artifact audit records and no-provider truthful run state. |
| Chief Auditor integrity controller | MISSING | Add deterministic persisted-chain verification against a versioned gate manifest. |
| Artifact-bound Human Review package | MISSING | Add a package linked to final artifact hash while preserving existing ReviewGate/ReviewDecision authority. |
| Publication eligibility for complete artifact chain | PARTIAL | Add authoritative server-side chain eligibility; external publishing remains disabled. |
| Real policy retrieval, rights verification, compliance provider | DEFER | Require approved source/provider adapters and workspace configuration. |

## Data model and immutable lineage

All records are workspace-scoped and protected by the project RLS convention. The new domain is additive and never rewrites `FinalArtifact`, `MediaQaResult`, `ContentAudit`, `ReviewGate`, or `ReviewDecision`.

| Record | Immutable / versioned fields | Purpose |
|---|---|---|
| `PlatformPolicySource` | platform, category, source, source reference, effective date, retrieved date, last verified, rule version, status | Records an attributable policy rule source. `freshness_unverified` blocks a current-policy claim. |
| `ArtifactRightsEvidence` | artifact, origin, provider/source, license/right basis, generation record, source reference, modification lineage, rights status | Records verified, declared, unverified, restricted, or blocked rights evidence without inventing licensing. |
| `ComplianceAudit` | final artifact ID/hash, content version, platform, policy version, inputs snapshot, findings, evidence, warnings, disclosures, rights/reused/monetization risk, status, cost/retry state | Independent compliance review that applies only to the exact artifact hash. |
| `AuditGateManifest` | manifest version, content type, required gate definitions, active state | Explicit, versioned requirements. Gates are never inferred at runtime. |
| `ChiefAudit` | artifact ID/hash, content version, pinned manifest, gate snapshot, lineage/cost/provider checks, warnings/blockers, status | Whole-chain integrity record. It can only produce `pass_to_human_review`, `blocked`, or `error`. |
| `HumanReviewPackage` | artifact ID/hash, content version, review gate, chief audit, purpose, target platform, cost, audit summaries, warnings, disclosures | Evidence view for the existing Human Review Gate; it does not create a second approval system. |
| `ComplianceInvalidation` / `ChiefAuditInvalidation` | affected artifact/hash, reason, dimensions, actor, timestamp | Append-only downstream invalidation after a material artifact, content, policy, or rights change. |

## Platform policy versioning and untrusted input

A policy record is platform-specific and contains platform, category, source, source reference, effective/retrieved date, last verification date, rule version, and status. Policy web content is untrusted data, not instructions. The system rejects prompt-instruction patterns and secret-like strings before a fixture or policy record is admitted. A source may be stored as evidence, but no page or provider response can grant itself compliance authority.

When a policy source cannot be established or is stale, Compliance reports `policy_freshness_unverified` and blocks automatic progression. V1 does not claim legal certainty or "social media compliant" in the abstract.

## Rights, provenance, synthetic media, and claim risk

Rights evidence is recorded per relevant final artifact or source asset with a status of `verified`, `declared`, `unverified`, `restricted`, or `blocked`. Required missing evidence blocks. Synthetic imagery, video, voice, face/character generation, and materially altered media are stored in disclosure evidence; required platform disclosures are never silently removed.

Compliance consumes structured claim status and evidence. Material unverified claims, especially around money, earnings, health, safety, legal matters, guarantees, comparisons, statistics, testimonials, and product performance, cannot silently pass. Reused/low-effort risk is classified `low`, `medium`, `high`, or `unknown` from originality, workspace history, script/hook/template similarity, source material, and transformation evidence. High risk blocks progression.

## Required gate manifest

The default V1 manifest is versioned and explicit:

```json
{
  "manifest_version": 1,
  "content_type": "short_form_media",
  "required": [
    "research_audit",
    "strategy_audit",
    "language_audit",
    "fact_audit",
    "brand_audit",
    "originality_audit",
    "media_qa",
    "compliance",
    "chief_audit",
    "human_review"
  ]
}
```

A mandatory `blocked`, `error`, `not_run`, stale hash, cross-workspace reference, missing evidence, unreconciled provider/cost record, or invalidated dependency blocks the chain. There is no majority voting.

## Chief Auditor algorithm

Chief Auditor performs deterministic persisted-evidence checks, not subjective content generation. It verifies workspace identity, manifest presence/version, content version, exact final artifact hash, upstream required stages, audit states, policy freshness, rights evidence, source provenance, Media QA hash binding, Compliance hash binding, provider/cost reconciliation, repair lineage, invalidation state, and the continuing availability of the existing Human Review Gate. A changed artifact, script, audio, visual, subtitle, or material metadata invalidates affected downstream evidence and prevents a pass.

A `pass_to_human_review` result means only that the machine chain is complete enough for an existing human decision. It never means publish approval.

## Human Review and publication eligibility

A `HumanReviewPackage` presents final-media reference, purpose, target platform, objective where available, total cost, audit statuses, warnings, disclosures, and artifact identity. Approval remains exclusively in the existing ReviewGate / ReviewDecision flow and must be bound to the same workspace, final artifact hash, and current content version.

The new server-side artifact-chain eligibility is true only when all of the following hold: Chief Auditor has `pass_to_human_review`; a valid existing Human Review approval exists; approval content version and artifact hash match the current artifact chain; no mandatory evidence is stale or invalidated; and platform authorization remains valid. This determination augments the existing fail-closed publication-policy service. No route will publish externally, and automatic publishing remains disabled.

## Bounded execution, failures, and cost

Compliance and Chief Auditor requests are manual in preview, bounded to five provider/verification calls, 4,000 tokens, three attempts, one repair-routing recommendation, and zero preview-provider budget. No provider is configured, so a live request records a truthful no-provider or incomplete-input state with no call, spend, or fabricated result. Budget exhaustion, provider outage, or Chief Auditor failure is an incomplete/blocked state, never approval. Existing outbox, retry, backoff, idempotency, recovery, and DLQ primitives are reused.

## Founder Preview and production boundary

Browser-visible preview data remains real backend data or explicitly labelled test data. Test-only chain fixtures are service-only, require `test_data=true`, and never mount as browser endpoints. The branch remains non-merging until Founder approval. Real policy retrieval, rights verification, provider adapters, production credentials, background schedules, billing, and external publishing are out of scope.
