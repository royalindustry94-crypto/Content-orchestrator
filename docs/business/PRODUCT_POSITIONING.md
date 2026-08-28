# Product Positioning — Content Orchestrator

**Status:** Business foundation (not a product launch claim)  
**Audience:** Founder, advisors, early GTM  
**Assumption date:** 2026-07

---

## One-liner

**Content Orchestrator** is the multi-tenant control plane for AI-assisted content production: plan → generate → **human review** → publish — with **hard spend caps**, workspace isolation, and an audit trail.

It is **not** a general Zapier/Make replacement. It is a **vertical orchestration system** for teams that ship recurring video/content at volume and cannot afford uncontrolled AI spend or unreviewed publishing.

---

## Problem we solve

Content teams using AI providers (script, voice, video, visuals) hit the same failure modes:

1. **Cost blowups** — provider calls stack up with no reservation/cap before dispatch.  
2. **Quality & brand risk** — fully autonomous “agents” publish or advance work without a mandatory human gate.  
3. **Frankenstein pipelines** — Zapier/Make/n8n + spreadsheets + Slack approvals + shared API keys = no single source of truth, weak tenancy, weak audit.  
4. **Agency chaos** — multiple clients (workspaces) sharing tools without FORCE RLS-grade isolation.  
5. **Unreliable workers** — leases, retries, and recovery are hand-rolled or ignored until something duplicates or drops work.

**Core job-to-be-done:** *“Run a repeatable content factory where every costly step is budgeted, every sensitive advance is reviewed by a human, and every workspace stays isolated.”*

---

## Target customers (summary)

| Segment | Fit |
|---------|-----|
| **Content agencies** (3–30 people) managing multiple client brands | Primary |
| **In-house content ops** at SMBs shipping weekly/daily video | Primary |
| **Solo creators** at high volume with contractor reviewers | Secondary (Starter) |
| **Enterprises** with procurement, SSO, DPA needs | Later (Enterprise) |

Detail: [`IDEAL_CUSTOMER_PROFILE.md`](./IDEAL_CUSTOMER_PROFILE.md)

---

## Unique selling proposition (USP)

> **Orchestrate AI content production with non-bypassable Human Review Gates and enforceable spend controls — on a multi-tenant Postgres control plane built for agencies and content ops.**

Pillars customers should feel in the product:

1. **Human Review Gate** — restricted advances cannot be silently skipped.  
2. **Spend controls** — reserve/check caps before costly provider work.  
3. **Workspace isolation** — `workspace_id` + ENABLE/FORCE RLS as the tenancy backstop.  
4. **Production reliability** — leases, outbox, idempotency, audit — not demo automations.  
5. **Provider abstraction** — vendors at the edge; orchestration SoT stays yours.

---

## Competitive advantages (honest)

| Advantage | Why it matters | Caveat |
|-----------|----------------|--------|
| Vertical focus (content pipelines) | Clear messaging vs horizontal iPaaS | Smaller TAM than Zapier |
| Review Gate + spend as **product invariants** | Trust & margin protection | Must stay non-bypassable in UX |
| Multi-tenant RLS architecture | Agency multi-client safety | Harder to build; already invested |
| Bootstrappable stack (Postgres SoT, no Redis queue SoT) | Lower infra complexity/cost | Must stay disciplined on scope |
| Auditability | Agencies/clients demand receipts | Docs + UI must stay truthful |

We do **not** win on: 8,000 integrations, cheapest toy automations, or “fully autonomous AI employee” hype.

---

## Why customers switch (to us)

Typical switching triggers (see ICP):

- AI bill spiked after a runaway workflow.  
- Brand/legal incident from unreviewed AI output.  
- Agency client demanded isolation / audit they couldn’t prove.  
- n8n/Make sprawl became unmaintainable for content-specific stages.  
- Need reviewers (not just admins/editors) as a first-class role.

**Switching cost:** medium — they keep existing editors/providers; we replace the **control plane**, not every creative tool.

---

## Positioning statement (for website)

**For** content agencies and in-house content ops teams  
**who** run AI-assisted video/content pipelines and fear cost overruns and unreviewed publishes  
**Content Orchestrator** is a **content production control plane**  
**that** enforces Human Review Gates, spend caps, and workspace isolation  
**unlike** Zapier/Make/n8n (horizontal automation) or agent toys (autonomy without governance)  
**we** make governed scale the default.

---

## Assumptions

- Peak product ambition (from engineering context): multi-pillar content factories, up to ~50 videos/day peak for larger tenants — **aspirational capacity**, not a Year-1 sales promise.  
- Founder is bootstrapped; GTM must be low-CAC and sequential.  
- Product UI is still maturing; early sales may be design-partner / waitlist until activation path is real.
