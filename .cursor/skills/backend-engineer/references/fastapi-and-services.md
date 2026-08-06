# FastAPI, DI, REST & OpenAPI

## Route design

- Group by principal: user JWT routes vs `/workers/...` machine routes vs admin workspace routes.
- Use `APIRouter(prefix=..., tags=[...])`; register in `app/main.py`.
- Declare `response_model` and explicit `status_code` for success.
- For `204 No Content`, return `Response(status_code=204)` — no body.

## Dependency injection

| Dependency | Use for |
|---|---|
| `get_current_user` | Authenticated human identity from Supabase JWT |
| `get_current_session` | RLS-scoped `app_runtime` session |
| `require_workspace_member` / `require_workspace_admin` | Authz guards |
| `get_current_worker` | Machine auth from worker credential |
| `AsyncSessionLocal` | Service-role/owner session **only after** authz guard when RLS denies writes |

Do not open owner sessions from routes without a prior admin/worker authenticity check.

## REST practices

- Nouns for resources; HTTP verbs for actions (`POST` claim/ack where RPC-style machine ops are intentional and documented).
- Idempotent `PUT` for upserts where applicable; `PATCH` for partial updates with optional fields.
- Conflict → `409` with stable `code` when domain conflicts (lease, effect key, version).
- Validation → `422` via Pydantic; do not hand-roll what Pydantic already enforces.

## Schemas

- Pydantic v2 models in `app/schemas/`.
- `ConfigDict(from_attributes=True)` for ORM outs.
- `extra="forbid"` on inbound capability/protocol payloads when rejecting unknown fields matters.
- Never accept `workspace_id` from the body when it is already in the path + membership context (prefer path + guard).

## Service boundaries

```text
route handler
  authenticates / authorizes
  calls orchestration function(s) inside one session/transaction
  maps domain errors → HTTP
  emits audit at the edge when appropriate
```

Keep SQLAlchemy queries out of routers when logic is non-trivial — put them in orchestration/services.

## OpenAPI

- Meaningful `tags`, summaries via docstrings/function names.
- Document auth schemes used by machine vs user routes.
- Keep response models accurate so generated OpenAPI matches reality (no phantom fields).
