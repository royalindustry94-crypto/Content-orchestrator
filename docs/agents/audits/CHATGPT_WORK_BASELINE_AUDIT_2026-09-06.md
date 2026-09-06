# ChatGPT work — baseline independent audit

**Date (UTC):** 2026-09-06  
**Auditor:** Cursor Cloud Agent `bc-b09a2f25-5f8f-445c-b5b5-ba4eb8dcf7d9` (Build process agent roles)  
**Builder under review:** ChatGPT-family work — Codex lanes plus historical Manus/Lumora automation already on `main`  
**Standard:** `docs/MILESTONE_AUDIT_STANDARD.md`  
**This audit does not authorize merge or deploy.**

## Identity

| Field | Value |
|---|---|
| Audited `main` HEAD | `abb20981f68cb0de8e3ed75af9759e0b5b6fb656` (PR #51 merge) |
| Audited `main` migration head | `0050` (`0050_compliance_fk_indexes`) |
| Codex integration draft | PR #79 `codex/human-finished-creative-core` claimed head `77d7341ac04e732969f80fee46cca52c24100b73` |
| Codex Creative Director draft | PR #82 `codex/human-creative-director-core` claimed head `ea64175027794abda2728891ff733d451f88361a` |
| PR #79 claimed CI | Actions run `33950509245` — six required jobs PASS (Vercel previews FAIL; not required) |
| PR #82 claimed CI | Actions run `33970495944` — six required jobs PASS (Vercel previews FAIL; not required) |
| `main` Alembic on this checkout | single head `0050`; PR #79 adds `0051`+`0052`; PR #82 adds `0053` on `0052` |

Builder cannot be the sole certifier. Codex PR bodies already request an
independent PDF audit outside Git. This document is the in-repo baseline; it
is **not** that Founder-required PDF.

## Scope

Familiarize with the full build-to-live path and deep-audit current
ChatGPT/Codex work. Product code on this auditor branch was not changed.

Non-goals: merge, deploy, live providers, billing, publishing, branch-protection
mutation.

## 1. Scope / process

The audited `main` product is a bounded Founder Preview: Business Manager UI
plus Scout → Strategy → Content → Production → Compliance, with mandatory
Human Review and external publishing disabled (PR #48, governance PR #49/#51).

ChatGPT/Codex now has a large unmerged stack:

- PR #79 (draft, +5266/−290) consolidates safety closures, managed-Supabase
  ACL hardening, five-step setup, and agent-reliability scaffolding
- PR #82 (draft, +1644) stacks Human Creative Director planning tables on #79

**Finding A-01 — Medium / does not block this governance WP.**  
Many stale or experimental PRs remain open alongside the Codex lane
(#67, #71, #72, #77, #78, older Mission Control PRs). Risk is Founder
attention split and accidental merge of the wrong branch. Remediation:
Founder names one surviving implementation lane; auditor watches only that
lane plus `main`.

**Finding A-02 — High / blocks merge of ChatGPT drafts.**  
PR #79 and #82 are explicitly draft / do-not-merge until independent audit
of the *then-current* exact SHA. Their self-reported CI is necessary but
not sufficient. Merge is blocked until a dedicated SHA-locked audit of the
rebased candidate completes, including Human Review, RLS, spend, migrations,
tenant negatives, and runtime evidence.

## 2. Security and tenancy

On `main`:

- Tenant tables in the preview pipeline are designed with workspace scope
  and FORCE RLS (PR #48 audit record).
- This session could not mutate or independently re-read live GitHub branch
  protection (`403` on the protection API). Issue #50 is **closed** in
  GitHub, but `docs/LAUNCH_BLOCKERS.md` and `docs/TECHNICAL_DEBT_REGISTER.md`
  still list GOV-001 / TD-070 as **OPEN**.

**Finding A-03 — High / documentation and enforcement drift.**  
Ticket close is not proof that `main` is technically protected. Independent
re-read of the live ruleset is still required before scaling builders.
Do not treat GOV-001 as closed from the issue state alone.

**Finding A-04 — High / blocks managed-runtime claims.**  
Issue #66 remains OPEN: managed Supabase default grants gave `anon` /
`authenticated` DML on internal tables including `local_auth_credentials`
and `worker_credentials`. Local/CI Postgres does not model that default.
PR #79 includes `0051_managed_supabase_public_acl_hardening.py` and
`test_managed_supabase_migration_safety.py`. Those files are **unmerged**
and not independently certified on a live Supabase project in this audit.
Managed-runtime readiness stays **NOT VERIFIED / FAIL** for live claims.

## 3. Human Review Gate

On current `main` (`apps/api/app/schemas/content_desk.py`):

- `ReviewDecisionIn` is `{ approved, notes }`
- `decide_review_gate` does not take an expected `content_version_id`
- Gate creation stores `content_version_id=item.current_version_id` in
  `controller.py`
- A later content revision can therefore leave a still-awaiting gate whose
  approval is not bound to the exact version the reviewer saw

Codex issue #76 / PR #79 names this **S2-M1** and the diff adds:

- required `payload.content_version_id`
- compare against `gate.content_version_id` and `item.current_version_id`
  under `FOR UPDATE`
- fail closed when the reviewed version is no longer current

**Finding A-05 — High / blocks treating `main` HRG as exact-artifact safe
for ChatGPT's later content-revision work.**  
`main` does not yet bind the reviewer's displayed version at decision time.
PR #79's fix is directionally correct from the diff, but it is unmerged and
not independently certified on the exact head in this session. Until that
SHA is audited end-to-end, do not merge #79/#82 and do not claim stale-
approval closure.

**Finding A-06 — Informational / control preserved.**  
Preview publishing remains disabled by design (PUBLISH-001). PR #82 states
generation-plan approval is not final-content or publication approval. That
boundary must be re-proved on the #82 SHA (role tests + no publish route).

## 4. Spend / providers

On `main`, reservation commit is still conditional: a successful stage
submit can proceed when no open reservation exists (`dispatcher.py` looks
up a reservation and only commits if present).

PR #79 moves the reservation check **before** success handling and raises
`LeaseConflict("spend_reservation_missing")` when `success` is true and no
open reservation exists. Issue #76 calls this **S2-M4**.

**Finding A-07 — High on `main` for any chargeable success path; Medium
while preview providers stay unconfigured.**  
Preview departments are supposed to spend zero when unconfigured. The
`main` submit path still allows "success without reservation." That is a
real fail-open if a chargeable executor is attached. Codex's unmerged
default-deny + reservation requirement is the intended closure. It is not
certified until the exact #79 SHA is independently audited, including
worker unknown-stage default-deny (S2-M2).

Live OpenAI/Anthropic/Gemini/ElevenLabs/Creatomate paths remain deferred
(PROVIDER-001). No ChatGPT draft may activate them as a side effect.

## 5. Data / migrations

- `main` head `0050` with documented upgrade → downgrade base → re-upgrade PASS
  in the PR #48/#51 release record
- PR #79 adds `0051` (managed ACL) and `0052` (workspace content profiles +
  system RLS)
- PR #82 adds `0053` with claimed single parent `0052`

**Finding A-08 — High / merge process.**  
#82 must not land before #79. After #79, #82 must be rebased onto the then-
current protected `main` and re-audited. Parallel heads off the same parent
remain a merge blocker by repository rule.

This session did not replay #79/#82 migrations on a live database.

## 6. Reliability

Preview provider states on `main` are designed to be truthful
`NOT CONFIGURED`. Codex adds substantial agent-coordination surface
(`.agents/coordination/*`, `.cursor/hooks/*`, `scripts/agent-check.sh`).
That is process machinery, not customer runtime, but hooks/install scripts
must not weaken CI or leak secrets.

**Finding A-09 — Medium / process risk.**  
PR #79 changes `.github/workflows/ci.yml` and adds cloud install/start
scripts. Any CI mutation on a ChatGPT branch needs a line-by-line review so
required gates cannot be skipped. Not certified in this baseline.

## 7. Tests / CI

Re-checked via `gh pr checks` on 2026-09-06:

| PR | api | worker | web | security | docker-build | browser-smoke | Vercel |
|---|---|---|---|---|---|---|---|
| #79 | PASS | PASS | PASS | PASS | PASS | PASS | FAIL (not required) |
| #82 | PASS | PASS | PASS | PASS | PASS | PASS | FAIL (not required) |

This auditor did not re-run the suites locally against those SHAs.

**Finding A-10 — Informational.**  
Claimed API counts: #79 = 320 tests; #82 = 324 tests / 80.83% coverage.
`main` release record is 299 tests / 81.09%. Numbers are consistent with
added tests but must be re-read from the exact job logs before PASS.

## 8. UI / browser

`main` retains exact-head desktop + 390px smoke as a required CI job.
PR #82 is backend/planning-core; Cursor issue #80 owns the mobile workspace
UI and is explicitly still required before merge consideration.

**Finding A-11 — Medium / #82 merge.**  
No independent browser/mobile review of the Human Creative Director UI
contract was performed here. #82 says that review is still required. That
condition is acceptable only as a named pre-merge gate, not as a silent
skip.

## 9. Runtime / external evidence

| Claim | This session |
|---|---|
| Managed Supabase project posture | **NOT VERIFIED** (issue #66 open; connector not exposing a clean project here) |
| Production auth | **NOT VERIFIED** |
| PITR / managed backup drill | **BLOCKED — EVIDENCE UNAVAILABLE** |
| Live billing | Disabled by policy; **not** go-live |
| External publishing | Disabled by design |
| App live on a Founder environment | **NOT VERIFIED** from this audit |

Operational private beta remains CONDITIONAL / not runtime-verified, matching
`docs/LAUNCH_BLOCKERS.md`.

## 10. Documentation

Launch, executive, and debt docs on `main` are dated 2026-08-28 and still
describe GOV-001 as open after issue #50 was closed. Codex PRs rewrite those
docs on their branches; those rewrites are unmerged and not accepted here.

**Finding A-12 — Low / docs drift on `main`.**  
Reconcile issue #50 versus GOV-001/TD-070 only after an independent live
ruleset read. Do not let ChatGPT close the debt item from the GitHub issue
state alone.

## Verdicts

| Target | Verdict | Why |
|---|---|---|
| `main` product baseline as private-beta **code** | **CONDITIONAL** (unchanged from PR #51 record) | Preview pipeline audited historically; runtime and managed ACL not verified; HRG exact-version bind and chargeable-submit reservation remain gaps for later live work |
| `main` as production / live providers / billing / publish | **FAIL / BLOCKED** | By design and missing runtime evidence |
| Codex PR #79 | **FAIL for merge** | Independent exact-SHA audit of the current head is still required; safety diffs look serious and must be certified, not trusted |
| Codex PR #82 | **FAIL for merge** | Stacked on #79; UI contract and independent SHA audit outstanding |
| This WP (agent roles only) | Not a product milestone | Configuration/docs only |

CONDITIONAL on `main` is inherited from the existing Founder-facing release
record (runtime evidence missing, not a newly invented safety pass). New
ChatGPT feature merge is FAIL until the dedicated SHA audit lands.

## Blocking next actions (Founder)

1. Keep #79 and #82 draft. Do not merge.
2. Launch the ChatGPT Independent Auditor against the **current** #79 head
   and require a downloadable PDF if that remains the lane rule.
3. Do not start the Build Continuation Agent until you send a takeover
   phrase.
4. Re-read live `main` protection/ruleset (A-03).
5. Do not claim managed Supabase test readiness until #66 is remediated and
   independently re-probed on the isolated project (A-04).

```text
ROLE: auditor
CANDIDATE: main abb20981f68cb0de8e3ed75af9759e0b5b6fb656; PR79 77d7341ac04e732969f80fee46cca52c24100b73; PR82 ea64175027794abda2728891ff733d451f88361a
MIGRATION HEAD: main 0050; PR79 claimed 0052; PR82 claimed 0053
VERDICT: FAIL for ChatGPT draft merge; CONDITIONAL inherited for main preview-code baseline; FAIL for live/runtime claims
BLOCKERS: independent SHA audit of #79/#82; issue #66; live branch-protection re-read; HRG exact-version bind still unmerged; managed runtime NOT VERIFIED
NEXT AUTHORIZED ACTION: Founder launches auditor on a named SHA, or sends TAKEOVER to the continuation agent. No merge.
```
