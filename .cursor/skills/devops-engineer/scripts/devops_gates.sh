#!/usr/bin/env bash
# Advisory local gates mirroring CI shape (api / worker / web).
# Passing is necessary for confidence but NOT sufficient for VERIFIED —
# cite GitHub Actions on the pushed SHA for ship claims.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${ROOT}"

echo "==> api: ruff (if venv/deps available)"
if [[ -d "${ROOT}/apps/api" ]]; then
  (
    cd "${ROOT}/apps/api"
    if command -v ruff >/dev/null 2>&1 || [[ -x .venv/bin/ruff ]]; then
      if [[ -x .venv/bin/ruff ]]; then .venv/bin/ruff check .; else ruff check .; fi
    else
      echo "SKIP api ruff: install apps/api deps (pip install -e '.[dev]')"
    fi
  )
fi

echo "==> worker: ruff (if available)"
if [[ -d "${ROOT}/apps/worker" ]]; then
  (
    cd "${ROOT}/apps/worker"
    if command -v ruff >/dev/null 2>&1 || [[ -x .venv/bin/ruff ]]; then
      if [[ -x .venv/bin/ruff ]]; then .venv/bin/ruff check .; else ruff check .; fi
    else
      echo "SKIP worker ruff: install apps/worker deps"
    fi
  )
fi

echo "==> web: lint + build"
if [[ -d "${ROOT}/apps/web" ]]; then
  (
    cd "${ROOT}/apps/web"
    if [[ ! -d node_modules ]]; then npm ci; fi
    npm run lint
    npm run build
  )
fi

echo "OK: devops_gates.sh finished (advisory only — require Actions URL for VERIFIED)"
