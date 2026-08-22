# Lumora Private-Beta Go / No-Go Checklist

**Decision purpose:** determine whether Lumora may admit a controlled, non-paying private-beta cohort for one workflow. This checklist does not approve production launch, live billing, automatic external publishing, or scope expansion.

> A checked document is not evidence. Mark an item **PASS** only with its specified proof; otherwise mark **NO-GO**, **CONDITIONAL**, or **BLOCKED — EVIDENCE UNAVAILABLE**. The Founder makes the launch decision after reviewing this record.

## 1. Release identity and engineering gates

| Gate | Required evidence | Status at preparation | Decision rule |
|---|---|---|---|
| Approved branch/PR | Exact branch, SHA, PR URL, reviewer, and no unauthorised merge. | To be filled at launch. | No-go if SHA is unknown or branch protection/review is bypassed. |
| Hosted CI | API, worker, web, security, and Docker checks green for the exact deployment SHA. | To be rechecked at launch. | No-go if any required job is missing, pending, failed, or tied to a different SHA. |
| Database migration | Migration head, fresh replay, downgrade/replay evidence, and `alembic check` clean. | To be rechecked at launch. | No-go if schema state is ambiguous or a new migration lacks replay evidence. |
| HRG integrity | Exact-item HRG decision required; approval-reuse, concurrency, cross-tenant, and reject/timed-out paths tested. | Repository regression coverage required. | No-go on any HRG bypass or mismatch. |
| Spend integrity | Budget cap, reservation, claim, recovery, DLQ, and duplicate-effect regression coverage green. | Repository regression coverage required. | No-go on unaccounted spend or a cap bypass. |
| Security baseline | RLS, auth, metrics fail-closed, secret scan, dependency audit, and credential controls green. | Hosted and local evidence required. | No-go on a Critical/High security finding. |

## 2. Operational readiness

| Gate | Required evidence | Owner | Status / notes |
|---|---|---|---|
| Deployment access | Founder/operator has the authorised deployment environment and can follow `MONDAY_DEPLOYMENT_RUNBOOK.md` without sharing secrets. | Founder / engineering |  |
| Secret inventory | Required values are present only in the approved secret store; no values appear in repository, PR, tickets, or beta forms. | Founder / security |  |
| Database backup/restore | **BLOCKED — EVIDENCE UNAVAILABLE** until an authorised managed-provider backup/PITR restore drill records backup identifier, RPO, RTO, integrity checks, and owner sign-off. | Operations / database |  |
| Health and worker verification | Authenticated `/health/ready`, `/health/automation`, worker monitor, queue, and Mission Control agree after deployment. | Operator |  |
| Emergency stop | Operator knows authorised pause/emergency-stop action; a non-production rehearsal has been documented if safe. | Operator / engineering |  |
| Incident coverage | Named operator, engineering escalation contact, Founder decision contact, and `BETA_INCIDENT_PLAYBOOK.md` reviewed. | Founder |  |
| Metrics token | Every non-local deployed environment rejects a tokenless metrics request with `401`; proof is recorded without exposing the token. | Operations |  |

## 3. Beta workflow and tester safety

| Gate | Required evidence | Decision rule |
|---|---|---|
| Scope is one workflow | Operator and tester materials use idea/input → generation → processing → HRG → publish-ready → analytics only. | No-go if beta starts with CRM, marketplace, automatic publishing, or unrelated feature work. |
| Reviewer coverage | Every admitted workspace has a named reviewer and no reviewer is expected to approve content they cannot assess. | No-go for unidentified reviewer responsibility. |
| Rights/disclosure boundary | Tester onboarding includes rights and synthetic-media disclosure expectations; publication eligibility rejects missing attestations. | Pause affected item on uncertainty. |
| External-publish boundary | Billing is disabled and no automatic external publish path is enabled. | No-go if publication can happen without separate human authorisation. |
| Data boundary | Tester knows what must not be uploaded and how to report/remove content; export/deletion path and retention boundary are explained. | No-go if sensitive input handling is undefined. |
| Operator evidence log | Template is ready and one owner is assigned to record workflow, HRG, spend, alert, and incident identifiers. | No-go if outcomes cannot be measured. |

## 4. Tester cohort and measurement readiness

| Gate | Required evidence | Status / rule |
|---|---|---|
| Candidate pool | At least 10 qualified prospects are scored; invite only a small initial wave until daily operations are stable. | Recruitment plan exists; actual prospects are not fabricated. |
| Selection fit | Prospects match the defined creator/operator profiles and have a recurring content workflow. | Disqualify users seeking auto-posting, prohibited content, or free consulting rather than a beta workflow. |
| Feedback method | Tester has the onboarding guide and structured feedback form. | Feedback must tie to actual workspace/run/review events. |
| Cohort metrics | Activation, completion, accepted-output, repeat-use, technical-failure, cost-per-accepted-output, and WTP definitions are documented. | No product-market-fit claim before actual denominators exist. |
| Commercial boundary | No paid conversion or live billing. WTP discussion occurs only after actual workflow use. | No pricing claim from praise or hypothetical survey response. |

## 5. Launch decision record

| Field | Required entry |
|---|---|
| Decision date/time (UTC) |  |
| Exact deployed SHA / PR |  |
| Beta cohort cap / admitted workspaces |  |
| All no-go items resolved or explicitly accepted? |  |
| Open risks and mitigations |  |
| Managed-PITR status | PASS / CONDITIONAL / **BLOCKED — EVIDENCE UNAVAILABLE** |
| Live billing status | Must be **disabled** |
| Automatic external publishing status | Must be **disabled** |
| Founder decision | Proceed / proceed with constraints / hold |
| Approver name |  |

## References

[1]: [Private Beta Validation Plan](PRIVATE_BETA_VALIDATION_PLAN.md)
[2]: [Beta Operator Runbook](BETA_OPERATOR_RUNBOOK.md)
[3]: [Beta Incident Playbook](BETA_INCIDENT_PLAYBOOK.md)
[4]: [Monday Deployment Runbook](MONDAY_DEPLOYMENT_RUNBOOK.md)
