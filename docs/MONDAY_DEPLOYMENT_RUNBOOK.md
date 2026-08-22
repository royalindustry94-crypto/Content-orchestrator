# Monday Deployment Runbook

**Purpose:** deploy the latest **approved** Lumora release after the Founder has access to the intended deployment environment. GitHub remains the source of truth. This runbook does not authorize a merge, force-push, direct `main` write, live billing, automatic external publishing, or use of a secret in chat, a PR, or a repository file.

> **Deploy gate:** do not deploy a branch merely because it exists. The deployment SHA must be explicitly approved by the Founder or be the repository's approved release/merged commit. If the environment, provider access, managed backup, or approved SHA is unavailable, stop and report **BLOCKED — EVIDENCE UNAVAILABLE**.

## 1. One instruction for the Monday agent

Paste the following into Cursor/Replit only after the Founder has opened the repository and deployment environment:

```text
Act as Lumora release operator. GitHub is the only source of truth. Read docs/MONDAY_EXECUTION_PACKET.md, docs/MONDAY_DEPLOYMENT_RUNBOOK.md, docs/BETA_GO_NO_GO_CHECKLIST.md, docs/AUDIT_FINDING_CLOSURE.md, and the current open PR state before acting. Do not merge, force-push, write to main, enable live billing, enable automatic external publishing, or reveal secrets. Deploy only the exact SHA that I explicitly approve after you verify its PR/CI evidence. First inspect the deployment provider and secret store without printing values; if any required access, managed-backup/PITR evidence, or approved SHA is missing, stop with BLOCKED — EVIDENCE UNAVAILABLE. Follow the runbook's preflight, backup, migration, API, worker, web, health, HRG, spend, and Mission Control checks. Preserve the prior deployment reference for rollback. Report every executed command, deployed SHA, health result, migration head, worker state, and unresolved blocker. Do not invent or substitute a provider, secret, customer, cost, or test result.
```

## 2. Approved release and preflight record

Before changing the environment, record the following in an access-controlled release note. Do not place secrets or customer data in the note.

| Item | Required proof | Status |
|---|---|---|
| Release SHA | Exact commit SHA approved by Founder/release owner. |  |
| GitHub evidence | PR URL, required-check URLs and conclusions for that SHA, review/approval state. |  |
| Source state | Clean checkout of exact SHA; no local uncommitted deployment modifications. |  |
| Migration head | `cd apps/api && alembic heads`; record expected revision. |  |
| Environment classification | Staging/private beta/production-like; database provider; DNS/frontend URL. |  |
| Rollback reference | Currently deployed SHA/image/release ID and previous known-good migration head. |  |
| Backup/PITR | Backup identifier or provider recovery point, retention, and restore owner. |  |
| Operator authority | Founder, deployment owner, database owner, and incident owner are reachable. |  |

No-go conditions include an unknown SHA, failed/pending CI, no approved deployment authority, inability to identify a rollback reference, unverified database target, live billing enabled, or an automatic external publishing path enabled.

## 3. Secret and environment requirements

Use an approved secret store or deployment-provider configuration. Inspect names and presence only; do not print values. `.env.example` is an annotated template, **not** a production configuration.

| Variable / configuration | Required for | Rule |
|---|---|---|
| `ENVIRONMENT` | All services | Use the intended non-development value; docs/OpenAPI are disabled outside development. |
| `DATABASE_URL` | Alembic/owner migration connection | Owner/migration role only; TLS/network policy must match provider requirements. |
| `APP_DATABASE_URL` | API runtime | Must use the non-owner `app_runtime` role so RLS remains enforced. |
| `SUPABASE_JWT_SECRET`, algorithm, audience | API token verification | Store only in approved secret manager; rotate through owner process after compromise. |
| `AUTH_MODE` | Authentication boundary | Prefer `supabase` for production-like deployment. `local` is a narrow beta fallback; its production override must not be silently enabled. |
| `CORS_ALLOW_ORIGINS` | Web/API boundary | Exact approved HTTPS origin(s), no wildcard convenience setting. |
| `WORKER_CREDENTIAL`, `WORKER_ID`, `WORKER_NAME` | Worker registration and claiming | Store/rotate as credentials; do not paste into runbook/logs. |
| `METRICS_SCRAPER_TOKEN` | Metrics in non-local deployments | Required; verify tokenless `/metrics` returns `401` without printing token. |
| `BILLING_ENABLED` | Billing boundary | Must remain `false` for private beta. Do not set Stripe values or activate checkout. |
| Provider integration keys | Only an explicitly tested beta stage needs them. | Omit unused integrations; log availability as `BLOCKED — EVIDENCE UNAVAILABLE`, not as a false green state. |
| Deployment metadata | Mission Control context. | Set branch, SHA, deployment time, CI status/URL truthfully; omit rather than fabricate. |

### Database requirements

The target database must be isolated from local/staging test data, reachable through secure provider/network configuration, and backed up or PITR-capable per the approved environment policy. The runtime connection must remain restricted to `app_runtime`; do not solve a migration/RLS issue by disabling RLS or running the application with the owner role.

`docker-compose.staging.yml` contains a self-hosted validation stack with local PostgreSQL defaults. It is useful for a controlled staging rehearsal but is **not** evidence of a managed production backup/PITR posture. Do not expose its database port publicly or reuse its development credentials in a managed deployment.

## 4. Deployment sequence

### A. Prepare source and artifacts

1. In a clean directory, fetch GitHub and check out the exact approved SHA.
2. Confirm the PR/head SHA and CI checks correspond to the same SHA.
3. Build or retrieve immutable API, worker, and web artifacts tagged with the exact SHA; retain the current deployed artifact/version as rollback target.
4. Run no migration until backup/PITR and rollback reference are recorded.

For a controlled self-hosted staging rehearsal only, the repository supports:

```bash
cp .env.example .env
# Populate only through the approved secret mechanism; do not commit .env.
docker compose -f docker-compose.staging.yml up --build
```

The compose API runs `alembic upgrade head` only when `RUN_MIGRATIONS=1`; it starts after Postgres is healthy. The worker waits for API liveness, and web waits for API liveness. Treat this as a staging procedure; a managed deployment should run the same checks through its provider's approved release mechanism.

### B. Database and migration gate

1. Stop or pause writers/worker claims before any potentially disruptive migration.
2. Confirm owner connection points to the intended database and runtime connection points to `app_runtime`.
3. Capture a managed recovery point or authorised logical backup reference. Do not store dump content in Git.
4. Run migration once through the approved owner connection:

```bash
cd apps/api
alembic current
alembic upgrade head
alembic current
alembic check
```

5. Confirm the resulting revision equals the pre-recorded expected head. If migration fails, do not repeatedly retry or edit migration history. Preserve logs, restore or roll back using the provider/runbook, and open an incident.

### C. Start services in safe order

1. Start API with `APP_DATABASE_URL` runtime role and health checks enabled.
2. Verify API liveness and readiness before starting worker claims:

```bash
curl -fsS https://<approved-api-host>/health/live
curl -fsS https://<approved-api-host>/health/ready
curl -fsS https://<approved-api-host>/health/automation
```

3. Start one approved worker with its managed credential. Verify registration/heartbeat and eligible worker state before admitting beta work.
4. Start or switch the web artifact and verify the exact approved frontend URL through the HTTPS path.
5. With no sensitive values in terminal history, verify metrics access behavior:

```bash
# Expected: HTTP 401 outside local/test/CI when no bearer token is sent.
curl -o /dev/null -s -w '%{http_code}\n' https://<approved-api-host>/metrics
```

6. Verify Mission Control presents health, worker state, jobs, HRG queue, spend, and alerts consistently. If health endpoints and dashboard disagree, pause intake.

### D. Controlled beta smoke

Before inviting a tester, use a disposable, authorised test workspace only. Verify:

| Smoke | Expected result |
|---|---|
| Unauthenticated protected route | Denied. |
| Cross-workspace access attempt | Denied; do not use a real tester's data to test this. |
| One intentional workflow | Stage records are observable and spend remains within cap. |
| Human Review Gate | Exact-item reviewer can approve/reject; approval cannot be reused for a different item. |
| Publish-ready handoff | Output becomes publish-ready only; no automatic external publication occurs. |
| Failure/retry | A safe test failure produces truthful state; do not bulk-retry or clear DLQ. |
| Data governance route | Admin-only behavior and confirmation mismatch protection remain enforced, if a non-destructive authorised test is available. |

Record the deployed SHA, workspace/run/gate IDs, result, operator, and time. No real tester is admitted until all smoke rows pass.

## 5. Rollback and recovery

### Application rollback

Prefer switching API/worker/web artifacts back to the recorded previous known-good SHA/image. Stop new worker claims first, then switch artifacts, then verify readiness, automation health, worker registration, and Mission Control.

Do **not** automatically run `alembic downgrade` as an application rollback. A downgrade can be destructive or incompatible with data written by the new version. Use it only after the database owner confirms it is safe for the exact migration path and a verified backup/PITR point exists. No migration may be deleted, renamed, renumbered, or edited to force a rollback.

### Database recovery

For managed PostgreSQL, prefer restore to a new instance/project and validate before cutover. For self-hosted staging, use the repository's `docs/ops/BACKUP_AND_RESTORE.md` procedure: stop writers, recreate/restore the target, verify migration head, `app_runtime`, RLS, health, authenticated read, and review/worker coherency.

If backup/PITR is unavailable, do not claim rollback readiness. Record **BLOCKED — EVIDENCE UNAVAILABLE** and obtain the database owner's decision before deployment.

## 6. Emergency stop

The emergency-stop action is an operational safety mechanism, not a workaround for broken controls.

1. Pause worker claims through the authorised Mission Control action or provider service control.
2. Stop new beta intake and do not start/retry jobs.
3. Preserve SHA, deployment/release ID, workspace/content/run/gate/assignment/provider-effect/reservation identifiers, alerts, and redacted logs.
4. Classify and follow `BETA_INCIDENT_PLAYBOOK.md`.
5. Resume only after the appropriate owner validates the fix or configuration control.

## 7. Post-deployment handoff

The operator records the exact deployed SHA, migration head, PR/CI URLs, environment, health endpoints, worker state, first smoke result, current spend caps, remaining blockers, and named on-call owners in `MONDAY_EXECUTION_PACKET.md` or the access-controlled release record. Do not replace an unavailable field with an estimate.

## References

[1]: [Canonical Deployment Guide](ops/DEPLOYMENT.md)
[2]: [Backup and Restore Guide](ops/BACKUP_AND_RESTORE.md)
[3]: [Beta Go / No-Go Checklist](BETA_GO_NO_GO_CHECKLIST.md)
[4]: [Beta Incident Playbook](BETA_INCIDENT_PLAYBOOK.md)
[5]: [Mission Control Readiness](BETA_MISSION_CONTROL_READINESS.md)
