#!/usr/bin/env bash
# QA Breaker advisory gate — NOT a VERIFIED approval by itself.
# Exit 0 = local commands succeeded; Exit 1 = failure.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

ok() { printf 'OK   %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*" >&2; }
fail() { printf 'FAIL %s\n' "$*" >&2; FAILED=1; }
FAILED=0

echo "=== QA Breaker advisory gate ==="
echo "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo "sha:    $(git rev-parse HEAD 2>/dev/null || echo unknown)"

# Weak-test heuristics
if command -v rg >/dev/null 2>&1; then
  SKIP_HITS="$(rg -n "pytest.mark.(skip|xfail)" apps/api/tests apps/worker 2>/dev/null | wc -l | tr -d ' ')"
  echo "info: skip/xfail markers in api/worker tests: ${SKIP_HITS}"
  if rg -n --glob '**/test_*.py' -e 'assert\s+True\b|assert\s+1\s*==\s*1' apps/api/tests 2>/dev/null | head -5 | grep -q .; then
    warn "possible trivial asserts found — inspect manually"
  fi
fi

if [[ -d apps/api ]]; then
  if command -v ruff >/dev/null 2>&1; then
    (cd apps/api && ruff check app tests) && ok "api ruff" || fail "api ruff"
  else
    warn "ruff unavailable"
  fi
  if python3 -m pytest --version >/dev/null 2>&1; then
    (cd apps/api && python3 -m pytest -W error -q --tb=line) && ok "api pytest -W error" || fail "api pytest"
  else
    warn "pytest unavailable"
  fi
  if command -v alembic >/dev/null 2>&1; then
    if (cd apps/api && alembic heads 2>/dev/null | grep -q '(head)'); then
      ok "alembic heads reachable"
    else
      warn "alembic heads check inconclusive (DB/revision mismatch possible)"
    fi
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

if [[ -f apps/web/package.json ]] && command -v npm >/dev/null 2>&1; then
  if [[ -d apps/web/node_modules ]]; then
    (cd apps/web && npm run lint) && ok "web lint" || fail "web lint"
    if npm --prefix apps/web run | grep -q 'build'; then
      (cd apps/web && npm run build) && ok "web build" || fail "web build"
    fi
  else
    warn "web node_modules missing — frontend gate skipped"
  fi
fi

echo "=== summary ==="
if [[ "$FAILED" -ne 0 ]]; then
  fail "QA advisory gate FAILED — not VERIFIED"
  exit 1
fi
ok "QA advisory gate passed commands — STILL require attack matrix, concurrency, migration replay, CI green for VERIFIED"
exit 0
