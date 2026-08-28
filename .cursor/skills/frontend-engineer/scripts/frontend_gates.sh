#!/usr/bin/env bash
# Advisory frontend gates for apps/web.
# Passing this script is necessary but not sufficient for VERIFIED.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
WEB="${ROOT}/apps/web"

if [[ ! -d "${WEB}" ]]; then
  echo "FAIL: apps/web not found at ${WEB}"
  exit 1
fi

cd "${WEB}"

if [[ ! -d node_modules ]]; then
  echo "Installing apps/web dependencies..."
  npm ci
fi

echo "==> lint"
npm run lint

echo "==> test"
npm run test

echo "==> build (tsc + vite)"
npm run build

echo "OK: frontend_gates.sh completed (advisory only — not VERIFIED by itself)"
