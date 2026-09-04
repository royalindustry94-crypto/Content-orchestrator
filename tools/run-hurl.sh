#!/usr/bin/env bash
# Run the defensive Review Desk Hurl collection against a local API.
# Usage: tools/run-hurl.sh [vars.env]
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
vars="${1:-$root/tools/hurl/vars.env}"

if ! command -v hurl >/dev/null 2>&1; then
  echo "hurl is not installed. See https://github.com/Orange-OpenSource/hurl" >&2
  exit 1
fi

if [[ ! -f "$vars" ]]; then
  echo "Missing $vars — copy tools/hurl/vars.env.example and fill local values." >&2
  exit 1
fi

hurl --variables-file "$vars" "$root/tools/hurl/auth-mode.hurl"
hurl --variables-file "$vars" "$root/tools/hurl/auth-login.hurl"
if grep -q '^workspace_id=replace-with-workspace-uuid' "$vars"; then
  echo "Skipping review-gates.hurl until workspace_id is set in $vars"
  exit 0
fi
hurl --variables-file "$vars" "$root/tools/hurl/review-gates.hurl"
