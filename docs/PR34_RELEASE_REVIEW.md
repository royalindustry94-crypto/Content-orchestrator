# PR #34 — Pre-Merge Release Review (Independent)

**Reviewer stance:** external principal engineer with authority to reject.
**Scope:** full diff `main..cursor/p2-beta-launch-b52d` (117 files, +7,141/−553), head `4d6277e`.
**Method:** three independent adversarial review passes (auth/RLS, money paths,
orchestration runtime) plus direct verification on real PostgreSQL. Every
finding below was confirmed against source, not taken on faith. No code was
modified during this review.

## Independently verified — passing

| Gate | Result |
|---|---|
| Alembic replay | Fresh DB: 34 up → 34 down → 34 up, clean; single head `0032_merge_p1` (parallel 0031 heads merged correctly) |
| RLS / FORCE RLS | Every workspace-owned table has ENABLE + FORCE RLS (0 exceptions); write policies are role-scoped member policies, no permissive fallback |
| Test suite | 181 passed on real PostgreSQL with warnings-as-errors |
| CI | Green at head (api, worker, web, docker-build, fail-closed security audits) |
| Human Review Gate | No bypass path found: transitions require reviewer/admin decision; workers/outbox/scheduler cannot advance a gated run |
| Audit logging | No secrets/credentials in audit lines in reviewed paths |
| Migration downgrades | Present and exercised for all new migrations |

## Findings

### Critical
None.

### High

**H-1 — Unsafe authentication default (`AUTH_MODE=local`)**
- **Evidence:** `apps/api/app/core/config.py:47` — `auth_mode: str = Field(default="local")`. `/auth/signup` and `/auth/login` (`apps/api/app/api/routes/auth.py`) mint valid bearer JWTs whenever local mode is active; the only guard is `auth_mode != "local"` → 404.
- **Risk:** If `AUTH_MODE` is omitted or mis-set in any deployment, the API silently defaults to open local account issuance, bypassing Supabase identity governance. Fail-open on an authentication control.
- **Fix:** Default to `supabase`; fail startup fast when `environment=production` and `AUTH_MODE=local` without an explicit audited override. Add a startup test.

**H-2 — Entitlement granted on checkout completion without payment verification**
- **Evidence:** `apps/api/app/services/billing.py:257–269` — `checkout.session.completed` sets `plan="pro"`, `status="active"` unconditionally; `payment_status` and actual subscription status are never checked.
- **Risk:** A workspace gains paid access before payment succeeds (async payment methods, failed first invoice). Money-path access-control violation.
- **Fix:** Drive entitlement from `customer.subscription.*` events with `status ∈ {active, trialing}` (or fetch the subscription and derive status); treat checkout completion as linkage only.

**H-3 — Spend cap bypass at commit time via worker-reported cost**
- **Evidence:** `apps/api/app/orchestration/dispatcher.py:417–420` accepts `result["estimated_cost_usd"]` from the worker's stage result; `controller.commit_spend` (`controller.py:778–796`) commits it with **no** cap or reconciliation check against the reservation.
- **Risk:** A buggy or compromised worker records arbitrarily large spend after a tiny reservation — daily/monthly caps hold only at reserve time. Breaks the fail-closed spend story.
- **Fix:** Enforce `actual ≤ reserved` (or re-check caps under `FOR UPDATE` at commit); on overage, flag and hold rather than silently commit.

**H-4 — Duplicate spend reservations break worker submit under retry/recovery**
- **Evidence:** `dispatcher.py:199–213` reserves spend on every dispatch attempt; recovery requeues (`recovery.py:215–221`) create additional `RESERVED` rows for the same `(pipeline_run_id, stage)`; submit assumes at most one via `scalar_one_or_none()` (`dispatcher.py:405–413`) → `MultipleResultsFound` → 500 on the worker submit path.
- **Risk:** Any recovered/retried stage can strand assignments in-flight, causing repeated lease churn and DLQ noise; spend accounting also double-reserves.
- **Fix:** Scope reservations to `assignment_id`/`attempt_number` with a uniqueness constraint; release the prior reservation on requeue; make submit deterministic on impossible states.

### Medium

**M-1 — Spend-hold misclassified as "no worker" → wrongful dead-lettering**
- **Evidence:** cap-exceeded pause returns `None` from `controller.reserve_spend` (`controller.py:718–745`); `dispatch_stage` and the scheduler (`scheduler.py:139–166`) treat all `None` outcomes as capacity outage, burn retry attempts, and eventually cancel + DLQ with "no eligible worker available".
- **Risk:** Budget-held runs are cancelled/DLQ'd instead of held; misleading operator signal.
- **Fix:** Typed dispatch outcomes (`NO_WORKER` / `SPEND_HOLD` / `BACKPRESSURE`); spend-hold must not consume retries or route to DLQ.

**M-2 — Stripe webhook idempotency is check-then-insert (race-prone)**
- **Evidence:** `billing.py:240–247` existence check, then insert at `:324–333` on unique `stripe_event_id`; concurrent replays can both pass the read; the resulting `IntegrityError` is not handled in `webhooks.py:42–52` → 500 → Stripe retries.
- **Risk:** Unstable webhook processing under Stripe's at-least-once delivery. (Single-delivery replays ARE handled; only the concurrent window is exposed.)
- **Fix:** Insert-first with `ON CONFLICT DO NOTHING` and branch on rowcount, or catch the unique violation as duplicate-success.

**M-3 — `/metrics` endpoint is unauthenticated**
- **Evidence:** `apps/api/app/api/routes/metrics.py:86–91` — no auth dependency.
- **Risk:** Queue depth, failure rates, and lease contention are attacker reconnaissance; low direct impact but unnecessary exposure.
- **Fix:** Require machine/scraper token or restrict to internal network in deployment config.

### Low

**L-1 — Worker-supplied `estimated_cost_usd` is unvalidated input** (subsumed by H-3 but independently: no bound/type sanity check on a money field crossing a trust boundary).
**L-2 — `GET /auth/mode` publicly discloses the auth mode** — minor recon aid; harmless once H-1 is fixed.

## API / frontend compatibility
No breaking changes found to pre-existing endpoints; new routes are additive. Web app calls match API schemas at head; web build and tests pass in CI.

## Documentation
Work packages, ops runbooks (backup/restore, on-call, deployment), and launch-blocker docs are present and consistent with the code reviewed.

---

## Verdict

# HIGHS FIXED — READY FOR RE-REVIEW

H-1…H-4 and M-2 are addressed on `cursor/p2-fix-pr34-highs-b52d` (migration `0033`). Re-review should cover the delta only.

| Finding | Status | Fix |
|---|---|---|
| H-1 AUTH_MODE default | **Fixed** | Default `supabase`; production forbids `local` unless `ALLOW_LOCAL_AUTH_IN_PRODUCTION=true` |
| H-2 checkout entitlement | **Fixed** | `checkout.session.completed` links customer/subscription IDs only; entitlement from `customer.subscription.*` with `active`/`trialing` |
| H-3 spend commit overage | **Fixed** | `commit_spend` clamps `actual ≤ reserved` + structured log; dispatcher validates Decimal |
| H-4 duplicate reservations | **Fixed** | Release prior open `(run, stage)` before re-reserve; submit picks latest; partial unique index `ux_spend_reservations_open_run_stage` |
| M-1 spend-hold → DLQ | **Fixed** | `DispatchOutcome.SPEND_HOLD`; scheduler parks job without attempt++/DLQ |
| M-2 webhook race | **Fixed** | `IntegrityError` on event insert → duplicate via savepoint |
| M-3 unauthenticated `/metrics` | **Fixed** | `METRICS_SCRAPER_TOKEN` Bearer auth; required in production |

**Regression tests:** `apps/api/tests/test_pr34_high_fixes.py` (+ updated billing/orchestration assertions).

---

## Original verdict (historical)

# MERGE BLOCKED

Four High-severity issues (H-1 fail-open auth default, H-2 unpaid entitlement, H-3 spend-cap commit bypass, H-4 retry-path 500s) individually justify rejection; three sit directly on the money/identity paths the beta sells as its core guarantees. All are small, well-localized fixes — none require redesign.

**Confidence: 90%** — every High finding was confirmed line-by-line in source; residual uncertainty covers unreviewed breadth (≈117 files) and runtime behaviors only observable under production Stripe traffic.

**Recommended path to merge:** fix H-1…H-4 (+ M-1/M-2 while in those files), add the regression tests named above, re-run the full gate set, then re-review the deltas only.
