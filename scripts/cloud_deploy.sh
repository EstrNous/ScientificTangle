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
DOCKER_CMD=(docker)

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
    if compose exec -T model python -c "
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

docker_cli() {
  "${DOCKER_CMD[@]}" "$@"
}

compose() {
  docker_cli compose "${COMPOSE_FILES[@]}" "$@"
}

edge_curl() {
  local url="$1"
  if [[ "$HTTPS" -eq 1 ]]; then
    curl -fsSk -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000"
  else
    curl -fsS -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000"
  fi
}

check_public_perimeter() {
  local base_url="$1"
  local code
  log "Public perimeter check"
  code="$(edge_curl "${base_url}/api/health")"
  if [[ "$code" != "200" ]]; then
    echo "Perimeter check failed: ${base_url}/api/health returned ${code}, expected 200" >&2
    exit 1
  fi
  code="$(edge_curl "${base_url}/model/v1/status")"
  if [[ "$code" != "404" ]]; then
    echo "Perimeter check failed: ${base_url}/model/v1/status returned ${code}, expected 404" >&2
    exit 1
  fi
  code="$(edge_curl "${base_url}/retrieval/health")"
  if [[ "$code" != "404" ]]; then
    echo "Perimeter check failed: ${base_url}/retrieval/health returned ${code}, expected 404" >&2
    exit 1
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
  echo "Docker daemon is not accessible. Try running with sudo or re-login after --install-docker." >&2
  exit 1
}

warn_existing_stateful_volumes() {
  local volume
  for volume in scientifictangle_pg_data scientifictangle_neo4j_data; do
    if docker_cli volume inspect "$volume" >/dev/null 2>&1; then
      cat >&2 <<EOF
Warning: existing Docker volume detected: $volume
If this VM was previously deployed with different DB passwords, Postgres/Neo4j may keep old credentials.
For a clean demo VM, remove old state explicitly before deploy:
  ${DOCKER_CMD[*]} compose ${COMPOSE_FILES[*]} down -v
EOF
    fi
  done
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

detect_docker_access

if ! docker_cli compose version >/dev/null 2>&1; then
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

if [[ "$WITH_DEMO" -eq 1 ]]; then
  require_yandex_for_demo
fi

build_compose_files
warn_existing_stateful_volumes

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
compose build

log "Starting stack (timeout ${WAIT_TIMEOUT}s)"
if ! compose up -d --wait --wait-timeout "$WAIT_TIMEOUT"; then
  echo "Stack failed to become healthy" >&2
  compose ps >&2 || true
  docker_cli logs st-auth-audit --tail 40 >&2 || true
  docker_cli logs st-neo4j --tail 40 >&2 || true
  exit 1
fi

if [[ "$WITH_DEMO" -eq 1 ]]; then
  log "Recreating model service to apply Yandex credentials"
  compose up -d --force-recreate model
  wait_for_model_yandex
fi

log "Seeding auth users"
compose exec -T auth_audit auth-seed-users

log "Seeding notification fixtures"
compose exec -T notification sh -c "cd /app/infra/postgres/notification_db && PYTHONPATH=. python seed.py"

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
  ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
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
    compose ps
    exit 1
  fi
done

check_public_perimeter "${PUBLIC_URL}"

if [[ -x "$ROOT_DIR/scripts/cloud_verify.sh" ]]; then
  log "Running cloud verify (critical checks)"
  bash "$ROOT_DIR/scripts/cloud_verify.sh" --base-url "${PUBLIC_URL}" --skip-search
fi

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
  ./scripts/cloud_verify.sh --base-url ${PUBLIC_URL}
  make cloud-down

================================================================
EOF
