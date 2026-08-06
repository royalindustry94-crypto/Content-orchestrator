# QA Breaker Skill

Adversarial QA skill for Content Orchestrator.

| | |
|---|---|
| **Invoke** | `/qa-breaker` |
| **Package** | [`.cursor/skills/qa-breaker/`](../.cursor/skills/qa-breaker/) |
| **Guide** | [`.cursor/skills/qa-breaker/README.md`](../.cursor/skills/qa-breaker/README.md) |
| **Authority** | [`.cursor/skills/AUTHORITY_MATRIX.md`](../.cursor/skills/AUTHORITY_MATRIX.md) |

## Responsibilities

- Independent breaker (not the implementer)
- Attack matrix; real Postgres; concurrency/recovery/migrations/frontend
- Reject mocks/SQLite/weak happy-path-only tests
- Regression tests per defect; warnings-as-errors
- Never weaken suites; never merge; re-audit after fixes; evidence for VERIFIED

## Advisory gate

```bash
bash .cursor/skills/qa-breaker/scripts/qa-breaker-gate.sh
```
