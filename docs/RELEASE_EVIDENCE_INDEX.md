# Release Evidence Index

**Candidate SHA:** `c91d9d3a3530b944801c50ad8f2be77879101e49`
**Audit branch base:** `c91d9d3a3530b944801c50ad8f2be77879101e49`
**Local validation host:** isolated PostgreSQL 16.14 and Python 3.12.3 environment
**Evidence date:** 2026-08-18 GMT+8

> **Status vocabulary:** **VERIFIED** means directly executed against the named candidate before audit-branch documentation/remediation commits. **REPORTED** means an external page or historic document asserts a result but it was not independently reproduced. **BLOCKED** means a required hosted resource, credential, or authority was unavailable.

| ID | Requirement / check | Exact candidate / command | Result | Evidence state | Limit |
|---|---|---|---|---|---|
| E-01 | Candidate ancestry | `git fetch refs/pull/*/head`; `git merge-base --is-ancestor` for #36→#37→#38→#39→#40→#41→#43 | Linear cumulative ancestry; candidate `c91d9d3…` | VERIFIED | Does not authorize a merge. |
| E-02 | Fresh migration | `alembic upgrade head` on empty PostgreSQL 16 DB | Head `0035` | VERIFIED | Local isolated database only. |
| E-03 | Migration replay | `alembic downgrade base` then `alembic upgrade head` | Replayed to `0035` | VERIFIED | Local isolated database only. |
| E-04 | Schema drift | `alembic check` after fresh upgrade and replay | `No new upgrade operations detected` twice | VERIFIED | Does not prove hosted schema state. |
| E-05 | API code quality | `ruff check .` in `apps/api` | Passed | VERIFIED | Exact candidate before audit changes. |
| E-06 | API suite / coverage | `pytest --cov=app --cov-fail-under=75` in `apps/api` | 203 passed; 77.41% coverage | VERIFIED | Tests do not constitute hosted production proof. |
| E-07 | Worker suite | `ruff check . && pytest` in `apps/worker` | 4 passed | VERIFIED | Local only. |
| E-08 | Web quality gates | `npm run lint && npm run build && npm test && npm audit --audit-level=high` | lint/build passed; 23 tests passed; 0 high+ audit findings | VERIFIED | Local only. |
| E-09 | HRG / tenant smoke | `API_BASE=http://127.0.0.1:8000 node scripts/verify_hrg_isolation.mjs` | 13/13 passed: creation, decision, double-decision rejection, cross-tenant denials, health truthfulness | VERIFIED | Disposable local tenants only. |
| E-10 | Browser navigation / mobile smoke | `DEMO_EMAIL=<ephemeral> DEMO_PASSWORD=<ephemeral> node scripts/ui_smoke_cdp.mjs` | 16 surfaces; 0 blank/crash, console problems, uncaught exceptions, unlabeled controls, mobile failures, footer mismatches | VERIFIED | Local Vite/API stack; preexisting script default credential was not used. |
| E-11 | RLS catalog | `pg_class`, `pg_policies`, and grants queried after candidate migration | 40 public tables have RLS and FORCE RLS; `leads`, `worker_logs`, `review_gates`, `spend_reservations`, and `workspace_billing` all enabled/forced | VERIFIED | Catalog inspection uses audit superuser; access attacks are E-06/E-09. |
| E-12 | Direct RLS adversarial coverage | `test_rls_blocks_cross_workspace_*` included in E-06 | Cross-workspace workspace, membership, lead, and worker-log access blocked through `app_runtime` sessions | VERIFIED | Test identities are disposable local database identities. |
| E-13 | Python dependency audit | `pip-audit` against compiled API and worker requirements | 0 known vulnerabilities for both graphs | VERIFIED | Point-in-time public advisory database; no full history secret scan locally. |
| E-14 | npm dependency audit | `npm audit --audit-level=high` | 0 vulnerabilities | VERIFIED | Point-in-time npm advisory data. |
| E-15 | Candidate logical restore | `pg_dump -Fc` then `pg_restore --exit-on-error` into a separate DB | 0.154 s dump; 0.383 s restore; head `0035`; 40/40 RLS/FORCE RLS; row counts preserved | VERIFIED | Local logical restore, not a managed-provider PITR restore. |
| E-16 | GitHub checks on target | Public commit checks page | Five named checks shown; complete job outcomes and immutable run URL unavailable without sign-in | PARTIALLY VERIFIED | Do not call full CI green from this evidence. |
| E-17 | Docker images | Candidate GitHub documents report CI Docker success | Reported only | REPORTED | Docker runtime unavailable locally; public full job log inaccessible. |
| E-18 | Gitleaks / full-history secrets scan | Candidate docs and public PR assert pass | Reported only | REPORTED | Local `gitleaks` executable unavailable; historic default preview credential was found separately and removed on this audit branch. |
| E-19 | Managed PITR / hosted restore | No provider access or credentials in session | Not executed | BLOCKED — EVIDENCE UNAVAILABLE | Production RPO/RTO cannot be claimed. |
| E-20 | Live Stripe | No live Stripe secrets or authorized live environment | Not executed; candidate default is billing disabled | BLOCKED — EVIDENCE UNAVAILABLE | Do not activate billing. |
| E-21 | Commercial validation | No customer interviews, usage telemetry, or payment evidence supplied | Not executed | BLOCKED — EVIDENCE UNAVAILABLE | No product-market-fit claim is justified. |

## Evidence artifacts

Audit-run logs and temporary backup artifacts are retained only in the isolated local audit workspace and are intentionally not committed. The repository records the reproducible commands, target SHA, results, and limitations above; it does not commit customer, token, or database data.

## Sprint 2 evidence (open-finding closure, audit branch)

**Audit branch:** `audit/closure-evidence-0035`
**Evidence date:** 2026-08-19 GMT+8

These entries supersede E-16, E-17 and E-18, which were limited by unauthenticated
access to GitHub. Authenticated retrieval resolved all three.

| ID | Requirement / check | Exact command or subject | Result | Evidence state | Limit |
|---|---|---|---|---|---|
| E-22 | Candidate CI, complete conclusions | `gh api` run/job lookup for `c91d9d3…` | [Run 31251558524][2] conclusion **success**; jobs web, docker-build, worker, api, security all success | VERIFIED | SHA-specific; does not transfer to any other commit. |
| E-23 | Audit-branch CI, complete conclusions | `gh api` run/job lookup for `5039fe0…` | [Run 32159036719][3] conclusion **success**; all five jobs success | VERIFIED | Covers the commit pushed before this sprint's further changes. |
| E-24 | Secret scan and dependency audit in CI | `security` job step conclusions | Gitleaks **success**; pip-audit (API) **success**; pip-audit (worker) **success** | VERIFIED | Supersedes E-18's REPORTED state. |
| E-25 | Docker image build | `docker-build` job conclusion | success on both runs | VERIFIED | Supersedes E-17's REPORTED state. |
| E-26 | NO_WORKER budget-leak reproduction | Direct orchestration tests before the fix | Reproduced: reservation held with no worker and no lease while the job was retired | VERIFIED | Local isolated database. |
| E-27 | Metrics fail-open reproduction | Environment-matrix authorisation tests | Reproduced: staging/preview/demo/beta/unknown served telemetry with no token | VERIFIED | Code-level; hosted configuration remains unverified. |
| E-28 | Local-auth brute-force reproduction | Repeated-login and timing tests | Reproduced: unlimited attempts and an unknown-versus-known timing difference | VERIFIED | Local isolated database. |
| E-29 | Soft-delete RLS reproduction | Runtime-role tombstone probe vs. control update | `deleted_at` write refused; ordinary column write accepted; removing only the SELECT predicate made the identical write succeed | VERIFIED | Root cause isolated by rolled-back experiment. |
| E-30 | Post-fix API gate | `alembic downgrade base && alembic upgrade head && ruff check . && pytest --cov=app --cov-fail-under=75` | Migration cycle clean; lint clean; **262 passed**; coverage **77.92%** | VERIFIED | Local isolated database. |
| E-31 | Post-fix worker and web gates | `ruff check . && pytest`; `npm run lint && npm run build && npx vitest run && npm audit --audit-level=high` | 4 passed; build succeeded; 23 passed; 0 vulnerabilities | VERIFIED | Local only. |
| E-32 | Post-fix dependency audit | `pip-audit` on compiled API and worker requirements | No known vulnerabilities for both graphs | VERIFIED | Point-in-time advisory data. |
| E-33 | Publication eligibility control | `tests/test_publication_policy_closure.py` | 15 passed, including fail-closed per missing attestation, duplicate-fingerprint refusal, and RLS attestation authority | VERIFIED | No publishing executor exists yet to gate. |
| E-34 | Data export and deletion control | `tests/test_data_governance_closure.py` | 10 passed, including cross-tenant refusal, credential exclusion, confirmation mismatch, retention of financial records, and the soft-delete visibility contract | VERIFIED | Retention automation and legal notification remain out of scope. |
| E-35 | Repository-fix audit commit hosted CI | [Run 32273905572][4] for `efdeb1d6d9b7ed9a988923cb0ae22e1108e9673a` | **api, web, worker, security and docker-build all success** | VERIFIED | This is the full hosted CI result for the repository-fix commit. A subsequent documentation-only commit requires its own CI result. |

## References

[1]: https://github.com/royalindustry94-crypto/Content-orchestrator/commit/c91d9d3a3530b944801c50ad8f2be77879101e49/checks
[2]: https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/31251558524
[3]: https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/32159036719
[4]: https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/32273905572
