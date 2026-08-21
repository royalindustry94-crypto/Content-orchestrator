# Lumora Private-Beta Incident Playbook

**Purpose:** Contain harm, preserve evidence, and make a clear owner decision during the controlled private beta. This playbook does not authorize direct writes to `main`, force-pushes, secret disclosure, production billing activation, or bypassing the Human Review Gate.

## 1. First-response rule

> **Contain first; investigate second; resume only with evidence.**

If the report may involve tenant isolation, Human Review Gate bypass, uncontrolled publication, spend/cost integrity, credentials, payment, or a Critical/High security issue, pause the affected workflow immediately. If the blast radius is unknown, pause all beta intake and workers through the authorised operational control.

Record the deployed SHA, workspace/content/run/gate identifiers, time in UTC, reporter, current status, and every action taken. Do not delete audit records, retry blindly, or request secrets through chat or feedback forms.

## 2. Severity and response targets

| Severity | Definition | Immediate action | Beta state | Initial owner |
|---|---|---|---|---|
| SEV-1 | Confirmed or credible suspected tenant escape, credential exposure, uncontrolled external publish, HRG bypass, payment/security integrity failure, or irreversible data loss. | Pause all workers and beta intake; preserve evidence; notify Founder and engineering/security owner. | **Global pause.** | Engineering/security lead. |
| SEV-2 | One workspace is blocked, spend/reservation is inconsistent, repeated DLQ/worker failure, stale HRG with material impact, or a data-deletion/export problem. | Pause affected workspace/workflows; stop retry loop; triage with on-call. | **Workspace pause** unless scope expands. | Beta operator + engineering. |
| SEV-3 | Non-security defect, confusing UX, one failed run with safe recovery, or documentation issue. | Record, give safe workaround only if it preserves controls, schedule repair. | Continue with observation. | Beta operator. |
| SEV-4 | Question, feature request, cosmetic issue, or non-blocking feedback. | Record in feedback/issue log. | Continue. | Product owner. |

The times below are operating targets, not claims about current staffed coverage: acknowledge SEV-1/2 immediately when observed, make a containment decision within 30 minutes, and update the reporter at least every 60 minutes until the system is safe or the incident is handed off.

## 3. Incident-specific containment

| Signal | Containment | Evidence to preserve | Do not do |
|---|---|---|---|
| Another workspace's data is visible | Stop user interaction; pause all beta access if scope is unknown. | Redacted screenshot, requester identity, workspace/content/run IDs, API route/action, UTC timestamp, deployed SHA. | Browse further data or ask the tester to prove access. |
| HRG bypass, wrong decision, or approval reuse | Pause the content item and affected workspace; if systemic, pause all workers. | Gate, run, content/version IDs; decision history; actor; request traces. | Reuse an approval, manually set approval, or externally publish. |
| External publication appears automatic | Emergency-stop workers and disable further publish attempts through authorised controls. | Output URL, content/run/eligibility IDs, platform, timestamps, action history. | Delete remote evidence or post a corrective message without approval. |
| Spend cap/reservation anomaly | Pause affected workspace and retry loop; do not submit duplicate work. | Spend/reservation rows, provider-effect IDs, assignment/attempt IDs, cap config, current run state. | Manually edit spend/audit rows or bypass cap. |
| Credential or secret exposure | Revoke/rotate through the authorised secret owner; pause affected integration. | Location, commit/PR SHA, scope, access log if available. | Paste the secret into tickets, PRs, chat, or documents. |
| Data export/deletion defect | Stop the request path; preserve request/response metadata and scope. | Workspace, requester, route, outcome, retained/withdrawn counts. | Retry deletion until it "looks right". |
| Worker / DLQ / retry failure | Pause the specific job if it repeats; determine whether a provider effect may already exist. | Assignment/attempt, worker ID, logs, DLQ record, provider-effect key, reservation state. | Clear DLQ or retry without classifying the failure. |
| Metrics/health mismatch | Treat automation health as untrusted; pause intake if health cannot be reconciled. | `/health/ready`, `/health/automation`, Mission Control state, worker monitor, timestamp. | Declare healthy based on one stale panel. |

## 4. Investigation and recovery checklist

1. **Classify scope.** Determine whether the issue is a single content item, workspace, integration, or global control. Unknown scope defaults to broader containment.
2. **Freeze state safely.** Use authorised pause/emergency-stop controls. Preserve the deployed SHA and PR URL before any remediation.
3. **Collect identifiers.** Capture workspace, user, content, version, run, gate, assignment, provider-effect, reservation, alert, and incident identifiers that exist. Redact personal data and never collect secrets.
4. **Establish facts.** Separate observed facts from hypotheses. A log line, screenshot, or dashboard assertion is not by itself proof of a root cause.
5. **Choose remediation path.** Repository defects require a branch, regression test, green local validation, review, and hosted CI. Operational configuration defects require the authorised owner and documented verification.
6. **Verify recovery.** Re-run the exact control test or operational check that would have blocked the incident. Do not close an incident on a code review alone.
7. **Communicate.** Tell affected testers what is known, what action they should take, and when the next update will arrive. Do not speculate about cause or expose other users' data.
8. **Post-incident review.** Record root cause, controls that failed, evidence, remediation, residual risk, owner, and whether beta scope must narrow.

## 5. Resume criteria

| Incident class | Resume only when |
|---|---|
| SEV-1 tenant/HRG/credential/publish/payment | An authorised security/engineering owner has confirmed containment; the fix or operational control is validated; the Founder authorises resumption. |
| Spend / provider effect | Reservation and provider-effect lineage are reconciled; the cap is not bypassed; a bounded retry policy is explicit. |
| Deletion/export | Scope and retained classes are understood; the affected request is safe or disabled; the tester receives an accurate update. |
| Worker/DLQ | The failed item is classified, any potential duplicate provider effect is addressed, and retry is safe. |
| Health/metrics | Readiness, automation state, and worker monitor agree; alerts are owned. |

## 6. Incident record template

| Field | Required entry |
|---|---|
| Incident ID / severity |  |
| Discovered by / UTC timestamp |  |
| Deployed SHA / PR |  |
| Scope | Global / integration / workspace / content item |
| Observed facts |  |
| Containment action and UTC time |  |
| Evidence references | Identifiers, redacted logs, screenshots, alert IDs; no secrets. |
| Root cause status | Unknown / suspected / confirmed |
| Remediation / verification | Branch/PR/test or authorised operational step |
| Tester communication | What was sent and when |
| Resume authority | Named owner and rationale |
| Follow-up owner / due date |  |

## References

[1]: [Beta Operator Runbook](BETA_OPERATOR_RUNBOOK.md)
[2]: [Data Governance Baseline](DATA_GOVERNANCE.md)
[3]: [Audit Finding Closure Register](AUDIT_FINDING_CLOSURE.md)
[4]: [Monday Deployment Runbook](MONDAY_DEPLOYMENT_RUNBOOK.md)
