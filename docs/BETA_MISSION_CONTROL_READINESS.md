# Mission Control Readiness for Private Beta

**Assessment scope:** the narrow private-beta workflow only. This assessment checks whether an operator can see jobs, failures, Human Review Gates, workers, spend, alerts, and health without building a new dashboard. It does not claim that hosted telemetry is populated until a deployment has real work.

## Coverage assessment

| Required visibility | Existing API / surface | Beta decision | Operating note |
|---|---|---|---|
| Jobs running and waiting | Mission Control V4 summary exposes `jobs_running` and `jobs_waiting`; operations dashboard provides executive/pipeline views. | **Present.** | Check by workspace and correlate to run IDs before retrying. |
| Jobs failed and DLQ | V4 summary exposes `jobs_failed_today` and critical alerts; operations actions and dashboard support failed-job/DLQ review. | **Present.** | Treat a repeated failure or DLQ as a triage event, not a bulk-retry queue. |
| Human Review Gate queue | Review-gate routes and dashboard content-command/pipeline surfaces expose awaiting review state. | **Present.** | An approval is item/run-specific; use the exact gate ID. |
| Worker state | Worker monitor/timeline plus V4 online/total counters. | **Present.** | Reconcile worker state with `/health/automation`; do not rely on a stale count alone. |
| Spend | V4 shows daily/monthly spend; operations dashboard has spend and cost-control surfaces. | **Present.** | Inspect caps, reservations, provider-effect lineage, and unexpected retry cost before resuming work. |
| Alerts | V4 exposes critical-alert count; operations dashboard exposes alert and activity surfaces. | **Present.** | Every critical alert needs an owner or triggers an intake pause. |
| System health | `/health/live`, `/health/ready`, `/health/automation`, Mission Control health indicators, and metrics route (token-gated outside local/test/CI). | **Present.** | Readiness, automation state, and worker monitor must agree. |
| Emergency stop | Operations quick-action routes include pause-workers, resume-workers, and emergency-stop. | **Present.** | Operator must be authorised and rehearsed before beta starts. |

## Minimum missing visibility for beta

No new dashboard capability is a beta blocker because each required visibility category already has an API/dashboard surface. The only gaps are **operational evidence gaps**, which cannot be solved by additional UI:

| Deferred item | Why deferred | Required beta operating control |
|---|---|---|
| Hosted alert delivery / paging evidence | Requires deployment credentials and an authorised alert destination. | Use a named operator, daily check, and documented manual escalation until verified. |
| Real-workload dashboards | Empty beta has no truthful operations data. | Record first-workflow IDs and compare Mission Control with health endpoints. |
| Historical trend analytics | Not necessary to safely run the first controlled workflows. | Use weekly cohort report from the operator log; defer richer analytics until data exists. |
| Automated platform-publish status | External automatic publishing is out of beta scope. | Treat outputs as publish-ready only; testers publish separately under their own account process. |

> **Decision:** No Mission Control UI implementation is authorised in this workstream. Building another interface would not close the operational evidence gaps and would expand scope away from the core workflow.

## Beta operator drill

Before admitting the first tester, the operator should verify the following in a non-production-safe environment or approved deployment:

1. Reach the dashboard as an authorised workspace administrator.
2. Read the current health indicators and compare them with `/health/ready` and `/health/automation`.
3. Locate jobs running/waiting, failed/DLQ work, pending HRG decisions, worker state, daily/monthly spend, and critical alerts.
4. Confirm the emergency-stop/pause path is authorised and that the incident playbook identifies who may use it.
5. Start no tester work if the dashboard state and health endpoints disagree.

## References

[1]: [Beta Operator Runbook](BETA_OPERATOR_RUNBOOK.md)
[2]: [Beta Incident Playbook](BETA_INCIDENT_PLAYBOOK.md)
[3]: [Private Beta Validation Plan](PRIVATE_BETA_VALIDATION_PLAN.md)
