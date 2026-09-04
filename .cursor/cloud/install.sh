#!/usr/bin/env bash
# Idempotent Cursor Cloud snapshot setup for The Business Manager.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PG_MAJOR="${PG_MAJOR:-16}"
DEV_DB=content_orchestrator
TEST_DB=content_orchestrator_test
LOCAL_RUNTIME_PASSWORD=app_runtime
cd "$ROOT"

create_local_env() {
  if [[ -f .env ]]; then
    return
  fi
  local jwt_secret
  jwt_secret="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  {
    printf 'ENVIRONMENT=development\n'
    printf 'LOG_LEVEL=INFO\n'
    printf 'DATABASE_URL=postgresql://postgres:postgres@localhost:5432/%s\n' "$DEV_DB"
    printf 'APP_DATABASE_URL=postgresql://app_runtime:%s@localhost:5432/%s\n' "$LOCAL_RUNTIME_PASSWORD" "$DEV_DB"
    printf 'AUTH_MODE=local\n'
    printf 'SUPABASE_JWT_SECRET=%s\n' "$jwt_secret"
    printf 'SUPABASE_JWT_ALGORITHM=HS256\n'
    printf 'SUPABASE_JWT_AUDIENCE=authenticated\n'
    printf "CORS_ALLOW_ORIGINS='[\"http://localhost:5173\",\"http://127.0.0.1:5173\"]'\n"
    printf 'DEFAULT_DAILY_SPEND_CAP_USD=50.0\n'
    printf 'DEFAULT_MONTHLY_SPEND_CAP_USD=1000.0\n'
    printf 'HEALTH_CHECK_INTERVAL_SECONDS=300\n'
    printf 'API_BASE_URL=http://127.0.0.1:8000\n'
  } >.env
  chmod 600 .env
}

printf '==> Installing PostgreSQL %s and Python venv support\n' "$PG_MAJOR"
if ! dpkg -s "postgresql-$PG_MAJOR" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    "postgresql-$PG_MAJOR" "postgresql-client-$PG_MAJOR" python3-venv
fi

printf '==> Starting PostgreSQL\n'
sudo pg_ctlcluster "$PG_MAJOR" main start 2>/dev/null || true
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then
    break
  fi
  sleep 1
done
sudo -u postgres pg_isready

printf '==> Creating local-only environment configuration\n'
create_local_env
set -a
# shellcheck disable=SC1091
source .env
set +a
LOCAL_RUNTIME_PASSWORD="$(python3 - <<'PY'
import os
from urllib.parse import unquote, urlparse

parsed = urlparse(os.environ["APP_DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1))
if not parsed.password:
    raise SystemExit("APP_DATABASE_URL must include the local app_runtime password")
print(unquote(parsed.password))
PY
)"

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

printf '==> Preparing local databases\n'
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER ROLE postgres WITH PASSWORD 'postgres';"
for database in "$DEV_DB" "$TEST_DB"; do
  if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$database'" | grep -q 1; then
    sudo -u postgres createdb "$database"
  fi
  if [[ -f scripts/bootstrap_local_postgres.sql ]]; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 \
      -v app_runtime_password="$LOCAL_RUNTIME_PASSWORD" \
      -d "$database" -f scripts/bootstrap_local_postgres.sql >/dev/null
  fi
done

printf '==> Installing Python and web dependencies\n'
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip -q
python -m pip install -e "apps/api[dev]" -e "apps/worker[dev]"
(cd apps/web && npm ci)

printf '==> Applying dev and test migrations\n'
(cd apps/api && alembic upgrade head)
(cd apps/api \
  && DATABASE_URL="$TEST_DATABASE_URL" \
     APP_DATABASE_URL="$TEST_APP_DATABASE_URL" \
     alembic upgrade head)

printf '==> Cursor Cloud environment installed\n'
