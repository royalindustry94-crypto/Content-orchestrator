# Agent Operating Protocol

This protocol applies to every human or AI agent working in this repository. `AGENTS.md` remains authoritative, including its "Operating authority" section (added 2026-09-09): the coding agent has standing authority to resolve findings and merge without per-change Founder approval. Where this document's older role table below implies a Founder-approval merge gate, `AGENTS.md`'s current authority section wins. If instructions conflict on anything else, the stricter safety, review, and evidence requirement wins.

## Job ownership

| Role | Primary worker | Owns | Must not do |
| --- | --- | --- | --- |
| Founder | Mitch / `royalindustry94-crypto` | Priorities, product decisions, real-money/credential decisions | Delegate the Human Review Gate to automation |
| Orchestrator | Codex | Triage, task boundaries, owner assignment, handoffs, evidence collection | Implement the same task it independently audits |
| Builder | Claude Code or Cursor, explicitly assigned per task | One queued issue, one branch, implementation, tests, pull request, and — once evidence supports it — the merge itself | Merge on unresolved P0/P1 evidence, weaken controls, or work outside the assigned issue |
| Pair assistant | GitHub Copilot | Small suggestions inside the active Builder's task | Own a task, approve a PR, or act as independent reviewer |
| Reviewer / QA | A fresh Codex or other designated agent that did not build the change | Scope review, regression checks, exact-head CI evidence | Modify the reviewed head while claiming independence |
| Security auditor | Independent agent | PASS / CONDITIONAL / FAIL audit against the exact head SHA and non-negotiables | Approve its own implementation or ignore missing evidence |
| Build watchdog | GitHub Actions | Monitor the latest repository CI run only and retry genuine failures within bounded limits | Change product code, alter protections, expose secrets, or merge |

Only one Builder owns a task at a time. A task must have an issue, a named owner, a branch, and a pull request before it can reach review.

## Work states

Use these labels when the queue is enabled:

- `agent:queued`: ready for assignment.
- `agent:active`: one Builder owns the task.
- `agent:review`: implementation stopped; exact-head review is required.
- `agent:blocked`: a real credential, external service, or safety decision only the Founder can make is required.
- `agent:done`: merged after every required gate.

A handoff must state the issue, owner, branch, exact head SHA, completed work, tests and run URLs, blockers, and the next role/action. Agents resume from that evidence instead of silently starting over.

## Continuity and restart rules

The Build Watchdog runs every 30 minutes and can also be started manually. It monitors the latest repository CI run only; it is not a multi-branch build queue and cannot restart a stopped coding-agent session.

- Failed, cancelled, timed-out, or stale CI is retried once.
- A queued or running latest CI build with no update for 90 minutes is treated as stalled, cancelled, and rerun once using the same run record.
- If no CI run exists, the watchdog dispatches CI on the default branch.
- After the retry limit, the watchdog fails visibly so a human or Orchestrator can investigate.
- Successful CI is not rerun merely to consume minutes.
- A stopped Builder does not justify inventing work; the Orchestrator may restart only a queued task with a real owner.
- No retry can bypass Human Review, FORCE RLS, spend controls, provider abstraction, audit logging, branch protection, or an independent audit.

## Merge gate

A Builder may merge once all of the following refer to the same head SHA:

1. Scope matches the assigned issue.
2. Required CI is successful.
3. Independent review and security audit are complete (reproduced, not just read — see `AGENTS.md`'s reproduce-before-trusting discipline).
4. The audit verdict is PASS, or a documented, non-safety-critical CONDITIONAL is recorded in `docs/TECHNICAL_DEBT_REGISTER.md`.
5. Human Review requirements are satisfied.
6. No unresolved P0/P1 blocker remains.

Real money, destructive/irreversible actions, and repo/org access changes still get flagged to the Founder before acting, per `AGENTS.md`.
