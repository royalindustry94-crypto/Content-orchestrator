#!/usr/bin/env bash
# Deterministic local evidence runner for coding agents and humans.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-quick}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${AGENT_CHECK_OUT:-$ROOT/validation-logs/agent-check/$STAMP}"
RESULTS_FILE="$EVIDENCE_DIR/results.txt"
LOG_FILE="$EVIDENCE_DIR/run.log"
mkdir -p "$EVIDENCE_DIR"
touch "$RESULTS_FILE"
NOT_RUN_COUNT=0

usage() {
  printf '%s\n' \
    "Usage: scripts/agent-check.sh [identity|quick|full]" \
    "" \
    "identity  Report branch, exact SHA, tree, dirty state, and Alembic heads." \
    "quick     Run API/worker lint+tests and web lint+test+build." \
    "full      Replay migrations on a localhost *_test DB, run coverage," \
    "          dependency audits, browser smoke when Chrome is available," \
    "          and Docker/Gitleaks when installed." \
    "" \
    "Evidence is written under validation-logs/agent-check/."
}

if [[ "$MODE" == "-h" || "$MODE" == "--help" ]]; then
  usage
  exit 0
fi
if [[ "$MODE" != "identity" && "$MODE" != "quick" && "$MODE" != "full" ]]; then
  usage >&2
  exit 2
fi

exec > >(tee -a "$LOG_FILE") 2>&1

record() {
  printf '%s\n' "$*" | tee -a "$RESULTS_FILE"
}

not_run() {
  NOT_RUN_COUNT=$((NOT_RUN_COUNT + 1))
  record "NOT-RUN  $*"
}

step() {
  local label="$1"
  shift
  printf '\n==> %s\n' "$label"
  if "$@"; then
    record "PASS  $label"
  else
    local status=$?
    record "FAIL  $label (exit $status)"
    return "$status"
  fi
}

report_identity() {
  local branch dirty migration_heads
  branch="$(git -C "$ROOT" branch --show-current)"
  dirty="no"
  if [[ -n "$(git -C "$ROOT" status --porcelain=v1)" ]]; then
    dirty="yes"
  fi
  if [[ -x "$ROOT/.venv/bin/alembic" ]]; then
    migration_heads="$(cd "$ROOT/apps/api" && "$ROOT/.venv/bin/alembic" heads 2>/dev/null || printf 'unavailable')"
  elif command -v alembic >/dev/null 2>&1; then
    migration_heads="$(cd "$ROOT/apps/api" && alembic heads 2>/dev/null || printf 'unavailable')"
  else
    migration_heads="unavailable"
  fi
  {
    printf 'branch=%s\n' "${branch:-DETACHED}"
    printf 'head=%s\n' "$(git -C "$ROOT" rev-parse HEAD)"
    printf 'tree=%s\n' "$(git -C "$ROOT" rev-parse 'HEAD^{tree}')"
    printf 'dirty=%s\n' "$dirty"
    printf 'migration_heads=%s\n' "$migration_heads"
    printf 'mode=%s\n' "$MODE"
    printf 'evidence_dir=%s\n' "$EVIDENCE_DIR"
  } | tee "$EVIDENCE_DIR/identity.txt"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Required command not found: %s\n' "$1" >&2
    return 1
  fi
}

activate_python() {
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    # shellcheck disable=SC1091
    source "$ROOT/.venv/bin/activate"
  fi
  require_command python3
  require_command ruff
  require_command pytest
  require_command alembic
}

configure_test_environment() {
  export DATABASE_URL="${AGENT_CHECK_DATABASE_URL:-postgresql://postgres:postgres@127.0.0.1:5432/content_orchestrator_test}"
  export APP_DATABASE_URL="${AGENT_CHECK_APP_DATABASE_URL:-postgresql://app_runtime:app_runtime@127.0.0.1:5432/content_orchestrator_test}"
  export TEST_DATABASE_URL="$DATABASE_URL"
  export TEST_APP_DATABASE_URL="$APP_DATABASE_URL"
  export SUPABASE_JWT_SECRET="${SUPABASE_JWT_SECRET:-agent-check-local-jwt-secret-at-least-32-characters}"
  export ENVIRONMENT=test
  export AUTH_MODE=local
}

verify_disposable_database() {
  python3 - <<'PY'
import os
import sys
from urllib.parse import urlparse

targets = set()
expected_users = {"DATABASE_URL": "postgres", "APP_DATABASE_URL": "app_runtime"}
for variable in ("DATABASE_URL", "APP_DATABASE_URL"):
    raw = os.environ[variable].replace("postgresql+asyncpg://", "postgresql://", 1)
    url = urlparse(raw)
    database = url.path.removeprefix("/")
    if url.hostname not in {"127.0.0.1", "localhost"} or not database.endswith("_test"):
        print(
            f"Refusing database checks: {variable} must target localhost and a database ending in _test",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if url.username != expected_users[variable]:
        print(
            f"Refusing database checks: {variable} must use the {expected_users[variable]} role",
            file=sys.stderr,
        )
        raise SystemExit(2)
    targets.add((url.hostname, url.port or 5432, database))
if len(targets) != 1:
    print(
        "Refusing database checks: owner and runtime URLs must target the same local endpoint and test database",
        file=sys.stderr,
    )
    raise SystemExit(2)
PY
}

run_browser_smoke() {
  local chrome_bin api_pid="" web_pid="" chrome_pid=""
  chrome_bin="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"
  if [[ -z "$chrome_bin" ]]; then
    printf 'Chrome/Chromium unavailable\n' >&2
    return 127
  fi

  export CORS_ALLOW_ORIGINS='["http://127.0.0.1:5173","http://localhost:5173"]'
  export OPS_PREVIEW_EMAIL=agent-smoke@example.com
  export OPS_PREVIEW_PASSWORD=agent-smoke-password-2026
  export DEMO_EMAIL="$OPS_PREVIEW_EMAIL"
  export DEMO_PASSWORD="$OPS_PREVIEW_PASSWORD"
  export UI_SMOKE_BASE=http://127.0.0.1:5173
  export UI_SMOKE_OUT="$EVIDENCE_DIR/browser"
  mkdir -p "$UI_SMOKE_OUT"

  if ! python3 - <<'PY'
import socket

sockets = []
try:
    for port in (8000, 5173, 9222):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(("127.0.0.1", port))
        except OSError as exc:
            raise SystemExit(f"Refusing browser smoke: local port {port} is already occupied: {exc}")
        sockets.append(server)
finally:
    for server in sockets:
        server.close()
PY
  then
    return 1
  fi

  (
    cd "$ROOT/apps/api"
    exec uvicorn app.main:app --host 127.0.0.1 --port 8000
  ) >"$UI_SMOKE_OUT/api.log" 2>&1 &
  api_pid=$!
  (
    cd "$ROOT/apps/web"
    exec npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
  ) >"$UI_SMOKE_OUT/web.log" 2>&1 &
  web_pid=$!
  "$chrome_bin" --headless=new --no-sandbox --disable-dev-shm-usage \
    --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 about:blank \
    >"$UI_SMOKE_OUT/chrome.log" 2>&1 &
  chrome_pid=$!

  cleanup_browser() {
    local process
    trap - RETURN
    for process in "$api_pid" "$web_pid" "$chrome_pid"; do
      if [[ -n "$process" ]]; then
        kill "$process" 2>/dev/null || true
      fi
    done
  }
  trap cleanup_browser RETURN

  local ready=0
  for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8000/health/ready >/dev/null \
      && curl -sf http://127.0.0.1:5173/ >/dev/null \
      && curl -sf http://127.0.0.1:9222/json/version >/dev/null; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "$ready" -ne 1 ]]; then
    printf 'Browser-smoke services failed readiness; see %s\n' "$UI_SMOKE_OUT" >&2
    return 1
  fi

  local smoke_status=0
  API_BASE_URL=http://127.0.0.1:8000 python3 "$ROOT/scripts/seed_ops_preview.py" \
    >"$UI_SMOKE_OUT/seed.log" 2>&1 || smoke_status=$?
  if [[ "$smoke_status" -eq 0 ]]; then
    node "$ROOT/scripts/ui_smoke_cdp.mjs" 2>&1 \
      | tee "$UI_SMOKE_OUT/smoke.log" || smoke_status=$?
  fi
  return "$smoke_status"
}

cd "$ROOT"
report_identity

if [[ "$MODE" == "identity" ]]; then
  record "PASS  Identity recorded"
  exit 0
fi

configure_test_environment
verify_disposable_database
activate_python
require_command npm

step "Alembic upgrade head on disposable test database" bash -c 'cd apps/api && alembic upgrade head'
step "API lint" bash -c 'cd apps/api && ruff check .'
if [[ "$MODE" == "quick" ]]; then
  step "API tests" bash -c 'cd apps/api && pytest'
else
  step "Alembic downgrade base on disposable test database" bash -c 'cd apps/api && alembic downgrade base'
  step "Alembic re-upgrade head on disposable test database" bash -c 'cd apps/api && alembic upgrade head'
  step "API tests with coverage gate" bash -c 'cd apps/api && pytest --cov=app --cov-fail-under=75'
fi

step "Worker lint" bash -c 'cd apps/worker && ruff check .'
step "Worker tests" bash -c 'cd apps/worker && pytest'
step "Web lint" bash -c 'cd apps/web && npm run lint'
step "Web tests" bash -c 'cd apps/web && npm test'
step "Web typecheck and build" bash -c 'cd apps/web && npm run build'

if [[ "$MODE" == "full" ]]; then
  step "Web dependency audit" bash -c 'cd apps/web && npm audit --audit-level=high'
  step "API dependency audit" bash -c 'cd apps/api && pip-audit --progress-spinner off'
  step "Worker dependency audit" bash -c 'cd apps/worker && pip-audit --progress-spinner off'
  if command -v google-chrome >/dev/null 2>&1 \
    || command -v chromium >/dev/null 2>&1 \
    || command -v chromium-browser >/dev/null 2>&1; then
    step "Browser smoke" run_browser_smoke
  else
    not_run "Browser smoke (Chrome/Chromium unavailable)"
  fi

  if command -v gitleaks >/dev/null 2>&1; then
    step "Gitleaks repository scan" gitleaks detect --source "$ROOT" --no-banner
  else
    not_run "Gitleaks repository scan (gitleaks unavailable)"
  fi

  if command -v docker >/dev/null 2>&1; then
    step "API Docker build" docker build -t content-orchestrator-api:agent-check "$ROOT/apps/api"
    step "Worker Docker build" docker build -t content-orchestrator-worker:agent-check "$ROOT/apps/worker"
    step "Web Docker build" docker build -t content-orchestrator-web:agent-check "$ROOT/apps/web"
  else
    not_run "Docker image builds (docker unavailable)"
  fi
fi

if [[ "$NOT_RUN_COUNT" -gt 0 ]]; then
  record "PARTIAL  agent-check $MODE completed with $NOT_RUN_COUNT unavailable check group(s)"
  printf '\nEvidence: %s\n' "$EVIDENCE_DIR"
  exit 3
fi

record "PASS  agent-check $MODE completed with no unavailable checks"
printf '\nEvidence: %s\n' "$EVIDENCE_DIR"
