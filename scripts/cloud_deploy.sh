#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST=""
HTTPS=0
WITH_DEMO=1
INSTALL_DOCKER=0
YANDEX_API_KEY=""
YANDEX_FOLDER_ID=""
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml)
WAIT_TIMEOUT="${WAIT_TIMEOUT:-2400}"

usage() {
  cat <<'EOF'
Usage: ./scripts/cloud_deploy.sh <PUBLIC_IP_OR_DOMAIN> [options]

Одна команда: сгенерировать .env, поднять весь стек, засеять пользователей и demo corpus.

Options:
  --https                  PUBLIC_URL=https://HOST, secure refresh cookie
  --no-demo                не запускать seed_demo (только users)
  --install-docker         установить Docker на Ubuntu (нужен sudo)
  --yandex-api-key KEY     Yandex AI API key
  --yandex-folder-id ID    Yandex folder ID
  -h, --help               эта справка

Пример:
  ./scripts/cloud_deploy.sh 203.0.113.10
  ./scripts/cloud_deploy.sh demo.example.com --https --yandex-api-key XXX --yandex-folder-id b1g...

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
    --yandex-api-key)
      YANDEX_API_KEY="${2:-}"
      shift 2
      ;;
    --yandex-folder-id)
      YANDEX_FOLDER_ID="${2:-}"
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

GEN_ARGS=(--host "$HOST")
if [[ "$HTTPS" -eq 1 ]]; then
  GEN_ARGS+=(--https)
fi
if [[ -n "$YANDEX_API_KEY" ]]; then
  GEN_ARGS+=(--yandex-api-key "$YANDEX_API_KEY")
fi
if [[ -n "$YANDEX_FOLDER_ID" ]]; then
  GEN_ARGS+=(--yandex-folder-id "$YANDEX_FOLDER_ID")
fi

log "Generating .env and credentials for host $HOST"
python3 scripts/generate_cloud_env.py "${GEN_ARGS[@]}"

if [[ "$HTTPS" -eq 1 ]]; then
  log "Generating self-signed TLS certificate for $HOST"
  export NGINX_SERVER_NAME="$HOST"
  python3 -m pip install -q cryptography 2>/dev/null || pip3 install -q cryptography
  rm -f secrets/tls/fullchain.pem secrets/tls/privkey.pem
  python3 scripts/generate_tls_certs.py
  COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.https.yml)
fi

log "Generating JWT keys"
python3 scripts/generate_auth_keys.py

log "Building images"
docker compose "${COMPOSE_FILES[@]}" build

log "Starting stack (timeout ${WAIT_TIMEOUT}s)"
docker compose "${COMPOSE_FILES[@]}" up -d --wait --wait-timeout "$WAIT_TIMEOUT"

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
  PUBLIC_URL="$(grep '^PUBLIC_URL=' .env | cut -d= -f2-)"
  python3 scripts/seed_demo.py \
    --api-url "http://127.0.0.1/api" \
    --username admin \
    --password admin12345
fi

PUBLIC_URL="$(grep '^PUBLIC_URL=' .env | cut -d= -f2-)"

log "Health check"
HEALTH_URL="${PUBLIC_URL}/api/health"
if [[ "$HTTPS" -eq 1 ]]; then
  HEALTH_URL="${PUBLIC_URL}/api/health"
fi
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
  docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml ps
  docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml logs -f nginx gateway
  make down

================================================================
EOF
