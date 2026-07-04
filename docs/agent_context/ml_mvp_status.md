# Статус ML MVP

**Обновлено:** 2026-07-04

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
- Internal integration slice: ingestion normalize, knowledge extraction handoff, retrieval query, orchestrator query run, gateway query proxy.
- Live Yandex smoke test без секретов в коде; тест пропускается, если `YANDEX_API_KEY` и `YANDEX_FOLDER_ID` не настроены.
- `eval/run_eval.py` умеет прогонять `/api/query` с auth token из env, нормализовать raw eval documents через ingestion `/v1/documents/normalize` и писать dashboard-ready JSON/Markdown.
- Alias mining получил локальный embedding-similarity слой без привязки к Qdrant.
- Conflict detection усилен на ML-стороне: сравнивает только сопоставимые артефакты с учетом свойства, материала, процесса, оборудования, географии, времени, условий и единиц.
- Gap suggestions проверяет покрытие numeric, geo, time, source type и entity constraints подтвержденным EvidenceBundle и снижает false positive gaps.
- Notification matching усилен metadata-aware scoring и штрафами для candidate/low-confidence artifacts.
- JSON-LD enrichment расширен provenance-полями QueryIR, EvidenceBundle, SourceSpan, gaps/conflicts и не экспортирует candidates как facts.
- Eval/perf отчеты получили versioned `eval/reports/*` artifacts, access leak и JSON-LD provenance метрики.
- Eval regression получил pinned input manifest `eval/pinned_demo_artifact.json`, suite-разбиение `eval/regression_suites.json` и comparison report в `eval/run_eval.py`.

## Закрыто в интеграции (не только model)

- Запись structured extraction в Neo4j через `Neo4jKnowledgeAdapter` (knowledge service).
- Индексация source spans и table rows в Qdrant `st_evidence_v1` (retrieval service).
- Query pipeline: query-ir → hybrid retrieval (dense + lexical + table + graph) → fusion → access revalidation → rerank → gaps → subgraph → answer synthesis (orchestrator).
- Qdrant retrieval applies geo/numeric/time/source filters before rerank: units/ranges, geo bucket/country and `published_year`.
- Official MVP questions have reviewed `expected_source_span_ids`; offline gate fails if any `official-*` expected source span set is empty.

## Что ещё не закрыто до полного ML/MVP

- Нет UI evaluation dashboard; доступны Markdown/JSON eval reports.
- Нет зафиксированного командного live eval artifact с реальными ответами на общем demo corpus; E4 закрепил только входы и правила regression comparison.
- Export service wiring: MVP Markdown/JSON идёт через orchestrator/gateway; JSON-LD endpoint готов в model, HTTP export service — reserved boundary/заглушка.
- Notification service wiring: ML matching готов, HTTP notification service — заглушка.

## Top-1 ML backlog

- Live eval artifact на общем demo corpus с поднятым стеком и Yandex secrets.
- Gap precision на реальном корпусе после seeded official/hybrid report.
- Access filtering correctness в связке с backend/Auth/retrieval через live eval gate.
- JSON-LD enrichment в финальном export service.
- Notification service wiring.
- p50/p95 latency по живому стэку, а не только локальная проверка отчета.

## VL/OCR позиция

Vision-language модель из `.env` не является обязательным MVP-путём. Она нужна только для сканов, изображений, слайдов без текстового слоя, графиков и таблиц как картинок. Если PDF/DOCX/PPTX уже дают текст и таблицы, model service должен использовать текстовый путь и не блокировать MVP на VL/OCR.
