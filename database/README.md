# database/

Non-application-code database assets: seed data scripts, one-off data
migrations/backfills that don't belong in Alembic's schema-migration
history, and ER diagrams. Schema migrations themselves live in
`apps/api/alembic/versions/` since Alembic needs them colocated with the
SQLAlchemy models they're generated from.

Empty until the data model milestone.
