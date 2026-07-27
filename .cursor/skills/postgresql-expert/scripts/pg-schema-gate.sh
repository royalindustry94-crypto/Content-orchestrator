#!/usr/bin/env bash
# PostgreSQL Expert advisory schema gate for Content Orchestrator.
# Exit 0 = no hard findings (still require fresh up/down/up + RLS tests).
# Exit 1 = likely schema/migration/RLS issues.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

ok() { printf 'OK   %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*" >&2; }
fail() { printf 'FAIL %s\n' "$*" >&2; FAILED=1; }
FAILED=0

echo "=== PostgreSQL Expert schema gate (advisory) ==="

if [[ ! -d apps/api/alembic/versions ]]; then
  fail "missing apps/api/alembic/versions"
else
  ok "alembic versions directory present"
fi

if command -v alembic >/dev/null 2>&1; then
  HEAD_COUNT="$(cd apps/api && alembic heads 2>/dev/null | grep -c '(head)' || true)"
  if [[ "${HEAD_COUNT}" == "1" ]]; then
    ok "single alembic head"
  else
    fail "expected exactly one alembic head, found ${HEAD_COUNT:-0}"
    (cd apps/api && alembic heads) || true
  fi
else
  warn "alembic not on PATH; skipped heads check"
fi

if command -v rg >/dev/null 2>&1; then
  # Float money heuristics in models/migrations (advisory; numeric is required)
  if rg -n -i --glob '!**/node_modules/**' \
      -e 'Mapped\[float\].*cost|cost_usd.*Float|Float\(.*money|DOUBLE PRECISION.*cap' \
      apps/api/app/models apps/api/alembic/versions 2>/dev/null | head -20 | grep -q .; then
    fail "possible float/double money storage found (use numeric):"
    rg -n -i --glob '!**/node_modules/**' \
      -e 'Mapped\[float\].*cost|cost_usd.*Float|Float\(.*money|DOUBLE PRECISION.*cap' \
      apps/api/app/models apps/api/alembic/versions 2>/dev/null | head -20 || true
  else
    ok "no obvious float money markers in models/versions"
  fi

  if rg -n --glob '!**/node_modules/**' \
      -e 'GRANT ALL ON ALL TABLES IN SCHEMA public TO PUBLIC|GRANT ALL PRIVILEGES' \
      apps/api/alembic/versions 2>/dev/null | head -20 | grep -q .; then
    fail "permissive GRANT ALL patterns found in migrations"
  else
    ok "no GRANT ALL TO PUBLIC / ALL PRIVILEGES patterns in versions"
  fi

  if rg -n -i --glob '!**/node_modules/**' \
      -e 'SECURITY DEFINER' apps/api/alembic/versions 2>/dev/null | head -5 | grep -q .; then
    warn "SECURITY DEFINER present — verify locked search_path on each function"
    rg -n -i --glob '!**/node_modules/**' -e 'SECURITY DEFINER|search_path' \
      apps/api/alembic/versions 2>/dev/null | head -30 || true
  fi
else
  warn "rg not installed; skipped SQL greps"
fi

if [[ -f apps/api/app/db/base.py ]] && grep -q 'WorkspaceScopedMixin' apps/api/app/db/base.py; then
  ok "WorkspaceScopedMixin present"
else
  fail "WorkspaceScopedMixin missing"
fi

if [[ -f apps/api/alembic/migration_helpers.py ]]; then
  ok "migration_helpers.py present"
else
  fail "migration_helpers.py missing"
fi

echo "=== summary ==="
if [[ "$FAILED" -ne 0 ]]; then
  fail "PG schema gate FAILED"
  exit 1
fi
ok "PG schema gate PASSED (advisory) — still run fresh up/down/up + RLS adversarial tests"
exit 0
