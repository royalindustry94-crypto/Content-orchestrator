# Data Governance Baseline

**Status:** Repository-side governance baseline for private beta.
**Legal status:** This is an engineering control document, not legal advice or a jurisdiction-specific privacy notice. Legal retention periods, controller/processor roles, and customer-facing notices require authorized legal review before production launch.

> **Evidence rule:** A documented retention or deletion rule is not proof that the candidate enforces it. Items marked **CONFIRMED OPEN** need implementation and test evidence before a production readiness claim.

## Data inventory and classification

| Data domain | Examples in candidate | Classification | Workspace boundary | Primary operational use | Current control / gap |
|---|---|---|---|---|---|
| Identity and access | user IDs, email, local-auth credential hashes, workspace memberships, roles, JWT claims | Restricted | Workspace/user as applicable | Authentication and authorization | RLS/FORCE RLS applies to workspace data; local-auth credential lookup is a documented pre-JWT exception and must remain non-HTTP-exposed. |
| Customer/account | workspace name, settings, billing identifiers, plan and entitlement state | Confidential | Workspace | Workspace administration and entitlement | RLS/FORCE RLS and API authorization are tested locally. |
| Content input/output | ideas, scripts, content items/versions, assets, publish records, review notes | Confidential; may be Restricted if users submit personal/sensitive material | Workspace | Generate, review, schedule, publish | HRG and workspace controls are tested locally; rights/policy preflight persistence is **CONFIRMED OPEN**. |
| Provider credentials | encrypted or stored provider configuration/credentials | Restricted | Workspace | Authorized provider calls | Never log, return, or include in exports by default. Key rotation and vault-provider assurance require environment evidence. |
| Worker and operations telemetry | worker credentials, worker logs, heartbeats, job schedules, failures, queue state | Confidential; Restricted when logs include personal/content context | Workspace or service-only scope | Reliability, debugging, audit | `worker_logs` are append-only and RLS/FORCE RLS protected on the candidate. Log minimization policy remains an implementation obligation. |
| Financial and usage | spend caps, reservations, spend logs, provider usage, billing webhooks, Stripe IDs | Restricted | Workspace | Cost limits, reconciliation, entitlement | Immutability and local regression coverage exist; live payment operation is not verified. |
| Security/audit | outbox/audit records, recovery audit, review decisions, incident references | Restricted | Workspace or service-only scope | Accountability and investigation | Append-only controls exist for selected audit tables; formal retention/hold automation is **CONFIRMED OPEN**. |
| Support/export | customer-requested export bundles, deletion requests, incident communications | Restricted | Workspace | Customer support and privacy operations | No verified self-service export/deletion workflow in the candidate: **CONFIRMED OPEN**. |

## Access-control matrix

| Actor | Permitted data | Control requirement | Prohibited action |
|---|---|---|---|
| Workspace member | Workspace content and records allowed by role/policy | Transaction-local user context; RLS/FORCE RLS; API workspace authorization | Cross-workspace access, privileged review/publish action without role. |
| Workspace editor | Content creation/editing where role permits | Same workspace and role checks | Review decision or admin-only billing/operations action unless explicitly authorized. |
| Workspace admin | Workspace operations, review, billing/settings where routes permit | Admin authorization plus RLS scope | Global worker control, another workspace’s records, or review bypass. |
| Worker identity | Assigned work and scoped operational writes | Credential-derived worker/workspace identity; lease/assignment validation; least privilege | Arbitrary workspace write, log rewrite/delete, or cross-workspace reference. |
| Application runtime role | Data required to execute authorized HTTP path | `app_runtime` grants plus RLS and transaction-local JWT claims | Owner/superuser bypass; direct service-only table access outside approved path. |
| Service/owner session | Infrastructure operations explicitly enumerated in code | Narrow route/service boundary; auditable action; no request traffic routed through owner role | Customer-facing broad access or unbounded export. |
| Support/operator | Only an approved, time-bounded support workflow | Named approval, purpose, workspace scope, immutable audit entry | Bulk browsing, credential retrieval, or ad hoc production export. |

## Retention and deletion rules

| Record class | Private-beta rule | Deletion / hold rule | Evidence state |
|---|---|---|---|
| Live content, assets, versions | Retain while workspace is active and publication/review obligations remain. | Customer-requested deletion must be scoped, authorized, and preserve legally/audit-required records under an explicit hold. | CONFIRMED OPEN — lifecycle jobs and request workflow not verified. |
| Review, spend, billing, security, and recovery audit records | Retain for operational accountability and reconciliation; do not mutate in place. | Redact/limit access where permitted; do not delete immutable evidence without an approved retention schedule and legal basis. | PARTIALLY CLOSED — selected immutability controls verified locally; retention automation absent. |
| Credentials and tokens | Retain only while active; never place in logs, exported bundles, repository files, or support transcripts. | Revoke/rotate promptly on compromise, workspace removal, or provider disconnect. | PARTIALLY CLOSED — repository paths reviewed; hosted key-vault/rotation evidence unavailable. |
| Worker logs and telemetry | Minimize context; retain only the debugging/audit value needed. | Remove/redact sensitive payload fields by policy before long-term retention. | CONFIRMED OPEN — bounded log context is implemented, but classification/redaction/TTL is not verified. |
| Backups | Retain according to selected provider configuration; encrypted and access-restricted. | Restore drills must prove backup accessibility before deletion assumptions are made. | PARTIALLY CLOSED — local logical restore verified; managed PITR/retention is blocked by missing hosted evidence. |

## Export and deletion controls

A valid export must include only the authenticated workspace’s eligible records, exclude credentials and service-only records by default, identify any omissions, and write an audit event. A valid deletion request must verify workspace authority, identify dependent records and immutable/audit exceptions, perform the change transactionally where possible, and write an outcome record. Neither workflow is verified in this candidate.

| Requirement | Current state | Required closure evidence |
|---|---|---|
| Workspace-scoped export | CONFIRMED OPEN | API/worker implementation; non-owner and cross-workspace adversarial tests; output schema; export audit record. |
| Credential exclusion | CONFIRMED OPEN | Explicit denylist plus tests that secrets never appear in a bundle. |
| Customer deletion request | CONFIRMED OPEN | Authorized workflow, dependency graph, retention-hold handling, audit record, and recovery implications. |
| Backup deletion handling | CONFIRMED OPEN | Provider-specific retention and expiry evidence; no unsupported claim of immediate purge from immutable backups. |

## Incident notification path

| Severity | Trigger | Immediate operational action | Notification owner | Evidence to preserve |
|---|---|---|---|---|
| Critical | Suspected tenant escape, secret exposure, unauthorized publish, money corruption, or destructive loss | Stop affected jobs/publishing, preserve logs/audit IDs, restrict access without disabling RLS, and escalate. | Security/incident lead and authorized workspace owner. | SHA, version IDs, event IDs, audit trail, scope, timestamps, containment actions. |
| High | Material authorization, reliability, billing, spend, or recovery failure | Pause affected workflow and investigate before retry/resume. | Engineering owner and affected workspace owner. | Reproduction, test/logs, affected data scope, corrective action. |
| Medium | Material UX/operability defect without immediate severe impact | Create tracked remediation, monitor recurrence, and communicate material impact. | Product/engineering owner. | Error evidence and customer-impact estimate. |

Notification timing, regulatory triggers, and customer communication templates are **BLOCKED — EVIDENCE UNAVAILABLE** pending jurisdiction, contracts, and legal authority.

## Provider / subprocessor inventory

| Provider / component | Candidate role | Data potentially processed | Required production control | Evidence state |
|---|---|---|---|---|
| PostgreSQL / managed database provider | Primary transactional database and backups | All stored workspace data | Region, encryption, backup/PITR, access log, DPA, restoration ownership | BLOCKED — provider and credentials unavailable. |
| Stripe | Checkout, webhook, entitlement metadata when enabled | Billing IDs, subscription/event data | Signed webhooks, least privilege, live-key authorization, DPA | PARTIALLY CLOSED in code; live integration blocked. |
| AI/model, speech, rendering, storage, and publishing providers | Optional workflow execution | Inputs/assets/prompts/output and possibly usage data | Per-provider data classification, retention, cost cap, credential scope, DPA and region review | CONFIRMED OPEN — provider selection and environment evidence unavailable. |
| GitHub | Source control and CI metadata | Repository code, logs, workflow results | Protected branches, secrets review, CI evidence linkage | PARTIALLY CLOSED — public repository evidence available; exact complete candidate CI run details not publicly accessible in this audit session. |

## Minimum beta operating rules

The private beta must restrict access to invited workspaces, keep production billing disabled, require the HRG before publish/schedule, use configured data providers only after workspace authorization, and log material security/review/spend events. A production launch remains blocked until hosted backup/PITR, provider inventory, retention/deletion/export controls, live-billing evidence, and legal/commercial governance are closed with appropriate authority.
