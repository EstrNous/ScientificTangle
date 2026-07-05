# Cloud deploy: инструкция для оператора

Одна команда после создания VM. Нужны только **публичный IP** (или домен) и доступ по SSH.

## 1. Создать VM в облаке

| Параметр | Значение |
|----------|----------|
| ОС | Ubuntu 22.04 или 24.04 |
| vCPU | 8, **гарантированные 100%** (не burstable) |
| RAM | 16 GB |
| Диск | 100 GB SSD/NVMe |
| Тип | **непрерываемая** (не preemptible / spot) |
| Сеть | публичный IPv4 |

Открыть в security group / firewall:

| Порт | Назначение |
|------|------------|
| 22 | SSH |
| 80 | UI + API (nginx) |

Порты 5432, 6379, 7474, 6333 и др. **наружу не открывать** — `docker-compose.cloud.yml` их не публикует.

## 2. Подключиться по SSH

```bash
ssh ubuntu@ВАШ_IP
```

## 3. Склонировать репозиторий

```bash
sudo apt-get update -y
sudo apt-get install -y git
git clone https://github.com/EstrNous/ScientificTangle.git
cd ScientificTangle
```

## 4. Запустить деплой (главный шаг)

Подставьте **свой публичный IP** вместо `203.0.113.10`:

```bash
chmod +x scripts/cloud_deploy.sh
./scripts/cloud_deploy.sh 203.0.113.10 --install-docker --yandex-api-key KEY --yandex-folder-id b1g...
```

Или положите ключи в `.env.yandex` (см. `.env.yandex.example`) — скрипт подхватит их автоматически.

Скрипт сам:

1. установит Docker (флаг `--install-docker`);
2. создаст `.env` из `.env.example` и запишет публичный адрес/Yandex-поля;
3. создаст JWT-ключи в `secrets/`;
4. соберёт и поднимет весь стек (`docker compose` + prod + cloud overrides);
5. засеет пользователей и demo corpus;
6. проверит `/api/health`;
7. запишет пароли в `infra/deploy/credentials.txt`.

### Опции

```bash
./scripts/cloud_deploy.sh 203.0.113.10 --install-docker
./scripts/cloud_deploy.sh demo.example.com --https --install-docker
./scripts/cloud_deploy.sh 203.0.113.10 --no-demo --install-docker
./scripts/cloud_deploy.sh 203.0.113.10 --yandex-api-key KEY --yandex-folder-id b1g...
./scripts/cloud_deploy.sh 203.0.113.10 --expose-ports --http-port 8080
```

Без ключей Yandex demo corpus **не запускается** (чтобы не индексировать в degraded-режиме). Для деплоя без demo: `--no-demo`.

С `--expose-ports` наружу публикуются порты сервисов (5432, 8000–8006, 3000 и др.) — открывайте их в firewall только при необходимости.

Через Makefile (на Linux VM):

```bash
make deploy-cloud HOST=203.0.113.10 DEPLOY_ARGS="--install-docker"
```

## 5. Открыть в браузере

```
http://ВАШ_IP/
```

Логин по умолчанию:

| Роль | Логин | Пароль |
|------|-------|--------|
| admin | `admin` | `admin` |
| researcher | `researcher` | `researcher` |

Полный список паролей (Grafana, БД) — в файле на сервере:

```bash
cat infra/deploy/credentials.txt
```

## 6. Проверка

Одна команда — полная диагностика стенда:

```bash
chmod +x scripts/cloud_verify.sh
./scripts/cloud_verify.sh
```

Скрипт показывает: `compose ps`, `/api/health` и `/api/health/all`, счётчики Postgres (ingestion, indexed documents, source spans), объекты MinIO `source-files`, `points_count` в Qdrant, проверку периметра (internal routes → 404), smoke export/eval и поиск.

Для HTTPS-стенда:

```bash
./scripts/cloud_verify.sh --https --base-url https://ВАШ_IP/
```

Ручные проверки (если нужны отдельно):

```bash
curl -fsS http://127.0.0.1/api/health
curl -fsS http://127.0.0.1/api/health/all
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml ps
```

### Что считать нормой

| Проверка | Норма |
|----------|-------|
| `/api/health` | HTTP 200 |
| `/api/health/all` | `status: ok` |
| `/model/v1/status`, `/model/health`, `/retrieval/health`, `/orchestrator/health`, `/ingestion/health`, `/knowledge/health` снаружи | HTTP 404 |
| `indexed_documents` | > 0 после загрузки корпуса |
| `source_span_lookup` | > 0 |
| Qdrant `points_count` | > 0 |
| `/api/search` | `total_found > 0` при загруженном корпусе |

Пустые counts при `--no-demo` до batch ingestion — ожидаемо (скрипт покажет WARN, не FAIL).

## 7. Recovery runbook

Если поиск/чат без источников или UI «не видит» датасет:

1. **Не делать** `down -v` без явной необходимости — volumes могут содержать нужные данные.
2. **Не запускать** `scripts/seed_demo.py` на полном корпусе одним запросом — лимит upload 200 MB на пачку, один multipart на 2.2G даст `413`.
3. Проверить, есть ли файлы на диске VM:

```bash
du -sh ~/ScientificTangle/demo/seed_data/yandex_disk_corpus
find ~/ScientificTangle/demo/seed_data/yandex_disk_corpus -type f | wc -l
```

4. Файлы на диске ≠ данные в приложении. Корпус нужно отправить через `scripts/seed_corpus_batches.py` (см. ниже) или маленькими пачками через UI Upload.
5. После каждой пачки:

```bash
./scripts/cloud_verify.sh --skip-search
```

6. Если `ingestion_tasks` в статусе `failed` — смотреть `error_message`:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml exec -T postgres psql -U st_user -d scientific_tangle -c "select id,status,error_message from ingestion_tasks order by created_at desc limit 5;"
```

7. Периметр: снаружи internal prefixes (`/model`, `/retrieval`, `/orchestrator`, `/ingestion`, `/knowledge`) должны отдавать 404. HTTP cloud использует `nginx.cloud.http.conf`; при старом dev nginx — пересоздать nginx: `docker compose ... up -d nginx` после `git pull`.

После cloud deploy не используйте `make up`: это dev-стек. Для cloud-стенда используйте:

```bash
make cloud-up
make cloud-ps
make cloud-logs SERVICE=nginx
make cloud-verify
make cloud-down
make cloud-down-v
```

## 8. Загрузка корпуса batch-ами

Для корпуса больше 200 MB не используйте `seed_demo.py` — он отправляет все файлы одним запросом и получит `413`.

После деплоя с `--no-demo`:

```bash
python3 -m pip install -q httpx
python3 eval/yandex_disk_corpus.py --output-dir demo/seed_data/yandex_disk_corpus

ADMIN_PASS="$(grep AUTH_SEED_ADMIN_PASSWORD .env | cut -d= -f2-)"
ADMIN_PASS="${ADMIN_PASS:-admin}"

python3 scripts/seed_corpus_batches.py \
  --api-url http://127.0.0.1/api \
  --corpus-dir demo/seed_data/yandex_disk_corpus \
  --username admin \
  --password "$ADMIN_PASS" \
  --resume
```

Если словарь уже активен, добавьте `--skip-dictionary`.

Скрипт группирует файлы пачками (~80 MB), пишет прогресс в `.seed_corpus_batches_state.json` и поддерживает `--resume` после падения.

## Yandex Cloud: cloud-init (опционально)

При создании VM вставьте в **user-data** содержимое `infra/deploy/yandex-cloud-init.yaml`, предварительно заменив:

- `YOUR_PUBLIC_IP` — публичный IP VM (известен после создания, можно вторым заходом по SSH);
- или запустите cloud-init только для установки Docker, а deploy вручную шагом 4.

## Частые проблемы

| Симптом | Решение |
|---------|---------|
| `Health check failed` | `docker compose ... logs gateway auth_audit orchestrator`; подождать 5–10 мин после первого build |
| Не открывается в браузере | проверить security group: порт 80 открыт; `curl http://127.0.0.1/` на VM |
| `seed_demo` failed / `413` | полный корпус не влезает в один upload; используйте `--no-demo` и `seed_corpus_batches.py` |
| Корпус на диске, но поиск пустой | файлы не в MinIO/Postgres/Qdrant; см. раздел Recovery runbook, `./scripts/cloud_verify.sh` |
| `/model` или `/retrieval` доступны снаружи | устаревший dev nginx; `git pull`, `docker compose ... up -d nginx` или deploy с `--https` |
| LLM не отвечает | добавить `YANDEX_API_KEY` и `YANDEX_FOLDER_ID` в `.env`, `docker compose ... up -d model gateway` |
| `password authentication failed` или Neo4j unhealthy после старых попыток | старые Docker volumes могли быть созданы с другими паролями; для чистого demo reset выполните `docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml down -v` и запустите deploy заново |

## Остановка и перезапуск

```bash
make cloud-down
make cloud-up
```

Или вручную (HTTP cloud):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml up -d
```

Полный сброс с удалением данных:

```bash
make cloud-down-v
./scripts/cloud_deploy.sh ВАШ_IP --install-docker
```

`make down` останавливает только dev-стек; для cloud используйте `make cloud-down-v`.
