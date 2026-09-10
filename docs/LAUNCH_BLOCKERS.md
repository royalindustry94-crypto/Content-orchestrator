# Launch Blockers

**Repository:** Content Orchestrator  
**Updated:** 2026-09-09 (Phase 0/1 recovery audit — reconciled against merged `main` @ `2ca92f8`)  
**Audited baseline:** `main` @ `2ca92f8`, after PR #94 (TD-072–TD-088) and PR #95 (Operations Dashboard frontend hardening) merged 2026-09-09T13:19 UTC  

> **2026-09-09 recovery-audit update:** the prior version of this file described PR #94 as
> "fix-pushed, pending independent re-audit before merge — not yet part of the merged audited
> baseline." That is now stale: **PR #94 and PR #95 are merged to `main`.** This recovery audit
> independently reproduced the full engineering evidence from a clean install against the
> merged head (not taken on trust from prior chat claims or CI logs alone): API **339 passed,
> 80.82% coverage** (75% floor), migration upgrade → downgrade-to-base → re-upgrade clean
> through head `0054`, `ruff check` clean; worker **7 passed**, lint clean; web lint/build
> clean, **31 tests passed**, `npm audit --audit-level=high` clean. GitHub's own "CI" workflow
> also shows green on this exact head (run `34363259425`). RUNTIME-001 remains CLOSED per the
> note below (unchanged by this update — see `docs/TECHNICAL_DEBT_REGISTER.md` TD-071).
> GOV-001 (branch protection, below) is now also independently verified CLOSED.
**Source of truth:** exact-head CI, retained browser evidence, repository/runtime probes — not prior chat claims

## Rule

Nothing is considered deployable or releasable from documentation alone. The current exact candidate must satisfy `docs/MILESTONE_AUDIT_STANDARD.md` and receive PASS before merge/release.

---

## Current verdict

| Target | Status | Reason |
|---|---|---|
| Product code baseline | **PRIVATE-BETA CAPABLE** | Business Manager + audited Research → Strategy → Content → Production → Compliance preview is merged and fail-closed |
| Development governance | **GREEN** | Independent audit standard is merged; GitHub `main` branch protection independently verified live 2026-09-09 (GOV-001/issue #50 closed) |
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

PR #94 and PR #95 (merged 2026-09-09) additionally closed the full TD-072–TD-088 batch
(RLS tenant-isolation backstops across `content_jobs.py`/`review_gates.py`/`profiles`/the
Operations Dashboard, a CRITICAL cross-tenant dashboard-blending fix, Stripe webhook
hardening, audit-trail and idempotency fixes) and hardened the Operations Dashboard
frontend (polling/freshness, explicit loading/error states, duplicate-submit protection).
Every finding has its own regression test, independently re-audited PASS (issue #91).

### Verified engineering evidence

Independently reproduced from a clean install against `main` @ `2ca92f8` during this
2026-09-09 recovery audit (not merely read from prior CI logs):

- API: **339 passed**, **80.82% coverage** (75% gate)
- Alembic: current audited head **`0054`**
- Migration lifecycle: upgrade → full downgrade to base → re-upgrade **PASS**
- Worker: **7 passed**, lint clean
- Web lint/build/tests: **PASS** (31 tests); `npm audit --audit-level=high`: **PASS** (2 pre-existing moderate advisories in a dev-only test-runner dependency, not shipped)
- `main` branch protection: **verified live** (`protected: true`)
- GitHub's own "CI" workflow: **green** on this exact head (run `34363259425`)
- Exact-head browser smoke (from the prior PR #48 baseline; not re-run this pass): desktop + exact 390px mobile **PASS**, retained as CI artifact

---

## Open blockers / conditions

### GOV-001 — Protect `main` — **CLOSED (2026-09-09)**

Tracked by GitHub issue **#50** (closed 2026-08-28; its linked implementation PR #59 was
never merged, so this recovery audit re-verified the control directly rather than trusting
the issue's closed state at face value).

Current evidence: live `GET`-equivalent read via `mcp__github__list_branches` this session
returns `{"name":"main","protected":true}`. Protection is active by some path other than
PR #59 (still open/draft, safe to close without merging at Founder discretion). The exact
per-check ruleset detail (which status checks are required, force-push/deletion block,
admin-enforcement) was not individually re-read — the connected tool surface only exposes
the `protected` boolean — so reopen narrowly if that finer-grained evidence is ever needed
for an external audit.

### RUNTIME-001 — Managed Supabase/runtime verification — **CLOSED (2026-09-09)**

Supabase MCP connector connected; live read-only audit performed against the actual managed
project (`content-orchestrator-test`, ref `vagfnbcnvtojljggxvxr`). Database/RLS/grant state
independently verified, migration drift found and corrected (managed DB confirmed at head
`0053` at verification time). `main` has since advanced to `0054` (TD-082); that migration
has **not** been applied to or verified against the managed database — only `0053` is
confirmed live there. PITR/backup
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

Previously closed P0/P1 engineering controls remain closed unless new evidence demonstrates regression. Their historical records remain in release/audit documents; this file now reflects the current `0054` codebase rather than the obsolete `0032_merge_p1` snapshot.

---

## Related

- `docs/MILESTONE_AUDIT_STANDARD.md`
- `docs/EXECUTIVE_STATUS_REPORT.md`
- `docs/TECHNICAL_DEBT_REGISTER.md`
- `docs/FINAL_RELEASE_AUDIT.md`
- `docs/DISASTER_RECOVERY_REPORT.md`
- `docs/BETA_RELEASE_CHECKLIST.md`
- GitHub issue #50 — protect `main`
