# Performance review (queries & dependencies)

Before adding a hot-path query or a new dependency, answer:

## Queries

1. What is the expected cardinality (rows touched per call)?
2. Is there an index supporting `WHERE` + `ORDER BY` (including partial indexes)?
3. Does this run under a row lock? How long is the critical section?
4. Can it become a sequential scan under production volume (50 videos/day peak target; design for more)?
5. Are we counting (`COUNT(*)`) on a growing table inside a tight loop? Cache/materialize carefully or lock a control row instead.

## Patterns to prefer

- Partial indexes for queue states (`PENDING`, in-flight provider)
- `LIMIT` + `SKIP LOCKED` over locking huge candidate sets without savepoints
- Batch maintenance ticks with bounded `batch_size`
- Avoid SELECT * into ORM graphs when only ids/status needed

## Dependencies

- New package cost: size, security surface, async compatibility, maintenance.
- Reject deps that duplicate stdlib or existing project helpers.
- Never add a cache/queue client to “make it faster” if it becomes a second SoT — escalate to `/chief-architect`.

## When to measure

- New claim/dispatch ordering
- New per-request aggregations for admin dashboards
- Migration that rewrites large tables (batch; estimate lock time)

If unsure, add an index in the same migration as the query that needs it, with a comment citing the access path.
