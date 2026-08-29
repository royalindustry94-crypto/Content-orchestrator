# WP-PB-005 — Pipeline provider abstraction + simulation provider

## Objective

Make the Scout → Strategist → Content → Producer → Compliance pipeline
executable and testable end to end before any paid vendor is activated, and
put the provider abstraction non-negotiable behind a real seam instead of an
absence.

## Problem

Every pipeline stage hard-coded its own "no provider" behaviour inline. Two
consequences:

1. **Untestable gates.** The Content Department's four mandatory auditors, the
   Producer handoff gate, Media QA, the Chief Auditor, and the Human Review
   Package existed only as test-only fixture helpers or as unreachable code.
   No operator or reviewer could exercise them, so their correctness rested on
   fixtures rather than on the paths that actually run.
2. **No abstraction to swap.** Non-negotiable #4 says no vendor may be
   hard-coded into the core path. That held only because no vendor existed at
   all. Adding the first one would have meant editing all five services.

## Plan

1. Add `app/providers` as the single seam: typed per-stage request/result
   dataclasses and an async `PipelineProvider` protocol.
2. Ship two implementations: `NullPipelineProvider` (default, preserves the
   existing fail-closed behaviour exactly) and `SimulationPipelineProvider`
   (deterministic, offline, zero-cost).
3. Select via `PIPELINE_PROVIDER_MODE`, defaulting to `null`; refuse
   `simulation` when `ENVIRONMENT` is production.
4. Route all five stages through the provider, sharing one persistence routine
   between the provider path and the test fixture path.
5. Implement the missing independent auditors as real deterministic checks over
   stored state: content language/fact/brand/originality, Media QA, and the
   Chief Auditor gate reconciliation.
6. Terminate the chain at a real Human Review Gate.
7. Surface the active provider in the API and mark simulated output in the UI.

## Non-goals

- Activating any live vendor. That remains PROVIDER-001, a separate audited
  milestone covering credentials, retries, idempotency, spend reserve/commit
  accounting, redaction, and supervised failure tests.
- Enabling external publishing. `publication_eligibility` still returns
  `external_publishing_disabled` unconditionally.
- Establishing platform policy freshness. Compliance summary still reports
  `policy_state: freshness_unverified`; a configured content provider does not
  establish policy currency.
- Any schema change. `status` and `provider_state` are unconstrained `Text`, so
  no migration was required and the Alembic head stays at `0050`.

## Safety analysis

| Non-negotiable | Effect |
|---|---|
| Human Review Gate | **Strengthened.** A Chief Auditor pass now opens a real gate; previously the chain had no terminus. `content_desk.open_review_gate` is the single implementation every path uses. |
| Workspace isolation | **Unchanged.** No new tables, no RLS policy changes. The one new orchestration write path (chief-audit raising a gate) uses the owner session behind an admin guard, matching the existing content-jobs route, because orchestration tables are owner-write-only by design. |
| Spend controls | **Unchanged.** Simulated usage is zero-cost and is still reserved and committed through the controller. Each stage refuses a provider that reports cost above the run's persisted ceiling. |
| Provider abstraction | **Established.** This is the seam that was previously missing. |
| Audit logging | **Unchanged.** All new stage outcomes emit outbox events. |
| No placeholders | **Upheld.** Simulation is opt-in, never a fallback: a configured provider that fails records an explicit failure rather than degrading to the not-configured path. |

### Why simulation is not a "silent fallback"

- Default is `null`; a deployment that sets nothing behaves bit-identically to
  before.
- It is refused in production with no break-glass override, unlike
  `AUTH_MODE=local`.
- Every stored record carries `provider_state = "simulation"`.
- Sources cite the RFC 2606 reserved `.invalid` TLD and can never resolve.
- Generated copy is prefixed `SIMULATED`.
- The web app banners every screen while it is active.
- `real_provider_mode` stays `false` in the production and compliance
  summaries.

### The auditors are real, not simulated

The four content auditors, Media QA, and the Chief Auditor read persisted state
only. They never consult the provider that produced the work, and they run
identically whichever provider that was. The fact auditor verifies *evidence
traceability*, not truth: it blocks quantitative and comparative claims rather
than assuming them correct, because establishing those needs an external
verification provider that is not configured.

## Deliverables

| Deliverable | Location |
|---|---|
| Provider seam | `apps/api/app/providers/{base,null,simulation,registry}.py` |
| Config + production guard | `apps/api/app/core/config.py` |
| Stage wiring | `app/services/{research,strategy,content_department,production,compliance}.py` |
| Content auditors | `content_department.run_content_audits` + `POST .../packages/{id}/audits` |
| Media QA | `production.run_media_qa` + `POST .../artifacts/{id}/media-qa` |
| Chief Auditor | `compliance.run_chief_audit` + `POST .../artifacts/{id}/chief-audit` |
| Shared review gate | `content_desk.open_review_gate` |
| Provider status API | `GET /pipeline/provider` |
| UI labelling | `apps/web/src/LumoraDashboard.tsx`, `app.css` |
| Bootstrap | `scripts/dev_up.sh` |
| Guide | `docs/TESTING_GUIDE.md` |

## Defects found and fixed

- `GET /production/runs/{id}` raised on every real job: the production output
  schemas lacked `from_attributes`, so the route's explicit `model_validate`
  against ORM rows always failed. Only the 401/403 path had been tested.

## Rollback

Set `PIPELINE_PROVIDER_MODE=null` (or unset it) to restore the previous
behaviour without a deploy of code. To revert entirely, drop the
`app/providers` package and the stage wiring; no migration is involved and the
Alembic head is unchanged.

## Evidence

| Check | Result |
|---|---|
| API tests | 323 passed, 79.64% coverage (75% gate) |
| Worker tests | 4 passed |
| Web tests / build / lint | 28 passed, build clean, eslint clean |
| Ruff | clean |
| Alembic head | `0050`, unchanged; upgrade → base → re-upgrade verified |
| Live end-to-end | Full chain driven over HTTP against a running stack, terminating at an awaiting Human Review Gate; publication still `false` / `external_publishing_disabled` after approval |

## Status — COMPLETE (2026-08-29)

Independent audit still required before merge per `docs/MILESTONE_AUDIT_STANDARD.md`.
