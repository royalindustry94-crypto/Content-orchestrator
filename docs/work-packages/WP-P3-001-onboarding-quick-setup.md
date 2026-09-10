# P3-001 — Onboarding: guided Quick Setup + manual Business Profile

## Objective

Close the onboarding gap identified in the 2026-09-09 recovery audit and
confirmed by competitive research: a new workspace previously had nothing
to configure beyond its name and spend caps. Every worker tile on Home
read "NOT CONFIGURED" with no path forward, and Strategy/Content Department
permanently reported `business_context_state: "incomplete"` — not because
a user hadn't finished setup, but because no workspace-level settings
existed to complete it at all. 74% of users say they'll switch to a
competitor over confusing onboarding (see competitive research, this
session); this repo's own PR #71 attempted the same fix in 2026-09 but
never got the independent re-audit required to merge, and was closed as
stale in this session's PR cleanup.

## Scope

In scope — both paths write the same underlying data, so a user who starts
guided and finishes manually (or vice versa) sees one consistent state:

- **Guided path**: a 4-step modal wizard (Business → Audience → Brand
  Voice → Content Plan) surfaced as a banner on Home for any workspace
  without a complete profile.
- **Manual/custom path**: the same fields as one flat form in Settings,
  editable any time, not gated behind the wizard.
- Backend: `workspace_content_profiles` (migration 0055), RLS-scoped
  exactly like `content_pillars` (editor/admin write, admin/editor/reviewer
  read — matches `require_workspace_content_author`), GET/PUT under
  `/workspaces/{id}/content-profile`.

Deliberately out of scope, not silently dropped:

- **Wiring the profile into content-job generation defaults.** PR #71 did
  this (a "first brief" step 5 that created a real Content Job falling
  back to profile fields). Left out here to keep this change reviewable
  and low-risk — it touches `content_desk.create_content_job()`/Draft
  Desk generation logic, a different risk surface. Natural next
  increment; the profile is already there for it to read.
- **Live AI provider activation** — unrelated to this change. TD-041
  stays open, gated on a Founder decision (provider/key/spend-cap).
  Nothing in this wizard claims or implies a provider is connected.
- **The hardcoded "Not configured" AI Workforce summary cards on Home**
  (`department_card__state` in `LumoraDashboard.tsx`) — found during the
  same investigation, always renders "Not configured" regardless of real
  state. A real truthfulness bug, but a separate, smaller fix; noted here
  rather than bundled in.

## Design

Backend mirrors `content_pillars` (migration 0003) exactly: same RLS role
shape, same mixins (`WorkspaceScopedMixin`, `TimestampMixin`, `ActorMixin`,
`VersionMixin`), same FK-covering-index convention (P1-006). All six
profile fields are optional — a step skipped in the wizard, or a field
cleared in Settings, is a real state the schema itself represents, not a
validation failure. `ContentProfileOut.is_complete` (computed field) is
what the frontend uses to decide whether to keep prompting; it's not a
backend-enforced gate on anything.

Frontend: `ContentSetupWizard.tsx` (new file) holds both the modal wizard
and `BusinessProfileSettings` (the manual form) — co-located since they're
the same concern in two shapes, not duplicated into the already-large
`LumoraDashboard.tsx`. Home fetches the profile once and shows a banner
only when incomplete; Settings fetches its own copy independently (simpler
than lifting shared state across the existing per-view data-fetch
machinery, and the profile is cheap to re-fetch).

## Tests

- `apps/api/tests/test_content_profile.py` (8 tests): null-until-saved,
  save/read round-trip with whitespace stripping, partial profile
  `is_complete: false`, full-replace-not-merge semantics, role gating
  (reviewer read-only, editor can write, non-member 403s both ways),
  cross-workspace isolation.
- `apps/web/src/navigation.smoke.test.tsx` (5 new tests): banner shown for
  no/partial profile, hidden once complete, full 4-step walk verifies the
  exact save payload, "Skip for now" closes without saving.
- Full clean-install suites: API 357 passed (was 349) / 81.00% coverage,
  migration round-trip clean through head `0055`; web 36 passed (was 31),
  lint/build clean.
- Live end-to-end verification (Playwright against the real running app,
  real Postgres, not mocked): signup → banner appears → wizard completes
  → banner disappears → **reload → still gone (real DB persistence)** →
  Settings shows the same saved data. Screenshots retained.
- Two pre-existing tests caught by this change during full-suite
  validation, both fixed here (not worked around): `test_data_governance_
  closure.py::test_every_workspace_scoped_table_is_classified` (new table
  classified `EXPORTABLE_TABLES` + `RETAINED_ON_DELETE`, matching
  `spend_caps`' treatment) and `test_fk_indexes_p1.py::test_no_unindexed_
  foreign_key_columns` (added the `created_by`/`updated_by` covering
  indexes directly in migration 0055, rather than a follow-up migration).

## Rollback

`alembic downgrade 0054` drops `workspace_content_profiles` outright — no
other table references it, nothing else changed.

## Status — COMPLETE (2026-09-09)
