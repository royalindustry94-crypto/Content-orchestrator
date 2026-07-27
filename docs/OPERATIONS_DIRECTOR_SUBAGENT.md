# Operations Director (Cursor subagent)

Project subagent:
[`.cursor/agents/operations-director.md`](../.cursor/agents/operations-director.md)

([Cursor subagents docs](https://cursor.com/docs/subagents.md))

## Purpose

Coordinates day-to-day operation of Content Orchestrator and the future
Executive Operations Hub: milestones, PRs, Actions, deployments, health,
roadmap priorities, lifecycle enforcement, cross-role communication, blockers,
audit trails, AI spend monitoring, Review Gate enforcement, risk escalation,
and operational reporting. Never implements production code. Never approves
releases without Release Manager + QA Breaker + Security Auditor. Always
requires evidence before reporting complete.

## Invoke

- Agent may auto-delegate when the task matches the subagent `description`
- Ask Agent to use the **Operations Director** subagent / `@operations-director`
- Use for daily ops standups, milestone tracking, and release-day coordination

## Report templates

| Output | Template |
|--------|----------|
| Daily Operations Report | [`daily-operations-report.md`](./operations-director/daily-operations-report.md) |
| Milestone Progress Report | [`milestone-progress-report.md`](./operations-director/milestone-progress-report.md) |
| Active Blockers | [`active-blockers.md`](./operations-director/active-blockers.md) |
| Risk Register | [`risk-register.md`](./operations-director/risk-register.md) |
| Outstanding Approvals | [`outstanding-approvals.md`](./operations-director/outstanding-approvals.md) |
| AI Spend Summary | [`ai-spend-summary.md`](./operations-director/ai-spend-summary.md) |

## Coordinates with

`/ceo` · Engineering Director · `/release-manager` · `/qa-breaker` ·
`/security-auditor` · `/devops-engineer` · `/executive-operations-hub-architect`

## Related

- [ENGINEERING_DIRECTOR_SUBAGENT.md](./ENGINEERING_DIRECTOR_SUBAGENT.md)
- [AUTHORITY_MATRIX](../.cursor/skills/AUTHORITY_MATRIX.md)
- [CEO_MASTER_RULE.md](./CEO_MASTER_RULE.md)
