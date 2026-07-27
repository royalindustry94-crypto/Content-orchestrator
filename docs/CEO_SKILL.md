# CEO Skill

The **CEO** Cursor Skill is the project’s high-level decision authority for
Content Orchestrator.

| | |
|---|---|
| **Invoke** | `/ceo` in Agent chat, or ask for a CEO decision |
| **Package** | [`.cursor/skills/ceo/`](../.cursor/skills/ceo/) |
| **Guide** | [`.cursor/skills/ceo/README.md`](../.cursor/skills/ceo/README.md) |

## What it enforces

- Lovable Quality Standards (complete, polished, no stubs)
- Zero placeholders and no silent failures
- Security, workspace isolation / FORCE RLS
- Human Review Gate and spend-cap controls
- Testing discipline (`pytest -W error`, adversarial RLS)
- Release discipline (design → impl → audit → CI → VERIFIED)
- Maintainability, scalability, production readiness over shortcuts

## Advisory gate

```bash
bash .cursor/skills/ceo/scripts/ceo-release-gate.sh
```
