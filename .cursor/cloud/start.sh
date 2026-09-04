#!/usr/bin/env bash
# Per-boot Cursor Cloud reconciliation. Long-running services use terminals.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PG_MAJOR="${PG_MAJOR:-16}"
cd "$ROOT"

sudo pg_ctlcluster "$PG_MAJOR" main start 2>/dev/null || true
ready=0
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  printf 'PostgreSQL failed readiness\n' >&2
  exit 1
fi

if [[ -d .venv && -f .env ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  readarray -t LOCAL_DATABASE_URLS < <(python3 - <<'PY'
import os
from urllib.parse import urlsplit, urlunsplit


def local_url(variable: str, expected_user: str, database: str) -> str:
    raw = os.environ[variable].replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlsplit(raw)
    current_database = parsed.path.removeprefix("/")
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise SystemExit(f"{variable} must target localhost in Cursor Cloud")
    if (parsed.port or 5432) != 5432:
        raise SystemExit(f"{variable} must target the local PostgreSQL port 5432")
    if parsed.username != expected_user:
        raise SystemExit(f"{variable} must use the {expected_user} role in Cursor Cloud")
    if current_database != "content_orchestrator":
        raise SystemExit(f"{variable} must target content_orchestrator in Cursor Cloud")
    print(urlunsplit(parsed._replace(path=f"/{database}")))


local_url("DATABASE_URL", "postgres", "content_orchestrator_test")
local_url("APP_DATABASE_URL", "app_runtime", "content_orchestrator_test")
PY
  )
  TEST_DATABASE_URL="${LOCAL_DATABASE_URLS[0]}"
  TEST_APP_DATABASE_URL="${LOCAL_DATABASE_URLS[1]}"
  (cd apps/api && alembic upgrade head)
  (cd apps/api \
    && DATABASE_URL="$TEST_DATABASE_URL" \
       APP_DATABASE_URL="$TEST_APP_DATABASE_URL" \
       alembic upgrade head)
fi

printf 'Cursor Cloud database ready on localhost:5432\n'
