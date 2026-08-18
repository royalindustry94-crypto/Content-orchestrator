#!/usr/bin/env bash
# Replit one-click entry: migrate, seed, run API + web on Replit's public port.
# Web listens on PORT (default 5000); API on 8000; Vite proxies /api → API.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${OPS_PREVIEW_EMAIL:?Set OPS_PREVIEW_EMAIL in .env for the local preview}"
: "${OPS_PREVIEW_PASSWORD:?Set OPS_PREVIEW_PASSWORD in .env for the local preview}"
export OPS_PREVIEW_EMAIL OPS_PREVIEW_PASSWORD

export ENVIRONMENT="${ENVIRONMENT:-development}"
export AUTH_MODE="${AUTH_MODE:-local}"
WEB_PORT="${PORT:-5000}"
if [[ -z "${CORS_ALLOW_ORIGINS:-}" ]] || ! python3 -c 'import json,os; json.loads(os.environ["CORS_ALLOW_ORIGINS"])' 2>/dev/null; then
  export CORS_ALLOW_ORIGINS="[\"http://localhost:${WEB_PORT}\",\"http://127.0.0.1:${WEB_PORT}\"]"
fi

# Replit Postgres defaults when DATABASE_URL unset
if [[ -z "${DATABASE_URL:-}" ]]; then
  export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/content_orchestrator"
fi
if [[ -z "${APP_DATABASE_URL:-}" ]]; then
  export APP_DATABASE_URL="postgresql://app_runtime:app_runtime@127.0.0.1:5432/content_orchestrator"
fi
if [[ -z "${SUPABASE_JWT_SECRET:-}" ]]; then
  export SUPABASE_JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  echo "SUPABASE_JWT_SECRET=$SUPABASE_JWT_SECRET" >> .env
fi

echo "==> Waiting for Postgres"
for i in $(seq 1 60); do
  if pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
pg_isready -h 127.0.0.1 -p 5432

echo "==> Migrating"
(cd apps/api && alembic upgrade head && alembic current)

echo "==> Starting API :8000"
(cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port 8000) &
API_PID=$!

echo "==> Starting web :${WEB_PORT}"
(cd apps/web && npm run dev -- --host 0.0.0.0 --port "$WEB_PORT" --strictPort) &
WEB_PID=$!

cleanup() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT

for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:8000/health/ready" >/dev/null \
    && curl -sf "http://127.0.0.1:${WEB_PORT}/" >/dev/null; then
    break
  fi
  sleep 1
done

echo "==> Seeding demo data"
API_BASE_URL=http://127.0.0.1:8000 python3 scripts/seed_ops_preview.py || true

echo "Replit preview on port ${WEB_PORT}; preview credentials are supplied through OPS_PREVIEW_ environment variables and are not echoed"
wait
