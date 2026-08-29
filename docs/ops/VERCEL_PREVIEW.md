# Vercel preview deployment (Founder phone testing)

**Purpose:** one phone-accessible URL for Founder testing of the simulation
pipeline, against the **isolated Supabase test project only**.

**Updated:** 2026-08-29

This is not a production deployment and must never become one. It exists so the
Review Desk and the Scout → Chief Auditor chain can be exercised from a phone
before any paid vendor, billing go-live, or external publishing milestone opens.

---

## 1. What gets deployed

| Piece | Where it runs |
|---|---|
| React/Vite SPA | Vercel static CDN, built from `apps/web` |
| FastAPI API | one Vercel Function, `api/index.py` |
| Database | your existing isolated Supabase **test** project |

Both are served from a single origin. The SPA already calls the API through a
relative `/api` prefix (`apps/web/src/api.ts`), `vercel.json` routes `/api/*` to
the Function, and the Function strips the prefix before FastAPI routes it. No
CORS is involved and no absolute API URL is baked into the build.

`api/index.py` imports the audited `app.main:app` unchanged. It sets
`RUNTIME_PROFILE=serverless` by assignment rather than by default, so a
dashboard misconfiguration cannot make the deployment claim background workers
it does not have.

---

## 2. Prerequisites, done once

### 2.1 Create the `app_runtime` login on the Supabase test project

Migration `0001` creates `app_runtime` as `NOLOGIN NOBYPASSRLS` and deliberately
never puts a password in source control. A managed project therefore needs the
login created out-of-band, once, in the Supabase SQL editor.

```sql
ALTER ROLE app_runtime LOGIN PASSWORD '<generate a strong password>';
```

`NOBYPASSRLS` must stay. That property is what makes FORCE RLS meaningful: the
runtime role cannot see another workspace's rows even if a query forgets to
scope. Do not grant it `BYPASSRLS`, and do not use the project's owner role for
`APP_DATABASE_URL`.

If `ALTER ROLE` reports that the role does not exist, migrations have not run
yet — do step 2.2 first, then come back.

### 2.2 Apply migrations from your machine, not from a request

The Function has no Alembic and never migrates. Run it against the test project
directly:

```bash
cd apps/api
DATABASE_URL='<supabase owner connection string>' alembic upgrade head
DATABASE_URL='<supabase owner connection string>' alembic current   # expect 0051
```

Migration `0001` fails closed if `auth.users` is absent, which is correct: on a
managed Supabase project Supabase owns that table, and the migration must never
manufacture it. Never run `scripts/bootstrap_local_postgres.sql` against a
managed project — it refuses by detecting `supabase_auth_admin`, but do not rely
on that as your only guard.

### 2.3 Know the signup caveat before you test

With `AUTH_MODE=local`, signup inserts directly into `auth.users`. On managed
Supabase that table is owned by `supabase_auth_admin`, so whether the insert is
permitted depends on what your project's connection role is granted. If signup
returns a 500 with a permissions error, that is this — not a code fault. Either
grant the runtime role insert on `auth.users` in the test project, or create the
test user through Supabase Auth and sign in with a Supabase-issued token.

---

## 3. Vercel project settings

Import the repository and select branch `cursor/finish-pipeline-for-testing-33b4`.
`vercel.json` already pins the build, so leave the dashboard build fields empty:

- Framework Preset: **Other** (set by `"framework": null`)
- Install Command: `npm --prefix apps/web ci`
- Build Command: `npm --prefix apps/web run build`
- Output Directory: `apps/web/dist`

---

## 4. Environment variables to enter in Vercel

Set these on the **Preview** environment. Values are yours to paste into the
Vercel dashboard; nothing secret belongs in chat, a commit, or an issue.

### Required

| Name | Value guidance |
|---|---|
| `ENVIRONMENT` | `preview`. **Must not be `production`** — the API refuses to start with a simulated provider in production, by design and with no override. `preview` also disables `/docs`, `/redoc` and `/openapi.json`. |
| `AUTH_MODE` | `local`, so `/auth/signup` and `/auth/login` work for Private Beta. |
| `SUPABASE_JWT_SECRET` | The test project's JWT secret, or any freshly generated random string of at least 32 bytes if you are only using local auth. Never reuse a production secret. |
| `DATABASE_URL` | Test project **owner** connection string. Used by the readiness check and by handlers that write orchestration rows behind an explicit workspace guard. |
| `APP_DATABASE_URL` | Test project connection string for **`app_runtime`**, through the **transaction pooler** (port `6543`). This is the RLS-enforced path every authenticated request uses. |
| `PIPELINE_PROVIDER_MODE` | `simulation`. Deterministic, offline, zero cost, every record labelled `simulation`. |

### Recommended

| Name | Value guidance |
|---|---|
| `METRICS_SCRAPER_TOKEN` | A random string. Without it `/api/metrics` returns 401 on `preview` anyway (only `local`, `test` and `ci` scrape tokenless), so this is only needed if you actually want to scrape. |
| `DEPLOYMENT_GIT_BRANCH`, `DEPLOYMENT_COMMIT_SHA` | Makes the Operations Dashboard show real deployment identity instead of "Unavailable". It never fabricates these. |

### Do not set

| Name | Why |
|---|---|
| `RUNTIME_PROFILE` | Forced to `serverless` by `api/index.py`. Setting it cannot help and must not appear to allow `server`. |
| `BILLING_ENABLED` | Defaults to `false`. Leave it unset; billing go-live is a separate gate (BILLING-001). |
| `ALLOW_LOCAL_AUTH_IN_PRODUCTION` | An audited production override. Irrelevant here and dangerous to normalise. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `CREATOMATE_API_KEY`, `N8N_WEBHOOK_BASE_URL`, `UPLOAD_POST_API_KEY` | Live provider activation is PROVIDER-001, deferred. The simulation provider calls nothing. |
| `STRIPE_*` | BILLING-001, deferred. |
| `CORS_ALLOW_ORIGINS` | Single origin, so CORS is not exercised. |

---

## 5. What does not run on this deployment

A Vercel Function is frozen between requests, so the three in-process
automation loops are not started. `GET /api/health/automation` reports this
explicitly — `status: "disabled"` with a reason and the affected capabilities —
rather than `idle`, which would read as loops that should be ticking.

Unavailable here:

- Draft Desk stage dispatch to background workers
- worker liveness sweep
- assignment lease recovery
- queue-depth back-pressure evaluation
- outbox catch-up delivery

Still fully working, because each completes inside the request that triggers it:

- signup, login, workspace and membership management
- every pipeline stage from Scout through Compliance
- all independent auditors
- opening **and deciding** the Human Review Gate — the decision event is
  dispatched inside the request transaction and the handler fails with 503
  rather than reporting a decision it did not apply
- spend reservation and commit

Vercel Cron is not a substitute: cron jobs run only on **production**
deployments, not previews. If you need the worker path exercised, run the stack
with `RUNTIME_PROFILE=server` (the default) via `scripts/dev_up.sh`.

---

## 6. Verify the deployment

```bash
python scripts/verify_preview.py https://<your-preview-host>
```

This drives the real HTTP routes and asserts readiness, honest automation
reporting, simulation labelling, signup and login, workspace creation, the full
Scout → Chief Auditor chain terminating at a Human Review Gate, publication
still blocked after human approval, cross-workspace isolation, and zero
committed spend. It creates two throwaway accounts, so point it at a test
project only.

Spot checks by hand:

```bash
curl -s https://<host>/api/health/ready
curl -s https://<host>/api/pipeline/provider
curl -s https://<host>/api/health/automation
curl -s -o /dev/null -w '%{http_code}\n' https://<host>/api/metrics      # expect 401
curl -s -o /dev/null -w '%{http_code}\n' https://<host>/api/openapi.json # expect 404
```

---

## 7. Testing gotcha worth knowing

Use topics made of **words, not numbers**. The writer echoes your topic into the
script, and `_extract_claims` classifies any sentence containing a digit as a
`NUMBER` claim, which the fact auditor blocks because no verification provider
can substantiate a quantity. "coffee brewing tips" runs clean; "top 5 coffee
tips" legitimately stops at the fact audit and the Producer gate then refuses
with a 409. That is the control working, not a defect.

---

## 8. Build troubleshooting

**The Function fails on import with a missing dependency.** Vercel's Python
installer prefers a root `pyproject.toml` over `requirements.txt`, and this
repository still carries a Replit-era root `pyproject.toml` that declares no
dependencies. `.vercelignore` excludes it for exactly this reason. If the build
still installs nothing, delete that file and root `main.py` — neither is used by
the API, the web app, or CI.

**Vercel serves the API for every route and the SPA never loads.** A detected
Python framework preset takes precedence over file-based `/api` functions and
becomes a catch-all. Confirm `"framework": null` in `vercel.json` and that the
dashboard preset is **Other**.

**Function bundle too large.** `.vercelignore` and `excludeFiles` in
`vercel.json` already drop docs, reports, tests, the worker and scripts. Python
functions are not tree-shaken, so anything reachable at build time is bundled.

**Requests time out.** `maxDuration` is 60s, the Hobby ceiling. The simulation
provider performs no network I/O, so a stage that takes anywhere near that
indicates a database problem — most likely `APP_DATABASE_URL` not pointing at
the transaction pooler.

---

## 9. Teardown

Delete the Vercel project or unlink the branch. Then, in the test project,
revoke the runtime login you created in 2.1:

```sql
ALTER ROLE app_runtime NOLOGIN;
```

Rotate `SUPABASE_JWT_SECRET` if it was ever shared.

---

## Related

- `docs/TESTING_GUIDE.md` — the pipeline walkthrough to run once you are in
- `docs/ops/DEPLOYMENT.md` — container/compose deployment
- `docs/LAUNCH_BLOCKERS.md` — RUNTIME-001, PROVIDER-001, BILLING-001, PUBLISH-001
- `scripts/serve_preview.py` — same routing shape, runnable locally
- `scripts/verify_preview.py` — the control verification harness
