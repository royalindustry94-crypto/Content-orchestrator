#!/usr/bin/env bash
# Advisory domain principles reminder. Does not prove product alignment.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${ROOT}"

echo "SHA: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
echo "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo
cat <<'EOF'
Content Orchestrator — principle gate (advisory)

  [ ] Multi-tenancy / workspace isolation
  [ ] Human Review Gate
  [ ] Spend controls
  [ ] Provider abstraction
  [ ] Auditability
  [ ] Production reliability (no placeholders / silent failures)
  [ ] Docs + tests + migration strategy considered
  [ ] Roadmap fit / no feature creep
  [ ] No premature Executive Operations Hub coupling

Fill assets/product-impact-assessment.md before claiming VERIFIED.
Advisory only — not VERIFIED by itself.
EOF
