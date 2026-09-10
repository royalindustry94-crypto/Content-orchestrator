#!/usr/bin/env bash
# Cloud Agent start: per-boot reconciliation. Brings up the PostgreSQL cluster
# (its data directory is durable in the snapshot, but the server process is
# not) and reconciles the schema to head. Idempotent and safe to re-run; must
# return once the database is ready. Long-running dev servers live in terminals.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PG_MAJOR=16
TEST_DB=content_orchestrator_test

echo "==> Starting PostgreSQL ${PG_MAJOR} cluster"
sudo pg_ctlcluster "${PG_MAJOR}" main start 2>/dev/null || true
ready=0
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then ready=1; break; fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "PostgreSQL failed readiness check" >&2
  exit 1
fi

# Migrate-on-start: the DB data dir is snapshot-durable, but a branch may add
# migrations after the snapshot was built. alembic upgrade head is a fast no-op
# when already current. Mirrors the repo's staging entrypoint (RUN_MIGRATIONS).
if [ -d .venv ] && [ -f .env ]; then
  echo "==> Reconciling schema (alembic upgrade head)"
  # shellcheck disable=SC1091
  . .venv/bin/activate
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
  ( cd apps/api && alembic upgrade head )
  ( cd apps/api \
    && DATABASE_URL="postgresql://postgres:postgres@localhost:5432/${TEST_DB}" \
       APP_DATABASE_URL="postgresql://app_runtime:app_runtime@localhost:5432/${TEST_DB}" \
       alembic upgrade head )
fi

echo "==> start complete; database ready on localhost:5432"
