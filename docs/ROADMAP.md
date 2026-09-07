# Product Roadmap — Launch Path

**Updated:** 2026-09-07 (staleness fix — see note below; content otherwise unchanged from 2026-08-03)  
**North star:** Private Beta → first 10 paying customers → PMF → positive cash flow.  
**Prioritization:** Revenue → Customer value → Platform reliability → Security → Performance → DX.

Planning docs alone do not count as progress. Each item below is a Work Package or an outcome.

> **This page is a historical Now/Next/Later shape, not the current launch-readiness verdict.**
> It was last substantively written 2026-08-03, before the PR #48/#49 governance baseline and
> the current audited state. For the actual current verdict, always defer to (dated 2026-08-28,
> or later where superseded): `docs/LAUNCH_BLOCKERS.md`, `docs/EXECUTIVE_STATUS_REPORT.md`, and
> `docs/TECHNICAL_DEBT_REGISTER.md`. In particular, the "Launch gate: **READY FOR PRIVATE BETA**"
> line below is the obsolete `cursor/p2-beta-launch-b52d` / `docs/FINAL_RELEASE_AUDIT.md` verdict
> from 2026-08-05 — the current baseline is CONDITIONAL (governance) / NOT YET RUNTIME-VERIFIED
> (operational beta), per `docs/LAUNCH_BLOCKERS.md`.

---

## Now (Private Beta wedge)

| WP | Outcome | Status |
|----|---------|--------|
| **WP-PB-001** | Review Desk API + UI (draft → Gate → approve/reject) | **Done** |
| WP-PB-002 | Spend caps API + ledger visibility (fail-closed demo) | **Done** (P0) |
| WP-PB-003 | Email or Slack notify on `REVIEW_REQUESTED` | Next (post-beta polish) |
| **WP-PB-004** | Stripe Checkout for founding Pro ($149–$199) | **Done (P-001)** |
| WP-PB-005 | One real BYOK generation path (replace stub scripting) | After desk is sellable |

**Launch gate:** P0–P1 Private Beta blockers closed on `cursor/p2-beta-launch-b52d` — see `docs/FINAL_RELEASE_AUDIT.md` (**READY FOR PRIVATE BETA**).


## Next (first 10 customers)

- Founder-led onboarding for agencies (2+ clients)
- Brand kit fields checked at Gate
- Audit export (CSV/PDF) for client reporting
- Multi-workspace UX polish

## Later (post-PMF)

- Broad integrations / connector race — **rejected until PMF**
- Autonomous publish modes — **rejected**
- Self-host — **rejected for bootstrap**
- Enterprise SSO/SOC theater — after paid demand

## Explicit non-goals until PMF

- Matching Zapier/Make connector counts
- Building an agent OS (Lindy/Relevance parity)
- TikTok-led growth product requirements

See also: `docs/PRODUCT_MARKET_FIT_AUDIT.md` (PIVOT), `docs/work-packages/`.
