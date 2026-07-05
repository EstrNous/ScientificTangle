# ScientificTangle

Web-приложение «Научный Клубок» для НОРНИКЕЛЬ AI SCIENCE HACK.

## Учётные записи (сразу после деплоя)

Пароли задаются в `.env` переменными `AUTH_SEED_*` (см. `.env.example`). Значения по умолчанию:

| Роль | Логин | Пароль | Переменные в `.env` |
|------|-------|--------|---------------------|
| admin | `admin` | `admin` | `AUTH_SEED_ADMIN_USERNAME`, `AUTH_SEED_ADMIN_PASSWORD` |
| researcher | `researcher` | `researcher` | `AUTH_SEED_RESEARCHER_USERNAME`, `AUTH_SEED_RESEARCHER_PASSWORD` |
| analyst | `analyst` | `analyst` | `AUTH_SEED_ANALYST_USERNAME`, `AUTH_SEED_ANALYST_PASSWORD` |
| manager | `manager` | `manager` | `AUTH_SEED_MANAGER_USERNAME`, `AUTH_SEED_MANAGER_PASSWORD` |

После `cloud_deploy.sh` копия всех учётных данных (UI, Grafana, БД) записывается в `infra/deploy/credentials.txt` — это тот же набор значений из `.env`, удобный для оператора.

```bash
cat infra/deploy/credentials.txt
```

---

## Поднять с нуля на сервере (пример: `51.250.103.29`)

```bash
ssh ubuntu@51.250.103.29
cd ~/ScientificTangle   # или git clone и cd

git fetch origin
git checkout main
git pull origin main
```

Опционально — полная очистка volumes (удалит все проиндексированные документы):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml down -v
```

Деплой **без скачивания корпуса** (поведение по умолчанию). Нужны ключи Yandex для LLM и embeddings:

```bash
chmod +x scripts/cloud_deploy.sh scripts/cloud_verify.sh

# Вариант 1: флаги
./scripts/cloud_deploy.sh 51.250.103.29 \
  --yandex-api-key ВАШ_КЛЮЧ \
  --yandex-folder-id b1g...

# Вариант 2: файл .env.yandex в корне репозитория
# YANDEX_API_KEY=...
# YANDEX_FOLDER_ID=...

# Вариант 3: переменные окружения
export YANDEX_API_KEY=... YANDEX_FOLDER_ID=...
./scripts/cloud_deploy.sh 51.250.103.29
```

Скрипт сам: создаёт `.env`, JWT-ключи, собирает и поднимает стек, сеет пользователей, активирует словарь. Корпус **не** скачивается — документы загружаются вручную через UI.

Открыть в браузере: `http://51.250.103.29/` → войти как `researcher` / `researcher`.

---

## Как отключить скачивание датасета

По умолчанию `cloud_deploy.sh` работает с `SKIP_CORPUS=1` — корпус не скачивается и не индексируется.

| Способ | Эффект |
|--------|--------|
| Деплой без флагов | Корпус не трогается (дефолт) |
| `--skip-corpus` | Явно запретить корпус |
| **Не** передавать `--with-corpus` | Полный корпус (5 GB+) не скачивается |
| **Не** передавать `--with-demo` | Demo-корпус с Яндекс.Диска не скачивается |

`ensure_cloud_corpus.py` вызывается **только** при `--with-corpus` и наличии ключей Yandex. Для видео-демо достаточно ручной загрузки трёх docx через UI.

---

## Пересборка после `git pull`

Cloud compose-файлы (HTTP, без expose):

```text
docker-compose.yml
docker-compose.prod.yml
docker-compose.cloud.yml
docker-compose.cloud.http.yml
```

С `--https`: вместо `cloud.http` → `docker-compose.cloud.https.yml`.  
С `--expose-ports`: дополнительно `docker-compose.cloud.expose.yml`.

```bash
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml"

$COMPOSE build
$COMPOSE up -d --wait

# Если UI не обновился — пересборка без кэша:
$COMPOSE build --no-cache ui
$COMPOSE up -d ui nginx
```

Только словарь (без корпуса):

```bash
python3 -m pip install -q httpx
python3 scripts/seed_dictionary.py \
  --api-url http://127.0.0.1/api \
  --username admin \
  --password admin
```

---

## Проверка стенда

```bash
./scripts/cloud_verify.sh
./scripts/cloud_verify.sh --base-url http://51.250.103.29/
```

Ручные проверки:

```bash
# Health
curl -fsS http://127.0.0.1/api/health
curl -fsS http://127.0.0.1/api/health/all

# Login (пароль из AUTH_SEED_ADMIN_PASSWORD или дефолт admin)
curl -fsS http://127.0.0.1/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"admin","password":"admin"}'

# /model/v1/status снаружи закрыт (ожидается 404)
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/model/v1/status

# /model/v1/status внутри контейнera (yandex_configured=true)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml \
  exec -T model python -c "
import httpx
r = httpx.get('http://127.0.0.1:8006/v1/status', timeout=10)
print(r.status_code, r.json())
"
```

| Проверка | Норма |
|----------|-------|
| `/api/health` | HTTP 200 |
| `/api/auth/login` | JSON с `access_token` |
| `/model/v1/status` снаружи | HTTP 404 |
| `/model/v1/status` внутри model | `yandex_configured: true` |

---

## Чеклист демо для видео (ручная загрузка 3 docx)

### Предусловия

- [ ] `./scripts/cloud_deploy.sh HOST --yandex-api-key ... --yandex-folder-id ...` завершился SUCCESS
- [ ] `./scripts/cloud_verify.sh` — failures: 0
- [ ] Внутри model: `yandex_configured: true`
- [ ] Корпус **не** скачивался (`--with-corpus` не использовался)

### Шаг 1 — загрузить три файла через UI (`/upload`)

| # | Файл | Official id |
|---|------|-------------|
| 1 | `Электроэкстракция никеля. Влияние состава электролита.docx` | official-002 |
| 2 | `Распределение Au, Ag и МПГ между меднымникелевым штейном и шлаком.docx` | official-003 |
| 3 | `Методы очистки шахтных вод.docx` | official-004 |

Дождаться завершения ingestion (уведомление «Обработка документа завершена» для каждого).

### Шаг 2 — задать вопросы в `/chat` (логин `researcher`)

**После файла 1** (`official-002`):

> Какие технические решения применяются для организации циркуляции католита при электроэкстракции никеля и какая оптимальная скорость потока указана в источниках?

**После файла 2** (`official-003`):

> Какие эксперименты и публикации за последние 5 лет описывают распределение Au, Ag и МПГ между медным или никелевым штейном и шлаком?

**После файла 3** (`official-004`):

> Какие способы закачки шахтных вод в глубокие горизонты применяются в России и за рубежом и какие технико-экономические показатели указаны для них?

### Шаг 3 — что показать жюри

- [ ] Ответ содержит кликабельные источники (`SourceSpan`) из загруженного docx
- [ ] Переключение RU ↔ EN в шапке
- [ ] Экспорт ответа (JSON / MD)
- [ ] `/search` — результаты по ключевым словам («никель», «Au», «шахтные воды»)
- [ ] `/strategic/coverage` под `manager` / `manager`

Полный список official-вопросов: `demo/official_questions.md`, `eval/gold_questions.json` (id `official-001` … `official-004`).

---

## Полезные ссылки

| Документ | Содержание |
|----------|------------|
| `infra/deploy/OPERATOR.md` | Подробный runbook оператора |
| `demo/demo_script.md` | Расширенный сценарий демо |
| `Makefile` | `make cloud-up`, `make cloud-verify`, `make cloud-down-v` |
