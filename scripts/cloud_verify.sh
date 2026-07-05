#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BASE_URL=""
HTTPS=0
SKIP_SEARCH=0
DOCKER_CMD=(docker)
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml)

FAILURES=0
WARNINGS=0

usage() {
  cat <<'EOF'
Usage: ./scripts/cloud_verify.sh [options]

Однокомандная диагностика cloud-стенда: compose, health, данные, периметр, smoke.

Options:
  --base-url URL     базовый URL edge (по умолчанию из PUBLIC_URL в .env или http://127.0.0.1)
  --https            использовать cloud.https compose overlay
  --skip-search      не проверять /api/search
  -h, --help         эта справка

Exit codes:
  0 — стек жив, периметр закрыт
  1 — критичные проверки не прошли
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --https)
      HTTPS=1
      shift
      ;;
    --skip-search)
      SKIP_SEARCH=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

section() {
  printf '\n=== %s ===\n' "$1"
}

ok() {
  printf '[OK] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
  WARNINGS=$((WARNINGS + 1))
}

fail() {
  printf '[FAIL] %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

env_value() {
  local key="$1"
  if [[ -f .env ]]; then
    grep -E "^${key}=" .env | tail -1 | cut -d= -f2- | tr -d '\r' || true
  fi
}

detect_docker_access() {
  if docker info >/dev/null 2>&1; then
    DOCKER_CMD=(docker)
    return 0
  fi
  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    DOCKER_CMD=(sudo docker)
    return 0
  fi
  fail "Docker daemon is not accessible"
  return 1
}

build_compose_files() {
  COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml)
  if [[ "$HTTPS" -eq 1 ]]; then
    COMPOSE_FILES+=(-f docker-compose.cloud.https.yml)
  else
    COMPOSE_FILES+=(-f docker-compose.cloud.http.yml)
  fi
}

compose() {
  "${DOCKER_CMD[@]}" compose "${COMPOSE_FILES[@]}" "$@"
}

resolve_base_url() {
  if [[ -n "$BASE_URL" ]]; then
    return 0
  fi
  local public_url
  public_url="$(env_value PUBLIC_URL)"
  if [[ -n "$public_url" ]]; then
    BASE_URL="${public_url%/}"
    if [[ "$HTTPS" -eq 1 ]] && [[ "$BASE_URL" != https://* ]]; then
      BASE_URL="https://${BASE_URL#http://}"
    fi
    return 0
  fi
  if [[ "$HTTPS" -eq 1 ]]; then
    BASE_URL="https://127.0.0.1"
  else
    BASE_URL="http://127.0.0.1"
  fi
}

edge_curl() {
  local url="$1"
  if [[ "$HTTPS" -eq 1 ]] || [[ "$BASE_URL" == https://* ]]; then
    curl -fsSk -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000"
  else
    curl -fsS -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000"
  fi
}

edge_http_code() {
  local url="$1"
  if [[ "$HTTPS" -eq 1 ]] || [[ "$BASE_URL" == https://* ]]; then
    curl -sSk -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000"
  else
    curl -sS -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000"
  fi
}

edge_curl_body() {
  local url="$1"
  if [[ "$HTTPS" -eq 1 ]] || [[ "$BASE_URL" == https://* ]]; then
    curl -fsSk "$url" 2>/dev/null || true
  else
    curl -fsS "$url" 2>/dev/null || true
  fi
}

check_compose_status() {
  section "Compose status"
  if ! compose ps; then
    fail "docker compose ps failed"
    return
  fi
  ok "compose ps"
}

check_api_health() {
  section "API health"
  local code body overall
  code="$(edge_curl "${BASE_URL}/api/health")"
  if [[ "$code" == "200" ]]; then
    ok "/api/health -> 200"
  else
    fail "/api/health -> ${code} (expected 200)"
  fi

  body="$(edge_curl_body "${BASE_URL}/api/health/all")"
  if [[ -z "$body" ]]; then
    fail "/api/health/all unreachable"
    return
  fi
  overall="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status","unknown"))' 2>/dev/null || echo unknown)"
  if [[ "$overall" == "ok" ]]; then
    ok "/api/health/all -> ok"
  elif [[ "$overall" == "degraded" ]]; then
    warn "/api/health/all -> degraded"
  else
    fail "/api/health/all -> ${overall}"
  fi
  printf '%s\n' "$body" | python3 -m json.tool 2>/dev/null | head -40 || printf '%s\n' "$body"
}

check_postgres_counts() {
  section "Postgres ingestion counts"
  local tasks_line docs points spans
  if ! tasks_line="$(compose exec -T postgres psql -U st_user -d scientific_tangle -At -c "select coalesce(string_agg(status || '=' || cnt::text, ', ' order by status), 'none') from (select status, count(*) cnt from ingestion_tasks group by status) t;" 2>&1)"; then
    fail "postgres ingestion_tasks query failed: ${tasks_line}"
    return
  fi
  if ! docs="$(compose exec -T postgres psql -U st_user -d scientific_tangle -At -c "select count(*) from indexed_documents;" 2>&1)"; then
    fail "postgres indexed_documents query failed: ${docs}"
    return
  fi
  if ! points="$(compose exec -T postgres psql -U st_user -d scientific_tangle -At -c "select coalesce(sum(indexed_points_count), 0) from indexed_documents;" 2>&1)"; then
    fail "postgres indexed_points query failed: ${points}"
    return
  fi
  if ! spans="$(compose exec -T postgres psql -U st_user -d scientific_tangle -At -c "select count(*) from source_span_lookup;" 2>&1)"; then
    fail "postgres source_spans query failed: ${spans}"
    return
  fi

  tasks_line="$(printf '%s' "$tasks_line" | tr -d '\r')"
  docs="$(printf '%s' "$docs" | tr -d '\r[:space:]')"
  points="$(printf '%s' "$points" | tr -d '\r[:space:]')"
  spans="$(printf '%s' "$spans" | tr -d '\r[:space:]')"

  printf 'ingestion_tasks: %s\n' "${tasks_line:-unknown}"
  printf 'indexed_documents: %s\n' "${docs:-0}"
  printf 'indexed_points: %s\n' "${points:-0}"
  printf 'source_spans: %s\n' "${spans:-0}"

  if [[ "${docs:-0}" -gt 0 && "${spans:-0}" -gt 0 && "${points:-0}" -gt 0 ]]; then
    ok "corpus data present"
  else
    warn "corpus data missing or incomplete (expected after batch ingestion)"
  fi
}

check_minio_counts() {
  section "MinIO source-files"
  local output count
  if ! output="$(compose exec -T minio sh -lc 'mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1 && mc ls --recursive local/source-files 2>/dev/null | wc -l' 2>&1)"; then
    fail "minio check failed: ${output}"
    return
  fi
  count="$(printf '%s' "$output" | tr -d '[:space:]')"
  printf 'source-files objects: %s\n' "${count:-0}"
  if [[ "${count:-0}" -gt 0 ]]; then
    ok "source-files bucket has objects"
  else
    warn "source-files bucket is empty"
  fi
}

check_qdrant_counts() {
  section "Qdrant st_evidence_v1"
  local output points
  if ! output="$(compose exec -T retrieval python -c 'import httpx; r=httpx.get("http://qdrant:6333/collections/st_evidence_v1", timeout=10); print(r.status_code); print(r.text[:4000])' 2>&1)"; then
    fail "qdrant check failed: ${output}"
    return
  fi
  points="$(printf '%s' "$output" | python3 -c 'import json,sys; data=sys.stdin.read().splitlines();
for line in data:
  if line.strip().startswith("{"):
    print(int(json.loads(line).get("result",{}).get("points_count",0))); break
else:
  print(0)' 2>/dev/null || echo 0)"
  printf '%s\n' "$output"
  printf 'points_count: %s\n' "${points:-0}"
  if [[ "${points:-0}" -gt 0 ]]; then
    ok "qdrant has indexed points"
  else
    warn "qdrant points_count is 0"
  fi
}

check_public_perimeter() {
  section "Public perimeter"
  local code path
  local blocked_paths=(
    "/model/v1/status"
    "/model/health"
    "/retrieval/health"
    "/orchestrator/health"
    "/ingestion/health"
    "/knowledge/health"
  )
  code="$(edge_curl "${BASE_URL}/api/health")"
  if [[ "$code" == "200" ]]; then
    ok "/api/health -> 200"
  else
    fail "/api/health -> ${code} (expected 200)"
  fi
  for path in "${blocked_paths[@]}"; do
    code="$(edge_http_code "${BASE_URL}${path}")"
    if [[ "$code" == "404" ]]; then
      ok "${path} -> 404"
    else
      fail "${path} -> ${code} (expected 404)"
    fi
  done
}

auth_login() {
  local body admin_password
  admin_password="$(env_value AUTH_SEED_ADMIN_PASSWORD)"
  admin_password="${admin_password:-admin}"
  if [[ "$HTTPS" -eq 1 ]] || [[ "$BASE_URL" == https://* ]]; then
    body="$(curl -fsSk "${BASE_URL}/api/auth/login" -H 'Content-Type: application/json' -d "{\"identifier\":\"admin\",\"password\":\"${admin_password}\"}" 2>/dev/null || true)"
  else
    body="$(curl -fsS "${BASE_URL}/api/auth/login" -H 'Content-Type: application/json' -d "{\"identifier\":\"admin\",\"password\":\"${admin_password}\"}" 2>/dev/null || true)"
  fi
  printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null || true
}

check_export_eval_smoke() {
  section "Export/eval smoke"
  local token code
  token="$(auth_login)"
  if [[ -z "$token" ]]; then
    warn "auth login failed, skipping export/eval smoke"
    return
  fi
  ok "auth login"

  if [[ "$HTTPS" -eq 1 ]] || [[ "$BASE_URL" == https://* ]]; then
    code="$(curl -fsSk -o /dev/null -w '%{http_code}' "${BASE_URL}/api/strategic/evaluation" -H "Authorization: Bearer ${token}" 2>/dev/null || echo 000)"
  else
    code="$(curl -fsS -o /dev/null -w '%{http_code}' "${BASE_URL}/api/strategic/evaluation" -H "Authorization: Bearer ${token}" 2>/dev/null || echo 000)"
  fi
  printf '/api/strategic/evaluation -> %s\n' "$code"
  if [[ "$code" == "200" ]]; then
    ok "strategic evaluation"
  elif [[ "$code" == "500" ]]; then
    warn "strategic evaluation returns 500 (known until eval files bundled)"
  else
    warn "strategic evaluation -> ${code}"
  fi

  if [[ "$HTTPS" -eq 1 ]] || [[ "$BASE_URL" == https://* ]]; then
    code="$(curl -fsSk -o /dev/null -w '%{http_code}' "${BASE_URL}/api/eval/report/summary" -H "Authorization: Bearer ${token}" 2>/dev/null || echo 000)"
  else
    code="$(curl -fsS -o /dev/null -w '%{http_code}' "${BASE_URL}/api/eval/report/summary" -H "Authorization: Bearer ${token}" 2>/dev/null || echo 000)"
  fi
  printf '/api/eval/report/summary -> %s\n' "$code"
  if [[ "$code" == "200" ]]; then
    ok "eval report summary"
  else
    warn "eval report summary -> ${code}"
  fi
}

check_search_smoke() {
  section "Search smoke"
  local token body total
  token="$(auth_login)"
  if [[ -z "$token" ]]; then
    warn "auth login failed, skipping search smoke"
    return
  fi
  if [[ "$HTTPS" -eq 1 ]] || [[ "$BASE_URL" == https://* ]]; then
    body="$(curl -fsSk "${BASE_URL}/api/search?question=%D0%BD%D0%B8%D0%BA%D0%B5%D0%BB%D1%8C&limit=5" -H "Authorization: Bearer ${token}" 2>/dev/null || true)"
  else
    body="$(curl -fsS "${BASE_URL}/api/search?question=%D0%BD%D0%B8%D0%BA%D0%B5%D0%BB%D1%8C&limit=5" -H "Authorization: Bearer ${token}" 2>/dev/null || true)"
  fi
  if [[ -z "$body" ]]; then
    warn "search request failed"
    return
  fi
  total="$(printf '%s' "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(int(d.get("total_found") or len(d.get("items") or [])))' 2>/dev/null || echo 0)"
  printf 'search total_found: %s\n' "$total"
  if [[ "${total:-0}" -gt 0 ]]; then
    ok "search returns results"
  else
    warn "search returned no results"
  fi
}

main() {
  build_compose_files
  resolve_base_url
  detect_docker_access || exit 1

  printf 'Cloud verify\nbase_url: %s\n' "$BASE_URL"

  check_compose_status
  check_api_health
  check_postgres_counts
  check_minio_counts
  check_qdrant_counts
  check_public_perimeter
  check_export_eval_smoke
  if [[ "$SKIP_SEARCH" -eq 0 ]]; then
    check_search_smoke
  fi

  section "Summary"
  printf 'failures: %s\n' "$FAILURES"
  printf 'warnings: %s\n' "$WARNINGS"
  if [[ "$FAILURES" -gt 0 ]]; then
    fail "critical checks failed"
    exit 1
  fi
  ok "critical checks passed"
  exit 0
}

main "$@"
