#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <backup_timestamp_dir>"
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
TARGET_DIR="$BACKUP_DIR/$1"

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-st_user}"
PG_DB="${PG_DB:-scientific_tangle}"
NEO4J_CONTAINER="${NEO4J_CONTAINER:-st-neo4j}"

if [[ ! -f "$TARGET_DIR/postgres.dump" ]]; then
  echo "missing $TARGET_DIR/postgres.dump"
  exit 1
fi

echo "Restoring PostgreSQL from $TARGET_DIR/postgres.dump"
PGPASSWORD="${PG_PASSWORD:-st_pass}" pg_restore \
  -h "$PG_HOST" \
  -p "$PG_PORT" \
  -U "$PG_USER" \
  -d "$PG_DB" \
  --clean \
  --if-exists \
  "$TARGET_DIR/postgres.dump"

if [[ -f "$TARGET_DIR/neo4j.cypher" ]]; then
  echo "Restoring Neo4j from $TARGET_DIR/neo4j.cypher"
  docker exec -i "$NEO4J_CONTAINER" cypher-shell -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-neo4j_pass}" \
    < "$TARGET_DIR/neo4j.cypher" || echo "neo4j restore skipped"
fi

echo "Restore completed from $TARGET_DIR"
