# Testing Guide

How to run Content Orchestrator locally and exercise it end to end.

**Updated:** 2026-08-29

---

## 1. Start everything

```bash
scripts/dev_up.sh --simulation
```

That one command creates `.env` if missing, generates the JWT secret, starts
Postgres (Docker, or uses a local server if one is already listening), installs
dependencies, applies migrations, and starts the API, worker, and web app.

When it prints `Ready.`, open **http://localhost:5173/**.

Re-running it is safe. `Ctrl+C` stops everything.

| Flag | Effect |
|---|---|
| `--simulation` | Deterministic offline content provider. The pipeline produces visible output. |
| *(none)* | No content provider. Every pipeline stage stops at `provider_not_configured`. |

### If you skip the script

You need Postgres 16 reachable at `DATABASE_URL`, then:

```bash
cd apps/api && alembic upgrade head && uvicorn app.main:app --reload --port 8000
cd apps/worker && python -m worker.main
cd apps/web && npm install && npm run dev
```

`SUPABASE_JWT_SECRET` has no default and the API will refuse to start without
it. The `app_runtime` role that `APP_DATABASE_URL` uses is created by the
Milestone 2 migration, so migrations must run before anything serves traffic.

---

## 2. What the simulation provider is

`PIPELINE_PROVIDER_MODE=simulation` selects a provider that generates content
**offline and deterministically**. It calls no external service and spends
nothing. It exists so the pipeline and its audit gates can be tested before any
paid vendor is activated.

What it does **not** change:

- The Human Review Gate is still mandatory.
- External publishing is still disabled.
- The independent auditors still run for real and still block bad output.
- Spend reservations are still made and committed.

Every record it writes is labelled `simulation`, its citations use the reserved
`.invalid` domain so they can never be mistaken for real sources, and the web
app shows a banner on every screen while it is active. It is **refused when
`ENVIRONMENT` is production**, with no override.

Activating a real vendor (OpenAI, ElevenLabs, a renderer, a policy source) is a
separate audited milestone — see PROVIDER-001 in `docs/LAUNCH_BLOCKERS.md`.

---

## 3. Sign up

On http://localhost:5173/ choose **Create account**.

- Password must be at least 12 characters.
- Your first workspace is created automatically and you are its admin.

---

## 4. The short path: Review Desk

This is the Private Beta revenue path and works in **either** provider mode.

1. **Home** → *Advanced operator controls* → **Create Pipeline**, enter a topic.
2. Go to **Human Review**. The draft is waiting there.
3. Open it, read the script, then **Approve** or **Reject**.

What to check: the item cannot reach `published` without a decision here, and
the script you approve is the exact version bound to the gate.

---

## 5. The full path: Scout to Human Review

Requires `--simulation`. Each stage refuses to start until the previous one has
passed its independent audit, so the order matters.

| # | Screen | Action | Expected |
|---|---|---|---|
| 1 | **Opportunities** | Run research with any objective | Run status `succeeded`; one opportunity appears |
| 2 | **Opportunities** | Run the Research Auditor on it | State `pass` |
| 3 | **Strategy** | Record a strategy request using that opportunity | Brief created |
| 4 | **Strategy** | Run the Strategy Auditor | State `pass`; Writer handoff eligible |
| 5 | **Content Department** | Record a content request using that brief | Package created, awaiting audits |
| 6 | **Content Department** | Run the content audits | Language, fact, brand, originality all `pass` |
| 7 | **Producer** | Request production for the package | Artifact rendered with a hash, 9:16, 45s |
| 8 | **Producer** | Run Media QA on the artifact | Status `pass`; readiness still `blocked` |
| 9 | **Compliance** | Request compliance for the artifact | Status `pass`, rights `verified` |
| 10 | **Compliance** | Run the Chief Auditor | `pass_to_human_review` |
| 11 | **Human Review** | A new gate is waiting | Approve or reject it |

> **Use topics made of words, not numbers.** The writer echoes your topic into
> the script, and any sentence containing a digit is classified as a `NUMBER`
> claim, which the fact auditor blocks because no verification provider can
> substantiate a quantity. "coffee brewing tips" runs clean; "top 5 coffee tips"
> stops at step 6 and the Producer gate then refuses with a 409. That is the
> control working.

### The interesting failures

These are worth testing deliberately, because they are the controls:

- **Skip step 2** and try step 3. The Strategist request is refused (409): a
  Research Auditor pass is required first.
- **Skip step 6** and check the Producer gate. It is refused: all four content
  audits must pass before Producer handoff.
- **Skip step 8** and try step 9. Compliance is refused: it requires a Media QA
  pass bound to that exact artifact hash.
- **Skip step 9** and run step 10. The Chief Auditor returns `blocked` with
  `compliance_missing`, and **no review gate is created**.
- **Repeat step 1 with the same objective.** The second run reports
  `opportunity_count: 0` — deduplicated, not piled up.
- **After approving in step 11**, request publication eligibility. It is still
  `false` with `external_publishing_disabled`. Nothing upstream unlocks
  publishing.

---

## 6. Other things to exercise

| Area | Where | Notes |
|---|---|---|
| Spend caps | **Money** | Caps are enforced fail-closed; a request over cap gets HTTP 402 and the run pauses on `spend_hold` |
| Workspace isolation | Create a second account | Neither account can see the other's workspace at all |
| Worker | **Workforce** | The reference worker idles until provisioned with a credential |
| Ops views | **Connections** | Overview, timeline, live logs, assistant |

The Home screen's bankroll figures and AI Workforce departments read
"Not connected" by design. They require a source-backed integration and will not
show invented numbers.

---

## 7. API directly

With `ENVIRONMENT=development` the OpenAPI explorer is at
**http://localhost:8000/docs**.

```bash
curl -s localhost:8000/pipeline/provider   # which provider is active
curl -s localhost:8000/health/ready        # API + database
curl -s localhost:8000/health/automation   # background loops
```

---

## 8. Running the test suites

```bash
cd apps/api    && pytest --cov=app --cov-fail-under=75
cd apps/worker && pytest
cd apps/web    && npm test && npm run build
```

The API suite needs Postgres and a database migrated to head. It uses
`content_orchestrator_test` by default; override with `TEST_DATABASE_URL` and
`TEST_APP_DATABASE_URL`.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| API exits on startup | `SUPABASE_JWT_SECRET` missing | `scripts/dev_up.sh` generates one; or set it in `.env` |
| `role "app_runtime" does not exist` | Migrations have not run | `cd apps/api && alembic upgrade head` |
| Pipeline screens all say "provider not configured" | Running in `null` mode | Restart with `scripts/dev_up.sh --simulation` |
| API refuses to start with a provider error | `ENVIRONMENT=production` with simulation | Simulation is forbidden in production by design |
| Postgres unreachable | No server and no Docker | `docker compose up -d postgres`, or run a local Postgres 16 |
| Web loads but every call fails | API not up on :8000 | The Vite dev server proxies `/api` to `localhost:8000` |

---

## 10. Testing from a phone

`scripts/dev_up.sh` binds to localhost, which a phone cannot reach. Two options:

```bash
# Same routing shape as the deployed preview (static SPA + API under /api).
npm --prefix apps/web run build
PIPELINE_PROVIDER_MODE=simulation RUNTIME_PROFILE=serverless \
  python scripts/serve_preview.py --host 0.0.0.0 --port 8080
```

Then reach it over your LAN, or put a tunnel in front of it. For a hosted
preview against the isolated Supabase test project, see
`docs/ops/VERCEL_PREVIEW.md`. Either way, verify it with:

```bash
python scripts/verify_preview.py http://<host>:8080
```

Note that `RUNTIME_PROFILE=serverless` intentionally stops the background loops,
so the Draft Desk worker path is not exercised — `/health/automation` says so.
Leave it at the default `server` if you need the worker.

---

## Related

- `docs/work-packages/WP-PB-005-pipeline-provider-abstraction.md`
- `docs/ops/VERCEL_PREVIEW.md`
- `docs/LAUNCH_BLOCKERS.md`
- `docs/BETA_OPERATOR_RUNBOOK.md`
- `docs/ops/DEPLOYMENT.md`
