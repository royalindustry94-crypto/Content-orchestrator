#!/usr/bin/env bash
# CEO advisory release gate for Content Orchestrator.
# Exit 0 = checks passed (CEO may still REJECT for product reasons).
# Exit 1 = hard gate failure.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

red() { printf 'FAIL %s\n' "$*" >&2; }
ok() { printf 'OK   %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*" >&2; }

FAILED=0

fail() {
  red "$1"
  FAILED=1
}

echo "=== CEO release gate (advisory) ==="
echo "repo: $ROOT"

# --- placeholders in production trees ---
if command -v rg >/dev/null 2>&1; then
  if rg -n -i --glob '!**/node_modules/**' --glob '!**/.venv/**' \
      -e '\b(TODO|FIXME|XXX)\b' -e 'NotImplementedError' \
      apps/api/app apps/worker/worker apps/web/src 2>/dev/null | head -40 | grep -q .; then
    warn "placeholder-like markers found (review manually):"
    rg -n -i --glob '!**/node_modules/**' --glob '!**/.venv/**' \
      -e '\b(TODO|FIXME|XXX)\b' -e 'NotImplementedError' \
      apps/api/app apps/worker/worker apps/web/src 2>/dev/null | head -40 || true
  else
    ok "no TODO/FIXME/XXX/NotImplementedError greps in app trees"
  fi
else
  warn "rg not installed; skipped placeholder grep"
fi

# --- API tooling ---
if [[ -d apps/api ]]; then
  export PATH="${HOME}/.local/bin:${PATH}"
  if command -v ruff >/dev/null 2>&1; then
    (cd apps/api && ruff check app tests) && ok "api ruff" || fail "api ruff"
  else
    warn "ruff not available"
  fi
  if command -v alembic >/dev/null 2>&1; then
    (cd apps/api && alembic current) && ok "alembic current" || fail "alembic current"
  else
    warn "alembic not available"
  fi
  if command -v pytest >/dev/null 2>&1 || python3 -m pytest --version >/dev/null 2>&1; then
    (cd apps/api && python3 -m pytest -W error -q --tb=line) && ok "api pytest -W error" || fail "api pytest"
  else
    warn "pytest not available"
  fi
fi

# --- worker ---
if [[ -d apps/worker ]]; then
  if command -v ruff >/dev/null 2>&1; then
    (cd apps/worker && ruff check .) && ok "worker ruff" || fail "worker ruff"
  fi
  if python3 -m pytest --version >/dev/null 2>&1; then
    (cd apps/worker && python3 -m pytest -q) && ok "worker pytest" || fail "worker pytest"
  fi
fi

# --- web (if tooling present) ---
if [[ -f apps/web/package.json ]] && command -v npm >/dev/null 2>&1; then
  if [[ -d apps/web/node_modules ]]; then
    (cd apps/web && npm run lint) && ok "web lint" || fail "web lint"
  else
    warn "apps/web/node_modules missing; skipped web lint"
  fi
fi

echo "=== summary ==="
if [[ "$FAILED" -ne 0 ]]; then
  red "CEO gate FAILED — do not VERIFIED / merge"
  exit 1
fi
ok "CEO gate PASSED (advisory) — CEO still issues final verdict"
exit 0
