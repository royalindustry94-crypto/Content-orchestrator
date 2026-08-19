# Open-Finding Closure Report

**Branch:** `audit/closure-evidence-0035`
**Base main:** `48ed04ad0d66881591554c39831397191ee5c2a4`
**Technical candidate audited:** `c91d9d3a3530b944801c50ad8f2be77879101e49`
**Pull request:** [#44](https://github.com/royalindustry94-crypto/Content-orchestrator/pull/44) (not merged)

**Evidence rule applied throughout:** a finding is only reported as closed when the
defect was first reproduced or the control was first exercised on this branch, and
the resulting test now fails if the fix is reverted. Nothing in this report is
promoted from documentation, and no gate was weakened to obtain a green result.

## 1. Release-integrity CI evidence (RI-01)

The previous audit could not read complete check conclusions from public pages.
Authenticated retrieval resolved this for both the original candidate and the
audit branch.

| Subject | CI run | Conclusion | Jobs |
|---|---|---|---|
| Candidate `c91d9d3…` | [run 31251558524][1] | success | web, docker-build, worker, api, security — all success |
| Audit branch `5039fe0…` | [run 32159036719][2] | success | docker-build, worker, web, security, api — all success |

The `security` job's steps were individually confirmed as successful, including
**Gitleaks** and `pip-audit` for both the API and worker packages. RI-01 is
therefore closed for these two SHAs; any *new* candidate SHA requires its own run.

## 2. Reproduced defects and their fixes

Four material defects were reproduced on real infrastructure. Each fix is
accompanied by a regression test that fails without it.

### D-1 — NO_WORKER dispatch permanently leaked workspace budget (H-2 / H-3 class)

`dispatcher.dispatch_stage` reserved spend before creating the stage assignment,
including when `select_worker` returned `None`. Because the scheduler retires a
job once a PENDING assignment exists, the bounded NO_WORKER ceiling path that
releases reservations became unreachable, and nothing else released the hold:
`submit_result` only runs after a worker submits, and the lease reaper only
handles leased assignments. A RESERVED row therefore persisted for work that had
no worker and no lease, and because reserved amounts count towards both the daily
and monthly caps, a workspace with no eligible worker lost budget indefinitely.

The fix reserves spend only when a worker is actually selected, and moves the
reservation for pre-existing PENDING assignments into `claiming.claim_assignment`,
where ownership actually transfers. An over-cap claim is refused fail-closed as an
audited `CAPACITY` non-grant and the assignment stays PENDING rather than being
granted without budget.

### D-2 — `/metrics` was fail-open outside production (M-G)

Scrape authorisation required a token only when `ENVIRONMENT` was
`production`/`prod`. Any staging, preview, demo, beta or misspelled environment
served queue depth, dead-letter counts, dispatch failure rates and worker
telemetry without authentication. The environment check is now a closed
allow-list (`local`, `test`, `ci`); every other value requires the token.

### D-3 — local authentication had no brute-force control (M-F)

`/auth/login` allowed unlimited attempts, enforced only an eight-character
password floor, and returned faster for unknown emails than for known ones, which
is a usable account-enumeration oracle. Migration **0036** adds durable
`failed_attempts`, `last_failed_at` and `locked_until` state; the login path locks
the credential row, counts failures in a fifteen-minute window, locks the account
for fifteen minutes after ten failures, clears state on success, and verifies a
dummy hash for unknown emails so the timing signal is removed. The password floor
was raised to twelve characters in the service, the request schema and the web
signup form.

### D-4 — soft delete was impossible under row-level security

This defect was discovered while implementing the governance deletion control and
is the reason data-deletion capability could not previously exist. On the RLS-bound
runtime role with a genuine workspace-admin identity:

| Statement | Result |
|---|---|
| `UPDATE content_items SET updated_by = updated_by` | 1 row updated |
| `UPDATE content_items SET deleted_at = now()` | `new row violates row-level security policy` |

The tables carrying `deleted_at` are `FORCE ROW LEVEL SECURITY`, and their SELECT
policy contained `deleted_at IS NULL`. PostgreSQL validates the row produced by an
UPDATE against the applicable policies, so the instant a row is tombstoned it
becomes invisible and the write is refused. Recreating only the SELECT policy
without that predicate, inside a rolled-back transaction, made the identical
UPDATE succeed — which isolates the predicate, not the role check, as the cause.

> The practical consequence was that the `deleted_at` column the schema is built
> around could never be written by the application role, so no archive, withdraw
> or delete behaviour was implementable.

Migration **0038** keeps the read audience for live rows unchanged, additionally
allows admins and editors of the owning workspace to see withdrawn rows they are
already entitled to write, and states an explicit `WITH CHECK` on the UPDATE
policies. Reviewers and every other tenant still cannot see withdrawn content.
RLS remains enabled and forced, no grant was widened, and no earlier migration was
edited, renamed or renumbered.

## 3. Controls implemented in this sprint

### Publication eligibility (PP-01)

Migration **0037** adds a workspace-scoped `publication_eligibility` table with
RLS, FORCE RLS, admin/reviewer-only attestation writes, and an admin-only delete
policy. `app/services/publication_policy.assert_publishable` is the single gate
and refuses publication unless the platform is supported, an eligibility record
exists for the exact content item and platform, the record references an
**approved** review gate, synthetic media is disclosed, rights are confirmed by a
named actor with a timestamp, an originality fingerprint is present, and no other
item in the workspace already carries that fingerprint for the same platform. The
duplicate rule exists because the platform policies cited in the control matrix
treat mass-produced repetitive output as ineligible.

### Workspace data export and deletion (DG-01)

`app/services/data_governance` implements an admin-only, workspace-scoped export
and deletion request, exposed at `/workspaces/{id}/data/export` and
`/workspaces/{id}/data/deletion-requests`, both audited. Credential and
service-only tables are on a hard denylist and are never exported; the bundle
names its own omissions so a partial export cannot be mistaken for a complete
one. Deletion withdraws customer content and preserves financial, review,
security and audit records, reporting each class explicitly. A deletion request
must restate the target workspace, so a mis-routed request changes nothing.

Table classification is asserted by test: any future workspace-scoped table that
is not deliberately placed on the export, deletable, retained-history, retained
or denied list fails the suite.

## 4. Verification performed on this branch

| Gate | Result |
|---|---|
| API migrations: `downgrade base` → `upgrade head` | Completed; `alembic check` reports no new upgrade operations |
| API lint (`ruff check .`) | All checks passed |
| API tests with CI coverage gate (`pytest --cov=app --cov-fail-under=75`) | **262 passed**, coverage **77.92%** |
| Worker lint and tests | All checks passed; **4 passed** |
| Web lint, production build, tests, `npm audit --audit-level=high` | Passed; **23 passed**; 0 vulnerabilities |
| `pip-audit` (API and worker requirement sets) | No known vulnerabilities found |
| Tracked-file credential literal scan | No hardcoded credential literals in non-test application or script code |

New test files added on this branch: `test_open_finding_closure.py`,
`test_billing_webhook_ordering.py`, `test_security_controls_closure.py`,
`test_publication_policy_closure.py`, `test_data_governance_closure.py`.

## 5. Findings that remain open

These require authority, credentials or evidence that does not exist inside the
repository. They are unchanged by this sprint and are not closable by engineering
work alone.

| Finding | Why it remains open | Required evidence |
|---|---|---|
| DR-01 — managed backup/PITR and hosted restore | No managed provider or production credentials are available in this environment | Authorised PITR drill recording backup identifier, RPO, RTO, post-restore integrity and owner sign-off |
| M-A / H-5 — live billing operation | Stripe live and test-mode credentials are not available; billing remains disabled | Authorised test-mode and production reconciliation drill with webhook evidence |
| M-B — local-auth production override | Fail-closed default is verified, but the override is an operational risk | Deployment policy that prohibits or alerts on the override |
| M-G (hosted portion) — metrics token in deployments | Code is now fail-closed for every non-local environment; hosted configuration was not observable | Verified 401 without a token on each deployed environment |
| CV-01 — commercial validation | No customer, cohort, payment or usage evidence exists | Controlled design-partner cohort with acceptance, repeat-use and willingness-to-pay data |
| UE-01 — unit economics | No provider invoices or realised usage exist | A reconciled provider bill against the internal spend ledger |

## 6. Recommendation

The repository-fixable portion of the audit backlog is closed with reproduction and
regression evidence, and the branch passes every gate the project enforces.
Merging remains a human decision and is not implied by this report: the branch
carries a database migration set and a row-level-security policy change, so it
warrants review by the database and security owners before any merge, and the
deployment-, billing- and commercially-blocked findings above must be closed by
their named owners before a production launch claim.

## References

[1]: https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/31251558524
[2]: https://github.com/royalindustry94-crypto/Content-orchestrator/actions/runs/32159036719
