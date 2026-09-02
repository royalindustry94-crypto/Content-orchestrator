# WP-PB-010 — Five-step content setup

**Status:** Founder Preview candidate  
**Founder direction:** Simplify the opening experience and support a done-for-you client service.  
**Merge gate:** Exact-head CI plus Founder visual approval.

## Outcome

Home presents one setup path with five steps:

1. Business — choose `My business` or `Done-for-you client`, then describe the business and offer.
2. Audience — describe who the content should attract.
3. Brand voice — define how the content should sound.
4. Content plan — choose the primary platform and desired outcome.
5. First brief — provide the first topic and target length.

Completing the final step creates a real Content Job through the existing workspace-scoped API. Draft Desk uses the supplied context to create the first draft, and the draft enters the mandatory Human Review Gate. Nothing is published automatically.

## Done-for-you isolation model

- The operator uses their own authenticated account; client passwords are never requested or stored.
- One workspace must be used per client.
- The selected workspace ID is supplied by the authenticated application shell and enforced by the existing membership guard and FORCE RLS path.
- Setup answers are cached in browser local storage under a workspace-specific key for convenience. They contain no credentials or secrets.
- The submitted context is persisted only as part of the generated draft in this bounded milestone. A durable Business Brain remains a separate schema/API milestone.

## Non-goals

- No customer impersonation or password sharing.
- No provider credential setup.
- No automatic or external publishing.
- No weakening of spend controls, Human Review, workspace guards, or RLS.
- No claim that browser-cached setup is a durable cross-device Business Brain.

## Verification

- API regression: setup context produces a tailored draft at an awaiting Human Review Gate.
- Web regression: the done-for-you path completes all five steps and calls the Content Job API with workspace-scoped setup fields.
- Web build, lint, unit tests, API suite, security checks, Docker builds, and browser smoke remain required by the protected `main` ruleset.
