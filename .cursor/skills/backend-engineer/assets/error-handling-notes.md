# Error handling notes

## Principles

1. **Fail closed** on authz, spend, lease ownership, and isolation violations.
2. **Explicit outcomes** for expected non-success (claim `no_work` / `capacity`) — still audited.
3. **Durable signal** when work cannot proceed (outbox, DLQ, pause_reason).
4. **Never** empty `except:` / `except Exception: pass` in production paths.
5. Maintenance loops may catch broad exceptions to **survive the tick**, but must `logger.exception` and not mark work successful.

## HTTP mapping (typical)

| Situation | Status |
|---|---|
| Validation | 422 |
| Unauthenticated | 401 |
| Unauthorized | 403 |
| Missing resource (or concealed) | 404 |
| State conflict / lease / idempotency | 409 |
| Upstream/deps unavailable | 503 |
| Unexpected bug | 500 (logged; no secret leakage) |

## Domain errors

Prefer small exception types with `code` + `message` (see lease errors) and translate in routers.

## Client body shape

Prefer stable JSON:

```json
{ "detail": "human readable", "code": "lease_expired" }
```

or FastAPI defaults where already pervasive — **match existing routes** in the area you edit; do not invent a second global error envelope without an ADR.
