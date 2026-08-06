# Approved stack & anti-drift policy

Content Orchestrator’s runtime stack is **frozen** unless an ADR is accepted
and `/ceo` concurs for cross-cutting product impact.

## Canonical layout

```text
apps/api      FastAPI + SQLAlchemy + Alembic (Python)
apps/web      React + TypeScript (Vite)
apps/worker   Python workers
database/     supporting SQL/docs as needed (Alembic owns schema)
docs/         architecture & milestone designs
```

## Allowed by default

| Area | Allowed |
|---|---|
| HTTP API | FastAPI routers, Pydantic schemas, dependency-injected sessions |
| Persistence | SQLAlchemy 2.x mapped models, async sessions, PostgreSQL |
| Schema change | Alembic revisions with `upgrade` **and** `downgrade` |
| Auth | Supabase JWT verify-only (users); per-worker credentials (machines) |
| Events | Transactional outbox in Postgres |
| Jobs | `job_schedule` / stage assignments in Postgres (SKIP LOCKED) |
| Frontend | React function components, TypeScript strictness per app config |
| Workers | Python claiming/ack/renew/submit against API or in-process orchestration as designed |

## Reject by default (architecture drift)

| Proposal | Why rejected |
|---|---|
| Redis/RQ/Celery/Bull as job SoT | Postgres is SoT; dual-write & consistency hazard |
| New ORM (Prisma, Drizzle, Tortoise) | Splits schema ownership; Alembic/SQLAlchemy is canonical |
| Express/Nest/Django rewrite | Stack freeze; huge cost, no proven need |
| Microservices split “for scale” | Premature; monorepo modular boundaries first |
| GraphQL gateway “because modern” | Unnecessary surface; REST + clear schemas exist |
| Second primary database | No scale proof; operational complexity |
| Shared global worker token | Broke identity/audit; per-worker credentials are ADR |
| In-memory orchestration state as truth | Lost on restart; not multi-replica safe |

## Dependency rules

1. **Justify every new package** — what invariant does it preserve better than stdlib/existing stack?
2. **No dependency for a 20-line helper** you can own.
3. **Pin and review** security-sensitive libs (JWT, crypto, HTTP clients).
4. **Workers must not** grow a parallel web framework.
5. **Web must not** embed server secrets or talk to Postgres directly.

## When a stack change is allowed

Only if all are true:

1. Written ADR in `docs/architecture-decisions.md` (use `assets/adr-template.md`)
2. Migration/compat/rollback plan reviewed by Chief Architect
3. Tests proving equivalence or cutover safety
4. `/ceo` escalation for product/security/financial impact

Until then: **REJECT**.
