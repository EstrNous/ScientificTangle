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

```bash
curl -fsS http://127.0.0.1/api/health
curl -fsS http://127.0.0.1/api/health/all
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml ps
```

После cloud deploy не используйте `make up`: это dev-стек. Для cloud-стенда используйте:

```bash
make cloud-up
make cloud-ps
make cloud-logs SERVICE=nginx
make cloud-down
```

## Yandex Cloud: cloud-init (опционально)

При создании VM вставьте в **user-data** содержимое `infra/deploy/yandex-cloud-init.yaml`, предварительно заменив:

- `YOUR_PUBLIC_IP` — публичный IP VM (известен после создания, можно вторым заходом по SSH);
- или запустите cloud-init только для установки Docker, а deploy вручную шагом 4.

## Частые проблемы

| Симптом | Решение |
|---------|---------|
| `Health check failed` | `docker compose ... logs gateway auth_audit orchestrator`; подождать 5–10 мин после первого build |
| Не открывается в браузере | проверить security group: порт 80 открыт; `curl http://127.0.0.1/` на VM |
| `seed_demo` failed | проверить интернет для скачивания corpus; повторить `python3 scripts/seed_demo.py --api-url http://127.0.0.1/api` |
| LLM не отвечает | добавить `YANDEX_API_KEY` и `YANDEX_FOLDER_ID` в `.env`, `docker compose ... up -d model gateway` |
| `password authentication failed` или Neo4j unhealthy после старых попыток | старые Docker volumes могли быть созданы с другими паролями; для чистого demo reset выполните `docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml down -v` и запустите deploy заново |

## Остановка и перезапуск

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml up -d
```

Полный сброс с удалением данных:

```bash
make down
./scripts/cloud_deploy.sh ВАШ_IP
```
