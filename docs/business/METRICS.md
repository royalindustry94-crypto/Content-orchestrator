# Metrics & KPIs — Content Orchestrator

**Purpose:** Define the numbers that matter for a bootstrapped, multi-tenant content orchestration SaaS.  
**Stance:** Profitability and unit economics over vanity. Cite assumptions. Do not treat early targets as forecasts.

---

## 1. Principles

1. **Measure activation before spend** — paid ads without activation is arson.
2. **Separate software margin from AI usage** — BYOK vs platform-metered must not be conflated.
3. **Tenant safety is a KPI category** — zero-tolerance incidents outweigh growth spikes.
4. **Targets below are directional Year-1/Year-2 assumptions**, not commitments.

---

## 2. Core financial KPIs

### MRR (Monthly Recurring Revenue)

**Definition:** Sum of active subscription fees recognized that month (exclude one-time services unless separately labeled).

**Segments:** Starter / Pro / Agency / Enterprise.

**Why it matters:** Primary heartbeat for bootstrapped runway.

**Assumption — early healthy shape:** Heavy Pro/Agency mix beats a mass of low-ACV Starter accounts that consume support.

### ARR (Annual Recurring Revenue)

**Definition:** MRR × 12 (or contracted annualized for Enterprise).

**Use:** Board-style snapshot; planning hiring (hire late).

### Gross Margin

**Definition:** `(Revenue − COGS) / Revenue`.

**COGS includes (typical):**
- Hosting (API, workers, DB, object storage, egress)
- Observability, email, auth vendors
- Payment fees
- **Platform-metered AI/video costs** (if any)
- Support tooling proportional to delivery (optional allocation)

**COGS excludes:** Founder salary (often OpEx), R&D salaries (OpEx), ads (OpEx).

**Targets (assumptions):**
- **Software-only (BYOK-heavy):** aim **≥80%** gross margin at modest scale
- **With platform-metered generation:** **50–70%** depending on markup discipline — treat usage as pass-through-plus, not loss leader

**Rule:** Never discount usage below provider cost + overhead + risk buffer.

### CAC (Customer Acquisition Cost)

**Definition:** Sales & marketing spend attributable to new customers / new customers acquired in period.

**Bootstrapped note:** Include paid tools and contractor content; **founder time** should be tracked in hours even if not dollarized at first.

**Payback target (assumption):** < 6 months for Pro/Agency blended; Starter may be longer — don’t over-invest paid CAC there.

### LTV (Lifetime Value)

**Definition (simple):** `ARPU × gross margin % × (1 / logo churn monthly)`  
Or cohort-based revenue until churn.

**Use with CAC:** LTV:CAC ≥ 3:1 is a **late** aspiration; early on, prioritize payback and retention quality over the ratio slogan.

**Assumption:** Agency LTV should dominate; design GTM accordingly.

---

## 3. Product & growth KPIs

### Activation Rate

**Primary definition:** % of new workspaces that place **at least one generated artifact into Review Gate** within 7 days of signup.

**Secondary (stronger):** % that **approve/export** at least once within 14 days.

**Why:** Predicts paid conversion better than signup count.

**Directional target (assumption):** 25–40% primary activation in early cohorts after onboarding is tuned; below 15% = onboarding emergency.

### Time-to-Value (TTV)

**Definition:** Median minutes from signup to first artifact in Review Gate.

**Target (assumption):** < 30 minutes for guided path; < 24 hours wall-clock for real-world busy users.

### Churn

| Type | Definition | Notes |
|------|------------|-------|
| Logo churn | Lost paying accounts / starting paying accounts | Monthly |
| Revenue churn | Lost MRR from churn & contraction / starting MRR | More important |
| Net revenue retention (NRR) | (Starting MRR + expand − contract − churn) / starting MRR | Long-term north star |

**Directional early targets (assumptions, SMB SaaS realism):**
- Monthly logo churn Starter: can be **5–8%+** — don’t panic alone; fix activation mix
- Pro/Agency monthly logo churn: aim **< 3–4%** once product stabilizes
- NRR: aim **> 100%** only after expansion motions exist (workspaces/seats)

### WAU / DAU

**WAU:** Weekly active users (operators + reviewers who take a meaningful action: create job, review, configure spend, run automation).

**DAU:** Daily active — **secondary** for this product; content ops is not a social feed.

**Ratio DAU/WAU:** Context only; low DAU can be healthy for weekly batch agencies.

### Cost per generated video

**Definition:** Fully loaded cost to produce one generated video artifact.

**Include:** Provider fees (if platform-paid), worker compute, storage, retries, failed runs allocated.

**BYOK accounts:** Track **customer-incurred** cost separately from **platform COGS** (platform COGS near $0 for tokens; still track compute/storage).

**Use:** Price usage add-ons; detect retry storms; protect margins.

**Guardrail:** Review Gate does not reduce generation cost — it reduces **reputation cost**. Still meter generations tightly.

---

## 4. Operational & trust KPIs (non-negotiable)

| KPI | Definition | Target mindset |
|-----|------------|----------------|
| Cross-tenant incidents | Any workspace data leak / wrong-tenant read | **Zero** |
| Gate bypass incidents | Publish without required review | **Zero** |
| Spend overcap incidents | Charges beyond configured caps due to our bug | **Zero** / immediate severity-1 |
| Job success rate | Successful terminal jobs / jobs started | Improve continuously; segment by provider |
| p95 job latency | Time to review-ready artifact | Publish honestly; don’t overpromise |
| Support tickets / paying account | Volume & severity | Watch after Agency growth |

---

## 5. Funnel KPIs

| Stage | KPI |
|-------|-----|
| Visitor → Signup | Landing conversion |
| Signup → Activated | Activation rate |
| Activated → Paid | Activation-to-paid % |
| Paid → Expanded | % accounts adding workspace/seat within 90 days |
| Paid → Referrer | % issuing successful referral |

**Assumption:** Optimize in that order. Never buy traffic into a broken activation step.

---

## 6. Dashboard cadence

| Cadence | Review |
|---------|--------|
| Daily | Incidents, job failure spikes, spend anomalies |
| Weekly | Signups, activation, trial status, MRR movement |
| Monthly | Churn cohorts, CAC, gross margin, cost per video, channel ROI |
| Quarterly | NRR, roadmap fit, pricing experiments, ICP refinement |

---

## 7. Vanity metrics to de-emphasize

- Raw signup count without activation  
- Social follower counts  
- “Videos generated” without review/export  
- DAU theater  
- Waitlist size as success  

---

## 8. Instrumentation requirements (product implications — not a build task here)

To make these KPIs real, the product must eventually emit:
- Workspace lifecycle events
- Spend ledger entries
- Review Gate state transitions
- Job cost attributions
- Subscription state from Stripe

**Assumption:** Until instrumentation exists, track manually in a spreadsheet for first customers — better imperfect truth than fake precision.

---

## 9. Example “healthy enough” early snapshot (illustrative, not a forecast)

> **Not a projection.** Example shape for a careful bootstrap after meaningful PMF work:

- 30–80 paying logos mixed Starter/Pro with a few Agency  
- MRR in low-to-mid five figures only after sustained execution (many never reach this in year one — plan runway accordingly)  
- Gross margin high on BYOK  
- Activation improving quarter over quarter  
- Zero tenant-isolation incidents  

If year-one reality is slower, that is normal for vertical B2B with governance positioning.

---

*Revisit definitions when packaging or billing model changes. Keep Gate/spend incidents as exec-level KPIs forever.*
