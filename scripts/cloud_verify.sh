#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(
  docker compose
  -f docker-compose.yml
  -f docker-compose.prod.yml
  -f docker-compose.cloud.yml
  -f docker-compose.cloud.http.yml
)

EDGE_URL="${EDGE_URL:-http://127.0.0.1}"
PUBLIC_EDGE_URL="${PUBLIC_EDGE_URL:-}"

echo "== compose ps =="
"${COMPOSE[@]}" ps

echo
echo "== health =="
curl -fsS "${EDGE_URL}/api/health" || echo "api/health FAILED"
curl -fsS "${EDGE_URL}/api/health/all" || echo "api/health/all FAILED"

echo
echo "== postgres ingestion counts =="
"${COMPOSE[@]}" exec -T postgres psql -U st_user -d scientific_tangle -c \
  "select status, count(*) from ingestion_tasks group by status order by status;"
"${COMPOSE[@]}" exec -T postgres psql -U st_user -d scientific_tangle -c \
  "select count(*) indexed_documents, coalesce(sum(indexed_points_count),0) indexed_points from indexed_documents;"
"${COMPOSE[@]}" exec -T postgres psql -U st_user -d scientific_tangle -c \
  "select count(*) source_spans from source_span_lookup;"

echo
echo "== minio source-files (last 20) =="
"${COMPOSE[@]}" exec -T minio sh -lc \
  'mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1 && mc ls --recursive local/source-files 2>/dev/null | tail -20' \
  || echo "minio listing unavailable"

echo
echo "== qdrant collection =="
"${COMPOSE[@]}" exec -T retrieval python -c \
  'import httpx; r=httpx.get("http://qdrant:6333/collections/st_evidence_v1", timeout=10); print(r.status_code); print(r.text[:2000])' \
  || echo "qdrant check failed"

if [[ -n "${PUBLIC_EDGE_URL}" ]]; then
  echo
  echo "== public perimeter =="
  for path in /api/health /model/v1/status /retrieval/health; do
    code="$(curl -s -o /dev/null -w "%{http_code}" "${PUBLIC_EDGE_URL}${path}" || true)"
    echo "${PUBLIC_EDGE_URL}${path} -> ${code}"
  done
fi

echo
echo "cloud_verify done"
