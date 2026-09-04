#!/usr/bin/env bash
# Scan locally built CI images with Trivy (HIGH/CRITICAL).
# Does not change GitHub CI fail-closed jobs; run after docker build.
set -euo pipefail

if ! command -v trivy >/dev/null 2>&1; then
  echo "trivy is not installed. See https://github.com/aquasecurity/trivy" >&2
  exit 1
fi

images=(
  content-orchestrator-api:ci
  content-orchestrator-worker:ci
  content-orchestrator-web:ci
)

found=0
for image in "${images[@]}"; do
  if docker image inspect "$image" >/dev/null 2>&1; then
    found=1
    trivy image --severity HIGH,CRITICAL --exit-code 1 "$image"
  else
    echo "skip $image (not built)"
  fi
done

if [[ "$found" -eq 0 ]]; then
  echo "No CI images present. Build first:"
  echo "  docker build -t content-orchestrator-api:ci ./apps/api"
  echo "  docker build -t content-orchestrator-worker:ci ./apps/worker"
  echo "  docker build -t content-orchestrator-web:ci ./apps/web"
  exit 1
fi
