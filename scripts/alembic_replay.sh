#!/usr/bin/env bash
# Alembic upgrade → downgrade base → upgrade head (replay) against DATABASE_URL.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/../apps/api"

echo "==> alembic upgrade head"
alembic upgrade head

echo "==> alembic downgrade base"
alembic downgrade base

echo "==> alembic upgrade head (replay)"
alembic upgrade head

echo "OK: migration replay succeeded"
