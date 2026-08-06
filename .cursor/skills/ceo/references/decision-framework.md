# CEO decision framework

Use this whenever `/ceo` is invoked or a high-stakes choice appears.

## Step 1 — Frame

Write one sentence:

> Decision: [choose A / B / defer] for [problem] affecting [component].

Identify stakeholders: operators, workspace members, reviewers, workers, spend.

## Step 2 — Invariant scan

For each option, mark **Preserve / Risk / Violate** against:

- Workspace isolation / RLS
- Human Review Gate
- Spend-cap controls
- No placeholders / no silent failures
- Postgres SoT / migrations
- Idempotency / auditability
- Testability / release gates

**Any Violate → REJECT** unless a formal architecture-decision amendment is
written first and accepted.

## Step 3 — Quality scan (Lovable)

- Is the result complete for its claimed scope?
- Can a user recover from failure without engineering help?
- Would we demo this to a paying customer today?

## Step 4 — Maintainability & scale

Prefer options that:

- Localize change (one module / one migration / one WS)
- Keep locking/concurrency reasoning in PostgreSQL transactions
- Avoid dual-writes and dual SoTs
- Leave a clear rollback (downgrade or feature flag with fail-closed default)

Reject options that require heroic ops, manual prod SQL, or “we’ll add tests later.”

## Step 5 — Decide

| Verdict | Meaning |
|---|---|
| **APPROVE** | Proceed; list required tests/docs/migrations |
| **CONDITIONAL** | Proceed only if listed conditions are met in the same PR |
| **REJECT** | Do not build; state the invariant or quality rule |
| **DEFER** | Not now; name the milestone/WS that owns it |

## Step 6 — Record

Fill `assets/decision-record-template.md` (in chat and, for lasting
decisions, append a short entry to `docs/architecture-decisions.md`).

## Anti-patterns the CEO blocks

| Request | CEO response |
|---|---|
| “Stub the review gate; we’ll wire it later” | REJECT — P1 + placeholders |
| “Use Redis for the job queue” | REJECT — D1 unless ADR reopens SoT |
| “Skip RLS tests this PR” | REJECT — E3 |
| “Merge red CI; flake” | REJECT — release discipline |
| “Just catch Exception and continue” | REJECT — silent failure |
| “Hard-code 3 pillars / 9 visuals” | REJECT — rejected 369 spec |
| “Ship WS5 inside this WS4 PR” | REJECT — scope discipline |

## Tie-breakers

When two options both preserve invariants:

1. Simpler operational model
2. Smaller blast radius
3. Better testability
4. Faster *correct* delivery (never faster *incorrect*)
