#!/usr/bin/env bash
# One command to get a testable stack running: database, migrations, API,
# worker, and web. Safe to re-run; every step is idempotent.
#
#   scripts/dev_up.sh                  # default: no content provider configured
#   scripts/dev_up.sh --simulation     # deterministic offline provider, so the
#                                      # whole pipeline produces visible output
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROVIDER_MODE="null"
for arg in "$@"; do
  case "$arg" in
    --simulation) PROVIDER_MODE="simulation" ;;
    --null) PROVIDER_MODE="null" ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n==> %s\n' "$1"; }

if [[ ! -f .env ]]; then
  log "Creating .env from .env.example"
  cp .env.example .env
fi

if ! grep -qE '^SUPABASE_JWT_SECRET=.+' .env; then
  SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  if grep -qE '^SUPABASE_JWT_SECRET=' .env; then
    python3 - "$SECRET" <<'PY'
import pathlib, sys
secret = sys.argv[1]
path = pathlib.Path(".env")
lines = path.read_text().splitlines(keepends=True)
path.write_text("".join(
    f"SUPABASE_JWT_SECRET={secret}\n" if line.startswith("SUPABASE_JWT_SECRET=") else line
    for line in lines
))
PY
  else
    printf 'SUPABASE_JWT_SECRET=%s\n' "$SECRET" >> .env
  fi
  log "Generated SUPABASE_JWT_SECRET in .env"
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

export ENVIRONMENT="${ENVIRONMENT:-development}"
export AUTH_MODE="${AUTH_MODE:-local}"
export PIPELINE_PROVIDER_MODE="$PROVIDER_MODE"
export DATABASE_URL="${DATABASE_URL:?DATABASE_URL must be set in .env}"
export APP_DATABASE_URL="${APP_DATABASE_URL:?APP_DATABASE_URL must be set in .env}"
if [[ -z "${CORS_ALLOW_ORIGINS:-}" ]] || ! python3 -c 'import json,os; json.loads(os.environ["CORS_ALLOW_ORIGINS"])' 2>/dev/null; then
  export CORS_ALLOW_ORIGINS='["http://localhost:5173","http://127.0.0.1:5173"]'
fi

DB_HOST="$(python3 -c 'import os,urllib.parse as u; print(u.urlsplit(os.environ["DATABASE_URL"]).hostname or "127.0.0.1")')"
DB_PORT="$(python3 -c 'import os,urllib.parse as u; print(u.urlsplit(os.environ["DATABASE_URL"]).port or 5432)')"

wait_for_port() {
  for _ in $(seq 1 "$3"); do
    if (exec 3<>"/dev/tcp/$1/$2") 2>/dev/null; then exec 3>&- 3<&-; return 0; fi
    sleep 1
  done
  return 1
}

if wait_for_port "$DB_HOST" "$DB_PORT" 1; then
  log "Postgres already reachable on $DB_HOST:$DB_PORT"
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  log "Starting Postgres via Docker"
  docker compose up -d postgres
  wait_for_port "$DB_HOST" "$DB_PORT" 60 \
    || { echo "Postgres did not become reachable on $DB_HOST:$DB_PORT" >&2; exit 1; }
else
  cat >&2 <<EOF
No Postgres on $DB_HOST:$DB_PORT and no usable Docker.

Start one of:
  docker compose up -d postgres
  a local PostgreSQL 16 server matching DATABASE_URL in .env
EOF
  exit 1
fi

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
  PYTHON="$VIRTUAL_ENV/bin/python"
else
  log "Creating .venv"
  python3 -m venv "$ROOT/.venv"
  PYTHON="$ROOT/.venv/bin/python"
fi

log "Installing Python dependencies"
"$PYTHON" -m pip install -q --upgrade pip
"$PYTHON" -m pip install -q -e "apps/api[dev]" -e "apps/worker[dev]"

if [[ ! -d apps/web/node_modules ]]; then
  log "Installing web dependencies"
  (cd apps/web && npm install)
fi

# Canonical Alembic intentionally refuses to manufacture Supabase auth objects.
# Local/CI parity is bootstrapped explicitly. The bootstrap itself refuses to
# run against a managed Supabase project by detecting supabase_auth_admin.
log "Bootstrapping local Postgres parity"
"$PYTHON" - <<'PY'
import asyncio
import os
from pathlib import Path
import asyncpg

async def main() -> None:
    sql = Path("scripts/bootstrap_local_postgres.sql").read_text()
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute(sql)
    finally:
        await conn.close()

asyncio.run(main())
PY

log "Applying migrations"
(cd apps/api && "$PYTHON" -m alembic upgrade head >/dev/null && "$PYTHON" -m alembic current)

PIDS=()
cleanup() { kill "${PIDS[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

log "Starting API on :8000"
(cd apps/api && "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
PIDS+=($!)

log "Starting worker"
(cd apps/worker && "$PYTHON" -m worker.main) &
PIDS+=($!)

log "Starting web on :5173"
(cd apps/web && npm run dev -- --host 0.0.0.0 --port 5173 --strictPort) &
PIDS+=($!)

wait_for_port 127.0.0.1 8000 60 || { echo "API did not start" >&2; exit 1; }
wait_for_port 127.0.0.1 5173 60 || { echo "Web did not start" >&2; exit 1; }

cat <<EOF

Ready.

  Web              http://localhost:5173/
  API              http://localhost:8000/
  API docs         http://localhost:8000/docs
  Provider mode    $PIPELINE_PROVIDER_MODE

Create an account on the web app (password must be at least 12 characters).
Walkthrough: docs/TESTING_GUIDE.md

Ctrl+C stops everything.
EOF

wait
