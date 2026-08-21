# Lumora Private-Beta Operator Runbook

**Scope:** This runbook operates one deliberately narrow workflow:

> **Idea/input → generation → processing → Human Review Gate → approval or rejection → publish-ready output → analytics review.**

It does not authorize automated external publishing, live billing, CRM workflows, marketplace features, or expansion beyond a controlled private-beta cohort. Every output remains publish-ready only until a named human separately decides to publish it through an approved platform process.

## 1. Operating roles and non-negotiable controls

| Role | May do | Must not do |
|---|---|---|
| Beta operator | Invite approved testers, create/monitor workspaces, triage operational alerts, stop workflows, collect evidence, and coordinate escalation. | Override an HRG decision, approve rights on behalf of a tester, enable billing, or publish externally without a separate authorised process. |
| Workspace reviewer | Approve or reject the exact version presented in the Human Review Gate; record a reason and rights/disclosure concerns. | Reuse an approval for a different content item, waive the HRG, or treat a publish-ready state as automatic publication. |
| Engineering on-call | Investigate technical failures, DLQ items, tenant/security reports, and cost anomalies; deploy only approved changes through GitHub review. | Change production data manually without an authorised incident process or merge a branch without approval. |
| Founder/product owner | Own beta scope, tester selection, weekly decision, and go/no-go decision. | Claim validation, pricing, or compliance before the evidence thresholds are met. |

> **Safety rule:** Pause the affected workspace immediately if a tenant-boundary, Human Review Gate, spend-cap, uncontrolled-publishing, payment-integrity, credential, or Critical/High security concern is suspected. Preserve evidence before retrying or deleting anything.

## 2. Daily preflight before admitting work

The operator completes the following on each beta day and records the outcome in the operator log. A failed item is a **no-start** condition unless the incident playbook explicitly permits a limited workaround.

| Check | How to verify | Pass condition | If failed |
|---|---|---|---|
| Approved release | Confirm the currently deployed SHA corresponds to an approved GitHub PR with all required checks green. | SHA, PR URL, deployment time, and reviewer are recorded. | Do not deploy or admit new work. |
| API readiness | Query `/health/ready` through the authenticated deployment path. | Healthy response; database readiness is true. | Stop intake; open an incident. |
| Automation truthfulness | Query `/health/automation` and compare it with worker state in Mission Control. | Response is not stale and agrees with worker monitor. | Pause workflow starts. |
| Worker capacity | Review Mission Control worker monitor, queue, and recent worker logs. | At least one eligible worker is online for planned stages; no unexplained saturation. | Keep testers in draft-only mode or pause. |
| HRG queue | Review pending, timed-out, and rejected gates. | No unexplained stale gate; reviewer coverage is named. | Assign a reviewer or defer new starts. |
| Spend | Review daily/monthly spend, caps, reservations, and failure/retry counts. | Within approved beta budget; no unexplained open reservation or cap alert. | Pause affected workspace; investigate before retry. |
| Alerts and health | Review critical/warning alerts, DLQ, failed jobs, and system-health indicators. | No unresolved critical alert; warning has an owner and ETA. | Follow the incident playbook. |
| External-publish boundary | Confirm billing remains disabled and no automatic publishing integration is enabled for beta. | Publish-ready only; no unapproved external submission path. | Emergency-stop workers and remove intake. |

## 3. Per-tester workflow operation

### Intake and setup

The operator verifies that the tester is on the approved list, has accepted the beta boundary, and has one named reviewer. The tester supplies one content idea, the intended platform, a rights statement for supplied inputs, and a clear audience/goal. Reject or defer an intake that requires prohibited material, lacks rights confidence, asks for automatic external publication, or falls outside the single workflow.

Create or verify the tester workspace, record its workspace identifier in the operator log, set the documented spend cap, and confirm the tester understands that Lumora produces a **publish-ready output**, not a publication. Do not store secrets, platform access tokens, or payment data in feedback documents or recruitment records.

### Generation and processing

Start one intentional workflow and retain its run/content identifiers. Observe queue state, worker assignment, provider effect, retry count, spend reservation, and user-visible status in Mission Control. A provider, timeout, or worker failure is recorded as a technical result; it must not be silently reclassified as tester abandonment.

When retrying, first check that the prior attempt has a coherent terminal/recovery state and that no unexplained reserved spend remains. Respect configured caps and bounded retries. Do not manually edit approvals, spend rows, provider-effect keys, or audit trails to make a workflow appear healthy.

### Human Review Gate

The named reviewer evaluates the exact content/version in the gate. The reviewer records an approval or rejection and, when possible, a structured reason. An approval applies only to the gate's exact content item and pipeline run; it is not transferable to another item, version, platform, or workspace.

A rejection is a valid beta result. Capture the reason, invite the tester to revise only if the workflow remains within scope, and count the rejection in the weekly evidence. Do not bypass a missing, timed-out, rejected, or mismatched gate.

### Publish-ready handoff and analytics

On approval, label the output **publish-ready**. Provide the tester with the approved version, disclosure/rights reminders, and any platform-specific human checklist. The tester performs any external publication under their own authorised account process; Lumora does not automatically publish during this beta.

Record only the analytics evidence the tester voluntarily provides or that an approved integration lawfully returns. Tie it to the content/workspace identifier, source, timestamp, and consent basis. Never infer audience performance from an unpublished or untracked output.

## 4. Normal operating cadence

| Cadence | Mandatory action | Evidence retained |
|---|---|---|
| Per workflow | Record intentional start, HRG outcome, technical result, spend state, and tester feedback link. | Workspace/content/run IDs, timestamps, operator note. |
| Daily | Complete preflight; review errors, DLQ, stale gates, worker capacity, spend, alerts, and security signals. | Dated operator-log entry and incident IDs. |
| Weekly | Review activation, completion, acceptance, repeat use, time saved, failure rate, cost per accepted output, and WTP evidence against `PRIVATE_BETA_VALIDATION_PLAN.md`. | Cohort report with denominators and exclusions. |
| Weekly | Review rejected outputs and operational incidents for repeated causes; decide one scoped improvement or explicitly defer. | Decision log and linked issue/PR where applicable. |
| Monthly or at cohort boundary | Founder decides continue, narrow, pause, or expand; no metric is substituted with anecdote. | Signed decision note and evidence links. |

## 5. Emergency stop and recovery

Use the smallest safe action first. Pause workers through the authorised Mission Control action if work must stop immediately. If the incident affects one workspace, pause that workspace's intake and do not retry its jobs until the root cause is understood. If the incident affects tenant isolation, HRG, spend, authentication, credentials, or uncontrolled publishing, pause all beta work and follow `BETA_INCIDENT_PLAYBOOK.md`.

Do not use database changes, force-pushes, production secrets, or a direct `main` push as an emergency workaround. Preserve run IDs, relevant audit/log references, alert state, and the deployed SHA. Recovery requires an owner decision and an evidence-backed validation appropriate to the incident class.

## 6. Required operator log template

| Field | Required value |
|---|---|
| Date/time and operator | UTC timestamp; named operator. |
| Deployed SHA / PR | Exact deployed SHA and approved PR URL. |
| Workspace / tester pseudonym | Workspace UUID and approved tester ID; do not put credentials or private tokens here. |
| Content / run / gate IDs | Exact identifiers for one intentional workflow. |
| Stage outcome | Completed, rejected, failed, paused, or awaiting review; include reason. |
| Spend / reservation status | Observed amount/state or `BLOCKED — EVIDENCE UNAVAILABLE` if not accessible. |
| Alert / incident reference | Link or `none`; incidents always get a reference. |
| Next action / owner | One accountable person and due time. |

## References

[1]: [Private Beta Validation Plan](PRIVATE_BETA_VALIDATION_PLAN.md)
[2]: [Beta Incident Playbook](BETA_INCIDENT_PLAYBOOK.md)
[3]: [Platform Policy Control Matrix](PLATFORM_POLICY_CONTROL_MATRIX.md)
[4]: [Mission Control Readiness Assessment](BETA_MISSION_CONTROL_READINESS.md)
