# Release gates — Content Orchestrator

## Gate matrix (production-like release)

| Gate | Evidence | Blocker if missing/fail |
|------|----------|-------------------------|
| Scope | Written scope / milestone notes | NOT VERIFIED |
| Identity | Branch + full SHA + PR URL | NOT VERIFIED |
| Architecture | `/chief-architect` when ADR/boundaries/stack touched | FAILED / NOT VERIFIED |
| CI | GitHub Actions green on **exact** SHA (`api` / `worker` / `web`) | FAILED |
| Tests | pytest (+ worker); coverage if gated in repo | FAILED |
| Migrations | Fresh PostgreSQL upgrade; head id; reverse or expand/contract notes via `/postgresql-expert` | FAILED |
| Security | `/security-auditor` on SHA; Critical/High = 0 | FAILED |
| QA | `/qa-breaker` on SHA | FAILED |
| DevOps | Deploy/rollback/secrets notes when shipping runtime | NOT VERIFIED / FAILED |
| Docs | Version, tag plan, changelog, release notes | NOT VERIFIED |
| Invariants | Review Gate, spend, audit, RLS, isolation | FAILED if knowingly broken |
| Placeholders | No TODO/mock/silent-fail on in-scope paths | FAILED |

## SHA discipline

Any commit after QA/Security/CI evidence **invalidates** prior approvals.
Restart affected gates on the new SHA before RELEASE READY.

## Relationship to other skills

```text
Implementers → QA + Security → DevOps CI/deploy evidence
        ↘
    Release Manager (assemble readiness report)
        ↘
    CEO (product VERIFIED / go-no-go)
        ↘
    Human merge (explicit order only)
```

## Fail closed

If unsure whether a gate applies to a production release, **require it** or escalate to `/ceo` for an explicit written waiver (never for Critical/High security or red CI).
