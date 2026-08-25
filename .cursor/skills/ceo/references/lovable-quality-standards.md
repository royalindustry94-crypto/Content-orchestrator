# Lovable Quality Standards — Content Orchestrator

These are the project’s **product and craft quality bar**. “Lovable” here
means *shippable, polished, trustworthy software* — not the rejected
TeslaFlow 369 numerology spec (`docs/architecture-decisions.md`).

The CEO enforces these on every milestone, API, worker path, and UI surface.

---

## 1. Completeness over theatre

- Every in-scope flow must work end-to-end in the target environment.
- No “Coming soon”, disabled CTAs that pretend to work, or demo-only happy paths.
- If a feature is out of scope, **omit it** from the UI/API rather than stubbing it.

## 2. Zero placeholders

Forbidden in production code and committed docs that describe “current behavior”:

- `TODO`, `FIXME`, `XXX`, `HACK` marking unfinished work
- Functions that return fake/success data “for now”
- Empty `except` / broad catch-and-log-only without user-visible or durable failure signal
- Commented-out critical paths left as the real implementation

Allowed: design docs that explicitly list **out of scope** for a later workstream.

## 3. No silent failures

Every failure mode must be one of:

1. **Fail closed** (reject, pause, hold, 4xx/5xx with stable error code), or
2. **Durable signal** (outbox event, audit row, DLQ, claim/recovery ledger), or
3. **Explicit non-success outcome** (e.g. claim `no_work` / `capacity`) that callers handle

Never: drop work, acknowledge success when side effects did not occur, or hide authz failures as empty 200s without RLS/tests.

## 4. Trust & safety surfaces

| Surface | Standard |
|---|---|
| Human Review Gate | Visible, mandatory, cannot be skipped by automation |
| Spend | Caps respected; operators can see hold/pause reasons |
| Auth | Clear 401/403; no credential enumeration via distinct errors where forbidden |
| Multi-tenant | User A never sees User B’s workspace data |

## 5. Operator & mobile experience

Primary operator often works from a phone:

- Short instructions with exact URLs when guiding humans
- Prefer plain language; define jargon once
- Dashboards (when built): one job per view; no cluttered “AI dashboard” soup

## 6. Visual / frontend craft (when building UI)

Apply the project frontend hard rules (see agent user rules / design guidance):

- Brand-first heroes; one composition per first viewport
- Expressive typography; atmospheric backgrounds; full-bleed hero imagery when promotional
- No card-spam, pill clusters, or generic purple-gradient AI aesthetics
- Motion with purpose (2–3 intentional motions), not noise
- Desktop **and** mobile must load and work

If changing an existing design system, **preserve** it rather than inventing a parallel look.

## 7. API & contract quality

- Stable error codes; documented auth principals (JWT vs worker credential)
- Idempotent mutating endpoints where retries are expected
- OpenAPI/schemas match behavior; no phantom fields
- Admin vs member vs machine routes clearly separated

## 8. Observability as product

- Structured audit events for security-sensitive actions
- Outbox events for domain transitions operators/systems depend on
- Metrics/logs must not contain secrets or raw credentials

## 9. Definition of “done”

A change meets Lovable Quality Standards only if:

1. Invariants hold (security, isolation, review gate, spend)
2. Tests prove the happy path **and** adversarial/failure paths
3. Migrations are reversible or explicitly justified
4. Docs (design/impl/audit when required) match reality
5. A skeptical CEO would merge it into production tonight
