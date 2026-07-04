#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
TARGET_DIR="$BACKUP_DIR/$TIMESTAMP"

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-st_user}"
PG_DB="${PG_DB:-scientific_tangle}"
NEO4J_CONTAINER="${NEO4J_CONTAINER:-st-neo4j}"

mkdir -p "$TARGET_DIR"

echo "Backing up PostgreSQL to $TARGET_DIR/postgres.sql"
PGPASSWORD="${PG_PASSWORD:-st_pass}" pg_dump \
  -h "$PG_HOST" \
  -p "$PG_PORT" \
  -U "$PG_USER" \
  -d "$PG_DB" \
  -F c \
  -f "$TARGET_DIR/postgres.dump"

echo "Backing up Neo4j to $TARGET_DIR/neo4j.cypher"
docker exec "$NEO4J_CONTAINER" cypher-shell -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-neo4j_pass}" \
  "CALL apoc.export.cypher.all(null, {streamStatements: true, format: 'cypher-shell'}) YIELD cypherStatements RETURN cypherStatements" \
  > "$TARGET_DIR/neo4j.cypher" 2>/dev/null || {
    docker exec "$NEO4J_CONTAINER" cypher-shell -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-neo4j_pass}" \
      "MATCH (n) RETURN n LIMIT 1" > "$TARGET_DIR/neo4j.meta"
    echo "neo4j apoc export unavailable; wrote $TARGET_DIR/neo4j.meta placeholder"
  }

echo "Backup completed: $TARGET_DIR"
