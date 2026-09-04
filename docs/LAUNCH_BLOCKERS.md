# Launch Blockers

**Product:** The Business Manager

**Repository:** Content Orchestrator

**Updated:** 2026-09-04

**Audited baseline:** `main` at `abb20981f68cb0de8e3ed75af9759e0b5b6fb656` after PR #51

**Unmerged candidates:** PR #71 at `dcb4b6e7746e330265e362dc8b59f7ae288932c1`
(migration head `0052`) and PR #72 at
`f151d7edb0e8b1df7e7fe2a21d9a526e1f765a6e`

**Source of truth:** exact-head CI, retained browser evidence, repository/runtime probes — not prior chat claims

## Rule

Nothing is considered deployable or releasable from documentation alone. The current exact candidate must satisfy `docs/MILESTONE_AUDIT_STANDARD.md` and receive PASS before merge/release. If an independent auditor is temporarily unavailable, technical work may continue but the milestone cannot self-certify PASS.

---

## Current verdict

| Target | Status | Reason |
|---|---|---|
| Product code baseline | **PRIVATE-BETA CAPABLE** | Business Manager + audited Research → Strategy → Content → Production → Compliance preview is merged and fail-closed |
| Development governance | **PASS** | Active repository ruleset `Protect main` requires a PR, one approval, resolved conversations and all six strict CI checks; issue #50 is closed |
| Operational private beta | **CONDITIONAL / NOT YET RUNTIME-VERIFIED** | PR #71/#72 integration and managed deployment/Supabase runtime evidence are not yet independently verified |
| Production | **BLOCKED** | Live providers, production auth/runtime evidence, managed PITR, billing go-live, policy/rights adapters and external publishing remain separate gates |

---

## Merged audited baseline

PR #48 merged the bounded Founder Preview pipeline with these workspace-scoped stages:

1. Business Manager UI
2. Scout + Research Auditor
3. Strategist + Strategy Auditor
4. Content Department
5. Producer + Media QA
6. Compliance + Chief Auditor

Safety boundaries remain explicit:

- Human Review Gate remains mandatory.
- External publishing remains disabled in the preview path.
- Unconfigured provider paths are truthful and spend zero provider cost.
- Workspace/RLS negative tests cover the new domain slices.
- No autonomous publishing or live-provider execution was enabled by the preview milestone.

### Verified engineering evidence

- API: **299 passed**, **81.09% coverage** (75% gate)
- Alembic: merged audited `main` head **`0050`**; unmerged PR #71 candidate head **`0052`**
- Migration lifecycle: upgrade → full downgrade to base → re-upgrade **PASS**
- Worker: **PASS**
- Web lint/build/tests/high-severity dependency audit: **PASS**
- Security: Gitleaks + API/worker dependency audits **PASS**
- Docker builds: **PASS**
- Exact-head browser smoke: desktop + exact 390px mobile **PASS**, retained as CI artifact
- Post-merge CI on audited `main`: all six jobs **PASS**

---

## Open blockers / conditions

### GOV-001 — Protect `main` — **CLOSED**

Tracked and closed by GitHub issue **#50**.

Live GitHub evidence captured on 2026-09-03:

- `main` reports `protected: true` at `abb20981f68cb0de8e3ed75af9759e0b5b6fb656`.
- Repository ruleset `Protect main` (`21731627`) is active for `~DEFAULT_BRANCH`.
- Pull requests require one approval, dismissal of stale approvals, last-push approval and resolved review conversations.
- Strict required checks are `api`, `worker`, `web`, `security`, `docker-build` and `browser-smoke`.
- Branch deletion and non-fast-forward updates are blocked.
- The ruleset has no bypass actors and reports `current_user_can_bypass: never`.

This closes the repository-enforcement gap. It does not replace exact-head audit evidence or authorize a merge when a required check is absent or failing.

### RUNTIME-001 — Managed Supabase/runtime verification — **OPEN / REMEDIATION IN PROGRESS**

An isolated managed Supabase test project now exists and is healthy. No Content Orchestrator application schema has been applied yet.

Independent audit issue **#60** identified blocking managed-runtime bootstrap risks. Work package `WP-RT-001` is correcting them before schema application:

- local-only `auth.users` shim removed from canonical managed migration path,
- local static `app_runtime` credential removed from canonical managed migration path,
- managed auth interaction reduced to the explicit application-owned profile signup trigger,
- local/CI parity moved to `scripts/bootstrap_local_postgres.sql`,
- managed pre-apply runbook added.

The managed schema remains blocked until the remediation candidate has exact-head CI evidence and independent re-audit can be completed.

### PROVIDER-001 — Live provider activation — **OPEN / DEFERRED**

Before enabling OpenAI/Anthropic/Gemini/ElevenLabs/Creatomate/n8n or equivalent live effects, require a separate audited milestone covering credentials, provider abstraction, retries/backoff/timeouts, idempotency, spend reserve/commit accounting, redaction/logging, supervised provider tests and failure behavior. Issue #58 remains a blocker for live cost-bearing traffic.

### BILLING-001 — Billing go-live — **OPEN / DEFERRED**

Billing code exists but production billing remains a separate live-secret/reconciliation gate. Do not infer paid-production readiness from the in-repo Stripe implementation.

### PUBLISH-001 — External publishing — **BLOCKED BY DESIGN**

No autonomous/external publishing milestone is authorized. Any future enablement requires current platform policy/rights evidence, exact-artifact compliance, immutable Human Review approval, rollback/kill-switch evidence and Founder authorization.

---

## Historical P0/P1 baseline

Previously closed P0/P1 engineering controls remain closed unless new evidence demonstrates regression. Their historical records remain in release/audit documents. This file distinguishes the merged `0050` baseline from the unmerged `0052` remediation candidate and does not self-certify the candidate.

---

## Related

- `docs/MILESTONE_AUDIT_STANDARD.md`
- `docs/EXECUTIVE_STATUS_REPORT.md`
- `docs/TECHNICAL_DEBT_REGISTER.md`
- `docs/FINAL_RELEASE_AUDIT.md`
- `docs/DISASTER_RECOVERY_REPORT.md`
- `docs/BETA_RELEASE_CHECKLIST.md`
- `docs/runtime/MANAGED_SUPABASE_TEST_RUNBOOK.md`
- `docs/audit/RULESET_EVIDENCE_2026-08-28.md`
- GitHub issue #60 — major managed-runtime audit
- GitHub issue #50 — protect `main` (**closed**)
