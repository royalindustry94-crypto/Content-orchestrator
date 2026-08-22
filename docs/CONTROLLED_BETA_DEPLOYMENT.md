# Controlled Beta Deployment Preparation

**Baseline:** `6a5bc999129309a55b6ea1f088d9de708e94be6c` on `main`

**Executable baseline:** `c4c501b61dea23f036560d6473c85cd848f4aadc`

**Migration head:** `0040`
**Deployment state:** Prepared only. No deployment, billing activation, automatic external publishing, or tester invitation is authorised by this document.

> The repository has a verified Docker Compose staging path. The sandbox is not an eligible persistent beta host. The safe supported route is an **operator-owned, access-restricted VM or container host running the repository’s Docker Compose service topology**, paired with a **managed PostgreSQL service with PITR** before any tester admission. The built-in Compose PostgreSQL volume is acceptable only for an operator-only verification; it is not evidence of recoverable tester data.

## 1. Baseline and release guard

| Check | Required result |
|---|---|
| Git revision | Deploy only `6a5bc999129309a55b6ea1f088d9de708e94be6c`; confirm `git rev-parse HEAD` after checkout. |
| Executable identity | Confirm `c4c501b…` is an ancestor and `git diff c4c501b… HEAD -- apps/api apps/worker apps/web apps/api/alembic` is empty. |
| Migration | `alembic heads` reports only `0040`; `alembic current` reports `0040` after migration. |
| Restricted capabilities | `BILLING_ENABLED=false`; no Stripe secrets; no automatic external publishing pathway enabled; Human Review Gate stays mandatory. |
| Access posture | Public ingress is disabled. Only the named release operator and an allowlisted internal/zero-trust route may reach the deployment. |

## 2. Recommended deployment path

Use the repository-supported `docker-compose.staging.yml` topology on a dedicated, non-public Linux VM or equivalent container host. It starts the `api`, `worker`, and `web` services; `web` proxies relative `/api` traffic to the API. Use a managed PostgreSQL instance with backups and PITR for any environment that can store tester data. The service host must connect to that database over TLS and must not expose the database port publicly.

For the first operator-only deployment verification, the Compose database may be used only if no tester or real customer data is admitted. Before invite or tester admission, replace it with managed PostgreSQL PITR evidence and keep the same owner/migration and runtime-RLS connection separation.

## 3. Secrets versus configuration

### Required secrets before operator-only deployment

| Secret | Purpose | Handling rule |
|---|---|---|
| `DATABASE_URL` | Owner/migration PostgreSQL connection | Store only in the deployment secret manager; used by manual migration job. |
| `APP_DATABASE_URL` | `app_runtime` PostgreSQL connection for request RLS | Separate from owner connection; never substitute owner credentials. |
| `SUPABASE_JWT_SECRET` | JWT verification | Minimum 32 bytes; do not log or commit. |
| `METRICS_SCRAPER_TOKEN` | Authenticates `/metrics` scraper | Required in a deployed environment; retain outside application logs. |
| `WORKER_CREDENTIAL` | Authenticates worker registration, claims, heartbeat, and results | One unique credential per worker; rotate on compromise. |

### Required non-secret environment variables

| Variable | Controlled-beta value or rule |
|---|---|
| `ENVIRONMENT` | `staging` or another non-`local` deployed value; never `development`. |
| `AUTH_MODE` | Prefer `supabase` with pre-provisioned identities before tester admission. `local` is limited to allowlisted operator verification and must not be used as an open public signup surface. |
| `CORS_ALLOW_ORIGINS` | Exact allowlisted beta web origin, as a JSON array; no wildcard. |
| `BILLING_ENABLED` | **`false`**. |
| `RUN_MIGRATIONS` | `0` after the manual, single-writer migration procedure succeeds. |
| `API_BASE_URL` | Internal API URL visible to the worker, not a public database URL. |
| `WORKER_ID` | Stable non-secret worker identifier. |
| `DEPLOYMENT_GIT_BRANCH` | `main`. |
| `DEPLOYMENT_COMMIT_SHA` | `6a5bc999129309a55b6ea1f088d9de708e94be6c`. |
| `DEPLOYMENT_AT`, `DEPLOYMENT_CI_STATUS`, `DEPLOYMENT_CI_URL` | Record real deployment metadata and [main CI run 32579026421][1]. |

### Optional integrations — leave unset for controlled beta

Stripe settings (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO`, checkout URLs), provider keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `CREATOMATE_API_KEY`), GitHub tokens, automation webhook URLs, and absolute frontend build variables are **not deployment prerequisites**. Do not add them until separately authorised and needed by a reviewed beta workflow.

## 4. Database deployment and migration procedure

1. Obtain an immutable backup identifier or PITR restore point from the managed database provider. Do not proceed if this evidence is absent for a tester-capable deployment.
2. Restrict or stop API and worker writers. Keep the current image tag and deployment manifest available for rollback.
3. Run one manual migration job using `DATABASE_URL` only:

   ```bash
   cd apps/api
   alembic upgrade head
   alembic current
   alembic check
   ```

4. Require `0040` from both `alembic current` and `alembic heads`. Record command time, operator, database identifier, and result.
5. Start API and web with `RUN_MIGRATIONS=0`. Start the worker only after worker credentials and a controlled smoke workspace are prepared.
6. Do not use a downgrade as a routine rollback. A destructive or incompatible rollback requires its own approved plan and restored database evidence.

## 5. Rollback and recovery

| Failure | Immediate action |
|---|---|
| Image/config regression | Stop the new API/worker deployment and redeploy the immediately previous verified image tag/configuration. Keep billing false and preserve logs. |
| Migration or data integrity issue | Stop writers; preserve evidence; restore to a new managed database instance from the pre-migration PITR/backup; validate there before any cutover. |
| Suspected RLS or tenant leak | Declare SEV-1, freeze writes and access, preserve snapshot/log evidence, and do not route traffic through an owner connection. |
| Spend storm | Pause the workspace/workers and lower a workspace cap with an authorised admin; do not globally disable controls. |
| Worker defect | Deregister/stop only the affected worker and preserve worker/outbox logs. |

## 6. Backup/PITR evidence before tester admission

Tester admission is blocked until the operator records: provider name and project/instance, backup or restore-point identifier and timestamp, retention policy, encryption/TLS confirmation, a side-by-side restore drill, measured RPO/RTO, `alembic current=0040`, `app_runtime` connectivity, a cross-workspace denial check, and signed owner acknowledgement. Docker-volume existence is not backup evidence.

## 7. Deployed health and security checks

Run these against the non-public API origin; retain only status, timestamps, and redacted responses in the deployment record.

```bash
curl -fsS "$API_ORIGIN/health/live"        # expected 200; {"status":"ok"}
curl -fsS "$API_ORIGIN/health/ready"       # expected 200; database=reachable
curl -fsS "$API_ORIGIN/health/automation"  # expected status=ok; tasks/ticks and no last_error
curl -sS -o /dev/null -w '%{http_code}\n' "$API_ORIGIN/metrics"  # expected 401
curl -fsS -H "Authorization: Bearer $METRICS_SCRAPER_TOKEN" "$API_ORIGIN/metrics" | head
```

The unauthenticated `/metrics` request must return **401** in `staging`, `preview`, `demo`, `beta`, production, or any other deployed environment. A bearer-authenticated request must return Prometheus text without disclosing the token.

## 8. Disposable-workspace smoke procedures

### Human Review Gate and tenancy smoke

Under an allowlisted, disposable operator identity and an `AUTH_MODE=local` verification deployment, run:

```bash
API_BASE="$WEB_ORIGIN/api" SMOKE_PASSWORD="<ephemeral-value>" \
  node scripts/verify_hrg_isolation.mjs
```

The script creates unique disposable tenants, creates one content job, requires an awaiting Human Review Gate, approves it, verifies its decision persists, verifies a second decision is rejected, verifies a foreign tenant cannot read the workspace/review/health surfaces, and verifies unauthenticated access is denied. Require every reported check to pass; delete or expire the disposable workspace through the approved data-governance process after evidence capture. For `AUTH_MODE=supabase`, use a pre-provisioned disposable JWT identity and execute the equivalent reviewed API calls; do not switch production-like auth to local merely to run the script.

### Spend-control smoke

Create a disposable workspace under an operator admin identity. Confirm an ordinary member receives `403` when attempting `PATCH /workspaces/{workspace_id}/spend`. As the workspace admin, set a low reversible cap through that route, record the returned snapshot, submit only the approved non-billable smoke fixture, and verify the operations spend view reports the cap/usage/reservation state. If a cap refusal or hold is triggered, treat it as a pass only when no provider effect was emitted and the event is observable in the workspace audit/activity path. Restore the initial cap or dispose of the workspace; do not raise a global cap.

### Worker and queue-health smoke

Start one worker with a unique `WORKER_CREDENTIAL` and `WORKER_ID`. Require successful registration and heartbeat in worker logs and the Workspace Operations worker monitor. Then require `/health/automation` to report active maintenance, outbox relay, and scheduler tasks with advancing ticks, no `last_error`, and a coherent `jobs_leased` value. Inspect authenticated `/workspaces/{workspace_id}/operations/workers`, `/operations/health`, and `/operations/spend` views; the worker must not merely be a running process without credentials or a heartbeat.

## 9. Exact tester-admission state

A tester may be invited only when every condition below is recorded against the deployed URL and current `main` SHA:

| Requirement | Required state |
|---|---|
| Deployment identity | Non-public deployment resolves to the approved main baseline; SHA and image identifiers recorded. |
| Database safety | Managed PITR restore drill evidence and pre-migration restore point recorded. |
| Health | `/health/live`, `/health/ready`, and `/health/automation` pass; automation loops have no errors. |
| Metrics | Tokenless `/metrics` returns `401`; authorised scrape succeeds. |
| HRG and isolation | Disposable smoke passes all HRG, double-decision, unauthenticated, and cross-workspace denial checks. |
| Spend and worker | Disposable workspace cap/visibility smoke and credentialed worker/queue-health smoke pass. |
| Billing and publishing | `BILLING_ENABLED=false`; no automatic external publishing enabled; Human Review Gate mandatory. |
| Identity and admission | Named beta owner, pre-provisioned tester identity, explicit consent, workspace assignment, support contact, and rollback owner exist. |

## 10. Current deployment verdict

**DEPLOYMENT BLOCKED** pending an operator-provided non-public host, managed PostgreSQL PITR/restore evidence, deployment secrets, exact CORS origin, pre-provisioned identity path, and an authorised deployment operator. The code baseline is verified; the blockers are deployment authority and hosted operational evidence, not a request to add product features.

## References

[1]: https://github.com/royalindustry94-crypto/actions/runs/32579026421
