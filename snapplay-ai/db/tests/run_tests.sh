#!/usr/bin/env bash
# Proves the schema against a real PostgreSQL 16 cluster.
#
# Creates a throwaway, socket-only cluster as the non-root cluster owner, applies the
# local auth shim and the migrations in order, runs every db/tests/test_*.sql, runs the
# two-session concurrency test, and always stops and removes the cluster on exit.
# Exit status is non-zero on any failure.
#
# Overridable: PGBIN, SNAPPLAY_TEST_PGDATA, SNAPPLAY_TEST_PGPORT, SNAPPLAY_TEST_PGUSER.
set -euo pipefail

PGBIN=${PGBIN:-/usr/lib/postgresql/16/bin}
PGDATA_DIR=${SNAPPLAY_TEST_PGDATA:-/home/user/pgdata/snapplay-test}
PGPORT=${SNAPPLAY_TEST_PGPORT:-54329}
PGOWNER=${SNAPPLAY_TEST_PGUSER:-pguser}
DBNAME=snapplay_test

TESTS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DB_DIR=$(cd "$TESTS_DIR/.." && pwd)

# Runs one command line as the cluster owner (postgres binaries refuse to run as root).
as_owner() {
  if [ "$(id -un)" = "$PGOWNER" ]; then
    bash -c "$1"
  else
    su "$PGOWNER" -c "$1"
  fi
}

PSQL="$PGBIN/psql -X -q -v ON_ERROR_STOP=1 -h $PGDATA_DIR -p $PGPORT -U postgres"

sql_file() {  # sql_file <db> <path>
  as_owner "$PSQL -d $1 -f '$2'"
}

sql_value() {  # sql_value <db> <sql>  -> single unaligned value
  as_owner "$PSQL -d $1 -At -c \"$2\""
}

cleanup() {
  local status=$?
  as_owner "$PGBIN/pg_ctl -D '$PGDATA_DIR' stop -m immediate -s" >/dev/null 2>&1 || true
  rm -rf "$PGDATA_DIR"
  if [ "$status" -ne 0 ]; then
    echo "FAILED (exit $status)" >&2
  fi
  exit "$status"
}
trap cleanup EXIT

# --- cluster -----------------------------------------------------------------
if [ -d "$PGDATA_DIR" ]; then
  as_owner "$PGBIN/pg_ctl -D '$PGDATA_DIR' stop -m immediate -s" >/dev/null 2>&1 || true
  rm -rf "$PGDATA_DIR"
fi
as_owner "$PGBIN/initdb -D '$PGDATA_DIR' -U postgres -A trust -E UTF8 --no-sync" >/dev/null
cat >> "$PGDATA_DIR/postgresql.conf" <<CONF
listen_addresses = ''
unix_socket_directories = '$PGDATA_DIR'
port = $PGPORT
fsync = off
synchronous_commit = off
full_page_writes = off
log_min_messages = warning
CONF
as_owner "$PGBIN/pg_ctl -D '$PGDATA_DIR' -l '$PGDATA_DIR/server.log' -w -s start"
as_owner "$PGBIN/createdb -h $PGDATA_DIR -p $PGPORT -U postgres $DBNAME"
echo "cluster: $("$PGBIN/pg_ctl" --version) at $PGDATA_DIR port $PGPORT"

# --- shim + migrations ---------------------------------------------------------
sql_file "$DBNAME" "$TESTS_DIR/00_local_auth_shim.sql"
echo "applied  tests/00_local_auth_shim.sql"
for migration in "$DB_DIR"/migrations/*.sql; do
  sql_file "$DBNAME" "$migration"
  echo "applied  migrations/$(basename "$migration")"
done

# --- SQL test files ------------------------------------------------------------
passed=0
for test_file in "$TESTS_DIR"/test_*.sql; do
  sql_file "$DBNAME" "$test_file"
  echo "PASS     tests/$(basename "$test_file")"
  passed=$((passed + 1))
done

# --- two-session concurrency: exactly one of two simultaneous reservations wins --
# A fresh user is left with exactly one available credit. Two psql sessions each open a
# transaction, pause so both are in flight, call create_job (which takes the account
# lock and reserves), then hold the lock across a second pause before committing. The
# second session blocks on the lock, sees zero available credits and must fail with
# P0402 while the first commits.
race_user=$(sql_value "$DBNAME" "insert into auth.users (email) values ('race@test.local') returning id")
sql_value "$DBNAME" "select public.adjust_credits('$race_user', -2, 'test', 'race:adjust')" >/dev/null
for side in a b; do
  cat > "$PGDATA_DIR/race_$side.sql" <<SQL
begin;
select pg_sleep(0.5);
select public.create_job('$race_user', '{}'::jsonb, '{}'::jsonb, 'race-$side');
select pg_sleep(1.5);
commit;
SQL
done
rc_a=0; rc_b=0
as_owner "$PSQL -d $DBNAME -f '$PGDATA_DIR/race_a.sql'" > "$PGDATA_DIR/race_a.out" 2>&1 &
pid_a=$!
as_owner "$PSQL -d $DBNAME -f '$PGDATA_DIR/race_b.sql'" > "$PGDATA_DIR/race_b.out" 2>&1 &
pid_b=$!
wait "$pid_a" || rc_a=$?
wait "$pid_b" || rc_b=$?

winners=0
for side in a b; do
  rc=$([ "$side" = a ] && echo "$rc_a" || echo "$rc_b")
  if [ "$rc" -eq 0 ]; then
    winners=$((winners + 1))
  elif ! grep -q 'insufficient_credits' "$PGDATA_DIR/race_$side.out"; then
    echo "race session $side failed for the wrong reason:" >&2
    cat "$PGDATA_DIR/race_$side.out" >&2
    exit 1
  fi
done
if [ "$winners" -ne 1 ]; then
  echo "race: expected exactly one winning session, got $winners" >&2
  cat "$PGDATA_DIR/race_a.out" "$PGDATA_DIR/race_b.out" >&2
  exit 1
fi
race_state=$(sql_value "$DBNAME" "select (select count(*) from public.jobs where user_id = '$race_user') || ',' || balance || ',' || reserved from public.credit_accounts where user_id = '$race_user'")
if [ "$race_state" != "1,1,1" ]; then
  echo "race: expected jobs,balance,reserved = 1,1,1 but got $race_state" >&2
  exit 1
fi
echo "PASS     two-session concurrency (one winner, one insufficient_credits)"
passed=$((passed + 1))

# --- two-session concurrency: only one worker may reclaim a stranded webhook claim --
# A webhook_events row is left exactly as a hard kill leaves it — claimed, never closed —
# and aged past the lease. Two psql sessions call claim_webhook_event on it at the same
# time. The first takes the row lock and re-stamps received_at; the second blocks on that
# lock and then sees a claim inside its lease. Exactly one may apply the paid event.
claim_key='lemonsqueezy:order_created:race'
sql_value "$DBNAME" "insert into public.webhook_events (provider, event_name, idempotency_key, payload, received_at) values ('lemonsqueezy', 'order_created', '$claim_key', '{}'::jsonb, now() - interval '1 hour') returning 1" >/dev/null
for side in a b; do
  cat > "$PGDATA_DIR/claim_$side.sql" <<SQL
begin;
select pg_sleep(0.5);
select public.claim_webhook_event('$claim_key', 'lemonsqueezy', 'order_created', '{}'::jsonb, 60);
select pg_sleep(1.5);
commit;
SQL
done
rc_a=0; rc_b=0
as_owner "$PSQL -d $DBNAME -At -f '$PGDATA_DIR/claim_a.sql'" > "$PGDATA_DIR/claim_a.out" 2>&1 &
pid_a=$!
as_owner "$PSQL -d $DBNAME -At -f '$PGDATA_DIR/claim_b.sql'" > "$PGDATA_DIR/claim_b.out" 2>&1 &
pid_b=$!
wait "$pid_a" || rc_a=$?
wait "$pid_b" || rc_b=$?
if [ "$rc_a" -ne 0 ] || [ "$rc_b" -ne 0 ]; then
  echo "webhook claim race: a session failed" >&2
  cat "$PGDATA_DIR/claim_a.out" "$PGDATA_DIR/claim_b.out" >&2
  exit 1
fi
claim_winners=$(cat "$PGDATA_DIR/claim_a.out" "$PGDATA_DIR/claim_b.out" | grep -c '^t$' || true)
if [ "$claim_winners" -ne 1 ]; then
  echo "webhook claim race: expected exactly one winner, got $claim_winners" >&2
  cat "$PGDATA_DIR/claim_a.out" "$PGDATA_DIR/claim_b.out" >&2
  exit 1
fi
echo "PASS     two-session concurrency (one webhook claim winner, one duplicate)"
passed=$((passed + 1))

echo "ALL TESTS PASSED ($passed test groups)"
