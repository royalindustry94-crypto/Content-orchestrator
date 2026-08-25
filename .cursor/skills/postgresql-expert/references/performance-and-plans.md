# Performance & query plans

## Review before merge

For new or changed hot paths (claim, schedule, spend, admin lists):

1. Identify predicates and sort order
2. Ensure a supporting index (often **partial**)
3. Reject unbounded `SELECT` without `LIMIT` on growing tables in loops
4. Watch for ORM N+1 — use targeted selects; avoid lazy loads in async request paths

## EXPLAIN discipline

- Use `EXPLAIN (ANALYZE, BUFFERS)` on staging/dev Postgres with realistic row counts when adding queue indexes
- Look for Seq Scan on large tables where Index Scan expected
- Nested Loop + repeated scans → possible missing index or N+1 pattern

## Anti-patterns

- `COUNT(*)` on huge tables inside tight claim loops without need
- Locking large candidate batches when one-row `SKIP LOCKED` + savepoint skip suffices
- Functions on indexed columns that defeat index use (`WHERE date_trunc(...)`) without matching expression index
- Over-indexing write-heavy append-only ledgers

## Dependencies

Do not introduce caching layers as a substitute for missing indexes without `/chief-architect` — Postgres SoT and correct indexes come first.
