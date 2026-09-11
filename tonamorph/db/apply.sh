#!/usr/bin/env bash
# Applies db/migrations/*.sql, in file-name order, to the database at $DATABASE_URL.
#
# Every file runs inside one transaction together with the row that records it in
# public.schema_migrations (created on first use), so a failing file leaves neither
# half-applied DDL nor a false record. Recorded files are skipped, which makes re-running
# the script a no-op. The run ends with `NOTIFY pgrst, 'reload schema'` so PostgREST
# picks up new functions without a restart.
#
#   export DATABASE_URL='postgresql://postgres.<ref>:<password>@<host>:5432/postgres'
#   bash db/apply.sh                 # apply whatever is not recorded yet
#   bash db/apply.sh --dry-run       # print the plan; connects read-only, writes nothing
#   bash db/apply.sh --from 0004     # files sorting before 0004 are recorded as already
#                                    # applied without being run (after a manual `psql -f`
#                                    # of the early files), 0004 onwards run normally
#
# DATABASE_URL must be a postgres:// or postgresql:// URL (Project Settings -> Database ->
# Connection string -> URI). It is passed to psql as an argument and is never printed.
# PSQL overrides the psql binary (default: the one on PATH). Works with bash 3.2 (macOS).
set -euo pipefail
export LC_ALL=C   # deterministic glob order: 0001_ < 0002_ < ...

die() {
  echo "apply.sh: $*" >&2
  exit 1
}

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

DRY_RUN=0
FROM=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --from)
      shift
      [ $# -gt 0 ] || die "--from needs a value, e.g. --from 0004"
      FROM=$1
      ;;
    --from=*) FROM=${1#--from=} ;;
    -h | --help)
      usage
      exit 0
      ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done

case "$FROM" in
  "" | [0-9A-Za-z_.-]*) ;;
  *) die "--from must be a migration file-name prefix such as 0004" ;;
esac
case "${DATABASE_URL:-}" in
  "") die "DATABASE_URL is not set" ;;
  postgres://* | postgresql://*) ;;
  *) die "DATABASE_URL must start with postgres:// or postgresql:// (value not shown)" ;;
esac

PSQL_BIN=${PSQL:-psql}
command -v "$PSQL_BIN" >/dev/null 2>&1 || die "psql not found (brew install libpq, or set PSQL=/path/to/psql)"

DB_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MIGRATIONS_DIR="$DB_DIR/migrations"
[ -d "$MIGRATIONS_DIR" ] || die "no migrations directory at $MIGRATIONS_DIR"

# -X: no ~/.psqlrc; -q: no per-statement chatter; ON_ERROR_STOP: first error aborts the file.
run_sql() {
  "$PSQL_BIN" -X -q -v ON_ERROR_STOP=1 "$DATABASE_URL" "$@"
}

TRACKING_TABLE="public.schema_migrations"
# client_min_messages: "if not exists" would otherwise print a NOTICE on every re-run.
CREATE_TRACKING="set client_min_messages = warning;
create table if not exists $TRACKING_TABLE (
  filename   text primary key,
  applied_at timestamptz not null default now()
)"

if [ "$DRY_RUN" -eq 1 ]; then
  exists=$(run_sql -At -c "select to_regclass('$TRACKING_TABLE') is not null")
  if [ "$exists" = "t" ]; then
    applied=$(run_sql -At -c "select filename from $TRACKING_TABLE")
  else
    applied=""
  fi
  echo "dry run: nothing will be written"
else
  run_sql -c "$CREATE_TRACKING" || die "could not connect or create $TRACKING_TABLE"
  applied=$(run_sql -At -c "select filename from $TRACKING_TABLE")
fi

is_applied() {  # is_applied <filename>
  printf '%s\n' "$applied" | grep -Fxq -- "$1"
}

record() {  # record <filename>  (only used outside the per-file transaction, for --from)
  run_sql -c "insert into $TRACKING_TABLE (filename) values ('$1')"
}

echo "migrations: $MIGRATIONS_DIR"
n_applied=0
n_skipped=0
n_baselined=0
for file in "$MIGRATIONS_DIR"/*.sql; do
  [ -e "$file" ] || die "no *.sql files in $MIGRATIONS_DIR"
  name=$(basename "$file")
  case "$name" in
    *[!0-9A-Za-z_.-]*) die "refusing a migration whose file name has unexpected characters: $name" ;;
  esac

  if is_applied "$name"; then
    echo "skip     $name (already applied)"
    n_skipped=$((n_skipped + 1))
    continue
  fi

  if [ -n "$FROM" ] && [[ "$name" < "$FROM" ]]; then
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "baseline $name (would be recorded as applied without running: before --from $FROM)"
    else
      record "$name" || die "could not record $name"
      echo "baseline $name (recorded as applied without running: before --from $FROM)"
    fi
    n_baselined=$((n_baselined + 1))
    continue
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "pending  $name (would apply)"
    n_applied=$((n_applied + 1))
    continue
  fi

  # The file and its tracking row commit together or not at all.
  if run_sql --single-transaction -f "$file" \
    -c "insert into $TRACKING_TABLE (filename) values ('$name')"; then
    echo "applied  $name"
    n_applied=$((n_applied + 1))
  else
    echo "FAILED   $name (transaction rolled back; nothing recorded; later files not attempted)" >&2
    exit 1
  fi
done

if [ "$DRY_RUN" -eq 1 ]; then
  echo "plan: $n_applied to apply, $n_skipped already applied, $n_baselined to baseline"
  exit 0
fi

run_sql -c "notify pgrst, 'reload schema'" || die "migrations applied, but NOTIFY pgrst failed"
echo "done: $n_applied applied, $n_skipped already applied, $n_baselined baselined; PostgREST schema reload requested"
