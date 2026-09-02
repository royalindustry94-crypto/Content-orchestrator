#!/bin/sh
set -eu

# Staging must not boot with merely non-empty database passwords. Keep this
# check local to the process and never print the supplied values.
: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in the staging environment}"
: "${APP_RUNTIME_PASSWORD:?Set APP_RUNTIME_PASSWORD in the staging environment}"

if [ "${#POSTGRES_PASSWORD}" -lt 32 ] || [ "${#APP_RUNTIME_PASSWORD}" -lt 32 ]; then
  echo "Database passwords must each contain at least 32 characters." >&2
  exit 1
fi

if [ "$POSTGRES_PASSWORD" = "$APP_RUNTIME_PASSWORD" ]; then
  echo "Owner and runtime database passwords must be different." >&2
  exit 1
fi

case "$POSTGRES_PASSWORD:$APP_RUNTIME_PASSWORD" in
  *:postgres|postgres:*|*:app_runtime|app_runtime:*)
    echo "Default database passwords are forbidden." >&2
    exit 1
    ;;
esac

echo "Staging database secret checks passed."
