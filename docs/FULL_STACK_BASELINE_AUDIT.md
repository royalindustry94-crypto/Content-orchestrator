# Full-Stack Baseline Release Audit

**Audit date:** 2026-08-08  
**Release candidate:** cumulative PR stack #36, #37, #38, #39, #40, #41, #43  
**Base:** `main`  
**Functional candidate:** `cursor/p0-reliability-sprint-b52d`  
**Migration head:** `0035`  
**Decision threshold:** Critical 0, High 0, CI green, migration replay/security/HRG/isolation pass

## Executive decision

**Critical findings: 0 open**  
**High findings: 0 open**  
**Release blockers: 0 open**

The cumulative stack is approved for protected, bottom-up PR merging once the
latest candidate SHA has completed all five CI jobs. This document does not
authorize direct pushes, force pushes, branch-protection bypasses, or feature
development.

## Audited PR chain

| Order | PR | Branch | Base | Scope |
|---:|---:|---|---|---|
| 1 | #36 | `cursor/operations-dashboard-v1-b52d` | `main` | Operations Dashboard V1 |
| 2 | #37 | `cursor/operations-dashboard-v2-b52d` | PR #36 branch | Founder Control Center V2 |
| 3 | #38 | `feature/operations-dashboard-v3` | PR #37 branch | Mission Control V3 |
| 4 | #39 | `cursor/mission-control-v4-b52d` | PR #38 branch | Integrated Mission Control V4 |
| 5 | #40 | `cursor/ops-preview-seed-b52d` | PR #39 branch | Preview seed/launcher |
| 6 | #41 | `cursor/lumora-ui-v1-b52d` | PR #40 branch | Lumora UI baseline |
| 7 | #43 | `cursor/p0-reliability-sprint-b52d` | PR #41 branch | Reliability, final UI gate, full-stack hardening |

PR #42 is intentionally excluded because it is a sibling documentation PR and
was not included in the CEO-approved stack.

## Findings and remediation

### Critical

**Open: 0**

No critical defect was identified by the cumulative audit.

### High

**Open: 0**

One High was found and closed:

#### H-1 — Tenant admin could control global workers — fixed

The initial cumulative tree included `worker_registry.workspace_id IS NULL`
workers in workspace quick actions. A workspace admin could therefore drain,
resume, or emergency-stop shared platform workers and reap assignments outside
their tenant.

Remediation:

- `_workspace_workers()` now selects only workers explicitly pinned to the path
  workspace.
- A regression test creates both a workspace worker and global worker, calls
  pause and emergency-stop, and proves the global worker remains online and
  undrained.
- A fresh independent security re-review confirmed the finding is closed.

### Medium

**Open release blockers: 0**

The RLS defense-in-depth gap for new tenant tables was closed:

- Leads CRUD now uses `get_current_session`.
- Global search and live-log reads now use `get_current_session`.
- Lead services flush/refresh without clearing transaction-local JWT claims.
- Direct RLS tests prove a second tenant cannot read `leads` or `worker_logs`
  even when bypassing FastAPI authorization guards.
- Schema tests include both new tables in FORCE RLS assertions.

Non-blocking architecture note: some operations projections still use the owner
session because they aggregate service-only tables or perform worker
infrastructure mutations. Every such route remains admin-gated and explicitly
workspace-filtered. Production must use `APP_DATABASE_URL=app_runtime` and
`AUTH_MODE=supabase`; preview settings are not a production security baseline.

## Migration audit

### Authorized migrations

- `0034_operations_leads`
- `0035_worker_logs_v4`

### Replay procedure

A newly created, empty PostgreSQL 16.14 database was used:

1. `alembic upgrade head`
2. verify `0035 (head)`
3. `alembic check`
4. `alembic downgrade base`
5. verify no active revision
6. `alembic upgrade head`
7. verify `0035 (head)`
8. `alembic check`

**Result: PASS**

`alembic check` initially exposed historical metadata drift for raw-SQL,
migration-managed indexes plus three ORM type mismatches. Remediation:

- The exact migration-managed index allowlist is documented in `alembic/env.py`;
  only reflected indexes explicitly authored by historical migrations are
  excluded from autogenerate removal.
- ORM metadata now matches PostgreSQL `text` billing columns and the
  `smallint` workspace priority tier.

Final result: **No new upgrade operations detected.**

### Database guarantees

| Table | RLS | FORCE RLS | Policies | Required indexes |
|---|---|---|---|---|
| `leads` | enabled | enabled | SELECT members; INSERT/UPDATE admin+editor; DELETE admin | present |
| `worker_logs` | enabled | enabled | SELECT admin; no runtime write grant | present |

## Backend/API audit

Verified:

- All operations routes require workspace admin.
- Leads list/create/update are workspace-scoped and RLS-enforced.
- Worker-log ingest derives workspace from worker credentials and validates
  optional assignment/pipeline ownership before insert.
- Worker-log reads are admin-only and RLS-enforced.
- Search is bounded and uses SQLAlchemy-bound expressions.
- Human Review Gate decisions remain in the existing reviewer-authorized path.
- Quick actions cannot approve/bypass review gates.
- Retry/DLQ paths are workspace-filtered.
- GitHub integration uses a fixed API origin and server configuration.
- Health indicators are calculated from backend state.
- Alert metric/list parity is checked against the same backend response.

## Spend-control audit

Verified through the full API suite:

- Reservation/cap enforcement remains fail-closed.
- Daily/monthly/provider controls retain precision and concurrency guarantees.
- Operations endpoints are read-only for spend and do not mutate caps.
- Retry actions re-enter normal scheduling/reservation paths.

## Authentication and authorization audit

Verified:

- Local auth is limited to explicit local/test configuration.
- Production requirement remains `AUTH_MODE=supabase`.
- Workspace admin guards reject outsiders.
- Unauthenticated operations reads are rejected.
- User-facing RLS sessions set transaction-local `request.jwt.claim.sub`.
- Owner sessions remain limited to service-only paths and explicitly scoped
  operations.

## Human Review Gate smoke

The committed `scripts/verify_hrg_isolation.mjs` creates disposable tenants and
touches no seeded/customer data.

Result: **13/13 PASS**, including:

- disposable tenant/workspace creation;
- content job creates one awaiting gate;
- approval persists and sets `decided_at`;
- queue count decrements;
- double-decision returns HTTP 409;
- cross-tenant gate access denied.

## Workspace isolation smoke

Result: **PASS**

- Cross-tenant dashboard read: HTTP 403
- Cross-tenant review-gate read: HTTP 403
- Cross-tenant health read: HTTP 403
- Unauthenticated operations read: HTTP 401
- Foreign workspace visibility: 0
- Direct RLS leads read: 0 foreign rows
- Direct RLS worker-log read: 0 foreign rows

## Frontend and navigation audit

Result: **PASS**

- Vitest: 23/23
- ESLint: pass
- TypeScript `tsc -b`: pass
- Vite production build: pass
- npm audit high+: 0 vulnerabilities
- Navigation: 16/16 surfaces
- Blank screens: 0
- Uncaught exceptions: 0
- Console errors/warnings: 0
- Unlabeled live controls: 0
- Supplemental 390px mobile routes: 3/3, no page overflow
- Search live query: results rendered
- Footer/backend health mismatches: 0
- Alert type metric/list/backend parity: pass

## Test matrix

| Gate | Result |
|---|---|
| API Ruff | PASS |
| API pytest + 75% coverage gate | 201 passed; 77.31% |
| Worker Ruff | PASS |
| Worker pytest | 4 passed |
| Frontend Vitest | 23 passed |
| Frontend ESLint | PASS |
| TypeScript | PASS |
| Vite build | PASS |
| Alembic fresh upgrade | PASS |
| Alembic downgrade base | PASS |
| Alembic re-upgrade | PASS |
| Alembic check (twice) | PASS |
| Isolated Python dependency audit | 0 known vulnerabilities |
| npm audit high+ | 0 vulnerabilities |
| Gitleaks | PASS; one exact historical non-secret smoke value narrowly allowlisted |
| Docker builds | PASS in CI; local nested Docker overlayfs unavailable |
| Navigation smoke | 16/16 PASS |
| HRG/isolation/health smoke | 13/13 PASS |

## Docker note

The cloud VM's nested Docker daemon cannot mount overlayfs, so a local image
build cannot execute beyond base-layer mounting. This is an environment
limitation, not a Dockerfile failure. The dedicated CI Docker job builds API,
worker, and web images on a standard GitHub runner and is the authoritative
gate.

## Security conclusion

A clean isolated virtual environment reported **0 known dependency
vulnerabilities**. Gitleaks scans the cumulative PR history with default rules.
The one reported historical value was a generated test credential literal, not
a secret, and was removed; `.gitleaks.toml` suppresses only that exact historic
string so future findings remain fail-closed.

Fresh independent security re-review:

- Critical: 0
- High: 0
- Medium security blockers: 0
- Prior cross-tenant global-worker finding: closed

## Final release gate

The cumulative release candidate is approved only when all five CI jobs on the
final documentation SHA are green:

1. API
2. Worker
3. Web
4. Security
5. Docker build

No direct push, force push, or branch-protection bypass is permitted.

