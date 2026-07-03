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
- Schema-aware LLM extraction подключен как основной путь при настроенном Yandex, с deterministic fallback и обязательной проверкой `SourceSpan`.
- Model routing разведен по задачам: long-context для structured extraction, fast model для Query IR, multilingual model для alias/user-interest задач, chat model для answer synthesis.
- Alias mining расширен: seed aliases, русско-английские соответствия, транслитерация, нормализация дефисов/формул и fuzzy matching через `thefuzz`.
- In-memory model cache добавлен для embeddings, Query IR и structured extraction.
- Добавлен тонкий internal integration slice: ingestion normalize, knowledge extraction handoff, retrieval query, orchestrator query run, gateway query proxy.
- Добавлен live Yandex smoke test без секретов в коде; тест пропускается, если `YANDEX_API_KEY` и `YANDEX_FOLDER_ID` не настроены.
- `eval/run_eval.py` умеет прогонять `/api/query` с auth token из env, нормализовать raw eval documents через ingestion `/v1/documents/normalize` и писать dashboard-ready JSON/Markdown.
- Alias mining получил локальный embedding-similarity слой без привязки к Qdrant.

## Что ещё не закрыто до полного ML MVP

- Нет полноценной записи model outputs в Knowledge/Neo4j: графовая часть остается задачей отдельной DB/graph-интеграции. Qdrant MVP slice добавлен в Retrieval через `st_evidence_v1`, demo seed и live Yandex targets.
- Нет UI/evaluation dashboard; доступны Markdown/JSON eval reports.
- Нет зафиксированного командного live eval artifact на общем demo corpus: runner готов, но результат зависит от поднятого стэка, auth token и предоставленных raw/normalized documents.

## Top-1 ML backlog

- Полный conflict detection с учетом условий эксперимента, материала, процесса, географии и единиц.
- Gap precision на реальном корпусе после end-to-end retrieval.
- Access filtering correctness в связке с backend/Auth, не внутри model service.
- JSON-LD export enrichment в финальном export service.
- Notification matching в связке с user interests и новыми источниками.
- p50/p95 latency по живому стэку, а не только eval script.

## VL/OCR позиция

Vision-language модель из `.env` не является обязательным MVP-путём. Она нужна только для сканов, изображений, слайдов без текстового слоя, графиков и таблиц как картинок. Если PDF/DOCX/PPTX уже дают текст и таблицы, model service должен использовать текстовый путь и не блокировать MVP на VL/OCR.
