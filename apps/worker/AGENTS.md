# Worker agent guidance

This file adds worker-specific guidance to the repository-root `AGENTS.md`.

- Preserve the claim → execute → submit contract and bounded concurrency.
- Execution must be idempotent across retries and duplicate delivery. External side effects need stable idempotency keys.
- Workers cannot approve Human Review gates or publish externally.
- Worker-reported cost must use the same units and provider semantics as the API reservation path and must never exceed the reservation.
- Keep workspace and job identity attached through every stage. Do not trust payload identity without server-side verification.
- Use bounded timeouts, retry/backoff, lease expiry, and structured errors. Never swallow failures or log credentials.

From `apps/worker`, run `ruff check .` and `pytest`.
