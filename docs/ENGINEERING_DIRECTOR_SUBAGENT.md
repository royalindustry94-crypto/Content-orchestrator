# Engineering Director (Cursor subagent)

Project subagent:
[`.cursor/agents/engineering-director.md`](../.cursor/agents/engineering-director.md)

([Cursor subagents docs](https://cursor.com/docs/subagents.md))

## Purpose

Coordinates all engineering work for Content Orchestrator: receives tasks from
`/ceo`, selects and sequences specialist skills, prevents duplicate work,
requires independent `/security-auditor` and `/qa-breaker` review, requires
`/release-manager` before release recommendations, escalates conflicts to CEO,
and produces a final engineering summary. Does **not** implement specialist
deep work when a specialist is better suited. Never merges without QA + Security.

## Invoke

- Agent may auto-delegate when the task matches the subagent `description`
- Ask Agent to use the **Engineering Director** subagent / `@engineering-director`
- CEO skill should route multi-specialist engineering coordination here

## Delegates to

`/chief-architect` · `/backend-engineer` · `/frontend-engineer` ·
`/postgresql-expert` · `/devops-engineer` · `/documentation-writer`  
(+ `/content-orchestrator-expert`, `/executive-operations-hub-architect` when in scope)  
Independent: `/security-auditor`, `/qa-breaker` · Release: `/release-manager`

## Related

- [AUTHORITY_MATRIX](../.cursor/skills/AUTHORITY_MATRIX.md)
- [CEO Master Rule](./CEO_MASTER_RULE.md)
- [CURSOR_SKILLS.md](./CURSOR_SKILLS.md)
