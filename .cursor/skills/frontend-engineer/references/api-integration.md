# API integration — frontend

## Source of truth

- **FastAPI / OpenAPI** defines operations, status codes, and DTOs
- Do **not** invent endpoints, query params, or response fields
- If the UI needs data the API lacks → escalate `/backend-engineer` (and Architect if contract shape is new)

## Client patterns

1. Use a typed fetch/client layer (generated or hand-typed from OpenAPI)
2. Attach auth and workspace headers/context exactly as the backend contract requires
3. Map errors:
   - **4xx** → user-visible message; retry only if idempotent and product-safe
   - **401/403** → session/permission UX; do not fake success
   - **5xx / network** → error + retry when safe
4. Never catch-and-ignore

## Async / jobs

Backend work is often async. UI should:

- Show in-progress / queued / failed / needs-review states from API enums
- Poll or refresh on an explicit interval/user action — do not pretend completion
- Keep Review Gate items actionable only when API says they are actionable

## RBAC and tenancy (client)

| UI may | UI must not |
|--------|-------------|
| Hide/disable actions lacking permission | Rely on hiding as the only control |
| Scope lists to active workspace | Accept workspace ids from untrusted query strings without server checks |
| Show “forbidden” from 403 | Soft-fail into another tenant’s cached data |

## Testing API wiring

- Prefer tests that assert request shaping and error UI with mocked fetch **in unit tests**
- Do not ship the app pointed at mock servers as production
- Contract mismatches found in UI work → file for Backend; status NOT VERIFIED if blocked
