# Hackathon demo script — Научный Клубок

Сквозной сценарий для жюри и оператора стенда. Покрывает чат, сессии, upload, nginx-маршрутизацию, i18n и аналитику.

## 0. Предусловия

| Параметр | Локальный dev | Cloud HTTP |
|----------|---------------|------------|
| URL UI | http://localhost | `PUBLIC_URL` из `.env` |
| API | http://localhost/api | `{PUBLIC_URL}/api` |
| Корпус | `demo/seed_data/yandex_disk_corpus/` | тот же каталог на VM |
| LLM | `YANDEX_API_KEY` + `YANDEX_FOLDER_ID` в `.env` | обязательно для live-ответов |

Учётные записи после `auth-seed-users`:

| Роль | Логин | Пароль по умолчанию |
|------|-------|---------------------|
| admin | `admin` | `admin123` |
| researcher | `researcher` | `researcher123` |
| manager | `director` | `director123` |

## 1. Поднятие стенда

### Локально (dev)

```bash
make reset-demo
```

Пересоздаёт volumes, поднимает стек, создаёт пользователей и через публичный `/api`:

1. загружает и активирует ZIP справочников;
2. загружает файлы корпуса (если каталог не пуст);
3. ждёт завершения ingestion task.

Скрипт не обращается напрямую к Knowledge, Retrieval, Neo4j или Qdrant.

### Cloud HTTP

```bash
make cloud-up
make cloud-verify
```

Для корпуса > 200 MB — `scripts/seed_corpus_batches.py` (см. `infra/deploy/OPERATOR.md`).

## 2. Автоматические проверки перед демо

```bash
make test
make test-cloud-nginx
make lint
cd ui && npm ci && npm test && npm run build:e2e && npm run test:e2e
python eval/demo_quality_gate.py
```

E2E со стеком (опционально):

```bash
make up
RUN_E2E=1 python -m pytest tests/e2e -q
cd ui && RUN_UI_E2E=1 npm run test:e2e:stack
```

Официальные вопросы (после seed и live LLM):

```bash
export EVAL_AUTH_TOKEN="$(curl -s http://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"admin","password":"admin123"}' | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')"
make eval
```

Acceptance: для всех четырёх official-вопросов из `eval/gold_questions.json` ответ содержит `SourceSpan` из реального корпуса.

## 3. Nginx и периметр

Публичные маршруты (cloud HTTP, `nginx.cloud.http.conf`):

- `/` → UI
- `/api/` → gateway
- `/api/auth/` → auth_audit
- `/.well-known/jwks.json` → auth_audit
- `/health` → gateway health
- `/grafana/` → Grafana (basic auth)

Закрытые префиксы (должны отдавать **404** снаружи):

- `/orchestrator`, `/ingestion`, `/knowledge`, `/retrieval`, `/model`

Проверка:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/model/health    # ожидается 404
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/api/health     # ожидается 200
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1/api/documents/upload  # 401 без токена
```

Лимит upload: `client_max_body_size 200M` (nginx) = `UPLOAD_LIMIT_BYTES=209715200` (gateway/ingestion).

## 4. UI journeys (живое демо, ~15 мин)

Войти как **researcher** / **researcher123**, затем при необходимости переключить роль через admin.

### 4.1 Вход и i18n

1. Открыть `/login`, войти.
2. В шапке переключить **RU ↔ EN** — подписи вкладок и кнопок меняются без перезагрузки.
3. Убедиться, что после входа редирект на `/chat`.

### 4.2 Чат и сессии

1. `/chat` — боковая панель «История чатов».
2. **Новый чат** → сессия «Новый запрос» в списке; пустой черновик не дублируется при повторном клике.
3. Задать official-вопрос, например:
   > Какие методы обессоливания воды подходят для обогатительной фабрики при составе воды: сульфаты, хлориды, Ca, Mg, Na по 200-300 мг/л, если требуемый сухой остаток не более 1000 мг/дм3?
4. Дождаться ответа: фазы retrieval → synthesis → citations; кликабельные источники.
5. Переключить сессию в sidebar — история сообщений подгружается.
6. **Экспорт**: кнопки «Скачать JSON» и «Скачать MD» активны; JSON-LD — disabled (ожидаемо).

### 4.3 Чат с вложением

1. В поле ввода прикрепить PDF.
2. Отправить без текста — система ждёт завершения ingestion, затем задаёт вопрос «Что содержится в прикреплённых документах?».
3. Убедиться, что ответ ссылается на загруженный документ.

### 4.4 Upload

1. `/upload` — drag-and-drop или выбор файла.
2. **Загрузить** → блок «Этапы обработки» (parse → extract → index).
3. Колокольчик уведомлений → «Обработка документа завершена» → клик открывает source viewer.

### 4.5 Аналитика

Войти как **director** / **director123**:

1. `/strategic/coverage` — матрица покрытия направлений; экспорт PDF.
2. `/strategic/quality` — метрики качества ответов (citation coverage, latency).
3. `/admin/stats` (admin) — сводка документов, claims, кандидатов.

### 4.6 Дополнительные сценарии (по времени)

| # | Маршрут | Действие |
|---|---------|----------|
| 1 | `/profile` | Сохранить интересы |
| 2 | `/review` | Подтвердить кандидата, открыть источник |
| 3 | `/search` | Фильтры geo + год |
| 4 | `/admin` | Активировать словарь, сохранить роли |
| 5 | `/admin/audit` | Фильтр по `document_exported` |
| 6 | `/graph` | Локальный подграф вокруг сущности |

## 5. Offline UI smoke (без стека)

```bash
cd ui
npm run build:e2e
npm run preview:e2e &
npm run test:e2e
```

Покрывает сценарии 1–10 из `ui/e2e/no-live-scenarios.spec.js` с mock API.

## 6. Типичные сбои

| Симптом | Решение |
|---------|---------|
| 413 при upload | корпус > 200 MB — `seed_corpus_batches.py` |
| Пустой поиск | корпус не загружен; `make reset-demo` или batch seed |
| `/model` доступен снаружи | устаревший nginx; `docker compose ... up -d nginx` |
| Ответ без источников | проверить LLM keys, ingestion status, active dictionary |
| Mock-режим в prod | `VITE_USE_MOCK=false` в сборке UI |

## 7. Чеклист перед сдачей

- [ ] `make test` — green
- [ ] `make test-cloud-nginx` — green
- [ ] `cd ui && npm test` — green
- [ ] `./scripts/cloud_verify.sh` — OK (cloud)
- [ ] Четыре official-вопроса с SourceSpan (live eval)
- [ ] Demo script пройден оператором один раз end-to-end
