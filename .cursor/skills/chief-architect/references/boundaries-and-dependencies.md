# Boundaries & dependency direction

## System boundaries

```text
apps/web  ──HTTPS/JWT──►  apps/api  ◄──worker credential──  apps/worker
                              │
                              ▼
                         PostgreSQL
                      (sole source of truth)
```

| Boundary | May depend on | Must not depend on |
|---|---|---|
| `apps/web` | Public API contracts / types | SQLAlchemy models, DB URLs, worker secrets |
| `apps/api` routes | schemas, authz, services/orchestration | Worker process internals |
| `apps/api` orchestration | models, outbox, DB session | FastAPI `Request` objects deep in domain core (keep HTTP at edges) |
| `apps/worker` | API client / shared contracts | Importing `app.api.routes.*` as a library of side effects |
| Alembic | SQL / migration helpers | Application request lifecycle |

## API boundary rules

- Clear principals: **user JWT** vs **worker machine auth** vs **service-role session**.
- Routers translate HTTP ↔ domain calls; business rules live in orchestration/services.
- Error codes are stable and explicit; do not map authz failures to empty 200 lists without RLS tests proving isolation.
- Admin mutations that use service-role sessions require `require_workspace_admin` (or stronger) **before** opening the owner session.

## Service / module direction (api)

Preferred inward direction:

```text
api/routes → orchestration/services → models → db
                 ↓
              outbox/events
```

Avoid:

- models importing routes
- circular orchestration imports that force “run-time import inside function” as architecture (occasional leaf imports OK; cycles are a smell)
- duplicating claim/spend/review rules in routes and again in workers

## Package / monorepo

- Shared types/contracts may live in `packages/` only if both sides need them — do not create a junk drawer.
- Do not introduce a new deployable service for a problem solvable inside `apps/api` transactions.

## Compatibility

API and schema changes require:

- Backward compatibility for in-flight workers/clients, **or**
- Explicit versioned migration plan (credential grace, expand/contract columns, dual-read window)

Chief Architect rejects breaking changes that strand leased assignments, open review gates, or reserved spend rows without a cutover plan.
