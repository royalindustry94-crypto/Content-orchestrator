# Launch Blockers

**Repository:** Content Orchestrator  
**Updated:** 2026-09-09 (RUNTIME-001 closed; see note below — remainder of this file otherwise reflects `main`'s 2026-08-28 state, not yet the unmerged `claude/project-builder-handover-k95wpm` fixes)  
**Audited baseline:** `main` after PR #49 governance merge  

> **2026-09-09 update:** RUNTIME-001 below is now CLOSED — the Supabase MCP connector was
> connected and a live read-only audit performed against the actual managed project
> (`content-orchestrator-test`), including verifying the "RLS disabled" advisor findings are
> not exploitable (zero grants to `anon`/`authenticated`) and bringing the managed database's
> migration state in sync with the branch's head *at that time* (`0053`). See
> `docs/TECHNICAL_DEBT_REGISTER.md` TD-071. The branch has since advanced to migration `0054`
> (TD-082, in this same PR) — that migration has **not** been applied to or verified against the
> managed database; only `0053` is confirmed live there. Separately, TD-072 through TD-088 (RLS
> backstops on two more route files, a CRITICAL cross-tenant dashboard-blending fix, billing
> hardening, and three workspace-scoping/logic bugs) are fix-pushed on
> `claude/project-builder-handover-k95wpm` / PR #94, pending independent
> re-audit before merge — not yet part of this file's "Merged audited baseline" below.
**Source of truth:** exact-head CI, retained browser evidence, repository/runtime probes — not prior chat claims

## Rule

Nothing is considered deployable or releasable from documentation alone. The current exact candidate must satisfy `docs/MILESTONE_AUDIT_STANDARD.md` and receive PASS before merge/release.

---

## Current verdict

| Target | Status | Reason |
|---|---|---|
| Product code baseline | **PRIVATE-BETA CAPABLE** | Business Manager + audited Research → Strategy → Content → Production → Compliance preview is merged and fail-closed |
| Development governance | **CONDITIONAL** | Independent audit standard is merged; GitHub `main` branch protection is still disabled (issue #50) |
| Operational private beta | **CONDITIONAL / AWAITING OPERATOR VERIFICATION** | Managed Supabase runtime evidence is now established (RUNTIME-001 closed 2026-09-09); a hands-on Founder test of the live app is still pending |
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

### RUNTIME-001 — Managed Supabase/runtime verification — **CLOSED (2026-09-09)**

Supabase MCP connector connected; live read-only audit performed against the actual managed
project (`content-orchestrator-test`, ref `vagfnbcnvtojljggxvxr`). Database/RLS/grant state
independently verified, migration drift found and corrected (now at head `0054`). PITR/backup
policy specifically was not part of this pass — reopen narrowly for that if needed before a real
go-live certification. See `docs/TECHNICAL_DEBT_REGISTER.md` TD-071 for full evidence.

### PROVIDER-001 — Live provider activation — **OPEN / DEFERRED**

Before enabling OpenAI/Anthropic/Gemini/ElevenLabs/Creatomate/n8n or equivalent live effects, require a separate audited milestone covering credentials, provider abstraction, retries/backoff/timeouts, idempotency, spend reserve/commit accounting, redaction/logging, supervised provider tests and failure behavior.

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
