# Launch Blockers

**Repository:** Content Orchestrator  
**Updated:** 2026-08-28  
**Audited baseline:** `main` after PR #49 governance merge  
**Source of truth:** exact-head CI, retained browser evidence, repository/runtime probes — not prior chat claims

## Rule

Nothing is considered deployable or releasable from documentation alone. The current exact candidate must satisfy `docs/MILESTONE_AUDIT_STANDARD.md` and receive PASS before merge/release.

---

## Current verdict

| Target | Status | Reason |
|---|---|---|
| Product code baseline | **PRIVATE-BETA CAPABLE** | Business Manager + audited Research → Strategy → Content → Production → Compliance preview is merged and fail-closed |
| Development governance | **CONDITIONAL** | Independent audit standard is merged; GitHub `main` branch protection is still disabled (issue #50) |
| Operational private beta | **CONDITIONAL / NOT YET RUNTIME-VERIFIED** | Managed deployment/Supabase runtime evidence and current operator verification are not established in this audit |
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

WP-PB-005 then made that chain executable end to end behind the provider seam, and implemented the independent auditors that previously existed only as test-only helpers: the four Content Department auditors, Media QA, and the Chief Auditor gate reconciliation. A Chief Auditor pass now opens a real Human Review Gate, so the pipeline terminates at a human rather than at a dead end.

Safety boundaries remain explicit:

- Human Review Gate remains mandatory.
- External publishing remains disabled in the preview path.
- Unconfigured provider paths are truthful and spend zero provider cost.
- Workspace/RLS negative tests cover the new domain slices.
- No autonomous publishing or live-provider execution was enabled by the preview milestone.

### Verified engineering evidence

- API: **325 passed**, **79.68% coverage** (75% gate)
- Alembic: current audited head **`0050`**
- Migration lifecycle: upgrade → full downgrade to base → re-upgrade **PASS**
- Worker: **PASS**
- Web lint/build/tests/high-severity dependency audit: **PASS**
- Security: Gitleaks + API/worker dependency audits **PASS**
- Docker builds: **PASS**
- Exact-head browser smoke: desktop + exact 390px mobile **PASS**, retained as CI artifact
- Post-merge CI on PR #48 merge commit: all six jobs **PASS**

---

## Open blockers / conditions

### GOV-001 — Protect `main` — **HIGH / OPEN**

Tracked by GitHub issue **#50**.

Required before scaling development throughput or relying on repository enforcement:

- Require pull requests before merge.
- Require relevant CI gates before merge.
- Block force pushes and branch deletion.
- Keep emergency bypass Founder-controlled and documented.
- Independently verify the active branch protection/ruleset after configuration.

Current evidence: GitHub reports `main` as unprotected with no required status checks enforced.

### RUNTIME-001 — Managed Supabase/runtime verification — **OPEN**

The Supabase connector is installed but has not exposed a project to the current audit session. No managed database, production-auth, backup/PITR, or deployment claim may be marked verified from this state.

### PROVIDER-001 — Live provider activation — **OPEN / DEFERRED**

Before enabling OpenAI/Anthropic/Gemini/ElevenLabs/Creatomate/n8n or equivalent live effects, require a separate audited milestone covering credentials, retries/backoff/timeouts, idempotency, spend reserve/commit accounting, redaction/logging, supervised provider tests and failure behavior.

The **provider abstraction** part of this blocker is closed by WP-PB-005: `PIPELINE_PROVIDER_MODE` now selects a `PipelineProvider` implementation behind a typed seam, so activating a vendor is an implementation swap rather than an edit to five stage services. The default remains `null` (no vendor, fail-closed, zero spend). A deterministic offline `simulation` provider ships alongside it for pre-vendor testing; it performs no network I/O, spends nothing, labels every record it writes, and is refused when `ENVIRONMENT` is production with no override. Simulation does **not** discharge any part of this blocker relating to live vendors.

### BILLING-001 — Billing go-live — **OPEN / DEFERRED**

Billing code exists but production billing remains a separate live-secret/reconciliation gate. Do not infer paid-production readiness from the in-repo Stripe implementation.

### PUBLISH-001 — External publishing — **BLOCKED BY DESIGN**

No autonomous/external publishing milestone is authorized. Any future enablement requires current platform policy/rights evidence, exact-artifact compliance, immutable Human Review approval, rollback/kill-switch evidence and Founder authorization.

---

## Historical P0/P1 baseline

Previously closed P0/P1 engineering controls remain closed unless new evidence demonstrates regression. Their historical records remain in release/audit documents; this file now reflects the current `0050` codebase rather than the obsolete `0032_merge_p1` snapshot.

---

## Related

- `docs/MILESTONE_AUDIT_STANDARD.md`
- `docs/EXECUTIVE_STATUS_REPORT.md`
- `docs/TECHNICAL_DEBT_REGISTER.md`
- `docs/FINAL_RELEASE_AUDIT.md`
- `docs/DISASTER_RECOVERY_REPORT.md`
- `docs/BETA_RELEASE_CHECKLIST.md`
- GitHub issue #50 — protect `main`
