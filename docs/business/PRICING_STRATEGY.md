# Pricing Strategy

**Principle:** Price for **governance value** + **usage headroom**, not for hype seats.  
**Constraint:** Bootstrapped — protect gross margin when AI providers are the COGS spike.  
**Assumption date:** 2026-07

---

## Pricing model (recommended)

**Hybrid:**

1. **Platform subscription** (workspace seats + orchestration limits)  
2. **AI spend passthrough** (customer’s provider keys **or** metered wallet with markup)

**Hard rule:** Platform fee must remain profitable even if AI usage is zero that month. AI cost is **never** fully absorbed into a flat “unlimited generations” promise.

---

## Tiers

### Starter — $49/mo (annual $39/mo)

| | |
|--|--|
| **Who** | Solo / tiny studio validating the product |
| **Includes** | 1 workspace, 2 seats (admin + reviewer), capped monthly runs, Review Gate required, spend caps enabled |
| **Limits (illustrative)** | e.g. 50 pipeline runs/mo, 1 active workflow definition, community support |
| **Why it exists** | Low-friction learning; funnel into Pro; not the profit engine |
| **Expected margin** | **70–85%** on subscription if BYOK; thin if we subsidize models — **don’t subsidize** |

**Founder note:** Cap support time. If Starter consumes >20% of founder hours, raise price or cut features.

---

### Pro — $199/mo (annual $159/mo)

| | |
|--|--|
| **Who** | In-house content leads; small agencies (few clients) |
| **Includes** | Up to 5 workspaces **or** 1 workspace + higher run limits (pick one packaging — recommend **3 workspaces**), 5 seats, audit export, priority email |
| **Limits** | e.g. 500 runs/mo, multiple workflows, provider budget dashboards |
| **Why it exists** | Primary SMB revenue; matches ICP B and small A |
| **Expected margin** | **75–90%** on platform fee (BYOK); overall contribution depends on optional wallet markup **10–20%** if offered |

---

### Agency — $499/mo (annual $399/mo)

| | |
|--|--|
| **Who** | Agencies with multi-client isolation needs |
| **Includes** | 15+ workspaces, 15 seats, roles (admin/editor/reviewer), client-ready audit packs, higher concurrency, SLA-ish email (best-effort Year 1) |
| **Why it exists** | Captures willingness-to-pay for **tenancy + review + spend** — our strongest wedge |
| **Expected margin** | **80–90%** on platform; highest LTV segment if churn <3%/mo |

Optional add-on: **+$99/mo per +10 workspaces**.

---

### Enterprise — Custom (floor ~$1,500/mo)

| | |
|--|--|
| **Who** | Procurement-heavy orgs |
| **Includes** | SSO/SAML (when built), DPA, security questionnaire support, custom caps, dedicated onboarding (paid), uptime targets |
| **Why it exists** | Park inbound enterprise; **do not** custom-build for free |
| **Expected margin** | **60–80%** after support load; only take deals with clear scope |

**Year-1 rule:** No Enterprise custom engineering until Pro+Agency MRR covers founder salary buffer.

---

## Packaging principles

1. **Review Gate cannot be disabled** on any paid tier (product integrity).  
2. **Spend controls cannot be disabled** — only limits configured.  
3. Seats include at least one **reviewer** capability.  
4. Overage: soft block + upsell, not silent continue.  
5. Annual discount ≤20% to protect cash.

---

## Unit economics (illustrative, not a forecast)

| | Starter | Pro | Agency |
|--|---------|-----|--------|
| Price | $49 | $199 | $499 |
| Est. infra COGS/customer | $3–8 | $8–20 | $20–50 |
| Support COGS/customer | High % | Medium | Medium–high |
| Target gross margin (platform) | ≥70% | ≥75% | ≥80% |

**AI generations:** Customer BYOK preferred early (near **100%** pass-through). If wallet: list price = provider cost × **1.15–1.25**, with hard caps.

---

## Competitive price context (2026 public ranges; approximate)

- Make/Zapier/n8n: often **$9–$60/mo** entry for **horizontal** automation.  
- Lindy/Gumloop/Relevance-class AI agent tools: often **$20–$50+** entry, usage-sensitive.  

We price **above generic automation** because we sell **governed content production**, closer to agency ops software than toy zaps. If we cannot explain that in one sentence, price will feel expensive — fix positioning, don’t race to $9.

---

## Assumptions

- No free forever tier with expensive AI included.  
- Free trial: **14 days Pro limits** or waitlist until activation works.  
- Prices in USD; VAT/sales tax handled later via Stripe Tax.  
- Margins are **targets**, not guarantees — revisit monthly with real COGS.
