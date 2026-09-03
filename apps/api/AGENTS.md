# API agent guidance

This file adds API-specific guidance to the repository-root `AGENTS.md`.

- Keep route functions thin. Put domain behavior in services/orchestration modules and make transaction boundaries explicit.
- Every workspace route requires membership or role authorization before data access. Include negative outsider and cross-workspace tests.
- Runtime request paths should use the RLS-bound runtime session. Owner sessions require an explicit reason, a workspace predicate, and isolation tests.
- Validate external inputs with bounded Pydantic schemas. Avoid leaking secrets, SQL details, internal exceptions, or cross-tenant existence through errors.
- Reserve spend before provider work and commit no more than the reservation. Cap and provider failures must fail closed.
- Any publishable artifact must enter the Human Review Gate. Internal workflow completion must not imply external publication.
- Security-relevant mutations emit structured audit events without tokens, passwords, raw authorization headers, or provider payload secrets.

From `apps/api`, run `ruff check .` and `pytest --cov=app --cov-fail-under=75`. Database and RLS claims require real PostgreSQL.
