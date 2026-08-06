#!/usr/bin/env bash
# Host-run Ops Dashboard preview (when nested Docker cannot build images).
# Prerequisites: Postgres accepting DATABASE_URL, Node + Python deps installed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — set SUPABASE_JWT_SECRET before continuing."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

export ENVIRONMENT="${ENVIRONMENT:-development}"
export AUTH_MODE="${AUTH_MODE:-local}"
export CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-[\"http://localhost:5173\",\"http://127.0.0.1:5173\",\"http://localhost:8080\"]}"

echo "==> Migrating database"
(cd apps/api && alembic upgrade head && alembic current)

echo "==> Starting API on :8000 (background)"
(cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
API_PID=$!

echo "==> Starting web on :5173 (background)"
(cd apps/web && npm run dev -- --host 0.0.0.0 --port 5173 --strictPort) &
WEB_PID=$!

cleanup() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT

for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/health/ready >/dev/null \
    && curl -sf http://127.0.0.1:5173/ >/dev/null; then
    break
  fi
  sleep 1
done

echo "==> Seeding demo admin + ops data"
API_BASE_URL=http://127.0.0.1:8000 python3 scripts/seed_ops_preview.py

cat <<EOF

Preview ready
  Preview URL:      http://localhost:5173/
  Admin login URL:  http://localhost:5173/
  Username:         founder@lumora.local
  Password:         lumora-demo-2026

Staging compose (on a host with working Docker Engine):
  docker compose -f docker-compose.staging.yml up --build
  then open http://localhost:8080/ and run:
  API_BASE_URL=http://127.0.0.1:8000 python3 scripts/seed_ops_preview.py

Ctrl+C to stop.
EOF

wait
