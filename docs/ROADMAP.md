# Product Roadmap — Launch Path

**North star:** Private Beta → first 10 paying customers → PMF → positive cash flow.  
**Prioritization:** Revenue → Customer value → Platform reliability → Security → Performance → DX.

Planning docs alone do not count as progress. Each item below is a Work Package or an outcome.

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
- Brand kit fields checked at Gate — persist brand voice as data, inject
  into every generation call, surface conformance at the Gate (see
  `docs/COMPETITIVE_REVIEW_ANALYSIS.md` — competitors' AI output drifts
  off-brand because voice is only ever a one-off prompt)
- Audit export (CSV/PDF) for client reporting — include full decision
  history (who/when/why), not just final status; make it base-tier, not
  an Enterprise upsell (Planable/Sprout gate this and it's a top complaint)
- Multi-workspace UX polish
- Pre-generation cost estimate + near-cap warning ahead of the spend-cap
  block, and workspace-visible alerts on any publish/generation failure —
  reviewed competitors lose trust from silent failures and after-the-fact
  billing surprises (Zapier, Planable, Loomly); see
  `docs/COMPETITIVE_REVIEW_ANALYSIS.md`
- Review Gate: structured rejection reasons, reviewer reassignment, and
  time-in-gate tracking — data shows unstructured approval chains take
  2.6x longer (4.7 vs 1.8 days industry avg); our mandatory gate must not
  become the bottleneck agencies already complain about elsewhere
- Explicit no-training / data-retention statement for content submitted
  to the Gate, surfaced in-product — an unclaimed trust differentiator
  given client-confidentiality concerns with AI tools generally
- White-label the audit export (agency logo/colors), not just CSV/PDF —
  reviewed sources call client reporting the primary retainer-renewal
  moment for agencies

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
