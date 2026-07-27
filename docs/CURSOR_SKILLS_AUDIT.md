# Cursor Skills Audit — Content Orchestrator

**Date:** 2026-07-27  
**Branch:** `cursor/skills-audit-b52d`  
**Skills audited:** CEO · Chief Architect · Backend Engineer · PostgreSQL Expert  
**Auditor:** Cursor Cloud Agent (audit pass; no new skills created)

## Method

1. Consolidated all four skill packages onto one branch.
2. Inspected each `SKILL.md`, key `references/`, `assets/`, `scripts/`, and docs pointers against Cursor skill best practices and the required enforcement checklist.
3. Fixed defects in-place (authority boundaries, escalation, evidence, merge/QA/security).
4. Added `.cursor/skills/AUTHORITY_MATRIX.md` as shared non-skill governance.

---

## Shared findings (all skills)

| Finding | Severity | Fix |
|---|---|---|
| Overlapping authority (CEO “protects architecture”; Architect owns deep schema; Backend lands migrations without PG gate) | High | Authority matrix + per-skill may/must-not + mandatory deferral tables |
| Skills could imply self-VERIFIED / self-COMPLETE | High | Evidence checklists; VERIFIED reserved to CEO with cited facts; others forbidden from empty VERIFIED |
| No explicit ban on merge without QA + security | High | Merge policy on every skill + CEO release discipline |
| GitHub-as-source-of-truth weak or missing | Medium | Stated in matrix + CEO/Architect/Backend/PG skills |
| Duplicate stack language without SQLAlchemy **2.x** on Architect table | Low | Architect stack table now says 2.x |
| Architect use-criteria included schema/RLS depth that belongs to PG Expert | High | Architect defers DDL/RLS/Alembic/EXPLAIN to `/postgresql-expert` |
| Backend workflow implemented schema before PG approval | High | Stop-and-escalate; PG APPROVE required before DDL |
| PG Expert workflow stepped into owning app feature tests/routes | Medium | Hand-off table to Backend; PG owns DB correctness |
| CEO description encouraged doing specialist technical work | High | CEO description + must-not: delegate only |
| Advisory scripts could be mistaken for release approval | Medium | Documented as advisory-only; evidence still required |

---

## Skill: CEO (`ceo`)

### Findings

1. Description too broad (“reviewing architecture trade-offs”, security/RLS) → risk of not delegating.
2. Operating posture “protect architecture” overlapped Chief Architect.
3. VERIFIED gates listed steps but did not hard-require specialist sign-offs or QA/security.
4. Merge rule existed but did not require QA + security approval.
5. GitHub SoT not explicit.
6. Retries/audit called out weakly vs checklist requirement (idempotency present; retries/audit strengthened in invariants table).

### Fixes applied

- Rewrote `SKILL.md`: may/must-not, mandatory delegation table, evidence-backed VERIFIED, merge+QA+security, GitHub SoT.
- Tightened `description` for discovery (delegates specialists).
- Updated `references/release-discipline.md` with specialist owners and evidence.

### Remaining risks

- A user can still `@ceo` and ask it to code; skill now forbids treating that as primary authority but agents may need enforcement via operator habit.
- Lovable Quality Standards remain product guidance (not a separate automated linter).

### Final status

**VERIFIED**

---

## Skill: Chief Architect (`chief-architect`)

### Findings

1. Use criteria listed schema/migration/index/constraint/RLS design as Architect work → incorrect overlap with PostgreSQL Expert.
2. Could be read as replacing Backend implementation.
3. No explicit “APPROVE ≠ VERIFIED / ≠ merge”.
4. SQLAlchemy version not pinned to 2.x in the freeze table.
5. React+TS present (good); GitHub SoT missing.

### Fixes applied

- Rewrote `SKILL.md` with may/must-not, DEFER_TO_PG / DEFER_TO_BACKEND verdicts, SQLAlchemy 2.x, GitHub SoT, merge/VERIFIED bans.
- Narrowed `description` to stack/SoT/boundaries/ADR.
- Annotated `references/data-architecture.md` that deep SQL belongs to PG Expert.
- Updated `references/review-protocol.md` verdict table.

### Remaining risks

- High-level concurrency review still sits on Architect; detailed SKIP LOCKED/EXPLAIN must be insisted upon via PG Expert — process dependency.

### Final status

**VERIFIED**

---

## Skill: Backend Engineer (`backend-engineer`)

### Findings

1. “Models, migrations” in when-to-use without PG approval gate → architecture/schema drift risk.
2. Could self-declare done without CEO evidence pack.
3. No merge/QA/security hard gate in SKILL body (checklist partial).
4. React+TS only implied; now “do not break web contracts”.
5. PR checklist lacked authority gates and evidence pack.

### Fixes applied

- Rewrote `SKILL.md`: stop-and-escalate table, PG/Architect gates, evidence pack, merge ban, no self-VERIFIED.
- Updated `assets/backend-pr-checklist.md` and `references/implementation-standards.md` collaboration section.

### Remaining risks

- Pair-implementing Alembic after PG approval still requires discipline so Backend does not “tweak” RLS solo.

### Final status

**VERIFIED**

---

## Skill: PostgreSQL Expert (`postgresql-expert`)

### Findings

1. Strong ownership of schema/RLS (good) but workflow implied owning SQLAlchemy app tests/routes.
2. Missing explicit merge/QA/security and GitHub SoT in SKILL body.
3. APPROVE could be confused with workstream VERIFIED.
4. Gate script false-positive on `Mapped[float]`+`Numeric` already fixed on skill branch; retained.

### Fixes applied

- Rewrote `SKILL.md`: explicit must/must-not, collaboration hand-off, evidence for migration APPROVE, merge ban, APPROVE ≠ VERIFIED.
- Strengthened `references/validation-and-testing.md` closing notes.

### Remaining risks

- Composite FK adoption is required “where needed”; historical tables may predate composite FKs — PG Expert must not silently rewrite history without migration plan + CEO/Architect as appropriate.

### Final status

**VERIFIED**

---

## Enforcement checklist (post-fix)

| Requirement | CEO | Architect | Backend | PG Expert |
|---|---|---|---|---|
| FastAPI | Yes (invariant) | Yes (freeze) | Yes | Via stack; no replace |
| SQLAlchemy 2.x | Yes | Yes | Yes | Yes (models match DB) |
| Alembic | Yes | Yes | Yes (after PG) | Yes (authority) |
| PostgreSQL | Yes | Yes | Yes | Yes |
| React + TypeScript | Yes | Yes | Contracts intact | N/A (no contradict) |
| Python workers | Yes | Yes | Yes | N/A (no contradict) |
| workspace_id | Yes | Yes | Yes | Yes |
| FORCE RLS | Yes | Yes | Yes | Yes |
| Human Review Gate | Yes | Yes | Yes | Ledger protection |
| spend controls | Yes | Yes | Yes | Money numeric + integrity |
| idempotency | Yes | Yes | Yes | Yes (uniques/TX) |
| retries | Yes | Yes (design) | Yes | SQL race angle |
| audit logging | Yes | Yes (design) | Yes | Immutable ledgers |
| no placeholders | Yes | Yes | Yes | Yes |
| no silent failures | Yes | Yes | Yes | Yes |
| reversible migrations | Yes | Yes | Yes (w/ PG) | Yes |
| real PostgreSQL testing | Yes | Yes | Yes | Yes (reject SQLite/mocks) |
| GitHub SoT | Yes | Yes | Yes | Yes |
| No merge w/o QA+security | Yes | Yes | Yes | Yes |
| Evidence before VERIFIED | Yes (issues label) | Cannot self-VERIFIED | Cannot self-VERIFIED | Cannot self-VERIFIED |

---

## Cursor best-practices compliance

| Practice | Status |
|---|---|
| Folder name = frontmatter `name` | Pass (all four) |
| Strong `description` | Pass (tightened) |
| Progressive disclosure via `references/` | Pass |
| Optional `scripts/` / `assets/` | Pass |
| Project path `.cursor/skills/` | Pass |
| No new skills in this audit | Pass |

---

## Fixes applied (files)

- `.cursor/skills/AUTHORITY_MATRIX.md` (new)
- `.cursor/skills/ceo/SKILL.md`
- `.cursor/skills/ceo/references/release-discipline.md`
- `.cursor/skills/chief-architect/SKILL.md`
- `.cursor/skills/chief-architect/references/data-architecture.md`
- `.cursor/skills/chief-architect/references/review-protocol.md`
- `.cursor/skills/backend-engineer/SKILL.md`
- `.cursor/skills/backend-engineer/assets/backend-pr-checklist.md`
- `.cursor/skills/backend-engineer/references/implementation-standards.md`
- `.cursor/skills/postgresql-expert/SKILL.md`
- `.cursor/skills/postgresql-expert/references/validation-and-testing.md`
- `.cursor/README.md`
- `docs/CURSOR_SKILLS.md` (new index)
- `docs/CURSOR_SKILLS_AUDIT.md` (this file)

## Remaining risks (global)

1. Skills are instructions — they do not mechanically block a mis-invoked agent from coding out of role; operators should invoke the correct `/skill`.
2. Four separate historical skill PRs (#3–#6) may conflict on `.cursor/README.md`; this audit branch is the consolidation source of truth going forward.
3. QA/security “approval” is a process checklist, not a separate automated skill (by design; no new skills in this audit).

## Final status

**VERIFIED**

---

## Addendum — Frontend Engineer (2026-07-27)

Skill **`frontend-engineer`** (`/frontend-engineer`) was added after this audit on branch `cursor/frontend-engineer-skill-b52d`. Authority matrix, CEO/Architect/QA/Security cross-links, and `docs/CURSOR_SKILLS.md` were updated to include it. This addendum does **not** re-open the four-skill audit status above; treat the new skill as separately reviewable.

## Addendum — DevOps Engineer (2026-07-27)

Skill **`devops-engineer`** (`/devops-engineer`) was added on branch `cursor/devops-engineer-skill-b52d`. Covers CI/CD, Actions least privilege, deploy/rollback, secrets/env, migration-safe rollout ops. Wired into authority matrix and CEO release discipline. Separately reviewable; does not re-open the four-skill audit VERIFIED above.

## Addendum — Release Manager (2026-07-27)

Skill **`release-manager`** (`/release-manager`) was added on branch `cursor/release-manager-skill-b52d`. Owns release readiness reports, versioning/changelog/tag plans, and gate evidence assembly. Product go/no-go **VERIFIED** remains `/ceo`. Separately reviewable.

## Addendum — Documentation Writer (2026-07-27)

Skill **`documentation-writer`** (`/documentation-writer`) was added on branch `cursor/documentation-writer-skill-b52d`. Owns accurate docs/ADR drafts/reports with no invented features and no doc↔code drift. ADR acceptance remains `/chief-architect`. Separately reviewable.

## Addendum — Content Orchestrator Expert (2026-07-27)

Skill **`content-orchestrator-expert`** (`/content-orchestrator-expert`) was added on branch `cursor/content-orchestrator-expert-skill-b52d`. Domain guardian for principles, roadmap fit, creep/drift, and product impact assessments. Product go/no-go remains `/ceo`; ADR acceptance remains `/chief-architect`. Separately reviewable.

## Addendum — Executive Operations Hub Architect (2026-07-27)

Skill **`executive-operations-hub-architect`** (`/executive-operations-hub-architect`) was added on branch `cursor/exec-ops-hub-architect-skill-b52d`. Owns Ops Hub architecture (agents, ops approvals, dashboards, GitHub/Cursor/CI integrations). Hub is not content-orchestration SoT. Product stack ADRs remain `/chief-architect`. Separately reviewable.
