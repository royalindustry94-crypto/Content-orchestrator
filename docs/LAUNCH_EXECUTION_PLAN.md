# Launch Execution Plan — Content Orchestrator

**Source:** `docs/BETA_READINESS_AUDIT.md` (Launch Score 28/100, verdict NOT READY)  
**Purpose:** Executable engineering backlog only. No new strategy.  
**SKU assumption for shortest path:** Private Beta = **Agency Content / Draft Review Desk** (mandatory Human Review Gate + spend caps + multi-tenant workspaces). Full autonomous publish and analytics are post-revenue.

**Effort scale:** S ≤ 1 day · M 2–3 days · L ~1 week · XL > 1 week (single focused founder/engineer)  
**Risk scale:** Low / Medium / High / Critical  
**Revenue impact:** None / Indirect / Enables Beta / Enables Paid / Unlocks Expansion

**Reviewers (default roles):**

| Role | Who |
|------|-----|
| Security | Security Reviewer (or founder wearing security hat) |
| Migrations | Migration Reviewer when Alembic changes |
| Product | Founder / CEO |
| QA | Test Writer / founder |

---

## Execution order (recommended)

```
Wave 0 (serial):     L0-01 merge/land Review Desk foundation
Wave 1 (serial):     L0-02 orchestration runtime wiring
Wave 1b (parallel):  L0-03 spend · L0-05 staging · L0-06 docs  [after L0-02 starts, L0-03/05/06 can overlap]
Wave 2 (serial):     L0-04 real login  [needs Review Desk UI from L0-01]
Wave 2b (choose):    L0-07a Draft Desk SKU hardening  OR  L0-07b one BYOK generator
Wave 3 (serial):     L1-01 Stripe → then L1-02 notify, L1-03 ledger UI (parallel)
Wave 3b (parallel):  L1-04 backups · L1-05 export · L1-06 audit · L1-07 prod lockdown
Wave 4:              First 10 customers (founder sales + L1 support)
Wave 5:              P2 public-launch hardening
```

### Can run in parallel

- After Review Desk lands: **L0-03** (spend), **L0-05** (staging), **L0-06** (docs)  
- After Stripe ships: **L1-02**, **L1-03**, **L1-04**, **L1-05**, **L1-06**, **L1-07** (mostly independent)  
- Most **P2** items after first paid customer  
- Most **P3** items anytime without blocking launch  

### Never parallelize

| Constraint | Why |
|------------|-----|
| **L0-01 before depending UIs/APIs** | Downstream assumes content-jobs + review-gates on `main` |
| **L0-02 before claiming “pipeline works”** | Without scheduler/relay, jobs do not advance |
| **BYOK crypto before any provider-key UI (L0-07b)** | Plaintext keys are a company-ending trust failure |
| **Stripe webhook entitlement before charging (L1-01)** | Do not take money without access control |
| **Migrations that touch RLS/spend/billing tables** | One migration chain; no concurrent Alembic heads |
| **Gate bypass “shortcuts” for demo** | Violates product invariant; never ship |

---

# P0 — Launch blockers (Private Beta)

## L0-01 — Land Review Desk on `main`

| Field | Detail |
|-------|--------|
| **ID** | L0-01 |
| **Title** | Merge/re-land Review Desk API + UI (content jobs, review gates) |
| **Business value** | Makes the commercial wedge (Human Review Gate) reachable |
| **Customer impact** | Can submit draft → see queue → approve/reject |
| **Technical impact** | Adds product HTTP routes + web desk; may include outbox relay from PR #23 |
| **Dependencies** | None (unblocks nearly everything). Prefer starting from PR #23 |
| **Estimated effort** | M (if #23 mergeable) / L (if rebuild) |
| **Risk** | Medium |
| **Engineering effort** | M–L |
| **Revenue impact** | Enables Beta |
| **Acceptance criteria** | On `main`: create content job lands in awaiting gate; approve → published/succeeded; reject → failed; editor cannot decide; cross-workspace isolated; web desk usable |
| **Definition of Done** | Merged to `main`, CI green, CHANGELOG updated, demo script works on staging or local compose |
| **Required tests** | API: create/approve/reject/authz/isolation; web: client/unit or e2e smoke |
| **Required documentation** | Operator note in README; link work package if present |
| **Required reviewers** | Security, QA, Product |

---

## L0-02 — Wire orchestration runtime (scheduler + relay + consumers)

| Field | Detail |
|-------|--------|
| **ID** | L0-02 |
| **Title** | Start scheduler, outbox relay, `consumers.register_all`, scheduler lease reaper in production process |
| **Business value** | Pipelines move without manual test harnesses |
| **Customer impact** | Approvals resume runs; stages dispatch to workers when used |
| **Technical impact** | Lifespan (or dedicated process) ticks; closes “engine is a library” gap |
| **Dependencies** | L0-01 strongly preferred first (something to schedule). Relay may already be in #23 — still must add **scheduler** |
| **Estimated effort** | M |
| **Risk** | High (wrong wiring = stuck/dupe work) |
| **Engineering effort** | M |
| **Revenue impact** | Enables Beta |
| **Acceptance criteria** | Non-test env: job_schedule rows lease and dispatch; outbox review events resume runs without in-request-only hacks; scheduler leases reaped; no double-processing under two ticks |
| **Definition of Done** | Integration test or staging proof; CI green; ops note on tick intervals |
| **Required tests** | Lifespan/integration: schedule→assign; review approve via relay; lease reap; multi-tick idempotency |
| **Required documentation** | Architecture note: what runs in API process |
| **Required reviewers** | Security, QA, Migrations (if any), Product |

---

## L0-03 — Spend caps: seed + enforce monthly + customer API

| Field | Detail |
|-------|--------|
| **ID** | L0-03 |
| **Title** | Seed default spend caps on workspace create; enforce monthly; GET/PUT spend caps (+ basic ledger read) |
| **Business value** | Sellable cost control; fail-closed $ story |
| **Customer impact** | Sees/sets caps; over-cap holds runs |
| **Technical impact** | Workspace create seeds `SpendCap`; `reserve_spend` checks monthly; HTTP under `/workspaces/{id}/spend` |
| **Dependencies** | Can parallel with L0-05/L0-06 after L0-01; should land before paid beta demos |
| **Estimated effort** | M |
| **Risk** | High (money) |
| **Engineering effort** | M |
| **Revenue impact** | Enables Beta |
| **Acceptance criteria** | New workspace has daily+monthly caps; concurrent reserve cannot exceed; monthly enforced or column removed from promises; admin can read/update; non-admin 403 |
| **Definition of Done** | Tests for seed, daily, monthly, race; CHANGELOG; API docs snippet |
| **Required tests** | Seed on create; monthly block; FOR UPDATE race; authz |
| **Required documentation** | Defaults + fail-closed behavior |
| **Required reviewers** | Security, QA, Migrations (if any), Product |

---

## L0-04 — Supabase Auth in web (real login)

| Field | Detail |
|-------|--------|
| **ID** | L0-04 |
| **Title** | Replace token-paste with Supabase email/OAuth login + session |
| **Business value** | Real users can enter without founder minting JWTs |
| **Customer impact** | Sign up / log in / stay logged in |
| **Technical impact** | `@supabase/supabase-js` (or equivalent); session → API Bearer; fix `/api` proxy rewrite if not already |
| **Dependencies** | L0-01 (desk UI to attach login to) |
| **Estimated effort** | M |
| **Risk** | Medium |
| **Engineering effort** | M |
| **Revenue impact** | Enables Beta |
| **Acceptance criteria** | User can create account, create workspace, use Review Desk without pasting JWT; logout works; invalid session → login |
| **Definition of Done** | Staging demo with real Supabase project; env vars documented |
| **Required tests** | Web auth smoke; API 401 without token |
| **Required documentation** | `.env.example` Supabase URL/anon key; setup steps |
| **Required reviewers** | Security, Product, QA |

---

## L0-05 — Staging deploy (API + worker + web + Postgres)

| Field | Detail |
|-------|--------|
| **ID** | L0-05 |
| **Title** | Dockerize and deploy staging stack with secrets |
| **Business value** | Something customers can click; founder demos off localhost |
| **Customer impact** | Hosted Private Beta URL |
| **Technical impact** | Dockerfiles / compose for api+worker+web+db; CI deploy optional; secrets via host secret store |
| **Dependencies** | Parallelizable after L0-01; needs L0-02 before claiming full pipeline on staging |
| **Estimated effort** | L |
| **Risk** | Medium |
| **Engineering effort** | L |
| **Revenue impact** | Enables Beta |
| **Acceptance criteria** | Staging health ready; login (or interim auth) works; content→review→decide works end-to-end; worker registers if required by SKU |
| **Definition of Done** | Runbook: deploy, rollback, env list; staging URL in ops notes |
| **Required tests** | Smoke checklist (manual OK for beta) + CI still green |
| **Required documentation** | `docs/ops/STAGING.md` (or README section) |
| **Required reviewers** | Security, Product |

---

## L0-06 — Operator onboarding docs + honest README

| Field | Detail |
|-------|--------|
| **ID** | L0-06 |
| **Title** | Rewrite README; add Private Beta operator onboarding runbook |
| **Business value** | Founder can board design partners without archaeology |
| **Customer impact** | Clear “how we work with you in beta” |
| **Technical impact** | Docs only; fix wrong `JWT_SECRET_KEY` references |
| **Dependencies** | Parallel with L0-03/L0-05; update again after L0-04/L0-07 |
| **Estimated effort** | S |
| **Risk** | Low |
| **Engineering effort** | S |
| **Revenue impact** | Indirect |
| **Acceptance criteria** | README matches `main` reality; onboarding covers signup→workspace→submit→review→limits; no false “not built” claims for shipped systems |
| **Definition of Done** | Merged docs; Product sign-off |
| **Required tests** | None (link check optional) |
| **Required documentation** | This task *is* the documentation |
| **Required reviewers** | Product |

---

## L0-07a — Draft Review Desk SKU hardening (shortest path)

| Field | Detail |
|-------|--------|
| **ID** | L0-07a |
| **Title** | Ship Private Beta as Draft Review Desk (manual/script draft in; Gate mandatory; no fake AI claims) |
| **Business value** | Fastest honest beta; avoids BYOK crypto schedule |
| **Customer impact** | Agencies review/approve client drafts under spend holds when generation later attaches |
| **Technical impact** | Messaging + UI copy; ensure stub path labeled; Gate never skipped |
| **Dependencies** | L0-01, L0-02, L0-03 |
| **Estimated effort** | S |
| **Risk** | Low (product honesty) / Medium (narrower TAM) |
| **Engineering effort** | S |
| **Revenue impact** | Enables Beta |
| **Acceptance criteria** | No marketing/UI claims of autonomous AI video; `generated_by` visible as draft; Gate required |
| **Definition of Done** | Product copy approved; beta invite email template |
| **Required tests** | Regression: Gate still mandatory |
| **Required documentation** | Beta SKU one-pager |
| **Required reviewers** | Product, Security |

**XOR with L0-07b for Private Beta.** Pick **07a** for shortest path; **07b** if sales require “AI generates.”

---

## L0-07b — One BYOK generation path (alternative to 07a)

| Field | Detail |
|-------|--------|
| **ID** | L0-07b |
| **Title** | Encrypt-at-rest BYOK + one provider executor (e.g. OpenAI script) wired to worker |
| **Business value** | Sell AI-assisted drafting under caps |
| **Customer impact** | Paste key → generate draft → Gate |
| **Technical impact** | Encryption service + key env; credential API; worker executor replaces stub for one stage |
| **Dependencies** | L0-02, L0-03; **crypto before UI** |
| **Estimated effort** | XL |
| **Risk** | Critical (secrets) / High (provider cost) |
| **Engineering effort** | XL |
| **Revenue impact** | Enables Paid (if buyers require AI) |
| **Acceptance criteria** | Secrets never logged; rotate/revoke; spend reserve before provider call; failure doesn’t leak keys; Gate still mandatory |
| **Definition of Done** | Security review passed; staging with test key; runbook for key compromise |
| **Required tests** | Encrypt roundtrip; RLS on credentials; spend hold; failed gen releases reservation; authz |
| **Required documentation** | BYOK setup; threat model note |
| **Required reviewers** | Security (**required**), Migrations, QA, Product |

---

## L0-08 — Production security hygiene for beta host

| Field | Detail |
|-------|--------|
| **ID** | L0-08 |
| **Title** | Lock OpenAPI in non-dev; production CORS; secret scanning already in CI if available |
| **Business value** | Reduce attack surface before outsiders touch staging |
| **Customer impact** | Indirect trust |
| **Technical impact** | Config flags; CORS allowlist |
| **Dependencies** | L0-05 |
| **Estimated effort** | S |
| **Risk** | Medium |
| **Engineering effort** | S |
| **Revenue impact** | Indirect |
| **Acceptance criteria** | `/docs` disabled or authed in staging/prod; CORS only known origins |
| **Definition of Done** | Verified on staging |
| **Required tests** | Config tests for docs disabled |
| **Required documentation** | Env flags |
| **Required reviewers** | Security |

---

### P0 exit criteria (Private Beta)

- [ ] L0-01…L0-06 done  
- [ ] L0-07a **or** L0-07b done  
- [ ] L0-08 done  
- [ ] ≥3 design partners invited on staging  
- [ ] Zero known Gate-bypass or cross-tenant bugs  

---

# P1 — Required before first paying customer

## L1-01 — Stripe Checkout + webhook entitlement

| Field | Detail |
|-------|--------|
| **ID** | L1-01 |
| **Title** | Stripe Checkout for founding Pro; webhook sets workspace paid entitlement |
| **Business value** | First dollar; self-serve or assisted checkout |
| **Customer impact** | Pays → retains access to Desk |
| **Technical impact** | Stripe SDK; checkout session; webhook signature verify; entitlement flag/table |
| **Dependencies** | P0 complete; L0-05 staging |
| **Estimated effort** | L |
| **Risk** | High (money, webhooks) |
| **Engineering effort** | L |
| **Revenue impact** | Enables Paid |
| **Acceptance criteria** | Test-mode checkout succeeds; webhook idempotent; unpaid workspace blocked from create-job (policy TBD); refund/cancel path documented |
| **Definition of Done** | Live-mode ready checklist; Security review of webhook |
| **Required tests** | Signature fail→401; idempotent delivery; entitlement gate |
| **Required documentation** | Pricing link; webhook ops |
| **Required reviewers** | Security, Product, QA, Migrations |

---

## L1-02 — Review notification (email or Slack)

| Field | Detail |
|-------|--------|
| **ID** | L1-02 |
| **Title** | Notify reviewers on `REVIEW_REQUESTED` |
| **Business value** | Agencies won’t poll the queue |
| **Customer impact** | Faster reviews → retention |
| **Technical impact** | Outbox consumer → Resend/SendGrid or Slack webhook |
| **Dependencies** | L0-02 (relay running); L0-01 |
| **Estimated effort** | M |
| **Risk** | Medium |
| **Engineering effort** | M |
| **Revenue impact** | Enables Paid |
| **Acceptance criteria** | New gate sends one notification; no spam on redelivery (idempotent); failure loud in logs |
| **Definition of Done** | Staging proof with real inbox/channel |
| **Required tests** | Consumer unit + idempotency |
| **Required documentation** | How to set webhook/email secrets |
| **Required reviewers** | Security, QA |

---

## L1-03 — Spend ledger UI + API completeness

| Field | Detail |
|-------|--------|
| **ID** | L1-03 |
| **Title** | Customer-visible spend ledger (reserved/committed) in Desk |
| **Business value** | Trust; FinOps narrative vs credit-dark-pattern tools |
| **Customer impact** | Sees $ burned / remaining |
| **Technical impact** | Read APIs + simple web panel |
| **Dependencies** | L0-03 |
| **Estimated effort** | M |
| **Risk** | Low–Medium |
| **Engineering effort** | M |
| **Revenue impact** | Enables Paid |
| **Acceptance criteria** | Admin sees daily/monthly usage vs cap; numbers match DB |
| **Definition of Done** | Shown in customer demo |
| **Required tests** | API accuracy tests |
| **Required documentation** | Short help text in UI |
| **Required reviewers** | Product, QA |

---

## L1-04 — Automated backups + restore drill

| Field | Detail |
|-------|--------|
| **ID** | L1-04 |
| **Title** | Nightly (or continuous) DB backups; documented restore drill |
| **Business value** | Don’t lose a paying tenant |
| **Customer impact** | Continuity |
| **Technical impact** | Host backups / pg_dump cron / managed PITR |
| **Dependencies** | L0-05 |
| **Estimated effort** | M |
| **Risk** | High if skipped |
| **Engineering effort** | M |
| **Revenue impact** | Enables Paid |
| **Acceptance criteria** | Backup exists <24h; restore to scratch DB succeeded once; RPO/RTO written |
| **Definition of Done** | Drill log dated |
| **Required tests** | Manual drill checklist |
| **Required documentation** | `docs/ops/BACKUP_RESTORE.md` |
| **Required reviewers** | Security, Product |

---

## L1-05 — Export approved artifact

| Field | Detail |
|-------|--------|
| **ID** | L1-05 |
| **Title** | Download/export approved script/asset package |
| **Business value** | Completes value loop without full social publish |
| **Customer impact** | Leaves with usable output |
| **Technical impact** | Export endpoint + Desk button |
| **Dependencies** | L0-01 |
| **Estimated effort** | M |
| **Risk** | Low |
| **Engineering effort** | M |
| **Revenue impact** | Enables Paid |
| **Acceptance criteria** | After approve, authorized user downloads artifact; cross-tenant 404 |
| **Definition of Done** | Demo’d with design partner |
| **Required tests** | Authz + isolation |
| **Required documentation** | None beyond UI |
| **Required reviewers** | Security, QA |

---

## L1-06 — Audit admin mutations

| Field | Detail |
|-------|--------|
| **ID** | L1-06 |
| **Title** | `audit()` on workspace create/update and membership invite/role/remove |
| **Business value** | Agency trust; incident forensics |
| **Customer impact** | Indirect |
| **Technical impact** | Wire existing audit helper |
| **Dependencies** | None hard |
| **Estimated effort** | S |
| **Risk** | Low |
| **Engineering effort** | S |
| **Revenue impact** | Indirect |
| **Acceptance criteria** | Each mutation emits audit event with ids (no secrets) |
| **Definition of Done** | Tests assert audit call or log fields |
| **Required tests** | Unit/integration on routes |
| **Required documentation** | None |
| **Required reviewers** | Security |

---

## L1-07 — Entitlement enforcement + paid plan packaging

| Field | Detail |
|-------|--------|
| **ID** | L1-07 |
| **Title** | Enforce paid entitlement on product routes; document founding Pro limits |
| **Business value** | Convert trials; prevent freeload |
| **Customer impact** | Clear paywall |
| **Technical impact** | Guard on content-jobs / decide if needed; trial window optional |
| **Dependencies** | L1-01 |
| **Estimated effort** | M |
| **Risk** | Medium |
| **Engineering effort** | M |
| **Revenue impact** | Enables Paid |
| **Acceptance criteria** | Unpaid cannot create jobs (or limited trial); paid can; messaging clear |
| **Definition of Done** | Product-approved paywall copy |
| **Required tests** | Entitlement matrix |
| **Required documentation** | Pricing limits |
| **Required reviewers** | Product, Security, QA |

---

### P1 exit criteria (first paying customer → path to 10)

- [ ] L1-01…L1-07 done  
- [ ] At least one live-mode payment succeeded  
- [ ] Backups drilled  
- [ ] Founder can board customer without engineering on call  

**First 10 customers:** primarily founder-led sales + support using P0+P1 product; not a separate eng epic. Track as **L1-SALES** (non-eng): outreach, onboarding calls, feedback weekly.

---

# P2 — Post-launch improvements (after revenue begins / toward Public Launch)

## L2-01 — Second provider or higher-quality generation

| Field | Detail |
|-------|--------|
| **ID** | L2-01 |
| **Title** | Expand generation quality / second provider under BYOK |
| **Business value** | Reduce “AI quality” churn |
| **Customer impact** | Better drafts |
| **Technical impact** | Executor plugins; provider abstraction |
| **Dependencies** | L0-07b or upgrade from 07a |
| **Estimated effort** | L |
| **Risk** | Medium |
| **Engineering effort** | L |
| **Revenue impact** | Unlocks Expansion |
| **Acceptance criteria** | Second provider selectable; spend still reserved |
| **Definition of Done** | Used by ≥1 paid workspace |
| **Required tests** | Provider routing + spend |
| **Required documentation** | Provider matrix |
| **Required reviewers** | Security, QA |

---

## L2-02 — Brand kit checks at Gate

| Field | Detail |
|-------|--------|
| **ID** | L2-02 |
| **Title** | Brand voice / forbidden claims checklist on review UI |
| **Business value** | Agency WTP |
| **Customer impact** | Faster, safer approvals |
| **Technical impact** | Brand fields + Gate UI checks |
| **Dependencies** | L0-01 |
| **Estimated effort** | M |
| **Risk** | Low |
| **Engineering effort** | M |
| **Revenue impact** | Unlocks Expansion |
| **Acceptance criteria** | Reviewer sees brand constraints beside draft |
| **Definition of Done** | Used in Agency demo |
| **Required tests** | CRUD + isolation |
| **Required documentation** | Short help |
| **Required reviewers** | Product, QA |

---

## L2-03 — Email-based invites

| Field | Detail |
|-------|--------|
| **ID** | L2-03 |
| **Title** | Invite members by email (not raw user UUID) |
| **Business value** | Lower onboarding friction |
| **Customer impact** | Admins invite reviewers easily |
| **Technical impact** | Invite tokens or Supabase invite integration |
| **Dependencies** | L0-04 |
| **Estimated effort** | L |
| **Risk** | Medium |
| **Engineering effort** | L |
| **Revenue impact** | Indirect |
| **Acceptance criteria** | Email invite → accept → membership with role |
| **Definition of Done** | Staging e2e |
| **Required tests** | Invite expiry; authz |
| **Required documentation** | Invite flow |
| **Required reviewers** | Security, QA |

---

## L2-04 — Metrics + basic alerting

| Field | Detail |
|-------|--------|
| **ID** | L2-04 |
| **Title** | Expose `/metrics` or equivalent; alert on DLQ growth / relay lag |
| **Business value** | See fires before customers do |
| **Customer impact** | Reliability |
| **Technical impact** | Wire `orchestration/metrics.py`; alert channel |
| **Dependencies** | L0-02, L0-05 |
| **Estimated effort** | M |
| **Risk** | Low |
| **Engineering effort** | M |
| **Revenue impact** | Indirect |
| **Acceptance criteria** | Queue depth + DLQ count visible; one alert fires in drill |
| **Definition of Done** | On-call note |
| **Required tests** | Metrics smoke |
| **Required documentation** | Alert meanings |
| **Required reviewers** | Security, Product |

---

## L2-05 — DLQ admin API

| Field | Detail |
|-------|--------|
| **ID** | L2-05 |
| **Title** | List/inspect/replay dead-letter jobs for admins |
| **Business value** | Recover stuck customer work |
| **Customer impact** | Support speed |
| **Technical impact** | Admin routes + authz |
| **Dependencies** | L0-02 |
| **Estimated effort** | M |
| **Risk** | Medium (replay safety) |
| **Engineering effort** | M |
| **Revenue impact** | Indirect |
| **Acceptance criteria** | Admin lists DLQ; replay is idempotent-safe; non-admin 403 |
| **Definition of Done** | Used in a staging incident drill |
| **Required tests** | Authz + replay |
| **Required documentation** | Replay playbook |
| **Required reviewers** | Security, QA |

---

## L2-06 — One scheduler/export integration (e.g. Buffer or Drive)

| Field | Detail |
|-------|--------|
| **ID** | L2-06 |
| **Title** | Post-approve push to one external destination |
| **Business value** | Completes “export to where we work” |
| **Customer impact** | Less copy-paste |
| **Technical impact** | OAuth or API key integration |
| **Dependencies** | L1-05 |
| **Estimated effort** | L |
| **Risk** | Medium |
| **Engineering effort** | L |
| **Revenue impact** | Unlocks Expansion |
| **Acceptance criteria** | Approve → appears in destination; failures visible |
| **Definition of Done** | One paid customer uses it |
| **Required tests** | Mock provider + authz |
| **Required documentation** | Connect guide |
| **Required reviewers** | Security, QA |

---

## L2-07 — Rate limits + abuse controls

| Field | Detail |
|-------|--------|
| **ID** | L2-07 |
| **Title** | Rate limit auth and worker endpoints |
| **Business value** | Protect staging/prod from credential leak spam |
| **Customer impact** | Stability |
| **Technical impact** | Middleware / gateway limits |
| **Dependencies** | L0-05 |
| **Estimated effort** | M |
| **Risk** | Low |
| **Engineering effort** | M |
| **Revenue impact** | Indirect |
| **Acceptance criteria** | Excess requests 429; legitimate beta traffic unaffected |
| **Definition of Done** | Config documented |
| **Required tests** | Limit unit tests |
| **Required documentation** | Limits table |
| **Required reviewers** | Security |

---

## L2-08 — Self-serve onboarding polish (Public Launch bar)

| Field | Detail |
|-------|--------|
| **ID** | L2-08 |
| **Title** | Guided first-run checklist; empty states; marketing site CTA → signup |
| **Business value** | Public launch without founder for every signup |
| **Customer impact** | Time-to-value |
| **Technical impact** | Web UX |
| **Dependencies** | P0+P1, L0-04, L1-01 |
| **Estimated effort** | L |
| **Risk** | Low |
| **Engineering effort** | L |
| **Revenue impact** | Unlocks Expansion |
| **Acceptance criteria** | New user reaches first Gate item without docs call |
| **Definition of Done** | Activation metric defined and measured |
| **Required tests** | Critical-path e2e |
| **Required documentation** | Public help center stub |
| **Required reviewers** | Product, QA |

---

### P2 exit criteria (Public Launch posture)

- [ ] L2-04, L2-07, L2-08 done  
- [ ] Either solid BYOK generation (L0-07b/L2-01) or clear product positioning that doesn’t require it  
- [ ] Activation measured; support load understood  
- [ ] Backups + alerts operational  

---

# P3 — Future enhancements

| ID | Title | Effort | Risk | Revenue impact | Notes |
|----|-------|--------|------|----------------|-------|
| L3-01 | Full social publish network (multi-platform) | XL | High | Expansion | Defer; use L2-06 first |
| L3-02 | Analytics productization | L | Medium | Expansion | Schema exists; not launch-critical |
| L3-03 | SSO / SCIM | L | Medium | Expansion | Enterprise only |
| L3-04 | SOC2 program | XL | Medium | Expansion | Process, not a feature sprint |
| L3-05 | White-label | XL | High | Expansion | After Agency retention |
| L3-06 | n8n template pack / self-host | L | Medium | Indirect | Distraction pre-PMF |
| L3-07 | Autonomous agents / autopublish | XL | Critical | Negative if early | **Do not build** until Gate+spend proven with paid retention |
| L3-08 | Recurring job type producer | M | Medium | Indirect | Currently `NotImplementedError` by design |
| L3-09 | Close Cursor skill/agent PR sprawl | S | Low | None | Process hygiene; not launch |

Each P3 item when picked up must still define acceptance criteria, tests, docs, and reviewers in its Work Package — do not start without one.

---

## Critical Path

```
L0-01 Review Desk
   → L0-02 Runtime wiring
        → L0-04 Login ──────────────┐
        → L0-03 Spend ──────────────┤
        → L0-05 Staging ────────────┼→ L0-07a (or L0-07b) → L0-08
        → L0-06 Docs ───────────────┘
                                      ↓
                         PRIVATE BETA GATE
                                      ↓
                         L1-01 Stripe (serial)
                              ↓
              ┌───────────────┼───────────────┐
           L1-02           L1-03           L1-04
           notify          ledger          backups
              └───────────────┼───────────────┘
                         L1-05 export · L1-06 audit · L1-07 entitlement
                                      ↓
                         FIRST PAYING CUSTOMER
                                      ↓
                         Founder sales → 10 customers
                                      ↓
                         L2-04 · L2-07 · L2-08 (+ generation depth)
                                      ↓
                         PUBLIC LAUNCH POSTURE
```

**Critical path length (shortest):** L0-01 → L0-02 → (L0-03 ∥ L0-05) → L0-04 → L0-07a → L0-08 → L1-01 → (L1-02 ∥ L1-04) → L1-07.

---

## Expected timeline

Assumes **one focused founder-engineer**, no major interruptions, **L0-07a** (Draft Desk) not L0-07b, and PR #23 accelerates L0-01.

| Milestone | Calendar (realistic) | Cumulative effort |
|-----------|----------------------|-------------------|
| **Private Beta** | **3–5 weeks** | P0 ≈ 3–4 eng-weeks compressed with parallelization |
| **First paying customer** | **+1–2 weeks** after beta | P1 ≈ 1.5–2.5 eng-weeks + sales cycle |
| **First 10 paying customers** | **+4–8 weeks** after first paid | Mostly sales/CS; eng bugfix only |
| **Public Launch posture** | **+4–8 weeks** after ~10 paid or clear retention | P2 critical subset |

If **L0-07b (BYOK)** is required for beta: add **+2–4 weeks** before Private Beta.

---

## Task scoreboard (quick reference)

| ID | Priority | Effort | Risk | Revenue impact |
|----|----------|--------|------|----------------|
| L0-01 | P0 | M–L | Medium | Enables Beta |
| L0-02 | P0 | M | High | Enables Beta |
| L0-03 | P0 | M | High | Enables Beta |
| L0-04 | P0 | M | Medium | Enables Beta |
| L0-05 | P0 | L | Medium | Enables Beta |
| L0-06 | P0 | S | Low | Indirect |
| L0-07a | P0 | S | Low–Med | Enables Beta |
| L0-07b | P0 alt | XL | Critical | Enables Paid |
| L0-08 | P0 | S | Medium | Indirect |
| L1-01 | P1 | L | High | Enables Paid |
| L1-02 | P1 | M | Medium | Enables Paid |
| L1-03 | P1 | M | Low–Med | Enables Paid |
| L1-04 | P1 | M | High if skip | Enables Paid |
| L1-05 | P1 | M | Low | Enables Paid |
| L1-06 | P1 | S | Low | Indirect |
| L1-07 | P1 | M | Medium | Enables Paid |
| L2-01…L2-08 | P2 | M–L | Low–Med | Expansion / Indirect |
| L3-* | P3 | varies | varies | Future / avoid early |

---

## Final answer

### If we execute this plan without major interruptions, what is the shortest realistic path to launch?

**Private Beta in about 3–5 weeks** by:

1. Landing Review Desk on `main` (L0-01)  
2. Wiring scheduler + relay immediately after (L0-02)  
3. Parallelizing spend, staging, and docs (L0-03/05/06)  
4. Adding real login (L0-04)  
5. Choosing **Draft Review Desk (L0-07a)** instead of full BYOK  
6. Hardening host security (L0-08)

**First paying customer ~1–2 weeks after beta** once Stripe + entitlement + backups + notifications exist (L1-01/02/04/07).

**Public launch posture ~2–4 months from now** (not from “milestone complete”), after paid retention signal and P2 self-serve/ops hardening — **not** after building agents, n8n, or analytics.

**Do not lengthen the critical path** with skill PRs, connector races, or autonomy features. Those are P3 and actively compete with launch.

---

*This plan is the engineering backlog derived from the Beta Readiness Audit. Execute Work Packages in order; do not open a new strategy doc to start work.*
