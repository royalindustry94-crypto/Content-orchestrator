# Agent Operating Protocol

This protocol applies to every human or AI agent working in this repository. `AGENTS.md` remains authoritative. If instructions conflict, the stricter safety, review, and evidence requirement wins.

## Job ownership

| Role | Primary worker | Owns | Must not do |
| --- | --- | --- | --- |
| Founder | Mitch / `royalindustry94-crypto` | Priorities, queue approval, product decisions, final merge authorization | Delegate the Human Review Gate to automation |
| Orchestrator | Codex | Triage, task boundaries, owner assignment, handoffs, evidence collection | Implement the same task it independently audits |
| Builder | Claude Code or Cursor, explicitly assigned per task | One queued issue, one branch, implementation, tests, pull request | Push to `main`, auto-merge, weaken controls, or work outside the assigned issue |
| Pair assistant | GitHub Copilot | Small suggestions inside the active Builder's task | Own a task, approve a PR, or act as independent reviewer |
| Reviewer / QA | A fresh Codex or other designated agent that did not build the change | Scope review, regression checks, exact-head CI evidence | Modify the reviewed head while claiming independence |
| Security auditor | Independent agent | PASS / CONDITIONAL / FAIL audit against the exact head SHA and non-negotiables | Approve its own implementation or ignore missing evidence |
| Release steward | Codex after Founder approval | Confirm exact SHA, required checks, audit, and merge readiness | Merge with a failed, pending, stale, or mismatched gate |
| Build watchdog | GitHub Actions | Monitor the latest repository CI run only and retry genuine failures within bounded limits | Change product code, alter protections, expose secrets, or merge |

Only one Builder owns a task at a time. A task must have an issue, a named owner, a branch, and a pull request before it can reach review.

## Work states

Use these labels when the queue is enabled:

- `agent:queued`: Founder-approved and ready for assignment.
- `agent:active`: one Builder owns the task.
- `agent:review`: implementation stopped; exact-head review is required.
- `agent:blocked`: human approval, credential, external service, or safety decision is required.
- `agent:done`: merged after every required gate.

A handoff must state the issue, owner, branch, exact head SHA, completed work, tests and run URLs, blockers, and the next role/action. Agents resume from that evidence instead of silently starting over.

## Continuity and restart rules

The Build Watchdog runs every 30 minutes and can also be started manually. It monitors the latest repository CI run only; it is not a multi-branch build queue and cannot restart a stopped coding-agent session.

- Failed, cancelled, timed-out, or stale CI is retried once.
- A queued or running latest CI build with no update for 90 minutes is treated as stalled, cancelled, and rerun once using the same run record.
- If no CI run exists, the watchdog dispatches CI on the default branch.
- After the retry limit, the watchdog fails visibly so a human or Orchestrator can investigate.
- Successful CI is not rerun merely to consume minutes.
- A stopped Builder does not justify inventing work. The Orchestrator may restart only a Founder-approved `agent:queued` task.
- No retry can bypass Human Review, FORCE RLS, spend controls, provider abstraction, audit logging, branch protection, exact-head CI, an independent audit, or Founder approval.

## Merge gate

A Release Steward may propose a merge only when all of the following refer to the same head SHA:

1. Scope matches the Founder-approved issue.
2. Required CI is successful.
3. Independent review and security audit are complete.
4. The audit verdict is PASS, or the Founder explicitly accepts a documented CONDITIONAL verdict.
5. Human Review requirements are satisfied.
6. No unresolved P0/P1 blocker remains.
7. The Founder gives final merge approval.

Automation never merges.
