#!/usr/bin/env bash
# Fail if production source contains TODO/FIXME markers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

PATTERN='(\bTODO\b|\bFIXME\b)'

SCAN=()
[[ -d "${ROOT}/apps/api/app" ]] && SCAN+=("${ROOT}/apps/api/app")
[[ -d "${ROOT}/apps/worker/worker" ]] && SCAN+=("${ROOT}/apps/worker/worker")
[[ -d "${ROOT}/apps/web/src" ]] && SCAN+=("${ROOT}/apps/web/src")

if [[ ${#SCAN[@]} -eq 0 ]]; then
  echo "FAIL: no production scan paths found under ${ROOT}"
  exit 1
fi

echo "Scanning: ${SCAN[*]}"
set +e
HITS=$(rg -n -e "${PATTERN}" "${SCAN[@]}" --glob '!**/*.pyc' --glob '!**/__pycache__/**' 2>/dev/null)
RC=$?
set -e
if [[ ${RC} -eq 2 ]]; then
  echo "FAIL: ripgrep error"
  exit 1
fi

if [[ ${RC} -eq 0 && -n "${HITS}" ]]; then
  echo "FAIL: TODO/FIXME markers found in production paths:"
  echo "${HITS}"
  exit 1
fi

echo "OK: no TODO/FIXME markers in production scan paths"
