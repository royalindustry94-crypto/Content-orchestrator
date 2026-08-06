# Release discipline — CEO reference

Content Orchestrator ships by **milestone workstream**. GitHub is the
source of truth for code and CI evidence.

## Workstream lifecycle (required order)

```text
DESIGN → specialist APPROVALS → IMPLEMENT → TESTS + MIGRATIONS → AUDIT → CI GREEN → EVIDENCE → VERIFIED
```

| Step | Owner |
|---|---|
| Design doc | Workstream author; CEO accepts scope |
| Architecture ADR / boundary | `/chief-architect` |
| Schema / RLS / Alembic | `/postgresql-expert` |
| FastAPI / worker implementation | `/backend-engineer` |
| React+TypeScript UI | `/frontend-engineer` |
| QA (`/qa-breaker`) | Adversarial matrix, `pytest -W error`, migration replay, concurrency/recovery; not self-only |
| Security (`/security-auditor`) | Required when auth/RLS/workers/spend/review/CI secrets touched |
| VERIFIED label | `/ceo` only, with evidence including QA + security reports when applicable |

## Verification checklist

- [ ] Design landed before production behavior/schema
- [ ] `/chief-architect` sign-off if stack/boundaries/ADR touched
- [ ] `/postgresql-expert` sign-off if schema/RLS/migration touched
- [ ] `/frontend-engineer` sign-off if `apps/web` UI touched
- [ ] Fresh DB `upgrade` → `downgrade` → `upgrade` for new revisions
- [ ] `ruff` clean (api + worker); web lint/typecheck/build if UI touched (`/frontend-engineer` gates)
- [ ] `pytest -W error` full API suite + worker tests
- [ ] Adversarial RLS tests for every new table/policy
- [ ] Concurrency tests for lock-sensitive paths
- [ ] No placeholder/TODO on in-scope production paths
- [ ] Audit: defects found/fixed + remaining risks
- [ ] GitHub PR URL + SHA + Actions URL (green on that SHA)
- [ ] Migration head id cited
- [ ] QA approved; security approved
- [ ] Final status exactly: **VERIFIED** | **FAILED** | **NOT VERIFIED**
- [ ] **Not merged** unless human explicitly orders merge after the above

## Completion report fields

Branch · Commit SHA · PR URL · GitHub Actions URL · Migration head ·
Tests passed · Coverage · Security findings · Defects found/fixed ·
Remaining risks · Final status

## Merge policy

- Skills/agents **never merge** by default.
- Merge only on explicit human order **after** VERIFIED evidence **and** QA + security approval.
- Never force-push shared milestone branches; never rewrite history to hide failed gates.

## Advisory automation

```bash
bash .cursor/skills/ceo/scripts/ceo-release-gate.sh
```

Advisory only — not a substitute for specialist sign-offs or evidence.
