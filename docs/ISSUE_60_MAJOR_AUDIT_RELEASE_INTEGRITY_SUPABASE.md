# Issue #60 Major Independent Audit — release integrity + Supabase test-runtime readiness

Date: 2026-08-28  
Audited baseline: `main` @ `abb20981f68cb0de8e3ed75af9759e0b5b6fb656`  
Temporary Supabase bootstrap branch: `ops/supabase-test-schema-export` @ `09037d0af47dbe6a11452301e70d969885976a56`

## Scope evidence snapshot

- Baseline SHA match verified locally:
  - `origin/main` = `abb20981f68cb0de8e3ed75af9759e0b5b6fb656`
  - `origin/ops/supabase-test-schema-export` = `09037d0af47dbe6a11452301e70d969885976a56`
- CI run on audited baseline `main` (`33156887452`) shows all six expected jobs successful:
  - `api`, `worker`, `web`, `security`, `docker-build`, `browser-smoke`
- Branch listing currently reports `main` as protected (`protected: true`).

---

## Findings

### CRITICAL

1. **Managed-Supabase bootstrap SQL still mutates Supabase-managed `auth` objects.**  
   - Evidence:
     - `database/supabase_test_bootstrap/part_01.sql:10` — `CREATE SCHEMA IF NOT EXISTS auth;`
     - `database/supabase_test_bootstrap/part_01.sql:12` — `CREATE TABLE IF NOT EXISTS auth.users (...)`
     - `database/supabase_test_bootstrap/part_01.sql:128` — `DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;`
     - `database/supabase_test_bootstrap/part_01.sql:130-132` — creates trigger on `auth.users`
     - Source migration path: `apps/api/alembic/versions/0001_identity_and_access.py:31-44, 211-218`
   - Impact:
     - Applying this script to managed Supabase risks unintended interaction with Supabase-managed auth schema/trigger behavior.
     - Violates the issue requirement to avoid damage to Supabase-managed `auth` objects.
   - Blocking status: **Blocks schema application to managed Supabase until remediated.**

### HIGH

1. **`0001` still contains historical weak runtime credential pattern in migration source.**  
   - Evidence:
     - `apps/api/alembic/versions/0001_identity_and_access.py:58` — `CREATE ROLE app_runtime LOGIN PASSWORD 'app_runtime' ...`
   - Impact:
     - Even though exported bootstrap SQL sanitized this to `NOLOGIN`, the canonical migration source still embeds a static password pattern that must never be used as a managed-runtime credential.
     - Creates operator confusion and unsafe copy/paste risk.
   - Blocking status: **Must be resolved or strictly fenced before managed runtime schema rollout.**

2. **Governance state is internally contradictory and can mislead release decisions.**
   - Evidence:
     - `docs/LAUNCH_BLOCKERS.md:19, 60-73` still says branch protection is conditional/open.
     - `docs/EXECUTIVE_STATUS_REPORT.md:14, 71-74` still says branch protection issue remains open.
     - GitHub issue #50 is closed, and branch listing shows `main` protected.
   - Impact:
     - Decision-makers can act on stale governance status, undermining exact-head release integrity process.
   - Blocking status: **Release-governance blocker until reconciled with current GitHub state and required checks evidence.**

### MEDIUM

1. **Required-checks enforcement evidence is incomplete in this audit artifact.**
   - Evidence:
     - We verified `main` protected=true and observed the six CI jobs passing on baseline run `33156887452`.
     - Current accessible evidence here does not include a direct branch-protection payload proving all six contexts are configured as required checks.
   - Impact:
     - Control likely exists, but this report lacks direct, immutable required-checks configuration capture.
   - Blocking status: **Must be closed before declaring PASS for release-integrity audit.**

2. **Temporary branch CI run for this PR candidate is `action_required` with zero jobs (`33184376066`).**
   - Evidence:
     - Workflow run status: `completed`, conclusion `action_required`; workflow jobs list empty.
   - Impact:
     - Exact-head validation is not currently producing full CI evidence for this candidate head.
   - Blocking status: **Blocks PASS for exact-head release evidence on this audit branch.**

### LOW

1. **Supabase bootstrap process lacks an explicit “managed-safe apply list” doc in-tree.**
   - Evidence:
     - Bootstrap SQL exists in `database/supabase_test_bootstrap/part_01.sql` … `part_08.sql` and manifest file.
     - No companion doc in `docs/` describing which statements must be excluded for managed Supabase.
   - Impact:
     - Higher operator error probability during manual SQL application.
   - Blocking status: Non-blocking by itself, but contributes to higher execution risk.

### INFO

1. **Alembic chain is currently linearized to a single head at `0050`.**
   - Evidence:
     - `apps/api/alembic/versions/0032_merge_p1_heads.py` merges parallel `0031*` heads.
     - Revision graph parse indicates single head `0050`.

2. **Workspace isolation and safety controls have strong code/test anchoring in baseline.**
   - Evidence examples:
     - FORCE RLS check: `apps/api/tests/test_schema_migrations.py:53-64`
     - Runtime role cannot read local auth credentials: `apps/api/tests/test_security_controls_closure.py:257-272`
     - Human Review fail-closed publication checks: `apps/api/tests/test_publication_policy_closure.py:177+`
     - Spend fail-closed 402 behavior: `apps/api/app/api/routes/content_jobs.py:57-67`

---

## Explicit assessment of temporary Supabase SQL/bootstrap approach

**Assessment: CONDITIONAL-UNSAFE AS WRITTEN FOR MANAGED SUPABASE.**

- Positive:
  - The generated bootstrap SQL removed the plain `PASSWORD 'app_runtime'` from the exported branch SQL (`part_01.sql:20` now `NOLOGIN`).
  - Migration semantics through `0050` are represented in generated SQL chunks.
- Unsafe/insufficient for managed Supabase:
  - It still includes `auth` schema/table/trigger mutations (`part_01.sql` lines cited above).
  - It still includes role DDL (`CREATE ROLE app_runtime ...`) that may be incompatible with managed-role governance and should not be used as a credential bootstrap shortcut.

**Conclusion:** do not apply the current chunk set to managed Supabase unchanged.

---

## Changes that must occur **before** schema application

1. Remove/skip `auth` object creation and trigger DDL from the managed-Supabase apply path:
   - `CREATE SCHEMA IF NOT EXISTS auth`
   - `CREATE TABLE IF NOT EXISTS auth.users ...`
   - `DROP/CREATE TRIGGER ... ON auth.users`
2. Remove static-password role pattern from canonical migration guidance/source for managed runtime use; ensure no managed credential ever uses historical `app_runtime` password.
3. Define and document managed-safe role provisioning steps (least privilege, no hardcoded password, no broad admin PAT workaround).
4. Capture immutable branch-protection evidence proving required checks include: `api`, `worker`, `web`, `security`, `docker-build`, `browser-smoke`.
5. Reconcile stale governance docs (`docs/LAUNCH_BLOCKERS.md`, `docs/EXECUTIVE_STATUS_REPORT.md`) to current verified state.
6. Regenerate/re-review Supabase bootstrap SQL after the managed-safe exclusions and re-audit before any application.

---

## Runtime/private-beta readiness assessment

- **Code capability:** Strong for fail-closed preview posture (Human Review required, RLS enforced, spend controls present, providers can remain `not_configured`).
- **Operational/runtime readiness:** **Not yet proven** for managed Supabase test-runtime due to unresolved bootstrap safety and incomplete exact-head evidence.
- **Provider/publishing posture:** Keep providers `NOT CONFIGURED`, external publishing disabled, and cost-bearing traffic disabled pending explicit Founder-approved activation milestone.

---

## Final milestone verdict

# **FAIL**

Rationale: blocking safety/governance findings remain (managed Supabase bootstrap touches `auth` objects, static runtime credential pattern remains in canonical migration source, and exact required-checks enforcement evidence is incomplete in this audit artifact).

---

## Smallest safe next actions (priority order)

1. **Create managed-safe bootstrap variant** that excludes all `auth.*` DDL/trigger operations and unsafe role credential patterns.
2. **Publish explicit pre-apply runbook** for managed Supabase test project (role provisioning, apply order, verification queries, rollback note).
3. **Capture and attach exact branch-protection required-check evidence** for `main` with the six required contexts.
4. **Reconcile governance documents** to remove stale branch-protection contradiction.
5. Re-run exact-head CI/browser evidence and re-issue independent PASS/CONDITIONAL/FAIL gate on the updated audit head.
