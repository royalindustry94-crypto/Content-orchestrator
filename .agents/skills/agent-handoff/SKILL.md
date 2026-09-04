---
name: agent-handoff
description: Hand a Business Manager task between Cursor, Codex, or another repository-aware agent with exact scope, SHA, evidence, blockers, and next actions.
---

# Agent Handoff

Use repository state as the shared source of truth. Chat history is supporting context, not the authoritative record.

1. Confirm the task ID, current branch, exact HEAD and tree SHAs, base SHA, dirty state, and migration head.
2. State what changed and what remains. Do not repeat unsupported completion claims.
3. List executed checks with PASS, FAIL, or NOT-RUN and link evidence paths.
4. Record blockers, unresolved findings, required approvals, and the next bounded action.
5. Name the intended recipient by capability, such as `cursor-builder`, `codex-auditor`, or `human-founder`; do not assume a direct live channel exists.
6. Commit implementation before a `ready_for_review` or `verified` handoff; those statuses refuse a dirty worktree. Create the structured handoff with `scripts/agent_handoff.py create`. The default is local evidence under ignored `validation-logs/`. Use `--publish` only when authorized to add a metadata-only handoff commit to the task branch for another app or environment.
7. The receiving agent must run `scripts/agent_handoff.py validate <file>` while the task branch still exists. Validation checks the commit, tree, base ancestry, branch containment, and task folder. Re-check any safety-critical claim before acting.

Handoffs coordinate work; they do not authorize merges, deployments, spending, customer-data access, or external publishing.
