# Agent Operating Model

This repository uses a cost-aware delivery model designed to keep implementation moving without paying multiple AI workers to rediscover or redo the same work.

## Roles

### Controller — ChatGPT
Owns prioritization, architecture, acceptance criteria, task decomposition, risk classification, and final review.

The controller should not routinely read or re-audit the entire repository. It should create a bounded task and provide only the context needed for that task.

### Primary implementation worker — Cursor
Cursor is the default coding worker for normal implementation, refactors, tests, UI work, API work, documentation, and routine bug fixes.

Cursor works one scoped issue/work package at a time. It should expand context only when a concrete dependency requires it.

### Escalation specialist — Codex / high-reasoning worker
Use only when justified by risk or a concrete blocker. Typical triggers:

- authentication, authorization, RLS, tenant-isolation or secret-handling changes
- Human Review Gate or publication-policy changes
- spend-control or billing-integrity changes
- destructive/complex migrations or data-loss risk
- concurrency, locking, idempotency or cross-service integrity bugs
- repeated failure after focused implementation/debug attempts
- deep cross-cutting architectural change
- milestone, release, or explicit independent adversarial audit

Codex is not a second default implementation worker. Do not send the same routine task to Cursor and Codex in parallel.

### Verifier — GitHub Actions
GitHub Actions is the standard full-suite verifier. CI owns the normal full checks for API, worker, web, browser smoke, migrations, security, dependency audits, and secret scanning.

During implementation, workers should run targeted checks relevant to the changed surface. The PR then receives the complete CI pass.

## Default delivery flow

1. **Controller scopes the task**
   - one objective
   - acceptance criteria
   - in-scope and out-of-scope boundaries
   - likely files/surfaces
   - risk tier
   - targeted tests

2. **Cursor implements**
   - create/use a task branch
   - read `AGENTS.md`, the active task, and relevant files only
   - make the smallest production-ready change that satisfies acceptance criteria
   - run targeted tests while iterating

3. **Cursor hands off evidence**
   - files changed
   - behavior changed
   - tests run and results
   - unresolved risks or assumptions
   - escalation required: yes/no and why

4. **Open a PR**
   - GitHub Actions runs the standard full verification suite
   - avoid launching another full AI audit while CI is already checking deterministic concerns

5. **Controller reviews**
   - inspect the diff, acceptance criteria, CI status, and any risk-specific evidence
   - if clean, proceed under repository merge governance
   - if blocked or high-risk, escalate only the exact unresolved problem

6. **Codex/high-reasoning review only when triggered**
   - provide the failed check, relevant files, attempted fixes, logs/test output, and exact question
   - do not ask the specialist to rediscover the whole project unless this is an explicit milestone/release audit

## Risk tiers

| Tier | Typical work | Default worker | Independent escalation |
|---|---|---|---|
| R0 | docs, copy, isolated styling, test-only cleanup | Cursor | No |
| R1 | routine UI/API/worker feature inside established patterns | Cursor | Only if blocked |
| R2 | schema changes, provider integration, billing-adjacent, complex state | Cursor | Review if risk is material |
| R3 | auth/RLS, tenant isolation, Human Review Gate, spend controls, destructive migration, concurrency/data integrity | Cursor + specialist review | Required before merge |
| Release | milestone/release certification | implementation worker + independent auditor | Required |

Risk tier never overrides the non-negotiables or milestone governance in `AGENTS.md`.

## Context-budget rules

- Start with the active task, `AGENTS.md`, and directly relevant files.
- Search for symbols/paths before opening broad directories.
- Prefer diffs and targeted file reads over repeated whole-repository scans.
- Do not regenerate architecture summaries that already exist unless they are stale for the task.
- Reuse existing tests, runbooks, architecture docs, and agent memory rather than recreating them.
- Do not have multiple AI workers produce competing implementations for routine work.
- Split unrelated work into separate packages unless atomic integration requires otherwise.

## Testing division

### During implementation
Run the smallest deterministic checks that give fast feedback for the changed surface.

Examples:

- API change: focused pytest file/test plus lint for touched Python
- Web change: focused test plus lint/typecheck/build as appropriate
- Worker change: focused worker pytest plus lint
- Migration: upgrade/downgrade/replay checks relevant to the migration

### At PR
GitHub Actions is responsible for the repository-standard full suite. A failed CI job should be debugged from its concrete failure rather than triggering an immediate full AI audit.

## Escalation packet

When escalating, provide this compact packet:

```text
Task:
Risk tier:
Expected behavior:
Observed failure:
Relevant files:
Tests/checks already run:
Attempts already made:
Exact unresolved question:
```

A specialist should answer the unresolved question first. Broadening scope requires a concrete reason.

## Handoff template

```text
Objective completed:
Files changed:
Behavior changed:
Targeted tests run:
CI status:
Security/safety controls affected:
Unresolved risks:
Escalation required: YES/NO
Escalation reason (if YES):
Recommended next task:
```

## Full-repository audit policy

A full-repository or adversarial audit is appropriate only for:

- milestone completion
- release certification
- major architecture migration
- security incident or credible high-severity finding
- broad integrity concern supported by evidence
- explicit Founder request

Routine feature work should not automatically trigger a full repository audit.
