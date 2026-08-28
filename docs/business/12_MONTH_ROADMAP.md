# 12-Month Roadmap — Content Orchestrator

**Horizon:** Four quarters from foundation completion.  
**Constraints:** Bootstrapped founder; low infra cost; **no** product-feature implementation in the business-foundation task itself — this roadmap **sequences** future work.  
**Invariants every quarter:** Human Review Gate, spend controls, multi-tenant isolation (FORCE RLS).

**Stance:** Reliability and monetization before horizontal expansion. Brutal prioritization.

---

## North-star for the year

Ship a **commercially usable** content production control plane for agencies and in-house content ops: draft → **mandatory review** → export, with hard spend caps and workspace isolation — and **charge for it**.

---

## Q1 — Foundation to first paid value

**Theme:** Make the core loop trustworthy and chargeable.

### Product / engineering (business outcomes)
- Harden auth, workspaces, RLS, audit basics
- Job pipeline: create → generate → **Review Gate** → export (minimum viable providers)
- Spend caps + ledger; block overages cleanly
- Billing: Stripe for Starter/Pro (Agency manual OK)
- Observability for job failures and cost anomalies

### Business
- Close 5–15 design partners (ICP: agencies / content ops)
- Final public pricing page aligned to `PRICING_STRATEGY.md`
- Position messaging: control, not autonomy
- Instrument activation (first artifact in Review)

### Explicit non-goals
- Large connector catalog
- Mobile apps
- Autonomous publish modes
- Heavy paid acquisition

### Exit criteria
- Paying customers exist (even if few)
- Zero known Gate-bypass or cross-tenant paths in production
- Activation measurable

---

## Q2 — Activation, templates, agency readiness

**Theme:** Time-to-value and multi-client reality.

### Product / engineering
- Onboarding checklist with forced spend cap
- 3–5 opinionated templates (e.g. weekly short-form pipeline)
- Reviewer UX: assign, approve, reject with reasons
- Second workspace flows for Agency path
- BYOK key handling hardened
- Usage dashboard (software + generation cost visibility)

### Business
- Case studies / process write-ups (even anonymized)
- SEO pillar content + YouTube demo series starts
- Founder-led outbound to agencies
- Referral program **design** (launch only if retention signal exists)

### Explicit non-goals
- Marketplace of community nodes
- White-label
- TikTok-led growth bets

### Exit criteria
- Activation rate improving vs Q1 baseline
- At least one multi-workspace paying account
- Support load understood per plan

---

## Q3 — Expansion mechanics & selective integrations

**Theme:** Expand revenue inside accounts; reduce Zap/Make jealousy on *critical* paths only.

### Product / engineering
- Seats/roles: operator vs reviewer vs admin
- Automations: schedule + retry policies under spend caps
- 2–4 **high-ROI integrations** only (e.g. storage destination, Slack review notify, one scheduler) — chosen from customer interviews
- Audit export for Agency
- Performance/cost pass on workers (keep infra lean)

### Business
- Agency plan packaging finalized (workspaces, roles)
- Partnership conversations (consultants, editors)
- Affiliate pilot with strict messaging rules
- First pricing experiment (e.g. annual discount 15–20%) carefully

### Explicit non-goals
- Matching Zapier connector counts
- Building Relevance-class agent OS
- Self-host offering

### Exit criteria
- Expansion MRR visible (workspaces/seats)
- Integration choices validated by usage, not roadmap fantasy
- Gross margin tracked monthly

---

## Q4 — Retention, enterprise door, operational maturity

**Theme:** Become boringly reliable; open Enterprise without drowning.

### Product / engineering
- SSO path for Enterprise (or partner via IdP — choose lowest-ops approach)
- Stronger compliance artifacts: retention policies, audit trails, DPA template
- Chaos/failure playbooks for provider outages
- Scale testing for multi-tenant noisy neighbors
- Harden spend anomaly alerts

### Business
- 1–3 Enterprise conversations (custom) only if inbound/ICP fit
- Formalize customer success for Agency (lightweight QBRs)
- Launch referral if criteria met
- Reassess paid ads with real CAC data — default still organic-heavy

### Explicit non-goals
- Geographic expansion theater
- Rebrand for hype cycles
- Feature freezes broken for “AI agent autonomy” demands

### Exit criteria
- Documented churn reasons with countermeasures
- NRR measurable
- Runbooks for incidents exist and were practiced

---

## Cross-quarter capacity allocation (assumption)

| Bucket | ~% effort |
|--------|-----------|
| Reliability, Gate, spend, tenancy | 35% |
| Core UX / activation | 25% |
| Monetization & billing | 10% |
| Selective integrations | 15% |
| GTM enablement (docs, demos) | 10% |
| Experiments | 5% |

---

## Hiring (bootstrapped realism)

**Year one default:** founder + contractors for overflow (frontend polish, video editing for GTM).  
**First hire trigger (assumption):** sustained MRR covering hire + 6 months buffer, and support/engineering queue consistently blocked. Prefer senior generalist or part-time specialist over junior headcount.

---

## Dependencies & assumptions

- Provider APIs (video/LLM) remain buyable; prices may rise — BYOK + caps mitigate
- Stripe and Postgres-centric architecture remain cost-effective
- Design partners give weekly feedback
- No major compliance regime blocks launch in primary market (confirm legal)

---

## What would cause a roadmap reset

1. Cross-tenant or Gate-bypass incident → freeze features, fix trust  
2. Unit economics break on meterized generation → force BYOK-only  
3. ICP wrong (only hobbyists sign up) → reposition messaging and pricing; do not “add autonomy” to chase them  

---

*This roadmap is a planning instrument, not a public promise. Slip features before slipping invariants.*
