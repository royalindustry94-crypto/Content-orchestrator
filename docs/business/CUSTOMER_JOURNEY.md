# Customer Journey — Content Orchestrator

**Purpose:** Map the path from stranger to retained referrer.  
**Product invariants at every stage:** Human Review Gate, spend controls, workspace isolation.

---

## Journey overview

```
Visitor → Signup → Onboarding → First video → First automation
    → Paid plan → Expansion → Retention → Referral
```

Each stage has a **job**, **success metric**, **failure mode**, and **founder action**.

---

## 1. Visitor

**Job:** Understand in <60 seconds: this is a **content control plane**, not another AI generator toy.

**Experience:**
- Hero: brand + one control-centric promise + one CTA
- Proof: Gate + spend caps (screenshot/demo), not fake stats
- Anti-message: no “fully autonomous content empire”

**Success:** CTA click / demo view / docs visit  
**Failure:** Bounce because messaging sounds like every AI SaaS  
**Action:** SEO/YouTube entry pages → same promise; comparison pages vs Zapier/Make for content stacks

---

## 2. Signup

**Job:** Create account with minimal friction; set expectations on Gate and spend.

**Experience:**
- Email/OAuth signup
- Immediate workspace creation
- Clear notice: **nothing publishes without review**; **spend caps apply from day one**
- Optional: invite teammate later (don’t force)

**Success:** Verified account + workspace created  
**Failure:** Abandoned signup; spam accounts  
**Action:** Bot friction only as needed; email verification; default low spend ceiling

**Assumption:** Free trial or free Starter-limited tier; prefer time-boxed trial with hard caps over unlimited free.

---

## 3. Onboarding

**Job:** Configure enough context to produce one real draft safely.

**Steps (lean):**
1. Name workspace / brand
2. Connect or paste brand basics (voice, forbidden claims, logo later)
3. Set spend cap (forced choice — cannot skip)
4. Connect generation provider keys if BYOK, or use platform-metered credits if offered
5. Explain Review Gate in one interactive screen

**Success:** Onboarding checklist ≥80% complete; spend cap set  
**Failure:** Empty workspace syndrome; user never returns  
**Action:** Time-to-value < 30 minutes for motivated agency user (target assumption)

**Do not:** 20-step tours, empty dashboards with six upsell cards.

---

## 4. First video (activation candidate)

**Job:** Generate first draft asset under spend control; land in Review Gate.

**Experience:**
- Guided “create first job” — topic → script/asset draft → review queue
- Cost estimate **before** run when possible
- Cap enforcement visible if near limit
- Output appears in **Review**, not Publish

**Success:** First draft in review queue  
**Failure:** Generation errors, confusing cost, user skips because “too many steps”  
**Action:** Excellent empty states; sample brand kit; deterministic error messages

**Activation definition (recommended):** First item reaches Review Gate with a generated artifact.  
**Stronger activation:** First **approved** export / publish action.

---

## 5. First automation

**Job:** Prove repeatability — not one-off magic.

**Experience:**
- Save pipeline as reusable automation (trigger → generate → **always** Gate → export)
- Schedule or manual re-run
- Same spend + review rules apply

**Success:** Second job completes via saved automation  
**Failure:** User treats product as one-shot generator and churns  
**Action:** Prompt after first approve: “Make this repeatable”; templates for common agency flows

---

## 6. Paid plan

**Job:** Convert when value is felt (control + time saved), not when trial nagging peaks.

**Triggers:**
- Hit workspace/seat/automation limits
- Need higher spend ceiling with accountability
- Need client isolation (second workspace)
- Need audit / roles

**Experience:**
- Pricing page mirrors `PRICING_STRATEGY.md`
- Upgrade path: Starter → Pro → Agency clear
- Billing: Stripe; invoices for Agency+

**Success:** First paid invoice  
**Failure:** Trial ends with no activation; sticker shock vs Zapier free tier  
**Action:** Convert only activated users; extend trial for activated-but-unpaid with sales assist for Agency

**Assumption:** Self-serve for Starter/Pro; founder-assisted for Agency early.

---

## 7. Expansion

**Job:** Grow revenue inside account without destroying margins.

**Levers:**
- More workspaces (clients/brands)
- More seats (reviewers, operators)
- Higher automation volume
- Add-ons: SSO, audit exports, priority support (Enterprise)

**Success:** Expansion MRR; NRR > 100% over time (long-term target)  
**Failure:** Seat packing abuse; support cost spikes  
**Action:** Usage dashboards; soft nudges when approaching limits; Agency plan for multi-client

---

## 8. Retention

**Job:** Become the default content ops system of record for drafts → approvals → exports.

**Drivers:**
- Reliability of workers and providers
- Gate UX that reviewers actually use
- Spend predictability
- No data-loss / no cross-tenant incidents (**existential**)

**Health signals:** WAU of operators + reviewers; jobs/week; approve latency; support tickets

**Churn reasons (expected):**
- Not enough integrations
- Generation quality blame (even if BYOK)
- Team too small to need orchestration
- Price vs perceived usage

**Action:** Quarterly business reviews for Agency; kill-switch communication for provider outages; changelogs that matter

---

## 9. Referral

**Job:** Turn operators into distribution.

**When:** After retention evidence (e.g. 60+ days paid, ≥1 teammate active, NPS/proxy positive).

**Experience:**
- In-app referral: credit on both sides after referee pays
- Agency: higher reward or featured case study path
- Ask for intro to peer agencies (founder-led)

**Success:** Referral-originated trials with higher activation  
**Failure:** Launching referral before product love → refund abuse  
**Action:** Gate referral eligibility on activation + paid status

---

## Stage metrics (summary)

| Stage | Primary metric |
|-------|----------------|
| Visitor | Landing conversion rate |
| Signup | Signup completion rate |
| Onboarding | Checklist completion; spend cap set rate |
| First video | % with draft in Review |
| First automation | % with second automated job |
| Paid | Trial→paid; activation→paid |
| Expansion | Expansion MRR; workspaces/account |
| Retention | Logo churn; NRR; WAU |
| Referral | Referral rate; referred CAC |

---

## Journey anti-patterns

- Allowing publish without Gate “just for onboarding”
- Raising spend caps silently
- Forcing Enterprise sales motion on $49 buyers
- Measuring vanity DAU of curiosity clicks over review completions
- Promising timelines the worker stack cannot meet

---

## Founder intervention points (first year)

1. Personal onboarding calls for first 20 Agency trials  
2. Watch review queue friction weekly  
3. Kill channels that bring autonomy-seekers who churn in week 1  
4. Document every blocked publish that saved a customer — sales gold  

---

*Journey assumes multi-tenant SaaS with mandatory Gate and spend controls remain non-negotiable.*
