# Skill authority matrix (Content Orchestrator)

This file is **not** a skill. It defines who decides what so agents cannot
silently exceed authority or approve their own work.

| Concern | Primary | Must consult | Must not |
|---|---|---|---|
| Product scope, quality bar, go/no-go, product VERIFIED label | `/ceo` | Specialists + `/content-orchestrator-expert` impact + `/release-manager` readiness + `/security-auditor` when security-sensitive | Implement specialist deep work as substitute for delegation |
| Domain fit, platform principles, roadmap alignment, feature creep/drift, product impact assessment | `/content-orchestrator-expert` | `/ceo` for go/no-go; `/chief-architect` for SoT/boundaries; specialists for impl facts | Replace CEO VERIFIED; accept ADRs; implement features as primary; merge PRs |
| Stack freeze, SoT, service boundaries, ADR acceptance | `/chief-architect` | `/postgresql-expert` for schema/RLS/SQL; `/content-orchestrator-expert` for domain fit; `/ceo` for product/security escalate | Replace backend/PG implementation; merge PRs |
| FastAPI/worker code, DI, auth wiring, tests for app behavior | `/backend-engineer` | `/chief-architect` before arch change; `/postgresql-expert` before schema/RLS/migration design | Invent architecture; declare migration-safe without PG review; self-security-approve |
| React+TypeScript UI, reusable components, FastAPI client UX, a11y/responsive, frontend tests/build | `/frontend-engineer` | `/chief-architect` before app-shell/BFF/second-frontend; `/backend-engineer` for missing APIs; `/ceo` for product scope | Invent APIs/product; enforce authZ only in UI; merge PRs; self-security/QA-approve |
| CI/CD, GitHub Actions least privilege, Docker/deploy reliability, secrets/env hygiene, rollback, migration-safe rollout ops | `/devops-engineer` | `/chief-architect` for topology; `/postgresql-expert` for migration design; `/security-auditor` for secrets/supply-chain; `/ceo` for downtime/risk accept | Approve red CI or incomplete migrations; bypass QA/Security/Review Gate/spend; merge PRs |
| Release readiness, versioning/tags/changelogs, gate evidence assembly, RELEASE READY recommendation | `/release-manager` | `/ceo` for product VERIFIED; `/qa-breaker` + `/security-auditor` + `/devops-engineer` evidence; `/postgresql-expert` for migration proof; `/documentation-writer` for notes accuracy | Merge on assumptions; override QA/Security FAILED; skip rollback; self-approve without evidence |
| Technical/product docs, ADR drafts, impl/audit/release notes prose, OpenAPI doc sync, migration/ops documentation | `/documentation-writer` | `/chief-architect` for ADR acceptance; specialists for factual accuracy; `/release-manager` for readiness packaging | Invent features; leave doc↔code drift; accept ADRs unilaterally; merge PRs |
| Schema, RLS, Alembic chain, constraints, SQL concurrency, DB correctness | `/postgresql-expert` | `/chief-architect` if SoT/boundaries change; `/ceo` on isolation/financial escalate | Own FastAPI route design; merge PRs; accept SQLite/mocks |
| Independent security audit before PR/release approval | `/security-auditor` | `/postgresql-expert` for RLS depth; `/backend-engineer` / `/frontend-engineer` / `/devops-engineer` for remediations; `/release-manager` consumes approval; `/ceo` for residual Medium acceptance | Implement the change under review; approve own fixes without fresh re-audit; merge |
| Independent adversarial QA before PR/release approval | `/qa-breaker` | `/security-auditor` for security-shaped defects; `/postgresql-expert` for migration/RLS defects; implementers for remediations; `/release-manager` consumes approval; `/ceo` for VERIFIED | Happy-path-only approval; accept mocks/SQLite as final; merge; self-approve fixes without full restart |

## Independent review (mandatory)

No skill may:

1. **Merge** a pull request (human only; cloud agents never merge unless the human explicitly orders merge **and** QA + **security** have approved).
2. Mark work **VERIFIED** or **COMPLETE** without **factual evidence** (CI URL + SHA, migration head, test counts, adversarial RLS results, `/qa-breaker` + `/security-auditor` reports when applicable).
3. **Approve its own implementation** as final: the implementer skill proposes; a different skill or human reviewer must sign off on architecture/schema/security/QA as applicable.
4. Skip **QA** (`/qa-breaker`: full `pytest -W error`, migration replay, concurrency/recovery as in scope) or **security** review (`/security-auditor` on security-sensitive surfaces) before release claims. Production-like releases also require a `/release-manager` readiness report before `/ceo` product VERIFIED.
5. **Security Auditor** / **QA Breaker** may not approve remediations they authored without restarting their full audit on the new SHA.

## GitHub is source of truth

- Canonical code lives on GitHub (`royalindustry94-crypto/Content-orchestrator`).
- Commits/PRs on GitHub beat local-only claims.
- Never force-push shared milestone branches.
- Never rewrite history to hide failed gates.

## Approved stack (all skills)

FastAPI · SQLAlchemy 2.x · Alembic · PostgreSQL · React + TypeScript · Python workers.
