#!/usr/bin/env bash
# Chief Architect advisory drift scan for Content Orchestrator.
# Exit 0 = no hard findings (still review manually).
# Exit 1 = likely architecture drift or isolation gaps in changed trees.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

ok() { printf 'OK   %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*" >&2; }
fail() { printf 'FAIL %s\n' "$*" >&2; FAILED=1; }

FAILED=0
echo "=== Chief Architect drift scan (advisory) ==="

if ! command -v rg >/dev/null 2>&1; then
  warn "rg not installed; limited scans"
fi

# Discouraged SoT / framework markers in app code (heuristic)
if command -v rg >/dev/null 2>&1; then
  if rg -n -i --glob '!**/node_modules/**' --glob '!**/.venv/**' --glob '!**/attached_assets/**' \
      -e '\bcreateClient\(.*redis|from redis|import redis\b' \
      -e '\bcelery\b|\bkafka\b|bullmq|RQ\(' \
      -e '\bexpress\(\)|\bnest(js)?\b|\bprisma\b|\bdrizzle-orm\b' \
      apps docs packages 2>/dev/null | head -30 | grep -q .; then
    fail "possible non-approved stack / SoT markers found (review):"
    rg -n -i --glob '!**/node_modules/**' --glob '!**/.venv/**' --glob '!**/attached_assets/**' \
      -e '\bcreateClient\(.*redis|from redis|import redis\b' \
      -e '\bcelery\b|\bkafka\b|bullmq|RQ\(' \
      -e '\bexpress\(\)|\bnest(js)?\b|\bprisma\b|\bdrizzle-orm\b' \
      apps docs packages 2>/dev/null | head -30 || true
  else
    ok "no obvious Redis/Celery/Kafka/Express/Prisma/Drizzle markers in apps/docs/packages"
  fi

  # Placeholder / silent-failure heuristics in production trees
  if rg -n -i --glob '!**/node_modules/**' \
      -e '\b(TODO|FIXME|XXX)\b' -e 'NotImplementedError' -e 'except Exception:\s*pass' \
      apps/api/app apps/worker/worker 2>/dev/null | head -40 | grep -q .; then
    fail "placeholder or swallow-exception patterns found:"
    rg -n -i --glob '!**/node_modules/**' \
      -e '\b(TODO|FIXME|XXX)\b' -e 'NotImplementedError' -e 'except Exception:\s*pass' \
      apps/api/app apps/worker/worker 2>/dev/null | head -40 || true
  else
    ok "no TODO/FIXME/XXX/NotImplementedError/except-pass greps in api/worker app trees"
  fi
fi

# Alembic presence
if [[ -d apps/api/alembic/versions ]]; then
  ok "alembic versions directory present"
else
  fail "missing apps/api/alembic/versions"
fi

# WorkspaceScopedMixin reminder — count models without workspace_id is hard;
# instead ensure mixin module exists.
if [[ -f apps/api/app/db/base.py ]]; then
  if grep -q 'WorkspaceScopedMixin' apps/api/app/db/base.py; then
    ok "WorkspaceScopedMixin present in app/db/base.py"
  else
    fail "WorkspaceScopedMixin missing from app/db/base.py"
  fi
fi

echo "=== summary ==="
if [[ "$FAILED" -ne 0 ]]; then
  fail "drift scan found issues — Chief Architect should REJECT or CONDITIONAL"
  exit 1
fi
ok "drift scan clean (advisory) — still run full architecture review for design changes"
exit 0
