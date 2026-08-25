#!/usr/bin/env bash
# Security Auditor advisory scan for Content Orchestrator.
# Exit 0 = no hard heuristic hits (NOT a VERIFIED security approval).
# Exit 1 = potential issues requiring full audit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

ok() { printf 'OK   %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*" >&2; }
fail() { printf 'FAIL %s\n' "$*" >&2; FAILED=1; }
FAILED=0

echo "=== Security Auditor advisory scan ==="
echo "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo "sha:    $(git rev-parse HEAD 2>/dev/null || echo unknown)"

if command -v alembic >/dev/null 2>&1 && [[ -d apps/api ]]; then
  (cd apps/api && alembic current && alembic heads) || warn "alembic current/heads failed"
else
  warn "alembic unavailable"
fi

# Secret-like heuristics (working tree)
if command -v rg >/dev/null 2>&1; then
  if rg -n -I --glob '!.git/**' --glob '!**/node_modules/**' --glob '!**/.venv/**' \
      --glob '!**/uploads/**' --glob '!**/attached_assets/**' \
      -e 'BEGIN RSA PRIVATE KEY' -e 'BEGIN OPENSSH PRIVATE KEY' \
      -e 'AKIA[0-9A-Z]{16}' -e 'xox[baprs]-' \
      -e 'supabase_jwt_secret\s*=\s*["'\''](?!test|ci-)' \
      . 2>/dev/null | head -30 | grep -q .; then
    fail "possible committed secrets / private keys (review immediately):"
    rg -n -I --glob '!.git/**' --glob '!**/node_modules/**' --glob '!**/.venv/**' \
      --glob '!**/uploads/**' --glob '!**/attached_assets/**' \
      -e 'BEGIN RSA PRIVATE KEY' -e 'BEGIN OPENSSH PRIVATE KEY' \
      -e 'AKIA[0-9A-Z]{16}' \
      . 2>/dev/null | head -30 || true
  else
    ok "no obvious private-key / AKIA heuristics in working tree"
  fi

  if rg -n --glob '.github/workflows/*' -e 'pull_request_target' .github/workflows 2>/dev/null | grep -q .; then
    fail "pull_request_target present — review for secret exposure"
    rg -n --glob '.github/workflows/*' -e 'pull_request_target' .github/workflows || true
  else
    ok "no pull_request_target in workflows"
  fi

  if rg -n --glob '.github/workflows/*' -e 'permissions:' .github/workflows 2>/dev/null | grep -q .; then
    ok "workflows reference permissions: (review least-privilege manually)"
  else
    warn "no explicit permissions: keys found — confirm defaults are acceptable"
  fi
else
  warn "rg not installed"
fi

# Dependency audits (optional tools)
if command -v pip-audit >/dev/null 2>&1 && [[ -d apps/api ]]; then
  (cd apps/api && pip-audit) && ok "pip-audit api" || fail "pip-audit api reported issues"
else
  warn "pip-audit not available — record NOT RUN in audit report"
fi

if [[ -f apps/web/package.json ]] && command -v npm >/dev/null 2>&1; then
  if [[ -d apps/web/node_modules ]]; then
    (cd apps/web && npm audit --omit=dev) && ok "npm audit web" || warn "npm audit reported issues (triage)"
  else
    warn "apps/web/node_modules missing — npm audit skipped"
  fi
fi

echo "=== summary ==="
if [[ "$FAILED" -ne 0 ]]; then
  fail "advisory scan FAILED — open full /security-auditor workflow"
  exit 1
fi
ok "advisory scan clean — STILL NOT VERIFIED; complete full audit workflow"
exit 0
