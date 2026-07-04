# Сквозной MVP-прогон backend

## Подготовка

Реальный корпус размещается в `demo/seed_data/yandex_disk_corpus/`. Синтетический `mvp_normalized_documents.json` не используется для MVP acceptance.

## Чистый запуск

```bash
make reset-demo
```

Команда пересоздаёт локальные volumes, поднимает стек, создаёт пользователей и через публичный `/api` выполняет:

1. загрузку и активацию версионного ZIP-пакета справочников;
2. загрузку исходных файлов корпуса;
3. ожидание завершения ingestion task.

Скрипт не обращается напрямую к Knowledge, Retrieval, Neo4j или Qdrant.

## Проверка официальных вопросов

```bash
export EVAL_AUTH_TOKEN="<access_token>"
make eval
```

Acceptance считается успешным только при наличии доступных `SourceSpan` из реального корпуса для всех четырёх вопросов из `eval/gold_questions.json`.
