# Launch Blockers

**Repository:** Content Orchestrator  
**Updated:** 2026-08-29  
**Audited baseline:** `main` @ `abb20981f68cb0de8e3ed75af9759e0b5b6fb656`  
**Source of truth:** exact-head CI, retained browser evidence, repository/runtime probes — not prior chat claims

## Rule

Nothing is considered deployable or releasable from documentation alone. The current exact candidate must satisfy `docs/MILESTONE_AUDIT_STANDARD.md` and receive PASS before merge/release. If an independent auditor is temporarily unavailable, technical work may continue but the milestone cannot self-certify PASS.

---

## Current verdict

| Target | Status | Reason |
|---|---|---|
| Product code baseline | **PRIVATE-BETA CAPABLE** | Business Manager + audited Research → Strategy → Content → Production → Compliance preview is merged and fail-closed |
| Development governance | **PASS / ENFORCED** | Active `Protect main` ruleset requires PRs and the six strict CI checks; force-push/deletion blocked; no bypass actors |
| Operational private beta | **CONDITIONAL / REMEDIATION IN PROGRESS** | Isolated managed Supabase test project exists, but schema has not been applied pending issue #60 remediation and exact-head revalidation |
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
- Alembic: current audited head **`0050`**
- Migration lifecycle: upgrade → full downgrade to base → re-upgrade **PASS**
- Worker: **PASS**
- Web lint/build/tests/high-severity dependency audit: **PASS**
- Security: Gitleaks + API/worker dependency audits **PASS**
- Docker builds: **PASS**
- Exact-head browser smoke: desktop + exact 390px mobile **PASS**, retained as CI artifact
- Post-merge CI on audited `main`: all six jobs **PASS**

---

## Open blockers / conditions

### GOV-001 — Protect `main` — **CLOSED / VERIFIED**

GitHub issue **#50** is closed. Live ruleset evidence is recorded in `docs/audit/RULESET_EVIDENCE_2026-08-28.md`.

Verified enforcement:

- Pull requests required.
- Strict required checks: `api`, `worker`, `web`, `security`, `docker-build`, `browser-smoke`.
- Force pushes and deletion blocked.
- No bypass actors; current user cannot bypass.

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

Previously closed P0/P1 engineering controls remain closed unless new evidence demonstrates regression. Their historical records remain in release/audit documents; this file reflects the current `0050` codebase and the verified repository-protection state.

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
