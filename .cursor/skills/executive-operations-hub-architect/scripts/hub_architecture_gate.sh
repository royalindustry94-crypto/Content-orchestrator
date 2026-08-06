#!/usr/bin/env bash
# Advisory Hub architecture checklist. Does not prove design quality.
set -euo pipefail

echo "SHA: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
cat <<'EOF'

Executive Operations Hub — architecture gate (advisory)

  [ ] Business goals / roadmap reviewed
  [ ] Architecture written before major implementation
  [ ] Modules, APIs, events, data model, approval flow defined
  [ ] Hub is NOT content orchestration SoT
  [ ] GitHub / Cursor agents / CI/CD / Postgres behind clean interfaces
  [ ] Product Review Gate and spend controls preserved
  [ ] Risks, dependencies, rollout/rollback identified
  [ ] Docs, tests, migration plan for major changes
  [ ] Architecture report filled (assets/hub-architecture-report.md)

Advisory only — not VERIFIED by itself.
EOF
