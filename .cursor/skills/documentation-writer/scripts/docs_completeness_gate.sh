#!/usr/bin/env bash
# Advisory documentation completeness helper. Does not prove accuracy vs code.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${ROOT}"

echo "==> Key documentation paths"
for p in \
  docs/architecture-decisions.md \
  docs/CURSOR_SKILLS.md \
  docs/M3_RELEASE_REPORT.md \
  docs/milestone-2-identity-and-access.md \
  .github/workflows/ci.yml \
  docker-compose.yml
do
  if [[ -e "${p}" ]]; then
    echo "  OK  ${p}"
  else
    echo "  MISSING  ${p}"
  fi
done

echo
echo "SHA: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
echo
cat <<'EOF'
Manual checks required for VERIFIED:
  [ ] Docs match implemented code (no invented features)
  [ ] ADRs accepted by /chief-architect when stack/SoT/boundaries changed
  [ ] Migration revision ids cited correctly
  [ ] API docs match FastAPI routes / OpenAPI
  [ ] Links and version strings verified
  [ ] Completeness report filled (assets/completeness-report.md)

Advisory only — not VERIFIED by itself.
EOF
