#!/usr/bin/env bash
# Backend Engineer advisory quality gate for Content Orchestrator.
# Exit 0 = checks passed (still require design/ADR discipline).
# Exit 1 = hard failure.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

ok() { printf 'OK   %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*" >&2; }
fail() { printf 'FAIL %s\n' "$*" >&2; FAILED=1; }
FAILED=0

echo "=== Backend Engineer quality gate (advisory) ==="

if command -v rg >/dev/null 2>&1; then
  if rg -n -i --glob '!**/node_modules/**' \
      -e '\b(TODO|FIXME|XXX)\b' -e 'except Exception:\s*pass' -e 'except:\s*pass' \
      apps/api/app apps/worker/worker 2>/dev/null | head -40 | grep -q .; then
    fail "TODO/FIXME/XXX or swallow-exception patterns found"
    rg -n -i --glob '!**/node_modules/**' \
      -e '\b(TODO|FIXME|XXX)\b' -e 'except Exception:\s*pass' -e 'except:\s*pass' \
      apps/api/app apps/worker/worker 2>/dev/null | head -40 || true
  else
    ok "no TODO/FIXME/XXX/except-pass in api/worker trees"
  fi
else
  warn "rg not installed; skipped placeholder grep"
fi

if [[ -d apps/api ]]; then
  if command -v ruff >/dev/null 2>&1; then
    (cd apps/api && ruff check app tests) && ok "api ruff" || fail "api ruff"
  else
    warn "ruff not available"
  fi
  if command -v alembic >/dev/null 2>&1; then
    (cd apps/api && alembic heads && alembic current) && ok "alembic heads/current" || fail "alembic"
  else
    warn "alembic not available"
  fi
  if python3 -m pytest --version >/dev/null 2>&1; then
    (cd apps/api && python3 -m pytest -W error -q --tb=line) && ok "api pytest -W error" || fail "api pytest"
  else
    warn "pytest not available"
  fi
fi

if [[ -d apps/worker ]]; then
  if command -v ruff >/dev/null 2>&1; then
    (cd apps/worker && ruff check .) && ok "worker ruff" || fail "worker ruff"
  fi
  if python3 -m pytest --version >/dev/null 2>&1; then
    (cd apps/worker && python3 -m pytest -q) && ok "worker pytest" || fail "worker pytest"
  fi
fi

echo "=== summary ==="
if [[ "$FAILED" -ne 0 ]]; then
  fail "backend quality gate FAILED"
  exit 1
fi
ok "backend quality gate PASSED (advisory)"
exit 0
