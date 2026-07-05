# E6 Backend/ML-2: perf и reliability query path

**Дата:** 2026-07-04  
**Ветка:** `feat/top1-e6-bm2-perf-reliability`  
**Scope:** smoke/perf проверки query path, degraded mode, fallback, timeout и feature flags без запуска реальных моделей.

## Результат

| Проверка | Статус | Комментарий |
|---|---|---|
| Default flow (`top1_scientific_query_enabled=false`) | pass | `pipeline_mode=legacy`, synthesis path без scientific enrichment |
| Explicit filter `top1_scientific_query=false` | pass | Перекрывает env-флаг, legacy сохраняется |
| Gateway flag injection (run + stream) | pass | Флаг добавляется только при enabled и отсутствии явного filters-ключа |
| Graph exact fallback | pass | `knowledge_timeout` → warning + completed run |
| Verification fallback | pass | `model_timeout` на `/v1/conflicts/detect` → warning + completed run |
| Retrieval timeout | pass | `504 retrieval_timeout`, run помечен failed, `latency_ms` записан |
| Gateway/Orchestrator timeout mapping | pass | `504 orchestrator_timeout` / `retrieval_timeout` |
| Empty evidence degraded | pass | Пропуск synthesis, warning `insufficient_accessible_evidence` |
| Stream error phase | pass | SSE `phase=error` при downstream failure, run failed в PG |
| Stream degraded terminal | pass | `terminal_phase=degraded` при пустом evidence |
| Automatic retry downstream | n/a | Retry не реализован — fail-fast по дизайну |
| Live perf smoke (`scripts/perf_smoke.py`) | deferred | Требует seeded stack и разрешение организаторов |

**Итог:** query path готов к demo с точки зрения reliability: fallback не рвёт запрос, default flow не затронут выключенными feature flags, таймауты маппятся в 504 с персистентным failed run.

## Feature flags

| Флаг | Default | Поведение при default |
|---|---|---|
| `top1_scientific_query_enabled` | `false` | Legacy pipeline, gateway не инжектит filter |
| `top1_live_stream_enabled` | `false` | `/query/stream` → `404 stream_disabled` |

Включение `top1_scientific_query_enabled` не ломает override через `filters.top1_scientific_query=false`.

## Артефакты

- `scripts/query_reliability.py` — `build_reliability_report`, `classify_query_outcome`
- `tests/performance/test_query_reliability_report.py` — схема `ml_reliability_report.v1`
- `services/orchestrator/tests/test_query_reliability.py` — orchestrator fallback/timeout/stream
- `services/gateway/tests/test_query_reliability.py` — gateway flags и timeout mapping
- `scripts/perf_smoke.py` — live latency smoke (без изменений, deferred)

## Локальные проверки (без live models)

```text
python -m pytest tests/performance/test_perf_smoke.py tests/performance/test_query_reliability_report.py -q
PYTHONPATH=services/orchestrator:. python -m pytest services/orchestrator/tests/test_query_reliability.py -q
PYTHONPATH=services/gateway:. python -m pytest services/gateway/tests/test_query_reliability.py -q
git diff --check
```

## Известные ограничения

1. Live `perf_smoke` и `eval/run_eval.py` не запускались — организаторы запретили реальные модели.
2. Automatic retry для transient downstream errors отсутствует; при необходимости — отдельная карточка.
3. Stream endpoint остаётся за `top1_live_stream_enabled`; non-streaming `/query/run` — основной demo path.

## Dependency

E5 gate смержен (`origin/dev` @ `0165da4`: PR #60–#62). Blocker'ов на несмёрженные PR других ролей нет.
