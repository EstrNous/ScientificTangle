# Статус ML MVP

## Закрыто в model service

- Evidence-first контракты model service: confirmed/candidate layers, reason codes, unsupported warnings.
- Запрет confirmed artifacts без `SourceSpan`.
- Endpoints `services/model/app/api/v1.py`: embeddings, structured extraction, Query IR, reranking/scoring, answer synthesis, conflict detection, gap suggestions, user interest extraction, notification matching, JSON-LD enrichment, prompt registry, schema registry, model status.
- Yandex provider подключается через `.env`: `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, chat model, embedding doc/query models, timeout, temperature, max tokens.
- Deterministic degraded fallback работает явно, без скрытого хардкода demo-ответов.
- Версионированные prompts и JSON Schema registry лежат в репозитории.
- Eval dataset содержит 4 official MVP questions и 12 corpus-derived regression questions из публичного корпуса.
- Eval script считает MVP/top-1 метрики и пишет Markdown/JSON отчёты.

## Что ещё не закрыто до полного ML MVP

- Schema-aware LLM extraction для entities, relations, measurements, aliases и claims ещё не является основным путём; сейчас основной путь rule-based с Yandex fallback только для embeddings и answer synthesis.
- Model routing по `YANDEX_FAST_MODEL`, `YANDEX_LONG_CONTEXT_MODEL` и `YANDEX_MULTILINGUAL_MODEL` задан в config, но не полностью разведен по задачам extraction, Query IR и alias mining.
- Alias mining не добит до полного набора: русско-английские соответствия, транслитерация, fuzzy matching, embedding similarity и seed dictionaries пока частично покрыты.
- Нет интеграционного ML-прогона через реальные `NormalizedDocument` из ingestion service; corpus-derived gold собран dev-only пайплайном из временных normalized artifacts.
- Нет проверки live Yandex API в CI/smoke без секретов; локально `/v1/status` показывает готовность по факту заполненного `.env`.
- Нет model cache для повторных embeddings, Query IR и structured extraction.
- Нет end-to-end связки model outputs с Knowledge/Neo4j и Retrieval/Qdrant.
- Нет UI/evaluation dashboard; доступны Markdown/JSON eval reports.

## Top-1 ML backlog

- Полный conflict detection с учетом условий эксперимента, материала, процесса, географии и единиц.
- Gap precision на реальном корпусе после end-to-end retrieval.
- Access filtering correctness в связке с backend/Auth, не внутри model service.
- JSON-LD export enrichment в финальном export service.
- Notification matching в связке с user interests и новыми источниками.
- p50/p95 latency по живому стэку, а не только eval script.

## VL/OCR позиция

Vision-language модель из `.env` не является обязательным MVP-путём. Она нужна только для сканов, изображений, слайдов без текстового слоя, графиков и таблиц как картинок. Если PDF/DOCX/PPTX уже дают текст и таблицы, model service должен использовать текстовый путь и не блокировать MVP на VL/OCR.
