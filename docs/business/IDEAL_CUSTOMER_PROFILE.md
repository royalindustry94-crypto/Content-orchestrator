# Ideal Customer Profile (ICP)

**Assumption date:** 2026-07 · Bootstrapped GTM

---

## Primary ICP (buy now / design partners)

### Persona A — Agency Owner / Head of Content Ops

| Attribute | Detail |
|-----------|--------|
| Company | Content / creative / social agency, 3–30 FTEs |
| Clients | 5–40 brand clients |
| Role | Owner, COO, Head of Production |
| Technical | Low–medium; uses freelancers + tools |
| Budget owner | Yes (or strongly influences) |

**Pain points**

- Client AI costs unpredictable; hard to bill back accurately.  
- Junior staff “just run the agent” and burn budget / publish drafts.  
- Tools not built for multi-client isolation; shared Notion/Drive/Make scenarios.  
- Approvals live in Slack threads — no durable audit for clients.  
- Fear of one bad AI script going live.

**Budget (realistic)**

- Tooling budget: **$200–$2,000/mo** across stack.  
- Willing to pay **$149–$499/mo** for a control plane if it prevents one blowup/month.  
- Enterprise retainers exist but procurement is slow — Year 2+.

**Buying triggers**

- AI invoice surprise (>2× expected).  
- Client asks for audit / “who approved this?”.  
- Scaling from 5 → 15 clients and Make scenarios collapse.  
- Hiring first dedicated reviewer / QA editor.

**Objections**

| Objection | Response |
|-----------|----------|
| “We already have Make/n8n” | Keep them for glue; we own **content stages, review, spend**. |
| “Too early / UI incomplete” | Design-partner pricing; ship activation milestones first. |
| “Can’t migrate pipelines” | Start with **one client workspace** parallel run. |
| “AI should be fully automatic” | That’s the risk; Gate is the product. Walk away if they insist on bypass. |

---

### Persona B — In-house Content Lead (SMB)

| Attribute | Detail |
|-----------|--------|
| Company | DTC, SaaS, media, education — 20–200 employees |
| Role | Content Lead, Marketing Ops, Brand Studio lead |
| Volume | 4–30 pieces/week (video-heavy preferred) |

**Pain points**

- Marketing wants speed; brand/legal wants control.  
- Shared OpenAI/Anthropic keys with no per-campaign caps.  
- Freelancers + AI tools with no workspace boundaries.

**Budget:** $99–$399/mo software; sometimes marketing ops budget.

**Triggers:** First AI content program; compliance scare; agency consolidation in-house.

**Objections:** “Need YouTube/TikTok native scheduler first” → partner/integrations later; we orchestrate, don’t replace every social suite on day one.

---

## Secondary ICP

### Persona C — High-volume Solo / Small Studio

- 1–3 people, high output.  
- Buys **Starter** if Time-to-first-reviewed-video is <1 day.  
- Churn risk high if onboarding is heavy — keep Starter thin.

### Persona D — Enterprise Innovation / Ops

- Needs SSO, DPA, SOC2 narrative, vendor review.  
- **Do not prioritize** until Pro/Agency unit economics work.  
- Enterprise tier exists to park demand, not to chase logos early.

---

## Anti-ICP (do not sell)

- Teams wanting **fully autonomous publish with no human review**.  
- Pure iPaaS buyers (“connect 500 SaaS apps”).  
- Speculative “AI employee replaces my team” buyers with no process.  
- Anyone requiring Redis/Kafka/exotic multi-region SoT in v1.  
- Customers who refuse usage-based provider passthrough (we must stay margin-safe).

---

## ICP scoring (simple)

Score 0–2 each: multi-workspace need, AI content volume, review culture, budget owner access, willingness to passthrough AI cost.

- **≥8:** design partner / outbound priority  
- **5–7:** nurture / content marketing  
- **<5:** polite no

---

## Assumptions

- Early revenue concentrates in Persona A.  
- Average Agency deal Year 1: **$199–$399/mo** (Pro/Agency).  
- Sales motion: founder-led, not a sales team.
