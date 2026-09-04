---
name: milestone-plan
description: Plan a bounded Business Manager milestone before implementation when scope, acceptance evidence, risks, or sequencing are not already explicit.
---

# Milestone Plan

Create an implementation-ready work package without modifying code.

1. Read `AGENTS.md`, `docs/LAUNCH_BLOCKERS.md`, and the most relevant architecture document.
2. State the user outcome in plain language and identify the smallest shippable scope.
3. List explicit non-goals. Do not introduce a framework, provider, or autonomous publishing mode without Founder approval.
4. Identify affected trust boundaries: tenant isolation, Human Review Gate, spend, secrets, audit events, migrations, and external side effects.
5. Define acceptance evidence before implementation. Include exact tests, browser paths, migration checks, and required runtime evidence.
6. Sequence the work so each commit is reviewable and rollback is possible.
7. Record unresolved decisions. Ask only for choices that materially change the result.

Output a concise work package with: outcome, scope, non-goals, risks, acceptance evidence, implementation order, rollback, and open decisions.
