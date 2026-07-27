# Cursor Setup — Final Audit (CEO Foundation Refactor)

**Date:** 2026-07-27  
**Branch:** `cursor/cursor-foundation-refactor-b52d`  
**Directive:** CEO — Cursor Foundation Refactor (Phases 1–4)  
**Constraint:** No production application logic changes except cosmetic `ruff format` and test/tooling/CI/docs/Cursor config.

---

## Executive summary

The Cursor engineering environment was rebuilt on `main` as a **lean foundation**:

1. **`AGENTS.md`** is the repository entry point for AI agents.  
2. **Monolithic / overlapping role skills were not carried forward**; prior skill sprawl (CEO, Architect, Backend, PG, FE, DevOps, Docs, Release, Domain, Hub, Directors, etc. on feature branches) is **retired** in favor of modular rules + four focused reviewer agents.  
3. **Modular `.cursor/rules/*.mdc`** replace large always-on monoliths.  
4. **CI** gained migration replay, coverage gate, format check, placeholder scan, secret scan, CodeQL; MyPy is present but **non-blocking** until typing debt is cleared without logic rewrites.  
5. **Executable invariants** added (DB + static).  

**Final status: NOT VERIFIED** — local Postgres daemon unavailable in this environment; full pytest/coverage/migration-replay and GitHub Actions green on the PR SHA were not proven in-agent. Structure and static checks are in place.

---

## Phase 1 — Cursor Foundation

### Created

| Artifact | Why |
|----------|-----|
| `AGENTS.md` | Single entry point; architecture, non-negotiables, reviewer agents, CI map |
| `.cursor/rules/architecture.mdc` | Always-on stack freeze / no drift |
| `.cursor/rules/quality-bar.mdc` | No TODO/placeholder/silent failure |
| `.cursor/rules/review-gate-spend.mdc` | Non-bypassable Review Gate + spend |
| `.cursor/rules/verification-release.mdc` | Evidence, merge policy, escalation |
| `.cursor/rules/tenancy-rls.mdc` | Scoped to `apps/api` — workspace_id + FORCE RLS |
| `.cursor/rules/migrations.mdc` | Scoped to Alembic — reversible migrations |
| `.cursor/rules/python-api.mdc` | Scoped API conventions |
| `.cursor/rules/python-worker.mdc` | Scoped worker conventions |
| `.cursor/rules/frontend-web.mdc` | Scoped web conventions |
| `.cursor/agents/planner.md` | Focused reviewer — plan only |
| `.cursor/agents/migration-reviewer.md` | Focused reviewer — schema/RLS |
| `.cursor/agents/security-reviewer.md` | Focused reviewer — security (readonly) |
| `.cursor/agents/test-writer.md` | Focused reviewer — tests |
| `.cursor/README.md` | Index of rules + agents; documents skill retirement |

### Skills retained

**None** as installable `.cursor/skills/*/SKILL.md` packages on this foundation branch.

### Skills removed / not ported

All prior overlapping role skills from stacked feature branches were **not merged** into this foundation (by design of audit recommendation: reduce overlap/self-approval risk):

- `ceo`, `chief-architect`, `backend-engineer`, `postgresql-expert`
- `frontend-engineer`, `devops-engineer`, `documentation-writer`
- `security-auditor`, `qa-breaker`, `release-manager`
- `content-orchestrator-expert`, `executive-operations-hub-architect`
- Subagents `engineering-director`, `operations-director`
- Monolithic rules `ceo-master-rule.mdc`, `content-orchestrator-engineering-standard.mdc`

**Why:** Independent audit found high-severity authority overlap and self-VERIFIED risk. CEO directive asked to retain **only** Planner / Migration Reviewer / Security Reviewer / Test Writer.

### Reviewer agents created

Planner · Migration Reviewer · Security Reviewer · Test Writer

---

## Phase 2 — CI Enforcement

| Check | Status | Notes |
|-------|--------|-------|
| Ruff lint | **Verified existing** + kept | `ruff check` api + worker |
| Ruff formatting | **Added** | `ruff format --check app tests` (api); worker format applied |
| MyPy | **Added (non-blocking)** | `continue-on-error: true` — 42 errors in existing app; fixing would be production typing churn |
| Pytest | **Verified existing** | Strengthened with `-W error` |
| Coverage threshold | **Added** | `--cov-fail-under=70` + pyproject coverage config |
| PostgreSQL integration tests | **Verified existing** | api job Postgres 16 service |
| Alembic upgrade | **Verified existing** | |
| Alembic downgrade | **Added** | `alembic downgrade base` |
| Alembic replay | **Added** | upgrade after downgrade; script `scripts/alembic_replay.sh` |
| RLS invariant tests | **Verified existing** + **extended** | schema + isolation + new engineering invariants |
| Placeholder detection | **Added** | `scripts/check_placeholders.sh` |
| Secret scanning | **Added** | Gitleaks job |
| CodeQL | **Added** | python + javascript |
| ESLint | **Verified existing** | web job |
| TypeScript typecheck | **Verified existing** | `tsc -b` via `npm run build` |
| Production frontend build | **Verified existing** | Vite build |

---

## Phase 3 — Executable Invariants

| Invariant | Mechanism |
|-----------|-----------|
| Tenant tables have `workspace_id` | `test_engineering_invariants.py` |
| ENABLE + FORCE RLS | same + existing `test_schema_migrations.py` |
| Cross-workspace isolation | existing `test_cross_workspace_isolation.py` |
| Immutable audit/event tables | trigger checks in engineering + schema tests |
| Optimistic concurrency (`version`) | engineering invariants |
| Soft-delete (`deleted_at`) | engineering invariants |
| Reversible migrations | static AST check + CI downgrade/replay |
| Idempotency key enforcement | unique index presence check |
| FK index validation | catalog query in engineering invariants |
| No TODO/FIXME in production | `check_placeholders.sh` in CI |
| No bare `except:` | `test_static_engineering_checks.py` |
| WorkspaceScopedMixin nullable=False | static check |

---

## Phase 4 — Resume readiness

| Gate | Result |
|------|--------|
| Reports written | This file + AGENTS.md |
| CI green on SHA | **Not proven in-agent** (no Docker Postgres; Actions not yet run) |
| Reviewer agents present | Yes |
| Rules modular/scoped | Yes |
| AGENTS.md reflects architecture | Yes |
| Product features started | **No** (per directive) |

---

## Files created / modified (summary)

**Created:** `AGENTS.md`, `.cursor/rules/*`, `.cursor/agents/*`, `.cursor/README.md`, `scripts/check_placeholders.sh`, `scripts/alembic_replay.sh`, `apps/api/tests/test_engineering_invariants.py`, `apps/api/tests/test_static_engineering_checks.py`, `docs/CURSOR_SETUP_FINAL_AUDIT.md`

**Modified:** `.github/workflows/ci.yml`, `apps/api/pyproject.toml` (mypy/coverage), cosmetic `ruff format` on api app/tests + worker (no logic changes)

---

## Risks found

1. **MyPy debt (42 errors)** — blocking MyPy would require app typing fixes (production-adjacent). Mitigated with non-blocking CI step.  
2. **Migration downgrade base** — not executed here; may fail if any revision downgrade is incomplete. Static check requires non-empty `downgrade()`.  
3. **Gitleaks/CodeQL** — first-run permissions/license quirks possible on GH.  
4. **Coverage 70%** — may fail if suite coverage dipped; not measured locally without Postgres.  
5. **Skill retirement** — operators must use AGENTS.md + reviewer agents; old `/skill` names from unmerged branches will not exist on this foundation until intentionally reintroduced.

## Risks resolved

1. Overlapping monolithic Cursor skills/rules sprawl → lean modular foundation.  
2. Missing AGENTS.md entry point.  
3. CI gaps (replay, coverage gate, format, secrets, CodeQL, placeholder scan).  
4. Invariant suite gaps for FK indexes / soft-delete / version / static downgrade / bare except.

## Remaining recommendations

1. Clear MyPy errors and flip MyPy to blocking.  
2. Prove `alembic downgrade base` + replay on CI; fix any incomplete downgrades.  
3. Confirm coverage ≥70% on Actions.  
4. Optionally reintroduce **thin** skills later only with a fresh authority audit (do not restore sprawl).  
5. Add soft-delete behavior runtime tests (filter `deleted_at IS NULL`) beyond column presence.

---

## Final status

**NOT VERIFIED**

Reason: engineering foundation artifacts are landed, but objective CI-green evidence on the pushed SHA and live Postgres migration/invariant execution were not available in this agent environment.
