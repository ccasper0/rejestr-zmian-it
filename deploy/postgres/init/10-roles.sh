#!/bin/sh
# Postgres bootstrap: roles and privileges for "Rejestr zmian IT".
#
# Executed once by the official postgres image entrypoint, only when the data
# volume is empty (docker-entrypoint-initdb.d). The database itself
# ($POSTGRES_DB, default "rejestr") is created by the entrypoint.
#
# The SQL lives next to this script in roles.psql (the entrypoint ignores the
# .psql extension, so it runs only from here, with variables). The backend
# test fixtures (testcontainers) mount this same directory, so tests run
# against exactly these roles and grants.
#
# Passwords come exclusively from environment variables - never from the repo.
#
# NOTE: when the file lacks the executable bit (common on Windows checkouts),
# the entrypoint *sources* it instead of executing it. Hence no `set -u` and no
# `exit` here - the entrypoint already runs with `set -e`.
set -e

: "${APP_OWNER_PASSWORD:?APP_OWNER_PASSWORD must be set}"
: "${APP_RW_PASSWORD:?APP_RW_PASSWORD must be set}"

DB_NAME="${POSTGRES_DB:-rejestr}"
ROLES_SQL="${REJESTR_ROLES_SQL:-/docker-entrypoint-initdb.d/roles.psql}"

if [ ! -r "$ROLES_SQL" ]; then
    echo "rejestr-init: $ROLES_SQL not found" >&2
    false
fi

psql -v ON_ERROR_STOP=1 \
     --username "${POSTGRES_USER:-postgres}" \
     --dbname "$DB_NAME" \
     -v db_name="$DB_NAME" \
     -v owner_pw="$APP_OWNER_PASSWORD" \
     -v rw_pw="$APP_RW_PASSWORD" \
     -f "$ROLES_SQL"

echo "rejestr-init: roles app_owner and app_rw created in database ${DB_NAME}"
