# Private Beta Validation Plan

**Purpose:** Determine whether Lumora’s controlled private beta delivers a repeatable, valuable content-orchestration workflow. This plan does not claim customer validation exists today.

> **Current evidence state:** **BLOCKED — EVIDENCE UNAVAILABLE.** The repository contains no customer interviews, signed design-partner commitments, production usage cohort, payment evidence, or validated willingness-to-pay result. The measurements below are required before a product-market-fit or commercial-readiness claim.

## Product wedge

| Element | Definition | Deliberate boundary |
|---|---|---|
| Primary persona | A small content team owner or operator who is responsible for producing and approving recurring short-form/video content across one or more social channels. | Do not generalize results to agencies, enterprise media organizations, or consumer creators without separate evidence. |
| Core job to be done | “When I have an approved idea, help me turn it into a reviewable, rights-aware content package and publish it only after I approve the exact version.” | The job is not “generate unlimited social content” or “autonomously grow an audience.” |
| One end-to-end workflow | Idea/input → generation/processing → Human Review Gate → approval/rejection → schedule/publish → analytics/incident follow-up. | Do not count a generation-only session as full workflow completion. |
| Non-goal 1 | Automated publishing without version-specific human approval. | HRG remains the final safety valve. |
| Non-goal 2 | Marketplace, CRM, or peripheral dashboard expansion as a substitute for proving the core workflow. | Mission Control supports visibility; it does not define product value alone. |
| Non-goal 3 | Claiming platform-policy or rights compliance solely from generated content. | Human review and documented evidence remain required. |

## Measurement definitions

| Metric | Formula / event definition | Cohort and time window | Target for continued controlled beta | Stop / investigate condition |
|---|---|---|---|---|
| Activation | Workspace completes its first HRG-approved content package within 7 days of invitation ÷ invited workspaces that accepted access. | Weekly invited cohort. | Establish baseline over first 10 completed invitations; no threshold is valid before that sample exists. | Material onboarding failure, authorization failure, or inability to reach HRG. |
| Workflow completion rate | Content items that reach an approved or rejected HRG decision within 14 days ÷ content items intentionally started. | All intentional starts, weekly. | ≥ 70% after the first 30 intentional starts, excluding customer-requested cancellations but retaining system failures. | < 50% across two consecutive weekly cohorts or repeated abandoned system states. |
| Accepted-output rate | HRG-approved output versions ÷ versions submitted for HRG decision. | Weekly and by workflow stage. | ≥ 50% after 30 review decisions, segmented by content type. | < 30% after 30 decisions or an upward rejection trend with repeated reasons. |
| Repeat-use rate | Workspaces with a second intentional start within 14 days of first HRG decision ÷ activated workspaces. | Rolling 14-day cohort. | ≥ 40% after at least 10 activated workspaces. | < 20% after 10 activated workspaces, unless interviews identify a correctable onboarding constraint. |
| Time saved | Median customer-reported baseline minutes for the defined workflow − median measured Lumora active-work minutes, with review time shown separately. | Per participating workspace; compare the same content type. | Demonstrable positive median savings, corroborated by session timestamps and interview notes. | No measurable time saving or users bypass the workflow to finish work elsewhere. |
| Failure rate | Runs ending in terminal technical failure, DLQ, unexpected retry exhaustion, or unauthorized/failed operation ÷ intentional starts. | Weekly; exclude policy/user rejections from technical failure rate but report separately. | < 5% after first 30 starts; zero Critical/High safety failures. | ≥ 10%, any tenant/security/HRG/spend Critical/High defect, or unexplained duplicate provider effect. |
| Cost per accepted output | Workspace-attributable provider, render, storage, and operation cost for accepted versions ÷ accepted HRG-approved versions. | Monthly and by content type/provider. | Must remain below the pre-agreed beta budget and leave an evidenced path to target gross margin. | Unknown cost lineage, cap bypass, or cost above beta budget without approved learning value. |
| HRG rejection reasons | Structured reason code plus free-text rationale; measure share by code. | Every decision. | Every rejection has a reason or an explicit “no reason supplied” marker. | Missing version/reviewer/decision data or rejection patterns not triaged weekly. |
| Willingness to pay | At least one of: paid conversion, signed letter of intent with price range, or a documented price-sensitive commitment after customer has completed the workflow. | Qualified activated workspace. | Collect qualitative and quantitative evidence before choosing a production price. | Treat generic praise, click-throughs, or hypothetical survey answers alone as insufficient. |

## Instrumentation and evidence contract

The beta must create immutable or append-only events for workspace invitation/acceptance, content start, provider/reservation effect, HRG decision, scheduling/publish attempt, provider result, user-visible failure, and support/incident outcome. Each event must carry the workspace, content/version/run identifier, actor or service identity, timestamp, and correlation ID where architecture supports it.

| Instrumentation item | Required fields | Current evidence state |
|---|---|---|
| Workspace activation | invitation ID, accepted timestamp, first workflow start, first HRG decision | CONFIRMED OPEN — invitation cohort instrumentation not verified. |
| Workflow/run events | workspace, run, stage, attempt, outcome, error class, provider-effect id | PARTIALLY CLOSED — orchestration/audit records exist; product analytics aggregation is not verified. |
| HRG decision | content/version, reviewer, decision, timestamp, reason, authorized action | PARTIALLY CLOSED — decision path and idempotency tested locally; reason completeness and business reporting are not verified. |
| Cost attribution | workspace, content/run/stage, provider, reserved/actual amount, reconciliation status | PARTIALLY CLOSED — spend controls and regression tests exist; production provider cost/usage evidence is unavailable. |
| Feedback and WTP | participant, workflow reference, structured interview notes, price method, consent | CONFIRMED OPEN — no validated collection workflow. |

## Operating cadence and decision gates

| Cadence | Responsible role | Required action |
|---|---|---|
| Per workflow | Workspace reviewer | Approve/reject exact version; record reason and policy/rights flags. |
| Daily | Engineering/operator | Review failures, DLQ, retries, cost caps, stale gates, security events, and platform incidents. |
| Weekly | Product owner with engineering evidence | Review cohort funnel, rejection reasons, time saved, repeat use, cost per accepted output, and open defects. |
| Monthly | Authorized leadership | Decide continue, narrow, pause, or expand based on actual cohort data and capacity—not documentation claims. |

**Continue** only if no Critical/High release-safety finding is open, the controlled workflow completes reliably, and real participants demonstrate repeat value. **Pause** on any tenant boundary, HRG, spend, uncontrolled-publishing, or payment integrity failure. **Do not expand scope** until the core workflow has evidence across a meaningful cohort.
