# Prod compose: закрытый внешний периметр

**Обновлено:** 2026-07-04

## Назначение

Публичный стенд (demo/prod) поднимается через prod overlay: наружу доступен только nginx на 80/443. Backend, БД и observability остаются во внутренней сети `st-net`.

## Быстрый старт

Одна команда (создаёт `.env`, ключи, TLS, поднимает стек, seed пользователей):

```bash
make prod
```

С demo-корпусом:

```bash
make prod-demo
```

Smoke с хоста:

```bash
curl -k https://localhost/api/health
curl -k https://localhost/api/auth/login -H 'Content-Type: application/json' \
  -d '{"identifier":"admin","password":"admin"}'
```

UI: `https://localhost/`

Grafana: `https://localhost/grafana/` (basic auth из `GRAFANA_NGINX_BASIC_*`)

## Команды

| Команда | Что делает |
|---------|------------|
| `make prod` | `.env` + bootstrap + `up --build --wait` + seed пользователей |
| `make prod-demo` | `make prod` + загрузка demo corpus |
| `make up-prod` | только поднять prod-стек (без seed) |
| `make seed-prod` | seed пользователей в уже поднятом prod |
| `make logs-prod` | логи prod-стека |
| `make down-prod` | остановить prod |

## Dev vs prod

| Команда | Compose | Host ports |
|---------|---------|------------|
| `make up` | `docker-compose.yml` + `docker-compose.dev.yml` | все сервисы (как раньше) |
| `make prod` | `docker-compose.yml` + `docker-compose.prod.yml` | только nginx 80/443 |

## TLS

- Self-signed для staging генерируется автоматически в `make prod` (`scripts/generate_tls_certs.py`)
- Сертификаты: `secrets/tls/fullchain.pem`, `secrets/tls/privkey.pem`
- Продакшен: положить Let's Encrypt certs в `TLS_CERT_DIR` и задать `NGINX_SERVER_NAME` в `.env`

## Публичные маршруты nginx (prod)

- `/` → UI
- `/api/auth/`, `/.well-known/jwks.json` → auth_audit
- `/api/*` → gateway
- `/grafana/` → Grafana (basic auth)
- `/health` → gateway health probe

Маршруты `/orchestrator/`, `/ingestion/`, `/knowledge/`, `/retrieval/`, `/model/` в prod **закрыты** (404).

## Eval и скрипты с prod edge

```bash
EVAL_SERVICE_URL=https://localhost/api/query EDGE_TLS_VERIFY=false python eval/run_eval.py --official-only ...
```

## Проверка периметра

```bash
RUN_PROD_COMPOSE=1 python -m pytest -q tests/e2e/test_prod_perimeter.py
python scripts/audit_repo.py
```

## Секреты на стенде

Перед публичным деплоем сменить в `.env`:

- `POSTGRES_PASSWORD`, `MINIO_*`, `INTERNAL_SERVICE_TOKEN`
- `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_NGINX_BASIC_PASSWORD`
- JWT keys через `scripts/generate_auth_keys.py` (не коммитить)

## Связанные файлы

- [docker-compose.yml](../../docker-compose.yml) — base без host ports
- [docker-compose.dev.yml](../../docker-compose.dev.yml) — dev ports
- [docker-compose.prod.yml](../../docker-compose.prod.yml) — prod limits + nginx edge
- [infra/nginx/nginx.prod.conf.template](../../infra/nginx/nginx.prod.conf.template)
