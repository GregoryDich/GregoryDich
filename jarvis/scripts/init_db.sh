#!/bin/bash
set -euo pipefail

DB_PATH="${JARVIS_DB:-$HOME/jarvis/state.db}"
SCHEMA_PATH="$(dirname "$0")/../db/schema.sql"

if [ -f "$DB_PATH" ]; then
    echo "Database already exists at $DB_PATH"
    echo "To recreate, delete it first: rm $DB_PATH"
    exit 0
fi

mkdir -p "$(dirname "$DB_PATH")"
sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
echo "Created state.db at $DB_PATH"
echo "Tables:"
sqlite3 "$DB_PATH" ".tables"
