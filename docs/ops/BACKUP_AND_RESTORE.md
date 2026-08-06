# Postgres backup and restore

Content Orchestrator stores all durable product state in Postgres.
Treat backup and restore as a launch dependency, not a post-beta nicety.

## Strategy

### 1. Logical dumps (`pg_dump`) — portable / drill-friendly

Use for:

- Pre-migration snapshots
- Cross-environment copies (staging → local)
- Quarterly restore drills

Example (local compose / self-hosted):

```bash
# Custom format (supports parallel restore)
docker compose -f docker-compose.staging.yml exec -T postgres \
  pg_dump -U postgres -d content_orchestrator -Fc -f /tmp/co.dump

docker compose -f docker-compose.staging.yml cp postgres:/tmp/co.dump ./backups/co-$(date +%Y%m%d).dump
```

Plain SQL (human-readable, slower):

```bash
docker compose exec -T postgres \
  pg_dump -U postgres -d content_orchestrator --no-owner --no-acl \
  > backups/co-$(date +%Y%m%d).sql
```

Schedule nightly dumps off-host (object storage) with retention ≥ 30 days
for staging; longer for production.

### 2. Managed PITR — production default

Prefer a managed Postgres with continuous WAL archiving / point-in-time
recovery (PITR), for example:

- **Supabase** — project backups + PITR on qualifying plans; restore via
  dashboard / support path documented by Supabase
- **AWS RDS / Aurora** — automated backups + PITR to a timestamp
- **GCP Cloud SQL** — same pattern

Operational expectations for production:

| Control | Target |
|---------|--------|
| RPO | ≤ 15 minutes (WAL/PITR) or ≤ 24h if dump-only staging |
| RTO | Documented restore path exercised quarterly |
| Retention | ≥ 7 days PITR; ≥ 30 days weekly base backups |
| Encryption | At rest (provider default) + in transit (TLS) |

Do **not** rely solely on the Docker volume for `postgres_data` — volumes
are not backups.

## Restore steps

### A. Restore a `pg_dump` custom-format file (self-hosted / staging)

1. Stop API and worker writers (compose: stop `api` and `worker`).
2. Recreate or empty the target database:

   ```bash
   docker compose -f docker-compose.staging.yml exec -T postgres \
     psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'content_orchestrator' AND pid <> pg_backend_pid();"
   docker compose -f docker-compose.staging.yml exec -T postgres \
     psql -U postgres -c "DROP DATABASE IF EXISTS content_orchestrator;"
   docker compose -f docker-compose.staging.yml exec -T postgres \
     psql -U postgres -c "CREATE DATABASE content_orchestrator OWNER postgres;"
   ```

3. Restore:

   ```bash
   docker compose -f docker-compose.staging.yml cp ./backups/co-YYYYMMDD.dump postgres:/tmp/co.dump
   docker compose -f docker-compose.staging.yml exec -T postgres \
     pg_restore -U postgres -d content_orchestrator --clean --if-exists /tmp/co.dump
   ```

4. Confirm role + migrations:

   ```bash
   # app_runtime must exist (created by migration 0001 or retained in dump)
   docker compose -f docker-compose.staging.yml exec -T postgres \
     psql -U postgres -d content_orchestrator -c "\du app_runtime"
   cd apps/api && alembic current
   ```

5. Start API/worker; hit `/health/ready`.
6. Smoke-test an authenticated read (workspace list or Review Desk).

### B. Managed PITR restore

1. Choose restore timestamp (incident time minus safety margin).
2. Restore to a **new** instance/project when the provider supports it
   (prefer side-by-side validation over in-place overwrite).
3. Point staging/prod `DATABASE_URL` / `APP_DATABASE_URL` at the restored
   instance; rotate credentials if the incident involved credential leak.
4. Run `/health/ready`, then application smoke tests.
5. Only after validation, cut DNS/config over and decommission the bad
   primary per provider runbooks.

## What to verify after restore

- [ ] `alembic current` matches expected head (or intentionally older if
      restoring pre-migration)
- [ ] `app_runtime` can connect (`APP_DATABASE_URL`)
- [ ] RLS still enforced (non-member cannot read another workspace)
- [ ] Worker credentials / registry rows present if workers were in use
- [ ] Outbox / review gates look coherent for in-flight work

## Quarterly restore drill checklist

| Step | Owner | Done |
|------|-------|------|
| Pick a recent backup or PITR timestamp | Platform | ☐ |
| Restore into an isolated environment (not prod) | Platform | ☐ |
| Record wall-clock RTO | Platform | ☐ |
| Run `/health/live` + `/health/ready` | Platform | ☐ |
| Authenticated API smoke (one workspace read) | Platform | ☐ |
| Confirm a known content/review row exists | Product eng | ☐ |
| File gaps (missing WAL, bad retention, doc drift) | Platform | ☐ |
| Update this doc if the procedure changed | Platform | ☐ |

Store drill notes (date, RTO, backup id, issues) in the team ops channel
or incident tracker — not only in chat.

## Secrets and dumps

- Dump files contain PII and credentials metadata; encrypt at rest and
  restrict bucket ACLs.
- Never commit dumps to git.
- After a security incident, rotate `SUPABASE_JWT_SECRET` (forces re-login),
  worker credentials, and DB passwords **after** restore from a clean point.
