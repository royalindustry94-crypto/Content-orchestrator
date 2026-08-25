#!/usr/bin/env bash
# Advisory release identity helper. Does NOT prove CI/QA/Security gates.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${ROOT}"

echo "==> Release identity (advisory)"
echo "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo "sha:    $(git rev-parse HEAD 2>/dev/null || echo unknown)"
echo "short:  $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

if command -v gh >/dev/null 2>&1; then
  echo "==> gh pr view (if available)"
  gh pr view --json url,number,state,baseRefName,headRefOid 2>/dev/null || echo "No PR associated or gh unavailable"
else
  echo "gh CLI not available — paste PR URL manually"
fi

cat <<'EOF'

Required evidence (must paste into readiness report — this script does not collect it):
  [ ] GitHub Actions URL green on THIS sha
  [ ] /qa-breaker approval on THIS sha
  [ ] /security-auditor approval on THIS sha (Critical/High = 0)
  [ ] Migration head + fresh PostgreSQL verification
  [ ] Changelog / release notes / tag plan
  [ ] Rollback plan
  [ ] Invariants: Review Gate, spend, audit, RLS, isolation

Advisory only — not VERIFIED by itself.
EOF
