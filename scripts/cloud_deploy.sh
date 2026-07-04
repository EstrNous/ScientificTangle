#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST=""
HTTPS=0
WITH_DEMO=1
INSTALL_DOCKER=0
EXPOSE_PORTS=0
HTTP_PORT=80
HTTPS_PORT=443
YANDEX_API_KEY=""
YANDEX_FOLDER_ID=""
YANDEX_ENV_FILE=""
COMPOSE_FILES=()
WAIT_TIMEOUT="${WAIT_TIMEOUT:-2400}"

usage() {
  cat <<'EOF'
Usage: ./scripts/cloud_deploy.sh <PUBLIC_IP_OR_DOMAIN> [options]

Одна команда: сгенерировать .env, поднять весь стек, засеять пользователей и demo corpus.

Options:
  --https                  PUBLIC_URL=https://HOST, secure refresh cookie
  --no-demo                не запускать seed_demo (только users)
  --install-docker         установить Docker на Ubuntu (нужен sudo)
  --expose-ports           опубликовать порты сервисов (5432, 8000–8006, 3000, …)
  --http-port PORT         внешний порт nginx HTTP (по умолчанию 80)
  --https-port PORT        внешний порт nginx HTTPS (по умолчанию 443, с --https)
  --yandex-api-key KEY     Yandex AI API key
  --yandex-folder-id ID    Yandex folder ID
  --yandex-env-file PATH   файл с YANDEX_API_KEY и YANDEX_FOLDER_ID (по умолчанию .env.yandex)
  -h, --help               эта справка

Ключи Yandex (нужны для нормальной индексации demo corpus):
  1) флаги --yandex-api-key / --yandex-folder-id
  2) переменные окружения YANDEX_API_KEY / YANDEX_FOLDER_ID
  3) файл .env.yandex в корне репозитория
  4) уже записанные значения в существующем .env (повторный деплой)

Без ключей demo seed не запускается (используйте --no-demo, чтобы пропустить).

Примеры:
  ./scripts/cloud_deploy.sh 203.0.113.10 --yandex-api-key KEY --yandex-folder-id b1g...
  ./scripts/cloud_deploy.sh 203.0.113.10 --expose-ports --http-port 8080
  ./scripts/cloud_deploy.sh demo.example.com --https --install-docker

После успеха откройте в браузере PUBLIC_URL из infra/deploy/credentials.txt
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --https)
      HTTPS=1
      shift
      ;;
    --no-demo)
      WITH_DEMO=0
      shift
      ;;
    --install-docker)
      INSTALL_DOCKER=1
      shift
      ;;
    --expose-ports)
      EXPOSE_PORTS=1
      shift
      ;;
    --http-port)
      HTTP_PORT="${2:-}"
      shift 2
      ;;
    --https-port)
      HTTPS_PORT="${2:-}"
      shift 2
      ;;
    --yandex-api-key)
      YANDEX_API_KEY="${2:-}"
      shift 2
      ;;
    --yandex-folder-id)
      YANDEX_FOLDER_ID="${2:-}"
      shift 2
      ;;
    --yandex-env-file)
      YANDEX_ENV_FILE="${2:-}"
      shift 2
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -z "$HOST" ]]; then
        HOST="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$HOST" ]]; then
  usage >&2
  exit 1
fi

HOST="${HOST#http://}"
HOST="${HOST#https://}"
HOST="${HOST%/}"

log() {
  printf '\n==> %s\n' "$1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1" >&2
    exit 1
  fi
}

load_yandex_secrets() {
  local secrets_file="${YANDEX_ENV_FILE:-$ROOT_DIR/.env.yandex}"
  if [[ -f "$secrets_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$secrets_file"
    set +a
  fi
  if [[ -z "$YANDEX_API_KEY" && -f "$ROOT_DIR/.env" ]]; then
    YANDEX_API_KEY="$(grep -m1 '^YANDEX_API_KEY=' "$ROOT_DIR/.env" | cut -d= -f2- || true)"
  fi
  if [[ -z "$YANDEX_FOLDER_ID" && -f "$ROOT_DIR/.env" ]]; then
    YANDEX_FOLDER_ID="$(grep -m1 '^YANDEX_FOLDER_ID=' "$ROOT_DIR/.env" | cut -d= -f2- || true)"
  fi
}

env_value() {
  grep -m1 "^${1}=" "$ROOT_DIR/.env" | cut -d= -f2- || true
}

repair_compose_args() {
  REPAIR_COMPOSE_ARGS=()
  local token
  local expect_file=0
  for token in "${COMPOSE_FILES[@]}"; do
    if [[ "$token" == "-f" ]]; then
      expect_file=1
      continue
    fi
    if [[ "$expect_file" -eq 1 ]]; then
      REPAIR_COMPOSE_ARGS+=(--compose-file "$token")
      expect_file=0
    fi
  done
}

run_postgres_repair() {
  repair_compose_args
  if [[ "${1:-}" == "sync-only" ]]; then
    python3 scripts/repair_postgres_env.py --env "$ROOT_DIR/.env" --sync-urls-only
    return 0
  fi
  python3 scripts/repair_postgres_env.py --env "$ROOT_DIR/.env" "${REPAIR_COMPOSE_ARGS[@]}"
}

compose_container_id() {
  docker compose "${COMPOSE_FILES[@]}" ps -q "$1" 2>/dev/null | head -1
}

container_config_env() {
  local service="$1"
  local key="$2"
  local container_id
  container_id="$(compose_container_id "$service")"
  if [[ -z "$container_id" ]]; then
    return 1
  fi
  docker inspect "$container_id" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | grep -m1 "^${key}=" | cut -d= -f2- || true
}

auth_env_mismatches() {
  local key expected actual found=0
  for key in AUTH_ALLOWED_ORIGINS AUTH_DATABASE_URL; do
    expected="$(env_value "$key")"
    if [[ -z "$expected" ]]; then
      continue
    fi
    actual="$(container_config_env auth_audit "$key")"
    if [[ "$actual" != "$expected" ]]; then
      found=1
      printf '%s: expected=%s actual=%s\n' "$key" "$expected" "${actual:-<unset>}"
    fi
  done
  return $((found == 0 ? 0 : 1))
}

wait_for_auth_healthy() {
  log "Waiting for auth_audit to become healthy"
  if ! docker compose "${COMPOSE_FILES[@]}" up -d --wait --wait-timeout "$WAIT_TIMEOUT" auth_audit; then
    echo "auth_audit failed to become healthy" >&2
    docker logs st-auth-audit --tail 40 >&2 || true
    exit 1
  fi
}

sync_auth_facing_services() {
  local auth_services=(auth_audit orchestrator gateway nginx)
  local attempt details

  for attempt in 1 2; do
    if [[ "$attempt" -eq 1 ]]; then
      log "Applying .env to auth-facing services (force-recreate)"
    else
      log "Retry: force-recreate auth-facing services"
    fi
    docker compose "${COMPOSE_FILES[@]}" up -d --force-recreate "${auth_services[@]}"
    docker compose "${COMPOSE_FILES[@]}" up -d --wait --wait-timeout "$WAIT_TIMEOUT" "${auth_services[@]}"

    if auth_env_mismatches; then
      log "auth_audit env matches .env (AUTH_ALLOWED_ORIGINS, AUTH_DATABASE_URL)"
      wait_for_auth_healthy
      return 0
    fi

    details="$(auth_env_mismatches 2>&1 || true)"
    log "auth_audit env mismatch:"
    while IFS= read -r line; do
      [[ -n "$line" ]] && log "  $line"
    done <<< "$details"
  done

  echo "auth_audit env still mismatched after recreate" >&2
  auth_env_mismatches >&2 || true
  exit 1
}

require_yandex_for_demo() {
  local key folder
  key="$(env_value YANDEX_API_KEY)"
  folder="$(env_value YANDEX_FOLDER_ID)"
  if [[ -n "$key" && -n "$folder" ]]; then
    return 0
  fi
  cat >&2 <<'EOF'
Demo corpus требует ключи Yandex для нормальной индексации (embeddings + LLM).

Укажите ключи одним из способов:
  ./scripts/cloud_deploy.sh HOST --yandex-api-key KEY --yandex-folder-id FOLDER
  export YANDEX_API_KEY=... YANDEX_FOLDER_ID=... && ./scripts/cloud_deploy.sh HOST
  echo 'YANDEX_API_KEY=...' > .env.yandex && echo 'YANDEX_FOLDER_ID=...' >> .env.yandex

Или пропустите demo: --no-demo
EOF
  exit 1
}

wait_for_model_yandex() {
  log "Waiting for model service with Yandex credentials"
  for attempt in $(seq 1 60); do
    if docker compose "${COMPOSE_FILES[@]}" exec -T model python -c "
import httpx
response = httpx.get('http://127.0.0.1:8006/v1/status', timeout=10.0)
response.raise_for_status()
if not response.json().get('yandex_configured'):
    raise SystemExit('yandex_configured=false')
" 2>/dev/null; then
      return 0
    fi
    sleep 5
    if [[ "$attempt" -eq 60 ]]; then
      echo "Model service: yandex_configured=false после пересоздания контейнера" >&2
      echo "Проверьте YANDEX_API_KEY и YANDEX_FOLDER_ID в .env" >&2
      exit 1
    fi
  done
}

build_compose_files() {
  COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml)
  if [[ "$EXPOSE_PORTS" -eq 1 ]]; then
    COMPOSE_FILES+=(-f docker-compose.cloud.expose.yml)
  fi
  if [[ "$HTTPS" -eq 1 ]]; then
    COMPOSE_FILES+=(-f docker-compose.cloud.https.yml)
  else
    COMPOSE_FILES+=(-f docker-compose.cloud.http.yml)
  fi
}

install_docker_ubuntu() {
  log "Installing Docker (Ubuntu)"
  require_cmd sudo
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl git python3 python3-pip
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER" || true
  fi
  if ! docker compose version >/dev/null 2>&1; then
    sudo apt-get install -y docker-compose-plugin || true
  fi
}

if [[ "$INSTALL_DOCKER" -eq 1 ]]; then
  install_docker_ubuntu
fi

require_cmd docker
require_cmd python3

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is required" >&2
  exit 1
fi

load_yandex_secrets

GEN_ARGS=(--host "$HOST" --http-port "$HTTP_PORT" --https-port "$HTTPS_PORT")
if [[ "$HTTPS" -eq 1 ]]; then
  GEN_ARGS+=(--https)
fi
if [[ "$EXPOSE_PORTS" -eq 1 ]]; then
  GEN_ARGS+=(--expose-ports)
fi
if [[ -n "$YANDEX_API_KEY" ]]; then
  GEN_ARGS+=(--yandex-api-key "$YANDEX_API_KEY")
fi
if [[ -n "$YANDEX_FOLDER_ID" ]]; then
  GEN_ARGS+=(--yandex-folder-id "$YANDEX_FOLDER_ID")
fi

log "Generating .env and credentials for host $HOST"
python3 scripts/generate_cloud_env.py "${GEN_ARGS[@]}"
run_postgres_repair sync-only

if [[ "$WITH_DEMO" -eq 1 ]]; then
  require_yandex_for_demo
fi

build_compose_files

if [[ "$HTTPS" -eq 1 ]]; then
  log "Generating self-signed TLS certificate for $HOST"
  export NGINX_SERVER_NAME="$HOST"
  python3 -m pip install -q cryptography 2>/dev/null || pip3 install -q cryptography
  rm -f secrets/tls/fullchain.pem secrets/tls/privkey.pem
  python3 scripts/generate_tls_certs.py
fi

log "Generating JWT keys"
python3 scripts/generate_auth_keys.py

log "Building images"
docker compose "${COMPOSE_FILES[@]}" build

log "Starting stack (timeout ${WAIT_TIMEOUT}s)"
docker compose "${COMPOSE_FILES[@]}" up -d --wait --wait-timeout "$WAIT_TIMEOUT"

log "Repairing PostgreSQL credentials and database URLs"
run_postgres_repair
sync_auth_facing_services

if [[ "$WITH_DEMO" -eq 1 ]]; then
  log "Recreating model service to apply Yandex credentials"
  docker compose "${COMPOSE_FILES[@]}" up -d --force-recreate model
  wait_for_model_yandex
fi

log "Seeding auth users"
docker compose "${COMPOSE_FILES[@]}" exec -T auth_audit auth-seed-users

log "Seeding notification fixtures"
docker compose "${COMPOSE_FILES[@]}" exec -T notification sh -c "cd /app/infra/postgres/notification_db && PYTHONPATH=. python seed.py"

if [[ "$WITH_DEMO" -eq 1 ]]; then
  log "Preparing demo corpus"
  python3 -m pip install -q httpx 2>/dev/null || pip3 install -q httpx
  CORPUS_DIR="demo/seed_data/yandex_disk_corpus"
  if [[ ! -d "$CORPUS_DIR" ]] || [[ -z "$(find "$CORPUS_DIR" -type f 2>/dev/null | head -1)" ]]; then
    log "Downloading demo corpus from Yandex Disk"
    python3 eval/yandex_disk_corpus.py --output-dir "$CORPUS_DIR"
  fi
  log "Seeding demo corpus (offline, via gateway)"
  ADMIN_PASSWORD="$(env_value AUTH_SEED_ADMIN_PASSWORD)"
  ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin12345}"
  python3 scripts/seed_demo.py \
    --api-url "http://127.0.0.1/api" \
    --username admin \
    --password "$ADMIN_PASSWORD"
fi

PUBLIC_URL="$(env_value PUBLIC_URL)"

log "Health check"
HEALTH_URL="${PUBLIC_URL}/api/health"
for attempt in $(seq 1 30); do
  if curl -fsSk "${HEALTH_URL}" >/dev/null 2>&1 || curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    break
  fi
  sleep 5
  if [[ "$attempt" -eq 30 ]]; then
    echo "Health check failed for ${PUBLIC_URL}/api/health" >&2
    docker compose "${COMPOSE_FILES[@]}" ps
    exit 1
  fi
done

cat <<EOF

================================================================
ScientificTangle cloud deploy: SUCCESS

Откройте в браузере:
  ${PUBLIC_URL}/

Учётные данные:
  infra/deploy/credentials.txt

Полезные команды:
  docker compose ${COMPOSE_FILES[*]} ps
  docker compose ${COMPOSE_FILES[*]} logs -f nginx gateway
  make down

================================================================
EOF
