# External repo / OSS research — 2026-09-12

**Purpose:** survey GitHub for repos that could be adopted into Content
Orchestrator, evaluated against `AGENTS.md` constraints — specifically
"no new frameworks without an explicit work package," the Non-negotiables,
and the currently **deferred/blocked** gates in `docs/LAUNCH_BLOCKERS.md`
(`PROVIDER-001` open/deferred, `PUBLISH-001` blocked by design,
`BILLING-001` open/deferred).

**Method:** read the current codebase to find real gaps (not
hypothetical ones) — `apps/api/app/services/{content_department,
production, draft_desk, spend}.py`, `docs/LAUNCH_BLOCKERS.md`,
`docs/PLATFORM_POLICY_CONTROL_MATRIX.md`, `docs/TECHNICAL_DEBT_REGISTER.md`
— then searched GitHub for maintained candidates per gap. Star counts /
`updated_at` are as observed today; re-verify before acting on this later.

**Headline finding:** the vast majority of small (0–3 star) 2026-created
repos surfaced by these searches are unmaintained, unaudited,
likely LLM-generated demo repos ("guardrails in 3 lines of code" clones,
one-off tutorials). They are **not** recommended as dependencies —
listed only where relevant to show what exists. The recommendations
below are limited to repos with real adoption evidence (stars, age,
active commit history, or being the origin repo that many others fork/wrap).

---

## 1. Provider abstraction gateway — for the future `PROVIDER-001` milestone only

**Current state:** `.env.example` already anticipates
`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` /
`ELEVENLABS_API_KEY` / `CREATOMATE_API_KEY`, but no code path calls any
of them yet — `draft_desk.py`, `content_department.py`, and
`production.py` are explicitly deterministic/"no route invokes a real
provider" by design. `docs/LAUNCH_BLOCKERS.md` marks `PROVIDER-001` as
**OPEN / DEFERRED**, requiring its own audited milestone before any live
provider is wired in.

**Candidate:** [`BerriAI/litellm`](https://github.com/BerriAI/litellm) —
58.5k★, 11.4k forks, commits within the last day, Apache-2.0 core. Gives
one call shape across OpenAI/Anthropic/Gemini/Bedrock/VertexAI/etc.,
plus built-in cost tracking, retries, and rate limiting — directly maps
to Non-negotiable #4 ("Provider abstraction — no hard-coding a single
LLM/vendor into the core path") and to the retries/backoff/idempotency
and spend-accounting requirements PROVIDER-001 already lists as required
evidence.

**Recommendation:** do **not** add this now — PROVIDER-001 is explicitly
deferred and out of scope until its own audited milestone. When that
milestone is scoped, evaluate `litellm`'s Python SDK (not its optional
proxy/gateway server, which would be a second running service and its
own attack surface) against hand-rolling per-provider `httpx` clients.
The SDK gives retries/backoff/cost-tracking for free but adds a large
dependency surface (pull its `pip-audit` history before adopting) and
some indirection over our own idempotency-key / spend-reservation model,
which already exists in `app/orchestration/provider_effects.py` and
`app/services/spend.py` and must stay the source of truth regardless of
which HTTP client makes the call. Either way this is a `PROVIDER-001`
work-package decision, not one to make from this research pass.

---

## 2. External publishing — for the future `PUBLISH-001` milestone only

**Current state:** `docs/LAUNCH_BLOCKERS.md` marks `PUBLISH-001` as
**BLOCKED BY DESIGN** — "no autonomous/external publishing milestone is
authorized." `.env.example` has `UPLOAD_POST_API_KEY` reserved (a
managed SaaS multi-platform posting API), and `n8n/README.md` shows an
n8n-workflow integration point is planned but not yet built.

**Candidate:** [`gitroomhq/postiz-app`](https://github.com/gitroomhq/postiz-app)
— the real, actively-developed self-hosted multi-platform
scheduling/publishing app (AGPL-3.0; confirmed as the real upstream
because many 2026 forks/wrappers/Docker images reference it by exact
name and version tags, e.g. `v2.23.0`). It has first-party adapters for
30+ destinations, which is exactly the kind of "connector races" work
`AGENTS.md` explicitly lists as a **non-goal until PMF**.

**Recommendation:** do not integrate — this is squarely inside
`PUBLISH-001` (blocked by design) and the explicit non-goal "Connector
races (Zapier/Make parity)." Worth keeping on file for whenever
`PUBLISH-001` is authorized: postiz's adapters are AGPL, which has
license implications if embedded directly vs. run as a separate
self-hosted service the API calls out to — flag that licensing question
to the Founder before any future adoption, since it's a real
architecture/legal decision, not a drop-in library choice.

---

## 3. Duplicate / near-duplicate content guardrail — **not blocked, actionable now**

**Current state:** `docs/PLATFORM_POLICY_CONTROL_MATRIX.md` lists
"Duplicate / repetitive-content guardrail" as **CONFIRMED OPEN**,
requiring similarity thresholds validated against adversarial tests "so
a batch cannot evade review by superficial edits." Looking at
`apps/api/app/services/content_department.py:79-86,465-500`: the
existing `OriginalityFingerprint` check is a plain SHA-256 hash of the
whitespace-normalized script body/hook — it only catches **byte-for-byte
identical** text (after normalizing case/whitespace). A single changed
word defeats it entirely, which is exactly the gap the control matrix
calls out. There's also an unused `semantic_reference` column already on
`OriginalityFingerprint` that looks like it was reserved for exactly
this.

This gap is not touched by any of the three deferred/blocked gates
above — it's pure text-similarity math over content the system already
has, no live provider call, no external publish, no new secret.

**Candidates surveyed:**
- Near-duplicate detection is a well-established, small technique
  (SimHash / MinHash-LSH), not something that needs a heavyweight
  dependency. [`ekzhu/datasketch`](https://github.com/ekzhu/datasketch)
  (MinHash/LSH, ~2.7k★, actively maintained) is the standard library
  choice if a dependency is wanted.
- The various "LLM guardrails" / "PII redaction" repos found in this
  search (`llm-guardrails`, `chatbot-guardrails`, `forcefield`,
  `Cerberus-Proxy`, etc.) are almost all 0–2-star, days-to-weeks-old
  repos with no real adoption signal — **not recommended**.
  [`microsoft/presidio`](https://github.com/microsoft/presidio) is the
  one legitimately established PII-detection project in that space
  (confirmed by the number of real projects wrapping/porting it), but
  it solves a different problem (PII redaction, not content
  duplication) and would only be relevant if the existing regex-based
  secret/PII patterns in `content_department.py`
  (`_SECRET_PATTERN`, `_UNTRUSTED_INSTRUCTION`) prove insufficient in
  practice — no evidence of that yet, so not recommended today either.

**Recommendation:** implement SimHash directly (a few dozen lines,
public/standard algorithm, zero new dependency, no `pip-audit`/license
surface to review) rather than pulling in `datasketch` for one
algorithm we can write and unit-test ourselves. Written up as a ready
work package below.

---

## 4. Everything else considered and set aside

- **LLM-side prompt-injection/jailbreak frameworks** (Rebuff-style,
  NeMo Guardrails, etc.): same problem as above — most repos are
  low-signal 2026 clones; the two credible ones (NeMo Guardrails,
  Presidio) are provider/PII-side tools that don't apply until
  `PROVIDER-001` actually calls a live model.
- **Video assembly OSS** (searched for Remotion-style programmatic
  video generation as a `CREATOMATE_API_KEY` alternative): no results
  met a real-adoption bar in this pass; `production.py` has no live
  provider path yet anyway (`PROVIDER-001`), so this is premature.
- **AI-gateway alternatives to litellm** (`GoModel`, `control-layer`,
  various "LiteLLM alternative" repos): all far smaller/newer than
  `litellm` itself with no adoption evidence; not recommended over it
  if/when `PROVIDER-001` picks a gateway approach.

---

## Bottom line

Nothing here should be merged as a new runtime dependency right now.
Two things are ready to act on without violating `AGENTS.md`'s "no new
frameworks without an explicit work package" rule or either deferred
gate:

1. This document itself, as the research record.
2. `docs/work-packages/WP-P1-011-near-duplicate-guardrail.md` (added in
   this same change) — a scoped, dependency-free proposal to close the
   one CONFIRMED OPEN gap that isn't blocked by `PROVIDER-001`/
   `PUBLISH-001`. Not implemented yet — it touches a compliance-audited
   path (`content_department.py`) that this repo's own governance model
   says should get an independent review pass, not just the
   implementing agent's self-certification.
