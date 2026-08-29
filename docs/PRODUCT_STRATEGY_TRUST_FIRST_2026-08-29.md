# Content Orchestrator — Trust-First Product Direction

Status: PRODUCT DIRECTION / NOT RELEASE AUTHORIZATION  
Date: 2026-08-29  
Base: audited `main` release state  

## Positioning

Content Orchestrator should not compete as another AI content generator. Generation capability is increasingly commoditized. The defensible product is a governed content operating system that controls the full lifecycle from brief and source evidence through generation, review, spend, publication, reconciliation, and audit.

Primary positioning:

> AI content automation you can actually trust: generate, verify, approve, publish, reconcile, and audit every asset from one governed workspace with hard spending limits and no silent publishing failures.

Agency positioning:

> Run every client's AI content operation from one control plane without mixing data, losing approvals, or wondering what actually published.

## Product principles

1. Human Review remains mandatory before external publishing. Do not introduce autonomous publishing that bypasses review.
2. Workspace isolation remains mandatory. No feature may weaken `workspace_id` scoping, FORCE RLS, owner/runtime separation, or least privilege.
3. Spend controls fail closed. When a limit cannot be verified or a cap is reached, work is held rather than charged optimistically.
4. Publishing must be reconciled, not fire-and-forget. A provider submission acknowledgement is not equivalent to a confirmed live post.
5. Failures must be loud and actionable. No silent placeholders, swallowed provider errors, or false-success states.
6. Claims about factual content must carry provenance and verification state. Missing evidence is shown explicitly rather than hidden.
7. Model/provider choice is curated. Workspaces may choose approved quality/cost profiles or approved models; the product does not become an unrestricted model marketplace.
8. AI-detection scores are advisory only. They must never be treated as proof that content is human- or AI-generated. Prefer plagiarism checks, originality signals, repetition detection, style analysis, and human review.
9. External approval links, if introduced, must be short-lived, cryptographically signed, content/workspace scoped, revocable, and incapable of granting general workspace access.
10. Every milestone follows the existing PASS / CONDITIONAL / FAIL audit standard. Missing safety-critical evidence cannot receive PASS.

## Strategic product pillars

### 1. Trust Layer

The Human Review Desk becomes the place where a reviewer sees not only the generated asset but the evidence needed to trust it.

Required capabilities:

- source-grounded generation
- extracted factual claims
- citation/provenance links for attributable claims
- explicit `needs_verification` state when attribution is missing or weak
- brand-voice and policy checks
- plagiarism/originality checks
- repetition and low-quality/generic-output signals
- compliance findings and unresolved exceptions
- immutable linkage between the reviewed content version and the evidence reviewed

A content item cannot be represented as verified when unresolved factual claims remain.

### 2. Content Lineage

Every generated or published asset must answer:

- which campaign/brief created it
- which source material informed it
- which prompt/template version was used
- which model and provider generated each version
- which transformations or edits occurred between versions
- which compliance/quality checks ran and their results
- who requested generation
- who reviewed it
- who approved or rejected it
- which exact immutable content version was approved
- estimated and actual cost
- which provider/platform operation submitted it
- which external platform object was ultimately confirmed live

Lineage is append-only evidence, not editable marketing metadata.

### 3. Campaign Primitive

One brief should produce a coordinated asset graph rather than unrelated generations.

Examples:

- long-form article
- YouTube script
- Shorts/Reels/TikTok variants
- captions
- LinkedIn/Facebook/X variants
- email copy
- ad copy

All assets in a campaign inherit the same approved source set, brand context, claim evidence, and campaign objectives. Factual claims should be reused from an approved claim set rather than independently regenerated across channels.

### 4. Publishing Control Plane

Publishing is a lifecycle:

`preflight -> approved -> submitted -> provider_acknowledged -> reconciled -> confirmed_live`

Required behavior:

- platform-specific preflight validation before submission
- immutable idempotency key for every publish operation
- bounded retries with backoff
- reconciliation before a retry where duplicate publication is possible
- provider error preservation
- explicit terminal failure state
- actionable operator retry/fix path
- distinction between a genuine engagement value of zero and missing/failed analytics retrieval
- no transition to `confirmed_live` without positive reconciliation evidence

Publishing remains disabled until its separate release gates, provider readiness, rate limiting, and Founder authorization are satisfied.

### 5. Cost Control Plane

Cost controls become a first-class product surface, not only backend enforcement.

Required capabilities:

- estimated cost before a generation/campaign begins
- spend reservation before cost-bearing execution
- actual provider cost recorded afterwards
- estimated-vs-actual variance
- workspace, campaign, provider, and time-window views
- hard daily/monthly caps
- clear hold state when a cap is reached
- no fallback that executes without a valid spend decision

### 6. Agency / Enterprise Governance

Required direction:

- isolated client workspaces
- role-scoped collaboration
- four-eyes approval where policy requires approver != requester
- secure external review/approval links without general workspace access
- append-only audit history
- exportable evidence bundle covering generation through confirmed publication
- policy checks at point of creation, not as a post-hoc add-on

### 7. Extensibility

Content Orchestrator should integrate into existing stacks rather than require total replacement.

Target order:

1. stable public API
2. signed webhooks
3. n8n integration
4. Make/Zapier integration
5. MCP server after the API and permission model are mature
6. browser extension only if customer evidence justifies it

All external automation must preserve workspace scoping, review gates, spend controls, idempotency, and audit evidence.

## Table-stakes parity

Reach practical parity without diluting the trust/reliability core:

- long-form editing and AI assist
- templates
- tone/rewrite/repurpose
- brand profiles and brand kit
- product/knowledge context
- multi-channel calendar
- per-platform customization
- bulk scheduling/import where safe
- roles/comments/approval workflows
- cross-channel analytics and exports
- long-form-to-short repurposing, captions, transcript-driven edits, vertical reframing

These are parity requirements, not the moat.

## Priority order

### P0 — Complete current safety/release foundations

Before expanding the product surface:

- finish independent audit and managed Supabase remediation
- preserve the six required CI gates
- complete fail-closed workspace/IP/provider rate limiting before live providers
- continue supply-chain hardening and reproducible CI work
- keep live providers, production billing/auth, production deployment, and external publishing disabled until separately authorized

### P1 — Review-to-publish trust spine

Build the defensible core:

1. brand/source context
2. source-grounded generation
3. claim extraction and verification state
4. Human Review Desk evidence surface
5. immutable content lineage
6. governed publication state machine and reconciliation design

### P2 — Campaign primitive

Implement one brief -> coordinated multi-channel asset graph using shared sources, approved claims, brand context, and lineage.

### P3 — Visible cost controls

Expose pre-run estimate, reservations, actual spend, variance, workspace/campaign spend views, and hard-cap hold states.

### P4 — Agency governance

Add secure external approvals, four-eyes policy, evidence exports, and client-facing collaboration without weakening workspace isolation.

### P5 — Extensibility

Expose the stable API/webhook surface and integrations only after the permission, spend, review, idempotency, and audit contracts are mature.

## Explicit non-goals for the current phase

Do not:

- enable hands-off autonomous external publishing
- treat AI-detection scores as truth or as a hard gate
- expose unrestricted arbitrary model selection
- add production provider credentials to source or CI
- weaken Human Review for speed
- allow spend-control failures to default-open
- mark a publish job successful based only on a provider request returning successfully
- build every possible content type before the trust/reliability spine is strong
- merge this strategy work into the active managed-Supabase remediation PR

## Definition of done for future feature milestones

A strategic feature milestone is not complete until:

- workspace isolation has explicit tests
- failure paths are explicit and fail closed where safety/cost requires it
- retries are bounded and idempotent where applicable
- secrets are not logged or persisted in unsafe locations
- audit/lineage evidence is durable
- Human Review cannot be bypassed on externally publishing paths
- cost-bearing operations have a valid spend decision
- browser evidence exists for user-visible workflows
- all six required CI gates pass on the exact candidate
- an independent auditor gives PASS or an explicitly bounded CONDITIONAL consistent with the milestone audit standard

## Competitive thesis

Competitors increasingly automate content creation. Content Orchestrator should automate the business process around content creation: evidence, approval, spend, delivery, reconciliation, isolation, and audit.

The moat is the combination of:

`trust + lineage + governed review + fail-closed cost + reconciled publishing + true workspace isolation`

That combination is harder to reproduce than adding another generator or template library and should guide future product acceptance decisions.
