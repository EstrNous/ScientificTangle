# Demo script: seed, eval, official questions

Скрипт для ручного прогона MVP на поднятом стеке. Источник вопросов: `eval/gold_questions.json` (official-001…004), не `demo/official_questions.md`.

## 1. Поднять стек

```bash
docker compose up -d
```

Проверка health:

```bash
RUN_E2E=1 python scripts/run_tests.py
```

## 2. Seed retrieval index

```bash
python scripts/seed_demo.py --retrieval-url http://localhost:8005
```

Ожидаемый ответ содержит `vector_write.records_count` > 0.

## 3. Auth token

Зарегистрировать пользователя или залогиниться через auth_audit, получить Bearer token.

```bash
export EVAL_AUTH_TOKEN="<access_token>"
export EVAL_SERVICE_URL="http://localhost:8000/api"
```

## 4. Eval runner

```bash
make eval
```

или:

```bash
python eval/run_eval.py
```

Отчёты: `eval/reports/latest.json`, `eval/reports/latest.md`.

## 5. Official questions

4 MVP-вопроса в `eval/gold_questions.json` с `split: mvp`:

- official-001 — обессоливание воды
- official-002 — флотация никеля
- official-003 — ПГЭ
- official-004 — плавка

Нормализованные документы для demo: `demo/seed_data/mvp_normalized_documents.json`.

## 6. Live Yandex smoke (опционально)

```bash
make eval-yandex-live
```

Требует `YANDEX_API_KEY`, `YANDEX_FOLDER_ID` и поднятый стек.
