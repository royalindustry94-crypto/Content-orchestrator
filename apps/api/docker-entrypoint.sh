#!/bin/sh
set -eu

# Migrate-on-start when RUN_MIGRATIONS=1 (staging compose). Uses DATABASE_URL
# (owner role). Runtime traffic still uses APP_DATABASE_URL / app_runtime.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Running alembic upgrade head..."
  alembic upgrade head
fi

exec "$@"
